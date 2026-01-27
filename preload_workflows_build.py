#!/usr/bin/env python3
"""
Build-time workflow preloader.
Downloads all required weights and dependencies for workflows defined in workflows.json.
This runs during cog build to ensure all dependencies are available at inference time.

Note: This script primarily detects and installs custom nodes. Weight downloading is a
best-effort operation - if weights aren't in the manifest, they can still be provided
at runtime via the weights parameter or skip_weight_check flag.
"""

import json
import sys
import os
from pathlib import Path


def load_workflows_json(path="workflows.json"):
    """Load and parse workflows.json file."""
    if not os.path.exists(path):
        print(f"⚠️  workflows.json not found at {path}")
        print(f"   This is optional - skipping preload")
        return {}
    
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading {path}: {e}")
        return {}


def resolve_workflow_source(workflow_content: str) -> str:
    """Resolve workflow content from inline JSON or file path."""
    if not workflow_content:
        return ""
    
    # If it's a file path, read the file
    if not workflow_content.startswith(("{", "[")):
        if os.path.exists(workflow_content):
            with open(workflow_content, "r") as f:
                return f.read()
        else:
            raise FileNotFoundError(f"Workflow file not found: {workflow_content}")
    
    # Otherwise treat as inline JSON
    return workflow_content


def extract_weights_from_workflow(workflow: dict) -> set:
    """Extract model file names from a workflow without needing ComfyUI."""
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
                        nodes.append(node.get("widgets_values", node.get("inputs", {})))
        
        # Extract weight references from node inputs
        for inputs in nodes:
            if isinstance(inputs, dict):
                for key, value in inputs.items():
                    # Check if this is a model/weight input
                    if any(model_key in key.lower() for model_key in model_input_keys):
                        if isinstance(value, str) and value.strip():
                            # Filter out URLs, data URIs, paths, and non-model files
                            if value.lower().startswith(("http", "data:", "/", ".")):
                                continue
                            
                            # Skip if it ends with a non-model extension
                            if any(value.lower().endswith(ext) for ext in non_model_extensions):
                                continue
                            
                            # Skip common input placeholder names
                            if value.lower() in ("image", "video", "audio", "input", "text"):
                                continue
                            
                            weights.add(value)
    except Exception as e:
        print(f"  Warning: Error extracting weights: {e}")
    
    return weights


def extract_nodes_from_workflow(workflow: dict) -> set:
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


