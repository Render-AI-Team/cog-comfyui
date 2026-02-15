#!/usr/bin/env python3
"""
Workflow Dependency Installer
Downloads all required custom nodes and weights for arbitrary ComfyUI workflows.

Usage:
    python workflow_dependency_installer.py workflow.json [workflow2.json ...]
    python workflow_dependency_installer.py '{"nodes": [...]}'
    python workflow_dependency_installer.py -f workflow.json -f workflow2.json

This script will:
1. Parse the provided workflows (JSON files or inline JSON)
2. Extract all node types and weight references
3. Map node types to GitHub repositories using custom_node_class_map.json
4. Install required custom nodes
5. Download required weights using the weights manifest
"""

import json
import sys
import os
import argparse
import importlib
import subprocess
import requests
import time
from pathlib import Path
from typing import Set, Dict, List, Union, Optional
from functools import wraps

# Ensure we run from project root
script_file = Path(__file__).resolve()
project_root = script_file.parent
os.chdir(project_root)

# Base ComfyUI node types that don't require installation
BASE_COMFY_NODES = {
    'Reroute', 'Note', 'MarkdownNote', 'Primitive', 'CheckpointLoaderSimple',
    'CLIPTextEncode', 'CLIPTextEncodeSD3', 'ConditioningCombine', 'ConditioningSetArea',
    'ConditioningSetAreaPercentage', 'ConditioningSetMask', 'ControlNetLoader',
    'DualCLIPLoader', 'EmptyEvaluateLatents', 'EvaluateLatents', 'FrequencyDetailTransfer',
    'ImageScale', 'ImageScaleBy', 'ImageUpscaleWithModel', 'KSamplerAdvanced',
    'KSampler', 'KSamplerSelect', 'LatentBatch', 'LatentComposite', 'LatentCrop',
    'LatentFlip', 'LatentInterpolate', 'LatentRotate', 'LatentUpscale', 'LatentUpscaleBy',
    'LoraLoader', 'ModelMergeBlocks', 'ModelMergeLatentKeyframes', 'ModelMergePatch',
    'ModelMergeSub', 'ModelMergeSubStrength', 'ModelMergeSubforc', 'ModelMergeTogetherStrength',
    'ModelSamplingContinuousEps', 'ModelSamplingContinuousV', 'ModelSamplingDefault',
    'ModelSamplingDiscreteEps', 'ModelSamplingDiscreteV', 'ModelSamplingSD3', 'SaveImage',
    'VAEDecode', 'VAEDecodeTiled', 'VAEEncode', 'VAEEncodeTiled', 'VAELoader',
    'CheckpointLoader', 'DualCLIPTextEncode', 'UNETLoader', 'CLIPLoader',
    'CLIPSetLastLayer', 'StyleModelLoader', 'STYLEModelLoader', 'FreeU',
    'BBoxDetectorCombined', 'BBoxDetectorCombinedPreview', 'PK_HookedinpaintNoise',
    'GetNode', 'Switch', 'PrimitiveNode', 'StringInput', 'IntInput', 'FloatInput',
    'BooleanInput', 'BooleanToNumber', 'BooleanToString'
}

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry a function on failure with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            last_error = None
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        print(f"    ⚠️  Attempt {attempt} failed: {e}. Retrying in {current_delay}s...", flush=True)
                        time.sleep(current_delay)
                        current_delay *= backoff
                        attempt += 1
                    else:
                        break
            
            raise last_error
        return wrapper
    return decorator

# Add ComfyUI to path for imports
comfy_path = os.path.abspath("ComfyUI")
if comfy_path not in sys.path:
    sys.path.insert(0, comfy_path)

# ComfyUI-Manager integration
COMFYUI_MANAGER_MODEL_LIST_URL = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/model-list.json"
_comfyui_manager_models_cache = None
_comfyui_manager_cache_time = 0
COMFYUI_MANAGER_CACHE_DURATION = 3600  # 1 hour

