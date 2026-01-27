# Multiple Workflows Support

## Overview

The weight loading system now supports preloading weights for **multiple workflows** from a single JSON file. This is perfect for:

- Applications with multiple inference modes
- Multi-model inference pipelines  
- Batch workflow execution
- Pre-baking common workflow combinations

## Features

### 🔄 Auto-Detection
If `workflows.json` exists in the root directory, it's automatically loaded during setup:

```python
def setup(self, weights: str):
    # Auto-loads workflows.json if it exists
    # Otherwise falls back to PRELOAD_WORKFLOW environment variable
```

### 📦 Dual Format Support

The system supports two JSON formats:

#### Format 1: Named Workflows (Object)
```json
{
  "flux_schnell": {
    "1": {"inputs": {"ckpt_name": "flux1-schnell.safetensors"}, "class_type": "CheckpointLoaderSimple"},
    "2": {"inputs": {"clip_name": "clip_l.safetensors"}, "class_type": "CLIPLoader"}
  },
  "flux_dev": {
    "1": {"inputs": {"ckpt_name": "flux1-dev.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  },
  "sdxl": {
    "1": {"inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  }
}
```

**Advantages:**
- Clear workflow names
- Easy to reference later
- Self-documenting

#### Format 2: Workflows Array
```json
[
  {
    "name": "flux_schnell",
    "workflow": {
      "1": {"inputs": {...}, "class_type": "..."},
      "2": {"inputs": {...}, "class_type": "..."}
    }
  },
  {
    "name": "flux_dev",
    "workflow": {...}
  }
]
```

**Advantages:**
- More structured
- Support for metadata per workflow
- Explicit workflows key for collections

#### Format 3: Implicit Array
```json
[
  {
    "1": {"inputs": {...}, "class_type": "..."}
  },
  {
    "2": {"inputs": {...}, "class_type": "..."}
  }
]
```

## Usage

### Option 1: Auto-Load (Recommended)

Place a `workflows.json` file in the root directory:

```bash
# Copy the example
cp workflows.json.example workflows.json

# Edit to add your workflows
# Then deploy - it will auto-load during setup
```

### Option 2: Environment Variable

Set `PRELOAD_WORKFLOWS` to explicitly load a workflows file:

```bash
export PRELOAD_WORKFLOWS="/path/to/workflows.json"
# or
export PRELOAD_WORKFLOWS="https://example.com/workflows.json"
```

### Option 3: In cog.yaml

```yaml
build:
  python_version: "3.11"
  run:
    - cp workflows.json.example workflows.json
    # or download from remote:
    # - curl -o workflows.json https://example.com/workflows.json
```

## How It Works

When `preload_all_workflows()` is called:

1. **Parse** the workflows file (JSON)
2. **Detect format** (named object, explicit array, or implicit array)
3. **Extract weights** from each workflow
4. **Deduplicate** across all workflows
5. **Download** unique weights (parallel when possible)
6. **Report** progress and results

### Example Output

```
📄 Found workflows.json, auto-loading...
⏳ Preloading weights from all workflows...
  📄 flux_schnell: 5 weight(s)
  📄 flux_dev: 5 weight(s)
  📄 sdxl: 2 weight(s)

Found 8 unique weight(s) across 3 workflow(s)
⏳ Downloading 8 weight(s)...
  [1/8] flux1-schnell.safetensors... ✅
  [2/8] flux1-dev.safetensors... ✅
  [3/8] clip_l.safetensors... ✅
  [4/8] t5xxl_fp8_e4m3fn.safetensors... ✅
  [5/8] ae.safetensors... ✅
  [6/8] sd_xl_base_1.0.safetensors... ✅
  [7/8] sd_xl_refiner_1.0.safetensors... ✅
  [8/8] ... (other weights)

✅ All workflows preloaded
```

## Weight Deduplication

Shared weights across workflows are downloaded **only once**:

