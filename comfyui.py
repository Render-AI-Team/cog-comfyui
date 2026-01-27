import os
import urllib.request
import subprocess
import threading
import time
import json
import urllib
import uuid
import websocket
import random
import requests
import shutil
import glob
import importlib
import sys
import json as pyjson
import custom_node_helpers as helpers
from cog import Path
from node import Node
from weights_downloader import WeightsDownloader
from urllib.error import URLError


class ComfyUI:
    def __init__(self, server_address):
        self.weights_downloader = WeightsDownloader()
        self.server_address = server_address
        self.server_process = None

    def start_server(self, output_directory, input_directory):
        self.input_directory = input_directory
        self.output_directory = output_directory

        self.apply_helper_methods("prepare", weights_downloader=self.weights_downloader)

        start_time = time.time()
        server_thread = threading.Thread(
            target=self.run_server, args=(output_directory, input_directory)
        )
        server_thread.start()
        
        # Wait for HTTP server to respond
        while not self.is_server_running():
            if time.time() - start_time > 60:
                raise TimeoutError("Server did not start within 60 seconds")
            time.sleep(0.5)

        # Wait for node mappings to be loaded (custom nodes available)
        node_load_start = time.time()
        while not self.are_nodes_loaded():
            if time.time() - node_load_start > 120:
                raise TimeoutError("ComfyUI nodes did not load within 120 seconds")
            time.sleep(0.5)

        elapsed_time = time.time() - start_time
        print(f"Server started in {elapsed_time:.2f} seconds")

    def run_server(self, output_directory, input_directory):
        # Force CPU mode so ComfyUI runs on systems without CUDA/MPS
        command = (
            f"python ./ComfyUI/main.py --cpu --disable-xformers "
            f"--output-directory {output_directory} --input-directory {input_directory} --disable-metadata"
        )

        """
        We need to capture the stdout and stderr from the server process
        so that we can print the logs to the console. If we don't do this
        then at the point where ComfyUI attempts to print it will throw a
        broken pipe error. This only happens from cog v0.9.13 onwards.
        """
        self.server_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        def print_stdout():
            for stdout_line in iter(self.server_process.stdout.readline, ""):
                print(f"[ComfyUI] {stdout_line.strip()}")

        stdout_thread = threading.Thread(target=print_stdout)
        stdout_thread.start()

        for stderr_line in iter(self.server_process.stderr.readline, ""):
            print(f"[ComfyUI] {stderr_line.strip()}")

    def stop_server(self):
        if self.server_process and self.server_process.poll() is None:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=15)
            except Exception:
                try:
                    self.server_process.kill()
                except Exception:
                    pass
        self.server_process = None

    def is_server_running(self):
        try:
            with urllib.request.urlopen(
                "http://{}/history/{}".format(self.server_address, "123")
            ) as response:
                return response.status == 200
        except URLError:
            return False

    def are_nodes_loaded(self):
        """Check if ComfyUI has finished loading node mappings."""
        try:
            with urllib.request.urlopen(
                f"http://{self.server_address}/object_info"
            ) as response:
                if response.status == 200:
                    # Successfully retrieved node info - nodes are loaded
                    return True
        except (URLError, urllib.error.HTTPError):
            return False
        return False

    def apply_helper_methods(self, method_name, *args, **kwargs):
        # Dynamically applies a method from helpers module with given args.
        # Example usage: self.apply_helper_methods("add_weights", weights_to_download, node)
        for module_name in dir(helpers):
            module = getattr(helpers, module_name)
            method = getattr(module, method_name, None)
            if callable(method):
                method(*args, **kwargs)

    def extract_weights_from_multiple_workflows(self, workflows_data):
        """Extract weights from multiple workflows (array or object format).
        
        Args:
            workflows_data: Either a list of workflows or a dict of name->workflow mappings
            
        Returns:
            Set of all unique weights across all workflows
        """
        all_weights = set()
        
        if isinstance(workflows_data, list):
            for item in workflows_data:
                if isinstance(item, dict):
                    # Check if item has a "workflow" key or if it IS a workflow
                    if "workflow" in item:
                        weights = self.extract_required_weights(item["workflow"])
                    else:
                        weights = self.extract_required_weights(item)
                    all_weights.update(weights)
        elif isinstance(workflows_data, dict):
            if "workflows" in workflows_data:
                # Explicitly named workflows list
                for item in workflows_data["workflows"]:
                    if isinstance(item, dict):
                        if "workflow" in item:
                            weights = self.extract_required_weights(item["workflow"])
                        else:
                            weights = self.extract_required_weights(item)
                        all_weights.update(weights)
            else:
                # Object with named workflows
                for name, workflow in workflows_data.items():
                    if isinstance(workflow, dict) and not name.startswith("_"):
                        weights = self.extract_required_weights(workflow)
                        all_weights.update(weights)
        
        return all_weights

    def extract_required_weights(self, workflow):
        """Extract all weight/model file requirements from a workflow.
        
        Returns a list of all model files that the workflow needs.
        This is used for preloading weights during setup.
        """
        required_weights = []
        supported_extensions = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".onnx")
        
        for node in workflow.values():
            class_type = node.get("class_type")
            inputs = node.get("inputs", {})
            
            # Checkpoint loaders
            if class_type in ["CheckpointLoaderSimple", "CheckpointLoader", "unCLIPCheckpointLoader", "ImageOnlyCheckpointLoader"]:
                ckpt_name = inputs.get("ckpt_name")
                if ckpt_name and ckpt_name.endswith(supported_extensions):
                    required_weights.append(ckpt_name)
            
            # Split-model loaders
            elif class_type == "UNETLoader":
                unet_name = inputs.get("unet_name")
                if unet_name and unet_name.endswith(supported_extensions):
                    required_weights.append(unet_name)
            
            elif class_type == "CLIPLoader":
                clip_name = inputs.get("clip_name")
                if clip_name and clip_name.endswith(supported_extensions):
                    required_weights.append(clip_name)
            
            elif class_type == "DualCLIPLoader":
                for key in ["clip_name1", "clip_name2"]:
                    clip_name = inputs.get(key)
                    if clip_name and clip_name.endswith(supported_extensions):
                        required_weights.append(clip_name)
            
            elif class_type == "TripleCLIPLoader":
                for key in ["clip_name1", "clip_name2", "clip_name3"]:
                    clip_name = inputs.get(key)
                    if clip_name and clip_name.endswith(supported_extensions):
                        required_weights.append(clip_name)
            
            elif class_type == "QuadrupleCLIPLoader":
                for key in ["clip_name1", "clip_name2", "clip_name3", "clip_name4"]:
                    clip_name = inputs.get(key)
                    if clip_name and clip_name.endswith(supported_extensions):
                        required_weights.append(clip_name)
            
            elif class_type == "VAELoader":
                vae_name = inputs.get("vae_name")
                if vae_name and vae_name.endswith(supported_extensions):
                    required_weights.append(vae_name)
            
            elif class_type in ["ControlNetLoader", "DiffControlNetLoader"]:
                control_net_name = inputs.get("control_net_name")
                if control_net_name and control_net_name.endswith(supported_extensions):
                    required_weights.append(control_net_name)
            
            elif class_type == "CLIPVisionLoader":
                clip_name = inputs.get("clip_name")
                if clip_name and clip_name.endswith(supported_extensions):
                    required_weights.append(clip_name)
            
            elif class_type == "StyleModelLoader":
                style_model_name = inputs.get("style_model_name")
                if style_model_name and style_model_name.endswith(supported_extensions):
                    required_weights.append(style_model_name)
            
            elif class_type == "GLIGENLoader":
                gligen_name = inputs.get("gligen_name")
                if gligen_name and gligen_name.endswith(supported_extensions):
                    required_weights.append(gligen_name)
            
            elif class_type == "UpscaleModelLoader":
                model_name = inputs.get("model_name")
                if model_name and model_name.endswith(supported_extensions):
                    required_weights.append(model_name)
            
            elif class_type == "HypernetworkLoader":
                hypernetwork_name = inputs.get("hypernetwork_name")
                if hypernetwork_name and hypernetwork_name.endswith(supported_extensions):
                    required_weights.append(hypernetwork_name)
            
            elif class_type in ["LoraLoader", "LoraLoaderModelOnly"]:
                lora_name = inputs.get("lora_name")
                if lora_name and lora_name.endswith(supported_extensions):
                    required_weights.append(lora_name)
        
        # Return unique list of weights
        return list(set(required_weights))

    def validate_weights_from_multiple_workflows(self, workflows_data, skip_check=False):
        """Validate weights exist for multiple workflows.
        
        Returns tuple of (all_exist: bool, missing_weights: list)
        """
        if skip_check:
            return True, []
        
        required_weights = self.extract_weights_from_multiple_workflows(workflows_data)
        missing_weights = []
        
        for weight in required_weights:
            weight_canonical = self.weights_downloader.get_canonical_weight_str(weight)
            if weight_canonical in self.weights_downloader.weights_map:
                dest_info = self.weights_downloader.weights_map[weight_canonical]
                if isinstance(dest_info, list):
                    exists = any(
                        self.weights_downloader.check_if_file_exists(weight_canonical, d["dest"])
                        for d in dest_info
                    )
                else:
                    exists = self.weights_downloader.check_if_file_exists(
                        weight_canonical, dest_info["dest"]
                    )
                
                if not exists:
                    missing_weights.append(weight_canonical)
            else:
                missing_weights.append(weight)
        
        return len(missing_weights) == 0, missing_weights

    def validate_weights_exist(self, workflow, skip_check=False):
        """Validate that all required weights exist locally.
        
        Returns tuple of (all_exist: bool, missing_weights: list)
        This is a fast check that doesn't download anything.
        """
        if skip_check:
            return True, []
        
        required_weights = self.extract_required_weights(workflow)
        missing_weights = []
        
        for weight in required_weights:
            weight_canonical = self.weights_downloader.get_canonical_weight_str(weight)
            if weight_canonical in self.weights_downloader.weights_map:
                dest_info = self.weights_downloader.weights_map[weight_canonical]
                if isinstance(dest_info, list):
                    # Check if any of the destinations have the file
                    exists = any(
                        self.weights_downloader.check_if_file_exists(weight_canonical, d["dest"])
                        for d in dest_info
                    )
                else:
                    exists = self.weights_downloader.check_if_file_exists(
                        weight_canonical, dest_info["dest"]
                    )
                
                if not exists:
                    missing_weights.append(weight_canonical)
            else:
                # Weight not in manifest - might be a custom weight
                missing_weights.append(weight)
        
        return len(missing_weights) == 0, missing_weights

    def handle_weights(self, workflow, weights_to_download=None, skip_check=False, download_all_model_inputs=False):
        if weights_to_download is None:
            weights_to_download = []

        print("Checking weights")

        # Always normalize LoraLoader URL nodes so they still function when skipping checks
        self.convert_lora_loader_nodes(workflow)

        # Always download model files - they're validated by ComfyUI and must exist
        models_to_download = []
        for node in workflow.values():
            class_type = node.get("class_type")
            inputs = node.get("inputs", {})
            
            # Checkpoint loaders
            if class_type in ["CheckpointLoaderSimple", "CheckpointLoader", "unCLIPCheckpointLoader", "ImageOnlyCheckpointLoader"]:
                ckpt_name = inputs.get("ckpt_name")
                if ckpt_name and ckpt_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(ckpt_name)
            
            # Split-model loaders (Flux, SD3, Mochi, Wan, etc.)
            elif class_type == "UNETLoader":
                unet_name = inputs.get("unet_name")
                if unet_name and unet_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(unet_name)
            
            elif class_type == "CLIPLoader":
                clip_name = inputs.get("clip_name")
                if clip_name and clip_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(clip_name)
            
            elif class_type == "DualCLIPLoader":
                for key in ["clip_name1", "clip_name2"]:
                    clip_name = inputs.get(key)
                    if clip_name and clip_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                        models_to_download.append(clip_name)
            
            elif class_type == "TripleCLIPLoader":
                for key in ["clip_name1", "clip_name2", "clip_name3"]:
                    clip_name = inputs.get(key)
                    if clip_name and clip_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                        models_to_download.append(clip_name)
            
            elif class_type == "QuadrupleCLIPLoader":
                for key in ["clip_name1", "clip_name2", "clip_name3", "clip_name4"]:
                    clip_name = inputs.get(key)
                    if clip_name and clip_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                        models_to_download.append(clip_name)
            
            elif class_type == "VAELoader":
                vae_name = inputs.get("vae_name")
                if vae_name and vae_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(vae_name)
            
            # ControlNet loaders
            elif class_type in ["ControlNetLoader", "DiffControlNetLoader"]:
                control_net_name = inputs.get("control_net_name")
                if control_net_name and control_net_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(control_net_name)
            
            # Other model loaders
            elif class_type == "CLIPVisionLoader":
                clip_name = inputs.get("clip_name")
                if clip_name and clip_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(clip_name)
            
            elif class_type == "StyleModelLoader":
                style_model_name = inputs.get("style_model_name")
                if style_model_name and style_model_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(style_model_name)
            
            elif class_type == "GLIGENLoader":
                gligen_name = inputs.get("gligen_name")
                if gligen_name and gligen_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(gligen_name)
            
            elif class_type == "UpscaleModelLoader":
                model_name = inputs.get("model_name")
                if model_name and model_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(model_name)
            
            elif class_type == "HypernetworkLoader":
                hypernetwork_name = inputs.get("hypernetwork_name")
                if hypernetwork_name and hypernetwork_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(hypernetwork_name)

            # LoRA loaders (ensure LoRAs also download automatically)
            elif class_type in ["LoraLoader", "LoraLoaderModelOnly"]:
                lora_name = inputs.get("lora_name")
                if lora_name and lora_name.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                    models_to_download.append(lora_name)
        
        if models_to_download:
            print(f"Downloading {len(models_to_download)} model file(s) (always required for validation)")
            for model in set(models_to_download):
                self.weights_downloader.download_weights(model)

        if skip_check:
            print("⚠️  Skipping additional weight checks (LoRAs, embeddings, etc.)")
            # If download_all_model_inputs is enabled, still scan for and download any model files
            if download_all_model_inputs:
                print("✓ download_all_model_inputs enabled: scanning workflow for all model file inputs...")
                weights_to_download = []
                embeddings = self.weights_downloader.get_weights_by_type("EMBEDDINGS")
                embedding_to_fullname = {emb.split(".")[0]: emb for emb in embeddings}
                weights_filetypes = self.weights_downloader.supported_filetypes
                
                for node in workflow.values():
                    if node.get("class_type") in ["HFHubLoraLoader", "LoraLoaderFromURL"]:
                        continue
                    
                    for input_key, input_value in node.get("inputs", {}).items():
                        if isinstance(input_value, str):
                            # Check for embeddings by name
                            if any(key in input_value for key in embedding_to_fullname):
                                weights_to_download.extend(
                                    embedding_to_fullname[key]
                                    for key in embedding_to_fullname
                                    if key in input_value
                                )
                            # Check for any model file by extension
                            elif any(input_value.endswith(ft) for ft in weights_filetypes):
                                weight_str = self.weights_downloader.get_canonical_weight_str(input_value)
                                if weight_str != input_value:
                                    print(f"Converting model synonym {input_value} to {weight_str}")
                                    node["inputs"][input_key] = weight_str
                                weights_to_download.append(weight_str)
                
                weights_to_download = list(set(weights_to_download))
                if weights_to_download:
                    print(f"Downloading {len(weights_to_download)} additional file(s) (embeddings, custom inputs, etc.)")
                    for weight in weights_to_download:
                        self.weights_downloader.download_weights(weight)
            
            print("=====================================")
            return
            
        embeddings = self.weights_downloader.get_weights_by_type("EMBEDDINGS")
        embedding_to_fullname = {emb.split(".")[0]: emb for emb in embeddings}
        weights_filetypes = self.weights_downloader.supported_filetypes

        for node in workflow.values():
            # Skip HFHubLoraLoader and LoraLoaderFromURL nodes since they handle their own weights
            if node.get("class_type") in ["HFHubLoraLoader", "LoraLoaderFromURL"]:
                continue

            self.apply_helper_methods("add_weights", weights_to_download, Node(node))

            for input_key, input_value in node["inputs"].items():
                if isinstance(input_value, str):
                    if any(key in input_value for key in embedding_to_fullname):
                        weights_to_download.extend(
                            embedding_to_fullname[key]
                            for key in embedding_to_fullname
                            if key in input_value
                        )
                    elif any(input_value.endswith(ft) for ft in weights_filetypes):
                        # Sometimes a model will have a number of common filenames
                        weight_str = self.weights_downloader.get_canonical_weight_str(
                            input_value
                        )
                        if weight_str != input_value:
                            print(
                                f"Converting model synonym {input_value} to {weight_str}"
                            )
                            node["inputs"][input_key] = weight_str

                        weights_to_download.append(weight_str)

        weights_to_download = list(set(weights_to_download))

        for weight in weights_to_download:
            self.weights_downloader.download_weights(weight)

        print("====================================")

    def install_custom_nodes_for_workflow(self, workflow, user_node_map=None):
        """Install custom nodes declared in custom_nodes.json and any extras provided via workflow metadata.
        
        Args:
            workflow: Workflow JSON string or dict
            user_node_map: Optional dict mapping node class names to repo URLs (overrides default map)
        """
        try:
            script_path = os.path.join("scripts", "install_custom_nodes.py")
            if os.path.exists(script_path):
                subprocess.run([
                    "python",
                    script_path,
                ], check=True)
            else:
                print("Skipping scripts/install_custom_nodes.py (not included in image)")
        except Exception as e:
            print(f"Warning: custom node install step failed: {e}")

        # Optional: install additional repos specified in workflow extra_data.custom_nodes (list of repo URLs)
        try:
            if isinstance(workflow, str):
                wf_obj = json.loads(workflow)
            else:
                wf_obj = workflow
            extra_repos = (
                wf_obj.get("extra_data", {})
                .get("custom_nodes", [])
                if isinstance(wf_obj, dict)
                else []
            )
            for repo_url in extra_repos:
                if isinstance(repo_url, str) and repo_url.startswith("http"):
                    repo_name = os.path.basename(repo_url.rstrip("/").replace(".git", ""))
                    dest = os.path.join("ComfyUI", "custom_nodes", repo_name)
                    if not os.path.exists(dest):
                        print(f"Cloning extra custom node repo: {repo_url}")
                        subprocess.run(["git", "clone", "--recursive", repo_url, dest], check=True)
        except Exception as e:
            print(f"Warning: extra custom node install step failed: {e}")

        # Install mapped repos for missing classes in the workflow
        try:
            self._install_mapped_missing_nodes(workflow, user_node_map=user_node_map)
        except Exception as e:
            print(f"Warning: mapped custom node install step failed: {e}")

        # Ensure critical runtime pins are restored if any custom node pulled newer numpy/onnxruntime
        self._enforce_runtime_pins()

    def cleanup_custom_nodes(self):
        """Remove custom_nodes content after run to keep environment lean."""
        custom_nodes_dir = os.path.join("ComfyUI", "custom_nodes")
        try:
            for path in glob.glob(os.path.join(custom_nodes_dir, "*")):
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.isfile(path) and path.endswith( (".py", ".json") ):
                    os.remove(path)
        except Exception as e:
            print(f"Warning: custom node cleanup failed: {e}")

    def _extract_class_types(self, workflow):
        classes = set()
        try:
            if isinstance(workflow, str):
                wf_obj = json.loads(workflow)
            else:
                wf_obj = workflow

            if isinstance(wf_obj, dict):
                if "nodes" in wf_obj and isinstance(wf_obj.get("nodes"), list):
                    for node in wf_obj.get("nodes", []):
                        node_type = node.get("type") if isinstance(node, dict) else None
                        if node_type:
                            classes.add(node_type)
                else:
                    for node in wf_obj.values():
                        if isinstance(node, dict):
                            node_type = node.get("class_type")
                            if node_type:
                                classes.add(node_type)
        except Exception:
            pass
        return classes

    def _load_class_repo_map(self):
        class_map_path = "custom_node_class_map.json"
        if os.path.exists(class_map_path):
            try:
                with open(class_map_path, "r") as f:
                    return pyjson.load(f)
            except Exception:
                return {}
        return {}

    def _repo_commit_lookup(self):
        lookup = {}
        try:
            with open("custom_nodes.json", "r") as f:
                entries = pyjson.load(f)
            for entry in entries:
                repo = entry.get("repo")
                commit = entry.get("commit")
                if repo:
                    lookup[repo] = commit
        except Exception:
            pass
        return lookup

    def _clone_repo(self, repo_url, commit=None):
        repo_name = os.path.basename(repo_url.rstrip("/").replace(".git", ""))
        dest = os.path.join("ComfyUI", "custom_nodes", repo_name)
        if os.path.exists(dest):
            return
        print(f"Cloning custom node repo for missing class: {repo_url}")
        subprocess.run(["git", "clone", "--recursive", repo_url, dest], check=True)
        if commit:
            try:
                cwd = os.getcwd()
                os.chdir(dest)
                subprocess.run(["git", "checkout", commit], check=True)
                subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
            finally:
                os.chdir(cwd)

    def _install_mapped_missing_nodes(self, workflow, user_node_map=None):
        class_repo_map = self._load_class_repo_map()
        
        # Merge user-provided mappings (takes precedence)
        if user_node_map:
            print(f"Applying {len(user_node_map)} user-provided node-to-repo mappings")
            class_repo_map.update(user_node_map)
        
        if not class_repo_map:
            return

        # ensure ComfyUI on path to import nodes
        comfy_path = os.path.abspath("ComfyUI")
        if comfy_path not in sys.path:
            sys.path.append(comfy_path)

        try:
            nodes_module = importlib.import_module("nodes")
            available = set(getattr(nodes_module, "NODE_CLASS_MAPPINGS", {}).keys())
        except Exception:
            available = set()

        missing_classes = []
        for cls in self._extract_class_types(workflow):
            if cls not in available:
                missing_classes.append(cls)

        if not missing_classes:
            return

        repo_commit_lookup = self._repo_commit_lookup()
        repos_to_install = set()
        unresolved = []

        for cls in missing_classes:
            repo_url = class_repo_map.get(cls)
            if repo_url:
                # Skip installing base ComfyUI repo as a custom node
                if repo_url.rstrip('/') in ("https://github.com/comfyanonymous/ComfyUI", "https://github.com/Comfy-Org/ComfyUI"):
                    continue
                repos_to_install.add(repo_url)
            else:
                unresolved.append(cls)

        # Install all mapped repos
        if repos_to_install:
            print(f"Installing {len(repos_to_install)} custom node repos for {len(missing_classes)} missing classes...")
            for repo_url in repos_to_install:
                commit = repo_commit_lookup.get(repo_url)
                try:
                    self._clone_repo(repo_url, commit)
                    # Try installing python dependencies if present
                    repo_name = os.path.basename(repo_url.rstrip("/").replace(".git", ""))
                    dest = os.path.join("ComfyUI", "custom_nodes", repo_name)
                    reqs = os.path.join(dest, "requirements.txt")
                    if os.path.exists(reqs):
                        try:
                            subprocess.run(["python", "-m", "pip", "install", "-r", reqs], check=True)
                        except Exception as e:
                            print(f"Warning: failed to install requirements for {repo_name}: {e}")
                except Exception as e:
                    print(f"Warning: failed to clone repo {repo_url}: {e}")

        # Report unresolved nodes (ComfyUI-Manager map is comprehensive, so these are rare)
        if unresolved:
            print(f"⚠️  Warning: {len(unresolved)} node classes could not be resolved to any repo:")
            for cls in unresolved[:10]:  # Show first 10
                print(f"   - {cls}")
            if len(unresolved) > 10:
                print(f"   ... and {len(unresolved) - 10} more")

    def _enforce_runtime_pins(self):
        """Reinstall critical runtime pins from requirements.txt that custom nodes may override."""
        critical_packages = {"numpy", "onnxruntime", "onnxruntime-gpu"}
        pins_to_install = []

        try:
            req_file = "requirements.txt"
            if os.path.exists(req_file):
                with open(req_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Extract package name from spec like "numpy==1.26.4"
                        pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].strip()
                        if pkg_name in critical_packages:
                            pins_to_install.append(line)

            if pins_to_install:
                print(f"Enforcing {len(pins_to_install)} critical runtime pins: {', '.join(pins_to_install)}")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--no-deps", "--force-reinstall", *pins_to_install],
                    check=True,
                )
        except Exception as e:
            print(f"Warning: failed to enforce runtime pins: {e}")

    def is_image_or_video_value(self, value):
        filetypes = [".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm"]
        return isinstance(value, str) and any(
            value.lower().endswith(ft) for ft in filetypes
        )

    def handle_known_unsupported_nodes(self, workflow):
        for node in workflow.values():
            self.apply_helper_methods("check_for_unsupported_nodes", Node(node))

    def handle_inputs(self, workflow):
        print("Checking inputs")
        seen_inputs = set()
        missing_inputs = []
        for node in workflow.values():
            # Skip URLs in LoraLoader nodes
            if node.get("class_type") in ["LoraLoaderFromURL", "LoraLoader"]:
                continue

            if "inputs" in node:
                for input_key, input_value in node["inputs"].items():
                    if isinstance(input_value, str) and input_value not in seen_inputs:
                        seen_inputs.add(input_value)
                        if input_value.startswith(("http://", "https://")):
                            filename = os.path.join(
                                self.input_directory, os.path.basename(input_value)
                            )
                            if not os.path.exists(filename):
                                print(f"Downloading {input_value} to {filename}")
                                try:
                                    response = requests.get(input_value)
                                    response.raise_for_status()
                                    with open(filename, "wb") as file:
                                        file.write(response.content)
                                    print(f"✅ {filename}")
                                except requests.exceptions.RequestException as e:
                                    print(f"❌ Error downloading {input_value}: {e}")
                                    missing_inputs.append(filename)

                            # The same URL may be included in a workflow more than once
                            node["inputs"][input_key] = filename

                        elif self.is_image_or_video_value(input_value):
                            filename = os.path.join(
                                self.input_directory, os.path.basename(input_value)
                            )
                            if not os.path.exists(filename):
                                print(f"❌ {filename} not provided")
                                missing_inputs.append(filename)
                            else:
                                print(f"✅ {filename}")

        if missing_inputs:
            raise Exception(f"Missing required input files: {', '.join(missing_inputs)}")

        print("====================================")

    def connect(self):
        self.client_id = str(uuid.uuid4())
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")

    def post_request(self, endpoint, data=None):
        url = f"http://{self.server_address}{endpoint}"
        headers = {"Content-Type": "application/json"} if data else {}
        json_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(
            url, data=json_data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    print(f"Failed: {endpoint}, status code: {response.status}")
        except URLError as e:
            # If server is down, don't raise during cleanup
            print(f"Warning: post_request to {endpoint} failed: {e}")
            return

    # https://github.com/comfyanonymous/ComfyUI/blob/master/server.py
    def clear_queue(self):
        if not self.is_server_running():
            return
        self.post_request("/queue", {"clear": True})
        self.post_request("/interrupt")

    def queue_prompt(self, prompt):
        try:
            # Prompt is the loaded workflow (prompt is the label comfyUI uses)
            p = {"prompt": prompt, "client_id": self.client_id}
            data = json.dumps(p).encode("utf-8")
            req = urllib.request.Request(
                f"http://{self.server_address}/prompt?{self.client_id}", data=data
            )

            output = json.loads(urllib.request.urlopen(req).read())
            return output["prompt_id"]
        except urllib.error.HTTPError as e:
            print(f"ComfyUI error: {e.code} {e.reason}")
            http_error = True

        if http_error:
            raise Exception(
                "ComfyUI Error – Your workflow could not be run. Please check the logs for details."
            )

    def _delete_corrupted_weights(self, error_data):
        if "current_inputs" in error_data:
            weights_to_delete = []
            weights_filetypes = self.weights_downloader.supported_filetypes

            for input_list in error_data["current_inputs"].values():
                for input_value in input_list:
                    if isinstance(input_value, str) and any(
                        input_value.endswith(ft) for ft in weights_filetypes
                    ):
                        weights_to_delete.append(input_value)

            for weight_file in list(set(weights_to_delete)):
                self.weights_downloader.delete_weights(weight_file)

            raise Exception(
                "The weights for this workflow have been corrupted. They have been deleted and will be re-downloaded on the next run. Please try again."
            )

    def wait_for_prompt_completion(self, workflow, prompt_id):
        while True:
            out = self.ws.recv()
            if isinstance(out, str):
                message = json.loads(out)

                if message["type"] == "execution_error":
                    error_data = message["data"]

                    if (
                        "exception_type" in error_data
                        and error_data["exception_type"]
                        == "safetensors_rust.SafetensorError"
                    ):
                        self._delete_corrupted_weights(error_data)

                    if (
                        "exception_message" in error_data
                        and "Unauthorized: Please login first to use this node" in error_data["exception_message"]
                    ):
                        raise Exception("ComfyUI API nodes are not currently supported.")

                    error_message = json.dumps(message, indent=2)
                    raise Exception(
                        f"There was an error executing your workflow:\n\n{error_message}"
                    )

                if message["type"] == "executing":
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break
                    elif data["prompt_id"] == prompt_id:
                        node = workflow.get(data["node"], {})
                        meta = node.get("_meta", {})
                        class_type = node.get("class_type", "Unknown")
                        print(
                            f"Executing node {data['node']}, title: {meta.get('title', 'Unknown')}, class type: {class_type}"
                        )
            else:
                continue

    def load_workflow(self, workflow, skip_weight_check=False, skip_node_checks=False, download_all_model_inputs=False):
        if not isinstance(workflow, dict):
            wf = json.loads(workflow)
        else:
            wf = workflow

        # There are two types of ComfyUI JSON
        # We need the API version
        if any(key in wf.keys() for key in ["last_node_id", "last_link_id", "version"]):
            raise ValueError(
                "You need to use the API JSON version of a ComfyUI workflow. To do this go to your ComfyUI settings and turn on 'Enable Dev mode Options'. Then you can save your ComfyUI workflow via the 'Save (API Format)' button."
            )

        if not skip_node_checks:
            self.handle_known_unsupported_nodes(wf)
        self.handle_inputs(wf)
        self.handle_weights(wf, skip_check=skip_weight_check, download_all_model_inputs=download_all_model_inputs)
        return wf

    def reset_execution_cache(self):
        print("Resetting execution cache")
        with open("reset.json", "r") as file:
            reset_workflow = json.loads(file.read())
        self.queue_prompt(reset_workflow)

    def randomise_input_seed(self, input_key, inputs):
        if input_key in inputs and isinstance(inputs[input_key], (int, float)):
            new_seed = random.randint(0, 2**31 - 1)
            print(f"Randomising {input_key} to {new_seed}")
            inputs[input_key] = new_seed

    def randomise_seeds(self, workflow):
        for node_id, node in workflow.items():
            inputs = node.get("inputs", {})
            seed_keys = ["seed", "noise_seed", "rand_seed"]
            for seed_key in seed_keys:
                self.randomise_input_seed(seed_key, inputs)

    def run_workflow(self, workflow):
        print("Running workflow")
        prompt_id = self.queue_prompt(workflow)
        self.wait_for_prompt_completion(workflow, prompt_id)
        output_json = self.get_history(prompt_id)
        print("outputs: ", output_json)
        print("====================================")
        return output_json

    def get_history(self, prompt_id):
        with urllib.request.urlopen(
            f"http://{self.server_address}/history/{prompt_id}"
        ) as response:
            output = json.loads(response.read())
            return output[prompt_id]["outputs"]

    def extract_files_from_history(self, history_output, output_directories):
        """
        Extract file paths from ComfyUI history output.
        Dynamically parses all output types from the history metadata to find all generated files.
        Handles images, videos, audio, and any custom output types from extensions.
        Falls back to directory walking if history parsing fails.
        """
        files = []
        if not history_output:
            print("No history output, falling back to directory walk")
            return self.get_files(output_directories)
        
        if not isinstance(output_directories, list):
            output_directories = [output_directories]
        
        # Parse history output to find all output files
        # ComfyUI outputs are organized by node_id -> output_type -> [items]
        for node_id, node_output in history_output.items():
            # Dynamically check ALL keys in node_output (not just hardcoded types)
            # This catches custom outputs from extensions
            for output_type, output_data in node_output.items():
                # Output data should be a list of items
                if isinstance(output_data, list):
                    for item in output_data:
                        # Each item should be a dict with filename and optional subfolder
                        if isinstance(item, dict) and "filename" in item:
                            filename = item["filename"]
                            subfolder = item.get("subfolder", "")
                            # Try to locate file in any output directory
                            for output_dir in output_directories:
                                full_path = os.path.join(output_dir, subfolder, filename)
                                if os.path.exists(full_path):
                                    print(f"Found {output_type} file from history: {full_path}")
                                    files.append(Path(full_path))
                                    break
        
        # If no files found via history, fall back to directory walk as safety net
        if not files:
            print("No files found in history output, falling back to directory walk")
            return self.get_files(output_directories)
        
        return sorted(files)

    def get_files(self, directories, prefix="", file_extensions=None):
        files = []
        if isinstance(directories, str):
            directories = [directories]

        for directory in directories:
            for f in os.listdir(directory):
                if f == "__MACOSX":
                    continue
                path = os.path.join(directory, f)
                if os.path.isfile(path):
                    print(f"{prefix}{f}")
                    files.append(Path(path))
                elif os.path.isdir(path):
                    print(f"{prefix}{f}/")
                    files.extend(self.get_files(path, prefix=f"{prefix}{f}/"))

        if file_extensions:
            files = [f for f in files if f.name.split(".")[-1] in file_extensions]

        return sorted(files)

    def cleanup(self, directories):
        self.clear_queue()
        for directory in directories:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            os.makedirs(directory)

    def convert_lora_loader_nodes(self, workflow):
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoraLoader":
                inputs = node.get("inputs", {})
                if "lora_name" in inputs and isinstance(inputs["lora_name"], str):
                    if inputs["lora_name"].startswith(("http://", "https://")):
                        print(
                            f"Converting LoraLoader node {node_id} to LoraLoaderFromURL"
                        )
                        node["class_type"] = "LoraLoaderFromURL"
                        node["inputs"]["url"] = inputs["lora_name"]
                        del node["inputs"]["lora_name"]