# Progress tracking
PROGRESS_FILE = ".installation_progress.json"


def load_progress() -> Dict:
    """Load installation progress from tracking file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"installed_repos": [], "downloaded_weights": []}


def save_progress(progress: Dict):
    """Save installation progress to tracking file."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    except Exception:
        pass


def clear_progress():
    """Clear progress tracking file on successful completion."""
    if os.path.exists(PROGRESS_FILE):
        try:
            os.remove(PROGRESS_FILE)
        except Exception:
            pass


def load_class_repo_map() -> Dict[str, str]:
    """Load the custom node class to repository mapping."""
    map_file = "custom_node_class_map.json"
    if not os.path.exists(map_file):
        print(f"⚠️  Warning: {map_file} not found")
        return {}

    try:
        with open(map_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading {map_file}: {e}")
        return {}


def get_comfyui_manager_models() -> List[Dict]:
    """Fetch and cache ComfyUI-Manager's model database with retry logic."""
    global _comfyui_manager_models_cache, _comfyui_manager_cache_time
    
    current_time = time.time()
    if (_comfyui_manager_models_cache is not None and 
        current_time - _comfyui_manager_cache_time < COMFYUI_MANAGER_CACHE_DURATION):
        return _comfyui_manager_models_cache
    
    # Try to fetch with retry logic
    for attempt in range(3):
        try:
            if attempt == 0:
                print("📡 Fetching ComfyUI-Manager model database...")
            response = requests.get(COMFYUI_MANAGER_MODEL_LIST_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            _comfyui_manager_models_cache = data.get('models', [])
            _comfyui_manager_cache_time = current_time
            print(f"✅ Loaded {len(_comfyui_manager_models_cache)} models from ComfyUI-Manager")
            return _comfyui_manager_models_cache
        except Exception as e:
            if attempt < 2:
                delay = 1.0 * (2 ** attempt)
                print(f"    ⚠️  Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"⚠️  Failed to fetch ComfyUI-Manager models after 3 attempts")
                return []
    
    return []


def find_model_in_comfyui_manager(filename: str) -> Optional[Dict]:
    """Find a model by filename in ComfyUI-Manager's database."""
    models = get_comfyui_manager_models()
    
    # Try exact filename match first
    for model in models:
        if model.get('filename') == filename:
            return model
    
    # Try partial matches (case-insensitive)
    filename_lower = filename.lower()
    for model in models:
        model_filename = model.get('filename', '').lower()
        if filename_lower in model_filename or model_filename in filename_lower:
            return model
    
    return None


def load_workflows_from_json(workflows_path="workflows.json") -> List[str]:
    """Load workflow file paths from workflows.json."""
    if not os.path.exists(workflows_path):
        raise FileNotFoundError(f"Workflows file not found: {workflows_path}")
    
    try:
        with open(workflows_path, "r") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError(f"workflows.json must contain a dictionary, got {type(data)}")
        
        # Extract file paths from the dictionary values
        workflow_files = []
        for name, path in data.items():
            # Skip metadata keys
            if name.startswith("_") or name in ["metadata", "config", "settings"]:
                continue
            
            if isinstance(path, str):
                workflow_files.append(path)
            else:
                print(f"⚠️  Skipping {name}: expected string path, got {type(path)}")
        
        return workflow_files
    
    except Exception as e:
        raise ValueError(f"Error loading workflows from {workflows_path}: {e}")


def load_repo_commit_map() -> Dict[str, str]:
    """Load the repository commit mapping from custom_nodes.json."""
    commit_file = "custom_nodes.json"
    if not os.path.exists(commit_file):
        print(f"⚠️  Warning: {commit_file} not found")
        return {}

    try:
        with open(commit_file, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {item["repo"]: item.get("commit", "main") for item in data if "repo" in item}
            return {}
    except Exception as e:
        print(f"⚠️  Error loading {commit_file}: {e}")
        return {}


def parse_workflow(workflow_input: str) -> Dict:
    """Parse workflow from file path or JSON string."""
    # Try to parse as JSON first
    try:
        return json.loads(workflow_input)
    except json.JSONDecodeError:
        pass

    # If not JSON, treat as file path
    if os.path.exists(workflow_input):
        try:
            with open(workflow_input, "r") as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(
                f"Could not parse workflow from file {workflow_input}: {e}")
    else:
        raise ValueError(
            f"Workflow input is not valid JSON and file does not exist: {workflow_input}")


def extract_nodes_from_workflow(workflow: Dict) -> Set[str]:
    """Extract node class types from a workflow."""
    nodes = set()

    try:
        if isinstance(workflow, dict):
            # Try API format (numeric keys with class_type)
            for node_id, node_data in workflow.items():
                if isinstance(node_data, dict) and "class_type" in node_data:
                    nodes.add(node_data.get("class_type"))

            # If no nodes found, try UI format (has nodes array)
            if not nodes and "nodes" in workflow:
                for node in workflow.get("nodes", []):
                    if isinstance(node, dict) and "type" in node:
                        nodes.add(node.get("type"))
    except Exception as e:
        print(f"  Warning: Error extracting nodes: {e}")

    return nodes


def extract_weights_from_workflow(workflow: Dict) -> Set[str]:
    """Extract model file names and URLs from a workflow without needing ComfyUI."""
    weights = set()
    model_input_keys = {
        "ckpt_name", "vae_name", "lora_name", "model_name",
        "clip_name", "embedding_name", "upscale_model_name",
        "diffusers_name", "embeddings", "taesd_name", "conditioning_method",
        "preview_method", "model", "filename"
    }

    # File extensions that are definitely NOT models
    non_model_extensions = {
        ".mp4", ".mov", ".avi", ".mkv", ".webm",  # video
        ".jpg", ".jpeg", ".png", ".webp", ".gif",  # images
        ".wav", ".mp3", ".flac", ".m4a",  # audio
        ".txt", ".json", ".csv"  # data files
    }

    try:
        # Handle both API format (dict with numeric keys) and UI format
        nodes = []
        if isinstance(workflow, dict):
            # Try API format (numeric keys with class_type)
            for node_id, node_data in workflow.items():
                if isinstance(node_data, dict) and "inputs" in node_data:
                    nodes.append(node_data.get("inputs", {}))

            # If no nodes found, try UI format (has nodes array)
            if not nodes and "nodes" in workflow:
                for node in workflow.get("nodes", []):
                    if isinstance(node, dict):
                        # Add both inputs and widgets_values
                        inputs = node.get("inputs", {})
                        widgets = node.get("widgets_values", [])
                        
                        # Convert widgets list to a dict-like structure for processing
                        if widgets:
                            # Create a synthetic inputs dict from widgets
                            synthetic_inputs = {}
                            node_type = node.get("type", "").lower()
                            
                            # Map widget positions based on node type
                            if "checkpoint" in node_type or "checkpointloader" in node_type:
                                if len(widgets) > 0 and isinstance(widgets[0], str):
                                    synthetic_inputs["ckpt_name"] = widgets[0]
                            elif ("vae" in node_type and "loader" in node_type) or "vaeloader" in node_type:
                                if len(widgets) > 0 and isinstance(widgets[0], str):
                                    synthetic_inputs["vae_name"] = widgets[0]
                            elif ("clip" in node_type and "loader" in node_type) or "cliploader" in node_type or "dualcliploader" in node_type:
                                # CLIP loaders often have multiple widgets
                                for i, widget in enumerate(widgets):
                                    if isinstance(widget, str) and any(widget.lower().endswith(ext) for ext in ['.safetensors', '.ckpt', '.pt', '.pth', '.bin']):
                                        synthetic_inputs[f"clip_name_{i}"] = widget
                            elif ("lora" in node_type and "loader" in node_type) or "loraloader" in node_type:
                                if len(widgets) > 0 and isinstance(widgets[0], str):
                                    synthetic_inputs["lora_name"] = widgets[0]
                            elif "unet" in node_type and "loader" in node_type:
                                if len(widgets) > 0 and isinstance(widgets[0], str):
                                    synthetic_inputs["model_name"] = widgets[0]
                            elif "upscale" in node_type and "model" in node_type:
                                if len(widgets) > 0 and isinstance(widgets[0], str):
                                    synthetic_inputs["upscale_model_name"] = widgets[0]
                            else:
                                # For any loader-type node, check all widgets for model files
                                for i, widget in enumerate(widgets):
                                    if isinstance(widget, str) and any(widget.lower().endswith(ext) for ext in ['.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf']):
                                        synthetic_inputs[f"model_{i}"] = widget
                            
                            if synthetic_inputs:
                                nodes.append(synthetic_inputs)
                        
                        # Also add actual inputs if they exist
                        if inputs:
                            nodes.append(inputs)

        # Extract weight references from node inputs
        for inputs in nodes:
            if isinstance(inputs, dict):
                for key, value in inputs.items():
                    # Check if this is a model/weight input
                    if any(model_key in key.lower() for model_key in model_input_keys):
                        if isinstance(value, str) and value.strip():
                            # Allow URLs now - don't filter them out
                            # Only skip if it ends with a non-model extension
                            if any(value.lower().endswith(ext) for ext in non_model_extensions):
                                continue

                            # Skip common input placeholder names
                            if value.lower() in ("image", "video", "audio", "input", "text"):
                                continue

                            weights.add(value)
    except Exception as e:
        print(f"  Warning: Error extracting weights: {e}")

    return weights


def install_custom_nodes(node_types: Set[str], class_repo_map: Dict[str, str], repo_commit_map: Dict[str, str]):
    """Install custom nodes for the given node types."""
    # Filter out base ComfyUI nodes
    unresolved_after_base_filter = {n for n in node_types if n in BASE_COMFY_NODES}
    custom_nodes_needed = {n for n in node_types if n not in BASE_COMFY_NODES}
    
    if unresolved_after_base_filter:
        print(f"ℹ️  {len(unresolved_after_base_filter)} base ComfyUI nodes (already available): {', '.join(sorted(list(unresolved_after_base_filter))[:5])}")
        if len(unresolved_after_base_filter) > 5:
            print(f"    ... and {len(unresolved_after_base_filter) - 5} more")
    
    if not custom_nodes_needed:
        print("✅ All required nodes are already available (base ComfyUI)")
        return

    # Check which custom nodes are already available
    try:
        nodes_module = importlib.import_module("nodes")
        available_nodes = set(
            getattr(nodes_module, "NODE_CLASS_MAPPINGS", {}).keys())
    except Exception:
        available_nodes = set()

    missing_nodes = custom_nodes_needed - available_nodes
    if not missing_nodes:
        print(f"✅ All {len(custom_nodes_needed)} custom node types are already available")
        return

    print(f"📦 Installing {len(missing_nodes)} missing custom node types...")

    # Load progress for resumption
    progress = load_progress()
    installed_repos = set(progress.get("installed_repos", []))

    # Map missing nodes to repositories
    repos_to_install = set()
    unresolved = []

    for node_type in missing_nodes:
        repo_url = class_repo_map.get(node_type)
        if repo_url:
            # Skip installing base ComfyUI repo as a custom node
            if repo_url.rstrip('/') in ("https://github.com/comfyanonymous/ComfyUI", "https://github.com/Comfy-Org/ComfyUI"):
                continue
            repos_to_install.add(repo_url)
        else:
            unresolved.append(node_type)

    # Install repositories
    installed_count = 0
    for repo_url in repos_to_install:
        if repo_url in installed_repos:
            print(f"  ✅ {repo_url} (already installed)")
            installed_count += 1
            continue
            
        commit = repo_commit_map.get(repo_url, "main")
        try:
            print(f"  Installing {repo_url}@{commit}...")
            clone_repo(repo_url, commit)
            installed_count += 1
            installed_repos.add(repo_url)

            # Install Python dependencies if present
            repo_name = os.path.basename(
                repo_url.rstrip("/").replace(".git", ""))
            dest = os.path.join("ComfyUI", "custom_nodes", repo_name)
            reqs = os.path.join(dest, "requirements.txt")
            if os.path.exists(reqs):
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install",
                                   "-r", reqs], check=True, capture_output=True)
                    print(f"    ✅ Installed requirements for {repo_name}")
                except Exception as e:
                    print(
                        f"    ⚠️  Failed to install requirements for {repo_name}: {e}")
            
            # Save progress
            progress["installed_repos"] = list(installed_repos)
            save_progress(progress)

        except Exception as e:
            print(f"    ❌ Failed to install {repo_url}: {e}")
            print("❌ Exiting due to failed custom node installation")
            sys.exit(1)

    print(f"✅ Installed {installed_count} custom node repositories")

    if unresolved:
        print(f"❌ {len(unresolved)} node types could not be resolved:")
        for node in unresolved[:10]:
            print(f"   - {node}")
        if len(unresolved) > 10:
            print(f"   ... and {len(unresolved) - 10} more")
        print("❌ Exiting due to unresolved node types")
        sys.exit(1)


def clone_repo(repo_url: str, commit: str = None):
    """Clone a git repository to ComfyUI/custom_nodes/ with retry logic."""
    repo_name = os.path.basename(repo_url.rstrip("/").replace(".git", ""))
    dest = os.path.join("ComfyUI", "custom_nodes", repo_name)

    if os.path.exists(dest):
        print(f"    Repository {repo_name} already exists, skipping")
        return

    # Clone with retry logic
    for attempt in range(3):
        try:
            # Clone the repository (don't use --branch for commit hashes)
            cmd = ["git", "clone", "--depth", "1", repo_url, dest]
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)

            # If specific commit was requested, checkout the commit
            if commit and commit != "main":
                subprocess.run(["git", "checkout", commit], cwd=dest,
                               check=True, capture_output=True, timeout=30)
            return
        except subprocess.TimeoutExpired:
            if os.path.exists(dest):
                try:
                    import shutil
                    shutil.rmtree(dest)
                except Exception:
                    pass
            if attempt < 2:
                wait_time = 2 ** attempt
                print(f"      ⚠️  Clone attempt {attempt + 1} timed out. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Clone timeout after 3 attempts")
        except Exception as e:
            if os.path.exists(dest):
                try:
                    import shutil
                    shutil.rmtree(dest)
                except Exception:
                    pass
            if attempt < 2:
                wait_time = 2 ** attempt
                print(f"      ⚠️  Clone attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise


def download_weights(weights: Set[str]):
    """Download weights directly from URLs or try to find them from common sources."""
    if not weights:
        print("✅ No weights to download")
        return

    # Load progress for resumption
    progress = load_progress()
    downloaded_weights = set(progress.get("downloaded_weights", []))

    print(f"📥 Downloading {len(weights)} weights...")

    successful = 0

    for weight in sorted(weights):
        if weight in downloaded_weights:
            print(f"  ✅ {weight} (already downloaded)")
            successful += 1
            continue
            
        try:
            print(f"  Downloading {weight}...", end=" ", flush=True)
            
            # Check if it's a URL
            if weight.lower().startswith(('http://', 'https://')):
                # Download directly from URL
                download_from_url(weight)
                successful += 1
                print("✅")
            else:
                # Try to find and download from common sources
                if try_download_from_sources(weight):
                    successful += 1
                    print("✅")
                else:
                    raise ValueError(f"{weight} not found - no URL provided and unable to locate from common sources")
            
            # Save progress
            downloaded_weights.add(weight)
            progress["downloaded_weights"] = list(downloaded_weights)
            save_progress(progress)
                        
        except Exception as e:
            print(f"❌ {e}")
            print("❌ Exiting due to failed weight download")
            sys.exit(1)

    print(f"✅ Downloaded {successful}/{len(weights)} weights")


def get_available_downloader():
    """Detect which downloader tool is available (pget, wget, curl)."""
    for cmd in ['pget', 'wget', 'curl']:
        try:
            result = subprocess.run(['which', cmd], capture_output=True, timeout=5)
            if result.returncode == 0:
                return cmd
        except Exception:
            continue
    return None


def detect_model_type(filename: str, url: str = "") -> str:
    """Detect model type from filename and URL for correct ComfyUI directory placement.
    
    ComfyUI expects models in specific directories:
    - checkpoints: General diffusion models (CKPT, SafeTensors)
    - loras: LoRA adapters
    - vae: Variational autoencoders
    - text_encoders (or clip): CLIP and text encoding models
    - diffusion_models (or unet): UNet diffusion models
    - clip_vision: CLIP vision models
    - controlnet: ControlNet models
    - embeddings: Textual inversions and embeddings
    - upscale_models: Model upscalers
    - style_models: Style models
    - hypernetworks: Hypernetworks
    - photomaker: PhotoMaker models
    - audio_encoders: Audio encoding models
    - vae_approx: VAE approximation models (TAESD, etc.)
    - diffusers: Hugging Face diffusers format models
    - gligen: GLIGEN models
    - model_patches: Model patches
    - classifiers: Classifier models
    """
    filename_lower = filename.lower()
    url_lower = url.lower()
    combined = f"{filename_lower}|{url_lower}"
    
    # Define patterns for each model type, ordered by specificity
    # More specific patterns should come before generic ones
    patterns = {
        # Special cases first (most specific)
        'photomaker': ['photomaker'],
        'gligen': ['gligen'],
        'diffusers': ['/diffusers/', 'diffusers_model', 'hf-hub', 'huggingface'],
        
        # LoRA patterns (very specific)
        'loras': ['_lora.', '-lora.', '.lora', 'lora_', 'xlora', 'locon', '_lyco', '-lyco'],
        
        # VAE patterns 
        'vae': ['_vae.', '-vae.', '_vae-', '-vae-', 'vae_', ' vae', '(vae', 'vae)', 'vae.safetensors'],
        'vae_approx': ['taesd', 'vae_approx', 'approximation'],
        
        # Vision and encoding models
        'clip_vision': ['clip_vision', 'clip-vision', 'clipvision', 'vision_model', 'siglip'],
        'text_encoders': ['text_encoder', 'text-encoder', 'sd15_clip', 'sdxl_clip', 'clip'],
        
        # Control and style
        'controlnet': ['controlnet', 'control_net', '_cnet', '-cnet', 'cnet_', 'controlnet_', 't2i_adapter'],
        'style_models': ['style_model', 'stylegan', 'aesthetic', 'style.safetensors'],
        
        # Segmentation and detection
        'embeddings': ['embedding', 'textual_inversion', 'embedding_', '_embedding', 'embeddings', 'ti_'],
        'classifiers': ['classifier', 'classification', 'safety_checker'],
        
        # Upscaling and enhancement
        'upscale_models': ['upscale', 'upscaler', 'super-resolution', '_x4', '_x2', '_x8', '_x16', 
                          'realesrgan', 'bsrgan', 'esrgan', 'gfpgan', 'face_restore', 'codeformer'],
        
        # Diffusion and UNet models
        'diffusion_models': ['unet', 'diffusion', '_unet', '-unet', 'model_', 'flux', 'sd_', 'hunyuan'],
        
        # Hypernetwork
        'hypernetworks': ['hypernet', 'hypernetwork'],
        
        # Model patches
        'model_patches': ['patch', 'lora.patch', 'safetensors.patch'],
        
        # Audio models
        'audio_encoders': ['audio_encoder', 'wav2vec', 'vocos'],
    }
    
    # Check for exact patterns first (more specific matches)
    for model_type, keywords in patterns.items():
        for keyword in keywords:
            if keyword in combined:
                return model_type
    
    # Default to checkpoints for unknown model types
    return 'checkpoints'


def download_from_url(url: str, save_path: Optional[str] = None):
    """Download a weight file directly from a URL with fallback downloaders.
    
    Models are placed in ComfyUI-standard directories:
    - ComfyUI/models/checkpoints: Diffusion checkpoints
    - ComfyUI/models/loras: LoRA adapters
    - ComfyUI/models/vae: VAE models
    - ComfyUI/models/text_encoders: Text encoders (CLIP)
    - ComfyUI/models/diffusion_models: UNet/diffusion models
    - ComfyUI/models/clip_vision: CLIP vision models
    - ComfyUI/models/controlnet: ControlNet models
    - ComfyUI/models/embeddings: Embeddings/textual inversion
    - ComfyUI/models/upscale_models: Upscalers
    - ComfyUI/models/style_models: Style models
    - ComfyUI/models/hypernetworks: Hypernetworks
    - ComfyUI/models/photomaker: PhotoMaker models
    - ComfyUI/models/classifiers: Classifiers
    - ComfyUI/models/model_patches: Model patches
    - ComfyUI/models/audio_encoders: Audio encoders
    """
    import os
    
    # Determine destination based on URL and file type
    filename = os.path.basename(url.split('?')[0])  # Remove query parameters
    
    # Use save_path from ComfyUI-Manager if provided
    if save_path:
        dest_dir = f"ComfyUI/models/{save_path}"
    else:
        # Detect model type for correct classification
        model_type = detect_model_type(filename, url)
        dest_dir = f"ComfyUI/models/{model_type}"
    
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    
    # Check if file already exists
    if os.path.exists(dest_path):
        print(f"✅ {filename} exists in {dest_dir}")
        return
    
    # Determine which downloader to use
    downloader = get_available_downloader()
    
    if not downloader:
        raise Exception("No downloader available (tried pget, wget, curl)")
    
    # Try downloading with retry logic
    for attempt in range(3):
        try:
            if downloader == 'pget':
                subprocess.check_call(
                    ["pget", url, dest_path], 
                    close_fds=False,
                    timeout=600
                )
            elif downloader == 'wget':
                subprocess.check_call(
                    ["wget", "-O", dest_path, url],
                    timeout=600
                )
            elif downloader == 'curl':
                subprocess.check_call(
                    ["curl", "-L", "-o", dest_path, url],
                    timeout=600
                )
            
            # Get file size for reporting
            try:
                file_size_bytes = os.path.getsize(dest_path)
                file_size_megabytes = file_size_bytes / (1024 * 1024)
                print(f"✅ {filename} ({file_size_megabytes:.2f}MB) → {dest_dir}")
            except FileNotFoundError:
                print(f"✅ {filename} → {dest_dir}")
            return
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            
            if attempt < 2:
                wait_time = 2 ** attempt
                print(f"      ⚠️  Download attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed to download from {url} after 3 attempts: {e}")


def try_download_from_sources(weight_name: str) -> bool:
    """Try to download a weight from common sources like weights manifest, ComfyUI-Manager, etc."""
    # First try the existing weights downloader (local manifest)
    try:
        from weights_downloader import WeightsDownloader
        downloader = WeightsDownloader()
        downloader.download_weights(weight_name)
        return True
    except (ImportError, ValueError):
        # Not available in local manifest or WeightsDownloader not available
        pass
    
    # Try ComfyUI-Manager's model database
    model_info = find_model_in_comfyui_manager(weight_name)
    if model_info:
        try:
            url = model_info.get('url')
            if url:
                print(f"  (found in ComfyUI-Manager)", end=" ", flush=True)
                download_from_url(url, model_info.get('save_path'))
                return True
        except Exception as e:
            print(f"  (ComfyUI-Manager download failed: {e})", end=" ", flush=True)
    
    # TODO: Future enhancement - try to find from:
    # - HuggingFace model hub API
    # - CivitAI API  
    # - Model metadata embedded in workflows
    # - Common model naming patterns
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Install dependencies for ComfyUI workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python workflow_dependency_installer.py workflow.json
  python workflow_dependency_installer.py '{"nodes": [...]}'
  python workflow_dependency_installer.py -f workflow1.json -f workflow2.json
  python workflow_dependency_installer.py --workflows workflow1.json workflow2.json
  python workflow_dependency_installer.py -w  # Load all from workflows.json
  python workflow_dependency_installer.py -w --workflows-json custom_workflows.json
        """
    )

    parser.add_argument(
        "workflows",
        nargs="*",
        help="Workflow files or JSON strings"
    )

    parser.add_argument(
        "-f", "--file",
        action="append",
        dest="workflow_files",
        help="Workflow file paths (can be used multiple times)"
    )

    parser.add_argument(
        "-w", "--from-workflows-json",
        action="store_true",
        help="Load all workflows from workflows.json"
    )

    parser.add_argument(
        "--workflows-json",
        default="workflows.json",
        help="Path to workflows.json file (default: workflows.json)"
    )

    args = parser.parse_args()

    # Combine all workflow inputs
    all_workflows = args.workflows or []
    if args.workflow_files:
        all_workflows.extend(args.workflow_files)
    
    # Load workflows from workflows.json if requested
    if args.from_workflows_json:
        try:
            workflows_from_json = load_workflows_from_json(args.workflows_json)
            all_workflows.extend(workflows_from_json)
            print(f"📋 Loaded {len(workflows_from_json)} workflows from {args.workflows_json}")
        except Exception as e:
            print(f"❌ Error loading workflows from {args.workflows_json}: {e}")
            return 1

    if not all_workflows:
        parser.print_help()
        return 1

    print("🔍 Analyzing workflows and installing dependencies...\n")

    # Load mappings
    class_repo_map = load_class_repo_map()
    repo_commit_map = load_repo_commit_map()

    print(f"📋 Loaded {len(class_repo_map)} node-to-repo mappings")
    print(f"📋 Loaded {len(repo_commit_map)} repo commit mappings\n")

    all_node_types = set()
    all_weights = set()
    processed_workflows = 0

    # Process each workflow
    for i, workflow_input in enumerate(all_workflows, 1):
        try:
            print(f"[{i}/{len(all_workflows)}] Processing workflow...")
            workflow = parse_workflow(workflow_input)

            # Extract dependencies
            node_types = extract_nodes_from_workflow(workflow)
            weights = extract_weights_from_workflow(workflow)

            print(
                f"   Found {len(node_types)} node types, {len(weights)} weights")

            all_node_types.update(node_types)
            all_weights.update(weights)
            processed_workflows += 1

        except Exception as e:
            print(f"   ❌ Error processing workflow: {e}")
            continue

    print(f"\n📊 Summary:")
    print(f"   Workflows processed: {processed_workflows}")
    print(f"   Unique node types: {len(all_node_types)}")
    print(f"   Unique weights: {len(all_weights)}")

    if all_node_types:
        print(f"   Node types: {', '.join(sorted(list(all_node_types))[:10])}")
        if len(all_node_types) > 10:
            print(f"      ... and {len(all_node_types) - 10} more")

    if all_weights:
        print(f"   Weights: {', '.join(sorted(list(all_weights))[:10])}")
        if len(all_weights) > 10:
            print(f"      ... and {len(all_weights) - 10} more")

    print()

    # Install dependencies
    install_custom_nodes(all_node_types, class_repo_map, repo_commit_map)
    download_weights(all_weights)

    # Clear progress on successful completion
    clear_progress()

    print("\n🎉 Dependency installation complete!")
    print("   Your workflows should now be ready to run.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
