# Robust Weight Loading Implementation Guide

## Problem Summary

Dynamic weight loading at runtime was unreliable due to:
- Network failures during predict()
- Large model download timeouts  
- No persistence between runs
- Race conditions and timing issues
- Unpredictable latency

## Solution: Hybrid Preload + Validate Strategy

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ SETUP PHASE (One-time, before any predictions)             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Load user weights (if provided)                         │
│  2. Preload base model kit (optional, via env var)          │
│  3. Preload workflow weights (optional, via env var)        │
│  4. Start ComfyUI server                                    │
│                                                             │
│  Result: All common weights downloaded & validated          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PREDICT PHASE (Every request)                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Parse workflow JSON                                     │
│  2. Extract required weights (fast)                         │
│  3. Validate all weights exist (fast local check)           │
│                                                             │
│     ┌─ All exist? ────────────────> Proceed with workflow  │
│     │                                                        │
│     └─ Missing? ───> Two options:                           │
│                      a) Fail fast with clear error ←─ DEFAULT
│                      b) Download if flag enabled            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Improvements

1. **Preloading** - Download weights during setup(), not predict()
2. **Fast Validation** - Check existence without downloading
3. **Fail-Fast** - Clear errors before expensive processing
4. **Flexibility** - Support multiple loading strategies

## Usage

### 1. Environment Variable Configuration

Set these before setup() runs:

```bash
# Preload a common model kit
export BASE_MODEL_KIT="flux"  # Options: sd15, sdxl, flux, none (default)

# Preload specific workflow weights
export PRELOAD_WORKFLOW="/path/to/workflow.json"
# or
export PRELOAD_WORKFLOW="https://example.com/workflow.json"
```

### 2. Base Model Kits

Available kits in [predict.py](predict.py#L71-L91):

- **sd15**: Stable Diffusion 1.5 models
- **sdxl**: SDXL base + refiner
- **flux**: Flux dev + encoders
- **none** (default): No preloading

### 3. Workflow Preloading

Provide a workflow JSON during setup to download all its weights:

```bash
export PRELOAD_WORKFLOW="examples/api_workflows/flux_schnell_api.json"
```

The system will:
1. Parse the workflow
2. Extract all required weights  
3. Download them before any predictions run

### 4. Runtime Validation

During predict(), the system:
1. Extracts weights from workflow (via `extract_required_weights()`)
2. Validates they exist locally (via `validate_weights_exist()`)
3. Fails fast with clear error if missing

## New Methods

### In [comfyui.py](comfyui.py)

#### `extract_required_weights(workflow)` 

Parses workflow and returns list of all required model files.

```python
weights = comfyui.extract_required_weights(workflow)
# Returns: ['flux1-dev.safetensors', 'clip_l.safetensors', ...]
```

#### `validate_weights_exist(workflow, skip_check=False)`

Fast check if all required weights exist locally.

```python
all_exist, missing = comfyui.validate_weights_exist(workflow)
if not all_exist:
    raise ValueError(f"Missing weights: {missing}")
```

### In [predict.py](predict.py)

#### `preload_base_kit(kit_name)`

Downloads predefined model sets.

#### `preload_workflow_weights(workflow_json)`  

Downloads all weights for a specific workflow.

## Migration Guide

### Before (Unreliable)

```python
def predict(self, workflow_json: str):
    workflow = json.loads(workflow_json)
    # Weights downloaded during handle_weights()
    # Network failures cause prediction failures
    self.comfyUI.load_workflow(workflow)
```

### After (Robust)

```python
def setup(self, weights: str):
    # Option 1: Preload via environment
    if os.environ.get("BASE_MODEL_KIT") == "flux":
        self.preload_base_kit("flux")
    
    # Option 2: Preload specific workflow
    if workflow := os.environ.get("PRELOAD_WORKFLOW"):
        self.preload_workflow_weights(workflow)

def predict(self, workflow_json: str):
    workflow = json.loads(workflow_json)
    
    # Validate before processing (fast)
    all_exist, missing = self.comfyUI.validate_weights_exist(workflow)
    if not all_exist:
        raise ValueError(
            f"Missing required weights: {', '.join(missing)}\\n"
            f"Please ensure these are available or set PRELOAD_WORKFLOW."
        )
    
    # Proceed knowing all weights exist
    self.comfyUI.load_workflow(workflow)
```

## Benefits

### Reliability

- ✅ No network calls during predict()
- ✅ No download timeouts
- ✅ Deterministic behavior

### Performance  

- ✅ Fast local validation (< 1ms per file)
- ✅ No redundant downloads
- ✅ Predictable latency

### Developer Experience

- ✅ Clear error messages
- ✅ Fail-fast validation
- ✅ Easy debugging

### Flexibility

- ✅ Support custom models via user weights
- ✅ Multiple preload strategies
- ✅ Backward compatible

## Advanced Usage

### Custom Weight Bundles

Create a custom preload script:

```python
def preload_custom_kit(self):
    downloader = WeightsDownloader()
    custom_models = [
        "my-custom-model.safetensors",
        "my-lora.safetensors",
    ]
    for model in custom_models:
        downloader.download_weights(model)
```

### Conditional Preloading

Preload based on model type:

```python
model_type = os.environ.get("MODEL_TYPE")
if model_type == "video":
    self.preload_base_kit("video")  # You can add this kit
elif model_type == "flux":
    self.preload_base_kit("flux")
```

### Workflow Metadata

Add weight requirements to workflow JSON:

```json
{
  "_meta": {
    "title": "Flux Schnell Workflow",
    "required_weights": [
      "flux1-schnell.safetensors",
      "clip_l.safetensors",
      "ae.safetensors"
    ]
  },
  "nodes": { ... }
}
```

Then validate:

```python
if "_meta" in workflow and "required_weights" in workflow["_meta"]:
    for weight in workflow["_meta"]["required_weights"]:
        if not self.weight_exists(weight):
            raise ValueError(f"Missing required weight: {weight}")
```

## Troubleshooting

### "Missing required weights" error

**Cause**: Weights not available locally

**Solutions**:
1. Set `BASE_MODEL_KIT` environment variable
2. Set `PRELOAD_WORKFLOW` to your workflow path
3. Provide weights via setup `weights` parameter
4. Set `skip_weight_check=True` (not recommended)

### Slow setup times

**Cause**: Downloading too many weights

**Solutions**:
1. Use smaller base kit (sd15 instead of flux)
2. Pre-bake weights into container image
3. Only preload workflows you actually use

### Weight not in manifest

**Cause**: Custom/arbitrary model not in weights.json

**Solutions**:
1. Add to custom weights manifest
2. Provide via user weights tar
3. Use `skip_weight_check=True` and ensure file exists

## Future Enhancements

### Possible Additions

1. **Weight caching layer** - Shared cache across instances
2. **Lazy loading** - Download on first use, cache for subsequent
3. **Weight versioning** - Track and update model versions
4. **Bandwidth optimization** - Parallel downloads, resume support
5. **Container layers** - Pre-baked weight layers for fast startup

### Community Contributions

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add:
- New base model kits
- Weight validation strategies  
- Caching implementations
- Performance optimizations