```json
{
  "flux_schnell": {
    "uses": ["clip_l.safetensors", "ae.safetensors", "flux1-schnell.safetensors"]
  },
  "flux_dev": {
    "uses": ["clip_l.safetensors", "ae.safetensors", "flux1-dev.safetensors"]
  }
}
```

**Downloaded weights:** `clip_l.safetensors` and `ae.safetensors` are downloaded once and shared.

## Validation

You can validate weights exist for all workflows:

```python
from comfyui import ComfyUI
import json

comfyui = ComfyUI("127.0.0.1:8188")

with open("workflows.json") as f:
    workflows = json.load(f)

all_exist, missing = comfyui.validate_weights_from_multiple_workflows(workflows)
if not all_exist:
    print(f"Missing: {missing}")
```

## Advanced: Custom Metadata

Add metadata to workflows.json for advanced use cases:

```json
{
  "metadata": {
    "version": "1.0",
    "author": "your-name",
    "description": "Production workflows",
    "tags": ["flux", "sdxl", "video"]
  },
  "workflows": [
    {
      "name": "flux_schnell",
      "tags": ["fast", "production"],
      "description": "Fast Flux inference",
      "workflow": {...}
    }
  ]
}
```

The system automatically skips metadata keys (starting with `_` or named `metadata`, `config`, `settings`).

## Examples

### Example 1: Simple Multi-Workflow

```json
{
  "flux_1": {
    "1": {"inputs": {"ckpt_name": "flux1-dev.safetensors"}, "class_type": "CheckpointLoaderSimple"},
    "2": {"inputs": {"clip_name": "clip_l.safetensors"}, "class_type": "CLIPLoader"}
  },
  "sdxl": {
    "1": {"inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  }
}
```

### Example 2: With Explicit Structure

```json
{
  "workflows": [
    {
      "name": "txt2img_flux",
      "model_type": "flux",
      "workflow": {...}
    },
    {
      "name": "txt2img_sdxl", 
      "model_type": "sdxl",
      "workflow": {...}
    }
  ]
}
```

### Example 3: Video + Image Generation

```json
{
  "image_generation": {
    "1": {"inputs": {"ckpt_name": "flux1-dev.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  },
  "video_generation": {
    "1": {"inputs": {"ckpt_name": "svd.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  },
  "upscaling": {
    "1": {"inputs": {"model_name": "RealESRGAN_x2.onnx"}, "class_type": "UpscaleModelLoader"}
  }
}
```

## Performance Impact

| Metric | Time | Notes |
|--------|------|-------|
| Parse workflows.json | <100ms | Fast JSON parsing |
| Extract weights | <50ms | No I/O, in-memory |
| Download unique weights | Depends | Parallel downloads |
| Deduplication | ~0ms | Set operations |

**Result:** All N workflows processed with minimal overhead

## Troubleshooting

### "workflows.json not found"
The file exists but path is wrong:
- Use absolute paths or relative to repository root
- Check file permissions (readable by process)

### "No weights found in X workflow(s)"
Workflows are parsed but contain no weight loaders:
- Verify workflow structure (check node class_type)
- Ensure model inputs use standard parameter names

### "Failed to preload workflows: ..."
JSON parsing error:
- Validate JSON syntax (use jsonlint online)
- Check for trailing commas
- Ensure proper encoding (UTF-8)

## Migration from Single Workflow

### Before
```bash
export PRELOAD_WORKFLOW="workflows/flux.json"
```

### After
```bash
# Create workflows.json with all your workflows
# Auto-loads during setup
```

## Performance Tips

1. **Deduplicate manually** - Put shared models first to speed up processing
2. **Group by size** - Order downloads largest first
3. **Use CDN** - Ensure weights URL points to fast server
4. **Monitor** - Check logs for bottlenecks

## See Also

- [WEIGHT_LOADING_QUICK_REF.md](WEIGHT_LOADING_QUICK_REF.md) - Quick reference
- [ROBUST_WEIGHT_LOADING.md](ROBUST_WEIGHT_LOADING.md) - Full guide
- [workflows.json.example](workflows.json.example) - Example file
