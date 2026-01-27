# Workflow Support & Build-Time Preloading

## Quick Start

To analyze and prepare your workflows defined in `workflows.json`:

```bash
python preload_workflows_build.py
```

This will:
- Scan all workflows in `workflows.json`
- Detect required custom nodes and model files
- Report which dependencies are available vs. need to be provided

## Overview

The `cog build` command now includes a build-time preload step that analyzes all workflows defined in `workflows.json` and prepares the environment for them.

## What Happens During `cog build`

1. **Workflow Detection**: All workflows referenced in `workflows.json` are loaded and analyzed
2. **Node Type Extraction**: Custom node dependencies are extracted from each workflow
3. **Weight Analysis**: Model files referenced in workflows are identified
4. **Runtime Preparation**: Custom nodes are prepared for auto-installation at inference time

## Build Output Example

```
📁 Processing workflow: ltx2_i2v_basic
   Loading from: examples/ui_workflows/RuneXX/LTX-2-Workflows/LTX-2 - I2V Basic.json
   Found 1 weight(s)
   Found 36 node type(s): CFGGuider, CLIPTextEncode, DualCLIPLoader, ...

============================================================
📦 Installing 84 custom node type(s)
============================================================

⚠️  ComfyUI not fully initialized yet (No module named 'websocket')
   Custom nodes will be installed automatically at runtime

============================================================
📥 Preloading 7 unique weight(s) from 18 workflow(s)
============================================================

[1/7] Downloading LTX-2... ❌ LTX-2 unavailable

⚠️  7 weight(s) not available in manifest:
   Note: Workflows can still use these models if provided via:
   1. The 'weights' parameter during prediction
   2. Setting skip_weight_check=True in the predict call
   3. Pre-placing model files in ComfyUI/models/

✅ All workflows processed successfully!
```

## Workflow Support Guarantees

### ✅ Guaranteed at Runtime

- **Custom nodes will be available**: All node types detected in workflows are registered and ready
- **Custom node repos are mapped**: Using `custom_node_class_map.json` to resolve missing nodes
- **Node requirements are installed**: Python dependencies for custom nodes are installed
- **Workflow format handling**: UI format workflows are auto-converted to API format when needed

### ⚠️ Conditional Support

**Weight/Model Files**:
- Standard models in the supported weights manifest will be pre-downloaded
- Custom or arbitrary models not in the manifest can be provided via:
  - The `weights` parameter during prediction (tar/zip file with models)
  - Setting `skip_weight_check=True` in your predict call
  - Pre-placing model files in `ComfyUI/models/` directory

**Example with custom models**:
```bash
cog predict \
  -i workflow_json=@workflow.json \
  -i weights=@my_custom_models.tar \
  -i skip_weight_check=true
```

## Troubleshooting

### Build Fails Due to Missing Workflow Files
- Check that all paths in `workflows.json` are correct relative to the repo root
- Ensure workflow files are not excluded in `.gitignore`

### Missing Custom Nodes at Runtime
- The build script detects and maps nodes using `custom_node_class_map.json`
- If a node is unresolved, check if its repository is in `custom_nodes.json`
- Use `install_custom_nodes=True` parameter at inference to force installation

### Missing Model Files at Runtime
- If using custom/arbitrary models, use `skip_weight_check=True`
- Provide model files via the `weights` parameter (tar/zip format)
- Or place model files directly in the appropriate ComfyUI/models subdirectory

## Configuration

The preload script is available in the repository root:

```bash
# Run the analysis locally (before building)
python preload_workflows_build.py

# Or after installing dependencies
python3 -m pip install -r requirements.txt
python preload_workflows_build.py
```

To modify preload behavior, edit `preload_workflows_build.py`:
- `extract_weights_from_workflow()`: Model file detection logic
- `extract_nodes_from_workflow()`: Node type extraction
- `preload_all_workflows()`: Main preload orchestration

**Note**: The preload script is optional and non-blocking. If it's not run before `cog build`, everything will still work - custom nodes will just be auto-installed at runtime instead of being detected upfront.

## Files

- **`preload_workflows_build.py`**: Workflow analysis script (run manually or in your build pipeline)
- **`workflows.json`**: Workflow definitions to be analyzed
- **`custom_node_class_map.json`**: Maps node classes to repositories
- **`custom_nodes.json`**: List of supported custom node repos
- **`cog.yaml`**: Build configuration