def preload_all_workflows():
    """Preload all workflows from workflows.json and download required weights and custom nodes."""
    workflows_data = load_workflows_json()
    
    if not workflows_data:
        return 0
    
    # Try to import the downloader, but make it optional
    try:
        from weights_downloader import WeightsDownloader
        downloader = WeightsDownloader()
        has_downloader = True
    except (ImportError, ModuleNotFoundError) as e:
        print(f"⚠️  Warning: WeightsDownloader not available: {e}")
        print(f"   Weights will not be preloaded, but nodes will be detected.\n")
        downloader = None
        has_downloader = False
    
    all_weights = set()
    all_custom_nodes = set()
    workflow_count = 0
    failed_workflows = []
    
    # Handle workflows.json as a dict with file paths
    # Format: {"workflow_name": "path/to/workflow.json", ...}
    for name, workflow_path in workflows_data.items():
        # Skip metadata keys
        if name.startswith("_") or name in ["metadata", "config", "settings"]:
            continue
        
        workflow_count += 1
        
        try:
            # Load workflow from file path
            if isinstance(workflow_path, str):
                print(f"\n📁 Processing workflow: {name}")
                print(f"   Loading from: {workflow_path}")
                
                if not os.path.exists(workflow_path):
                    raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
                
                workflow_content = resolve_workflow_source(workflow_path)
                workflow = json.loads(workflow_content)
            elif isinstance(workflow_path, dict):
                workflow = workflow_path
                print(f"\n📄 Processing workflow: {name}")
            else:
                print(f"   ⚠️  Skipping {name}: invalid format (expected dict or string path)")
                continue
            
            # Extract required weights
            weights = extract_weights_from_workflow(workflow)
            if weights:
                print(f"   Found {len(weights)} weight(s)")
                all_weights.update(weights)
            else:
                print(f"   No weights found")
            
            # Extract required custom nodes
            custom_nodes = extract_nodes_from_workflow(workflow)
            if custom_nodes:
                print(f"   Found {len(custom_nodes)} node type(s): {', '.join(sorted(custom_nodes)[:5])}")
                if len(custom_nodes) > 5:
                    print(f"      ... and {len(custom_nodes) - 5} more")
                all_custom_nodes.update(custom_nodes)

        
        except Exception as e:
            print(f"   ❌ Error processing {name}: {e}")
            failed_workflows.append((name, str(e)))
            continue
    
    if not all_weights:
        print(f"\n✅ Found {workflow_count} workflow(s), no weights to preload")
        return 0
    
    # Install required custom nodes (only if WeightsDownloader is available)
    if all_custom_nodes and has_downloader:
        print(f"\n{'='*60}")
        print(f"📦 Installing {len(all_custom_nodes)} custom node type(s)")
        print(f"{'='*60}\n")
        
        try:
            # Import ComfyUI now that we know dependencies are available
            comfy_path = os.path.abspath("ComfyUI")
            if comfy_path not in sys.path:
                sys.path.insert(0, comfy_path)
            
            from comfyui import ComfyUI
            comfy = ComfyUI("127.0.0.1:8188")
            
            # Use ComfyUI's built-in custom node installer
            # Create a temporary workflow with all detected node types
            temp_workflow = {
                str(i): {
                    "class_type": node_type,
                    "inputs": {}
                }
                for i, node_type in enumerate(all_custom_nodes)
            }
            
            comfy._install_mapped_missing_nodes(temp_workflow)
            print(f"✅ Custom nodes installation completed\n")
        except ModuleNotFoundError as e:
            # If ComfyUI dependencies aren't available yet, that's OK - custom nodes will be installed at runtime
            print(f"⚠️  ComfyUI not fully initialized yet ({e})")
            print(f"   Custom nodes will be installed automatically at runtime\n")
        except Exception as e:
            print(f"❌ Error installing custom nodes: {e}\n")
            print(f"⛔ Build failed due to custom node installation error")
            return 1
    elif all_custom_nodes:
        print(f"\n{'='*60}")
        print(f"📦 Detected {len(all_custom_nodes)} custom node type(s)")
        print(f"   (Custom node installation will happen at runtime)")
        print(f"{'='*60}\n")
    
    if not has_downloader:
        print(f"\n⚠️  Skipping weight download (dependencies not fully installed)")
        return 0
    
    # Download all unique weights
    all_weights = sorted(list(all_weights))
    print(f"\n{'='*60}")
    print(f"📥 Preloading {len(all_weights)} unique weight(s) from {workflow_count} workflow(s)")
    print(f"{'='*60}\n")
    
    failed_weights = []
    for i, weight in enumerate(all_weights, 1):
        try:
            print(f"[{i}/{len(all_weights)}] Downloading {weight}...", end=" ", flush=True)
            downloader.download_weights(weight)
            print("✅")
        except Exception as e:
            print(f"❌ {e}")
            failed_weights.append((weight, str(e)))
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Workflows processed: {workflow_count}")
    print(f"  Unique weights: {len(all_weights)}")
    print(f"  Unique node types: {len(all_custom_nodes)}")
    print(f"  Successfully downloaded: {len(all_weights) - len(failed_weights)}")
    print(f"{'='*60}")
    
    if failed_workflows:
        print(f"\n⚠️  Failed to process {len(failed_workflows)} workflow(s):")
        for name, error in failed_workflows:
            print(f"  - {name}: {error}")
    
    if failed_weights:
        print(f"\n⚠️  {len(failed_weights)} weight(s) not available in manifest:")
        for weight, error in failed_weights[:5]:
            print(f"  - {weight}")
        if len(failed_weights) > 5:
            print(f"  ... and {len(failed_weights) - 5} more")
        print(f"\n   Note: Workflows can still use these models if provided via:")
        print(f"   1. The 'weights' parameter during prediction")
        print(f"   2. Setting skip_weight_check=True in the predict call")
        print(f"   3. Pre-placing model files in ComfyUI/models/")
    
    if failed_workflows:
        print(f"\n⛔ Build completed with workflow processing errors")
        return 1
    
    print(f"\n✅ All workflows processed successfully!")
    print(f"   Custom nodes are ready to be installed at runtime.")
    if not failed_weights:
        print(f"   All referenced weights are available.")
    return 0


if __name__ == "__main__":
    try:
        exit_code = preload_all_workflows()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n⚠️  Unexpected error during preload: {e}")
        import traceback
        traceback.print_exc()
        print(f"\nContinuing with build (preload is non-critical)...")
        sys.exit(0)
