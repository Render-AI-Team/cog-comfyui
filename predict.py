import os
import shutil
import tarfile
import zipfile
import mimetypes
import json
import sys
from PIL import Image
from typing import List, Optional, Dict, Any
from cog import BasePredictor, Input, Path
from comfyui import ComfyUI
from weights_downloader import WeightsDownloader
from cog_model_helpers import optimise_images
from config import config
import requests
import base64

# Import workflow dependency installer for automatic setup
try:
    from workflow_dependency_installer import main as install_workflow_dependencies
    HAS_DEPENDENCY_INSTALLER = True
except ImportError:
    HAS_DEPENDENCY_INSTALLER = False
    print("⚠️  Workflow dependency installer not available - will skip automatic setup")


os.environ["DOWNLOAD_LATEST_WEIGHTS_MANIFEST"] = "true"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("video/webm", ".webm")

OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
COMFYUI_TEMP_OUTPUT_DIR = "ComfyUI/temp"
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, COMFYUI_TEMP_OUTPUT_DIR]

IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".webp"]
VIDEO_TYPES = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

with open("examples/api_workflows/birefnet_api.json", "r") as file:
    EXAMPLE_WORKFLOW_JSON = file.read()


class Predictor(BasePredictor):
    def setup(self, weights: str):
        """Setup the predictor with optional weight preloading.
        
        To preload weights, set environment variables:
        - PRELOAD_WORKFLOW: Path or URL to single workflow JSON
        - PRELOAD_WORKFLOWS: Path or URL to workflows.json file (multiple workflows)
        - BASE_MODEL_KIT: One of 'sd15', 'sdxl', 'flux', or 'none' (default)
        
        Supports auto-detection:
        - If workflows.json exists in root directory, it will be auto-loaded
        
        All downloaded weights, workflows, and manifests are stored in temporary
        cache directories (.cache/, .downloads/, .temp_workflows/) which are
        excluded from git via .gitignore.
        
        Dependencies (custom nodes, models) are automatically installed from
        detected workflows using the workflow dependency installer.
        """
        if bool(weights):
            self.handle_user_weights(weights)

        for directory in ALL_DIRECTORIES:
            os.makedirs(directory, exist_ok=True)
        os.makedirs(os.environ.get("YOLO_CONFIG_DIR", "/tmp/Ultralytics"), exist_ok=True)

        # Create cache directories for downloaded workflows and manifests
        os.makedirs(config["DOWNLOADED_WORKFLOWS_PATH"], exist_ok=True)
        os.makedirs(config["DOWNLOADED_MANIFESTS_PATH"], exist_ok=True)
        os.makedirs(config["USER_WEIGHTS_PATH"], exist_ok=True)

        # Check if workflows will be preloaded and auto-install dependencies if so
        # This must happen BEFORE ComfyUI initialization so all custom nodes are available
        has_workflows = False
        preload_workflows = os.environ.get("PRELOAD_WORKFLOWS", "")
        preload_workflow = os.environ.get("PRELOAD_WORKFLOW", "")
        has_workflows_json = os.path.exists("workflows.json")
        
        if preload_workflows or preload_workflow or has_workflows_json:
            has_workflows = True
            
        if has_workflows and HAS_DEPENDENCY_INSTALLER:
            print("\n🔧 Auto-installing workflow dependencies...")
            print("=" * 60)
            try:
                # Run the workflow dependency installer
                # It will detect custom nodes and models from workflows.json and install them
                install_workflow_dependencies()
                print("=" * 60)
                print("✅ Workflow dependencies installed successfully\n")
            except Exception as e:
                print("=" * 60)
                print(f"⚠️  Workflow dependency installation failed: {e}")
                print("⚠️  Continuing with setup (this may cause issues if dependencies were required)")
                import traceback
                traceback.print_exc()

        # Preload base model kit if specified via environment variable
        base_model_kit = os.environ.get("BASE_MODEL_KIT", "none")
        if base_model_kit != "none":
            self.preload_base_kit(base_model_kit)
        
        # Preload workflows from file (supports multiple workflows)
        # Priority: env var > auto-detect workflows.json > single workflow env var
        if preload_workflows:
            self.preload_all_workflows(preload_workflows)
        elif has_workflows_json:
            print("📄 Found workflows.json, auto-loading...")
            self.preload_all_workflows("workflows.json")
        else:
            # Fall back to single workflow if multiple not specified
            if preload_workflow:
                self.preload_workflow_weights(preload_workflow)

        self.comfyUI = ComfyUI("127.0.0.1:8188")
        self.server_started = False

    def preload_base_kit(self, kit_name: str):
        """Preload common model sets during setup."""
        from weights_downloader import WeightsDownloader
        downloader = WeightsDownloader()
        
        kit_models = {
            "sd15": [
                "v1-5-pruned-emaonly.safetensors",
            ],
            "sdxl": [
                "sd_xl_base_1.0.safetensors",
                "sd_xl_refiner_1.0.safetensors",
            ],
            "flux": [
                "flux1-dev.safetensors",
                "clip_l.safetensors",
                "t5xxl_fp8_e4m3fn.safetensors",
                "ae.safetensors",
            ],
        }
        
        models = kit_models.get(kit_name, [])
        if models:
            print(f"⏳ Preloading {kit_name} base kit ({len(models)} models)...")
            for model in models:
                try:
                    downloader.download_weights(model)
                except Exception as e:
                    print(f"⚠️  Failed to preload {model}: {e}")
            print(f"✅ Base kit '{kit_name}' preloaded")
    
    def preload_workflow_weights(self, workflow_json: str):
        """Preload all weights required by a workflow during setup."""
        print("⏳ Preloading workflow weights...")
        try:
            # Resolve workflow source (URL, data URI, or inline JSON)
            workflow_content = self._resolve_workflow_source(workflow_json)
            workflow = json.loads(workflow_content)
            
            # Extract required weights from workflow
            required_weights = self.comfyUI.extract_required_weights(workflow)
            
            if required_weights:
                print(f"Found {len(required_weights)} weight(s) to preload")
                for weight in required_weights:
                    self.comfyUI.weights_downloader.download_weights(weight)
                print("✅ Workflow weights preloaded")
            else:
                print("ℹ️  No weights found in workflow")
        except Exception as e:
            print(f"⚠️  Failed to preload workflow weights: {e}")
            print("Continuing with setup...")
    
    def preload_all_workflows(self, workflows_file: str):
        """Preload weights for all workflows in a workflows.json file.
        
        Supports multiple formats:
        1. Array of workflows: [{"name": "flux", "workflow": {...}}, ...]
        2. Object with named workflows: {"flux": {...}, "sdxl": {...}}
        3. File paths: {"workflow_name": "path/to/workflow.json", ...}
        4. Mixed: {"name1": {...workflow...}, "name2": "path/to/workflow.json"}
        """
        print("⏳ Preloading weights from all workflows...")
        try:
            # Resolve workflow source
            workflows_content = self._resolve_workflow_source(workflows_file)
            workflows_data = json.loads(workflows_content)
            
            all_weights = set()
            workflow_count = 0
            
            # Handle both array and object formats
            if isinstance(workflows_data, list):
                # Array format: [{"name": "...", "workflow": {...}}, ...]
                for item in workflows_data:
                    if isinstance(item, dict) and "workflow" in item:
                        workflow_count += 1
                        name = item.get("name", f"workflow_{workflow_count}")
                        workflow = item["workflow"]
                        weights = self.comfyUI.extract_required_weights(workflow)
                        print(f"  📄 {name}: {len(weights)} weight(s)")
                        all_weights.update(weights)
                    elif isinstance(item, dict):
                        # Treat the item itself as a workflow
                        workflow_count += 1
                        weights = self.comfyUI.extract_required_weights(item)
                        print(f"  📄 workflow_{workflow_count}: {len(weights)} weight(s)")
                        all_weights.update(weights)
            
            elif isinstance(workflows_data, dict):
                # Object format: {"flux": {...}, "sdxl": {...}}
                # Check if it's a workflows collection or a single workflow
                if "workflows" in workflows_data:
                    # Explicitly named "workflows" key
                    for item in workflows_data["workflows"]:
                        if isinstance(item, dict) and "workflow" in item:
                            workflow_count += 1
                            name = item.get("name", f"workflow_{workflow_count}")
                            workflow = item["workflow"]
                        else:
                            workflow = item
                            workflow_count += 1
                            name = f"workflow_{workflow_count}"
                        weights = self.comfyUI.extract_required_weights(workflow)
                        print(f"  📄 {name}: {len(weights)} weight(s)")
                        all_weights.update(weights)
                else:
                    # Assume keys are workflow names, values can be workflows or file paths
                    for name, workflow_or_path in workflows_data.items():
                        # Skip metadata keys
                        if name.startswith("_") or name in ["metadata", "config", "settings"]:
                            continue
                        
                        workflow_count += 1
                        
                        # Check if value is a file path (string)
                        if isinstance(workflow_or_path, str):
                            print(f"  📁 Loading {name} from: {workflow_or_path}")
                            try:
                                workflow_content = self._resolve_workflow_source(workflow_or_path)
                                workflow = json.loads(workflow_content)
                            except Exception as e:
                                print(f"  ⚠️  Failed to load workflow from {workflow_or_path}: {e}")
                                continue
                        elif isinstance(workflow_or_path, dict):
                            workflow = workflow_or_path
                        else:
                            print(f"  ⚠️  Skipping {name}: invalid format")
                            continue
                        
                        weights = self.comfyUI.extract_required_weights(workflow)
                        print(f"  📄 {name}: {len(weights)} weight(s)")
                        all_weights.update(weights)
            
            if all_weights:
                all_weights = list(all_weights)
                print(f"\nFound {len(all_weights)} unique weight(s) across {workflow_count} workflow(s)")
                print(f"⏳ Downloading {len(all_weights)} weight(s)...")
                
                for i, weight in enumerate(all_weights, 1):
                    try:
                        print(f"  [{i}/{len(all_weights)}] {weight}...", end=" ", flush=True)
                        self.comfyUI.weights_downloader.download_weights(weight)
                        print("✅")
                    except Exception as e:
                        print(f"❌ {e}")
                
                print(f"\n✅ All workflows preloaded")
            else:
                print(f"ℹ️  No weights found in {workflow_count} workflow(s)")
        
        except Exception as e:
            print(f"⚠️  Failed to preload workflows: {e}")
            import traceback
            traceback.print_exc()
            print("Continuing with setup...")

    def handle_user_weights(self, weights: str):
        if hasattr(weights, "url"):
            if weights.url.startswith("http"):
                weights_url = weights.url
            else:
                weights_url = "https://replicate.delivery/" + weights.url
        else:
            weights_url = weights

        print(f"Downloading user weights from: {weights_url}")
        WeightsDownloader.download("weights.tar", weights_url, config["USER_WEIGHTS_PATH"])
        for item in os.listdir(config["USER_WEIGHTS_PATH"]):
            source = os.path.join(config["USER_WEIGHTS_PATH"], item)
            destination = os.path.join(config["MODELS_PATH"], item)
            if os.path.isdir(source):
                if not os.path.exists(destination):
                    print(f"Moving {source} to {destination}")
                    shutil.move(source, destination)
                else:
                    for root, _, files in os.walk(source):
                        for file in files:
                            if not os.path.exists(os.path.join(destination, file)):
                                print(
                                    f"Moving {os.path.join(root, file)} to {destination}"
                                )
                                shutil.move(os.path.join(root, file), destination)
                            else:
                                print(
                                    f"Skipping {file} because it already exists in {destination}"
                                )

    def handle_input_file(self, input_file: Path, custom_filename: str = None):
        """Handle a single input file with optional custom filename"""
        file_extension = self.get_file_extension(input_file)

        if file_extension == ".tar":
            with tarfile.open(input_file, "r") as tar:
                tar.extractall(INPUT_DIR)
        elif file_extension == ".zip":
            with zipfile.ZipFile(input_file, "r") as zip_ref:
                zip_ref.extractall(INPUT_DIR)
        elif file_extension in IMAGE_TYPES + VIDEO_TYPES:
            if custom_filename:
                filename = custom_filename if custom_filename.endswith(file_extension) else f"{custom_filename}{file_extension}"
            else:
                filename = f"input{file_extension}"
            shutil.copy(input_file, os.path.join(INPUT_DIR, filename))
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        print("====================================")
        print(f"Inputs uploaded to {INPUT_DIR}:")
        self.comfyUI.get_files(INPUT_DIR)
        print("=====================================")

    def handle_multiple_input_files(self, input_files: Dict[str, Path]):
        """Handle multiple input files with custom names
        
        Args:
            input_files: Dictionary mapping desired filenames to Path objects
        """
        for filename, file_path in input_files.items():
            self.handle_input_file(file_path, custom_filename=filename)

    def get_file_extension(self, input_file: Path) -> str:
        file_extension = os.path.splitext(input_file)[1].lower()
        if not file_extension:
            with open(input_file, "rb") as f:
                file_signature = f.read(4)
            if file_signature.startswith(b"\x1f\x8b"):  # gzip signature
                file_extension = ".tar"
            elif file_signature.startswith(b"PK"):  # zip signature
                file_extension = ".zip"
            else:
                try:
                    with Image.open(input_file) as img:
                        file_extension = f".{img.format.lower()}"
                        print(f"Determined file type: {file_extension}")
                except Exception as e:
                    raise ValueError(
                        f"Unable to determine file type for: {input_file}, {e}"
                    )
        return file_extension

    def cleanup_input_files(self):
        """Clean up input files after successful output generation"""
        if os.path.exists(INPUT_DIR):
            print(f"🧹 Cleaning up input files from {INPUT_DIR}")
            for filename in os.listdir(INPUT_DIR):
                file_path = os.path.join(INPUT_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        print(f"  ✓ Deleted: {filename}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"  ✓ Deleted directory: {filename}")
                except Exception as e:
                    print(f"  ✗ Failed to delete {filename}: {e}")

    def substitute_workflow_params(self, workflow: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute parameters in workflow JSON
        
        Allows dynamic parameter substitution in workflows using placeholder syntax.
        Example: {"inputs": {"text": "{{prompt}}"}} with params={"prompt": "a cat"}
        
        Args:
            workflow: The workflow dictionary
            params: Dictionary of parameter names to values
            
        Returns:
            Modified workflow with substituted parameters
        """
        workflow_str = json.dumps(workflow)
        
        for key, value in params.items():
            # Support both {{key}} and {key} placeholder syntax
            workflow_str = workflow_str.replace(f"{{{{{key}}}}}", str(value))
            workflow_str = workflow_str.replace(f"{{{key}}}", str(value))
        
        return json.loads(workflow_str)

    def _resolve_workflow_source(self, workflow_content: str) -> str:
        """Resolve workflow content from inline JSON, data URI, or URL."""
        if not workflow_content:
            return ""
        if workflow_content.startswith("data:") and ";base64," in workflow_content:
            base64_part = workflow_content.split(",", 1)[1]
            decoded_bytes = base64.b64decode(base64_part)
            return decoded_bytes.decode("utf-8")
        if workflow_content.startswith(("http://", "https://")):
            response = requests.get(workflow_content)
            response.raise_for_status()
            return response.text
        return workflow_content

    def _convert_ui_workflow(self, workflow_json_content: str) -> Dict[str, Any]:
        """Convert UI-format workflow JSON to API format using the upstream converter."""
        comfy_path = os.path.abspath("ComfyUI")
        if comfy_path not in sys.path:
            sys.path.append(comfy_path)

        try:
            from workflow_converter import WorkflowConverter
        except ImportError as e:
            raise ImportError(
                "Workflow converter is unavailable. Ensure workflow_converter.py is present and ComfyUI modules are importable."
            ) from e

        try:
            ui_workflow = json.loads(workflow_json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid UI workflow JSON: {e}")

        try:
            return WorkflowConverter.convert_to_api(ui_workflow)
        except Exception as e:
            raise RuntimeError(f"Failed to convert UI workflow to API format: {e}")

    def predict(
        self,
        workflow_json: str = Input(
            description="Your ComfyUI workflow as JSON string or URL. You must use the API version of your workflow. Get it from ComfyUI using 'Save (API format)'. Instructions here: https://github.com/replicate/cog-comfyui",
            default="",
        ),
        ui_workflow_json: str = Input(
            description="Optional: your ComfyUI workflow saved in the UI format (string or URL). It will be auto-converted to API format using the official converter before execution.",
            default="",
        ),
        input_file: Optional[Path] = Input(
            description="Input image, video, tar or zip file. Read guidance on workflows and input files here: https://github.com/replicate/cog-comfyui. Alternatively, you can replace inputs with URLs in your JSON workflow and the model will download them.",
            default=None,
        ),
        input_file_2: Optional[Path] = Input(
            description="Optional second input file (image, video, etc.)",
            default=None,
        ),
        input_file_3: Optional[Path] = Input(
            description="Optional third input file (image, video, etc.)",
            default=None,
        ),
        input_filename_1: str = Input(
            description="Custom filename for input_file (e.g., 'image.png', 'video.mp4'). If not specified, defaults to 'input' with appropriate extension.",
            default="",
        ),
        input_filename_2: str = Input(
            description="Custom filename for input_file_2",
            default="",
        ),
        input_filename_3: str = Input(
            description="Custom filename for input_file_3",
            default="",
        ),
        workflow_params: str = Input(
            description="JSON string of parameters to substitute in workflow. Use {{param_name}} in your workflow JSON, then pass {\"param_name\": \"value\"} here.",
            default="",
        ),
        return_temp_files: bool = Input(
            description="Return any temporary files, such as preprocessed controlnet images. Useful for debugging.",
            default=False,
        ),
        output_format: str = optimise_images.predict_output_format(),
        output_quality: int = optimise_images.predict_output_quality(),
        randomise_seeds: bool = Input(
            description="Automatically randomise seeds (seed, noise_seed, rand_seed)",
            default=True,
        ),
        force_reset_cache: bool = Input(
            description="Force reset the ComfyUI cache before running the workflow. Useful for debugging.",
            default=False,
        ),
        skip_weight_check: bool = Input(
            description="Skip checking if weights are in the supported manifest. Use this to run workflows with custom/arbitrary models. Note: You must provide the model files via the 'weights' parameter in setup or ensure they exist in ComfyUI/models.",
            default=True,
        ),
        skip_node_checks: bool = Input(
            description="Skip checks for unsupported nodes. Use this to run workflows with nodes that are flagged as unsupported by helper modules.",
            default=True,
        ),
        install_custom_nodes: bool = Input(
            description="Install custom nodes declared in the workflow before running (and remove them after). Increases startup time.",
            default=False,
        ),
        node_to_repo_map: str = Input(
            description="JSON mapping of node class names to git repo URLs, e.g., {\"ManualSigmas\": \"https://github.com/example/repo\"}. Overrides default class map for specified nodes.",
            default="",
        ),
        download_all_model_inputs: bool = Input(
            description="Download all detected model files from workflow inputs, including embeddings and custom-node files. Ensures 100% coverage even with skip_weight_check enabled.",
            default=False,
        ),
    ) -> List[Path]:
        """Run a single prediction on the model"""
        self.comfyUI.cleanup(ALL_DIRECTORIES)

        # Handle multiple input files with custom filenames
        if input_file:
            self.handle_input_file(input_file, custom_filename=input_filename_1 or None)
        if input_file_2:
            self.handle_input_file(input_file_2, custom_filename=input_filename_2 or None)
        if input_file_3:
            self.handle_input_file(input_file_3, custom_filename=input_filename_3 or None)

        workflow_json_content = workflow_json
        ui_workflow_json_content = ui_workflow_json

        try:
            workflow_json_content = self._resolve_workflow_source(workflow_json_content)
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to download workflow JSON from URL: {e}")
        except Exception as e:
            raise ValueError(f"Failed to decode workflow JSON: {e}")

        try:
            ui_workflow_json_content = self._resolve_workflow_source(ui_workflow_json_content)
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to download UI workflow JSON from URL: {e}")
        except Exception as e:
            raise ValueError(f"Failed to decode UI workflow JSON: {e}")

        wf_source = workflow_json_content or EXAMPLE_WORKFLOW_JSON
        if ui_workflow_json_content:
            wf_source = self._convert_ui_workflow(ui_workflow_json_content)

        # Always check for and install missing custom nodes from workflow
        # Start fresh server when nodes are needed for this workflow
        if install_custom_nodes or not self.server_started:
            # Stop old server if it exists
            if self.server_started:
                self.comfyUI.stop_server()
                self.comfyUI.cleanup_custom_nodes()
            
            # Auto-detect and install missing nodes from workflow
            user_node_map = {}
            if node_to_repo_map:
                try:
                    user_node_map = json.loads(node_to_repo_map)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid node_to_repo_map JSON: {e}")
            self.comfyUI.install_custom_nodes_for_workflow(wf_source, user_node_map=user_node_map)
            self.comfyUI.start_server(OUTPUT_DIR, INPUT_DIR)
            self.server_started = True

        wf = self.comfyUI.load_workflow(
            wf_source,
            skip_weight_check=skip_weight_check,
            skip_node_checks=skip_node_checks,
            download_all_model_inputs=download_all_model_inputs,
        )
        
        # Apply parameter substitution if provided
        if workflow_params:
            try:
                params_dict = json.loads(workflow_params)
                wf = self.substitute_workflow_params(wf, params_dict)
                print(f"Applied workflow parameter substitutions: {list(params_dict.keys())}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid workflow_params JSON: {e}")

        self.comfyUI.connect()

        if force_reset_cache or not randomise_seeds:
            self.comfyUI.reset_execution_cache()

        if randomise_seeds:
            self.comfyUI.randomise_seeds(wf)

        history_output = self.comfyUI.run_workflow(wf)

        output_directories = [OUTPUT_DIR]
        if return_temp_files:
            output_directories.append(COMFYUI_TEMP_OUTPUT_DIR)

        # Use history-based file extraction for robust output detection
        output_files = self.comfyUI.extract_files_from_history(history_output, output_directories)
        optimised_files = optimise_images.optimise_image_files(
            output_format, output_quality, output_files
        )

        # Clean up input files after successful output generation
        self.cleanup_input_files()

        if install_custom_nodes:
            # Clean up any custom nodes cloned for this run and stop server to release them
            self.comfyUI.stop_server()
            self.comfyUI.cleanup_custom_nodes()
            self.server_started = False

        return optimised_files
