# IMPORTANT: Understanding Model Restrictions & Arbitrary Workflows

## Quick Facts

✅ **Workflows:** Can use ANY ComfyUI workflow (with parameters below)  
⚠️ **Models:** By default, limited to ~900 pre-approved models  
✅ **Solution:** Use `skip_weight_check=True` for custom models  

## The Two Levels of "Arbitrary"

### 1. Arbitrary Workflows ✅ (Now Supported)

You can use **any** ComfyUI workflow structure:
- Any nodes (standard or custom)
- Any node combinations
- Multiple inputs, parameter substitution
- Video, image, controlnet, etc.

```python
predictor.predict(
    workflow_json=any_comfyui_workflow  # Any workflow works!
)
```

### 2. Arbitrary Models ⚠️ (Requires Flag)

By default, only ~900 models in `weights.json` are supported. For custom models:

```python
predictor.predict(
    workflow_json=workflow_with_custom_model,
    skip_weight_check=True  # <-- Required for non-listed models
)
```

## Why The Restriction?

The weight/model system exists to:
1. **Cache models** - Download once, use many times
2. **Manage storage** - Not download entire internet
3. **Ensure reliability** - Known working models
4. **Track licenses** - Comply with model licenses

## How to Use Custom Models

### Option 1: Skip Weight Check (Recommended)

```python
# Your workflow uses "my_custom_model.safetensors"
predictor.predict(
    workflow_json=workflow,
    skip_weight_check=True  # Bypasses validation
)
```

**Requirements:**
- Model must exist in `ComfyUI/models/checkpoints/` (or appropriate dir)
- Provide via `weights` parameter OR bake into Docker image

### Option 2: Add to Weights Manifest

Edit `weights.json` or create `downloaded_user_models/weights.json`:

```json
{
  "CHECKPOINTS": [
    "my_custom_model.safetensors"
  ]
}
```

### Option 3: Provide via Setup

```python
predictor.setup(weights="https://example.com/my_models.tar")
predictor.predict(workflow_json=workflow, skip_weight_check=True)
```

## Complete Examples

### Example 1: Supported Model (No Changes Needed)

```python
workflow = {
    "checkpoint": {
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},  # In weights.json
        "class_type": "CheckpointLoaderSimple"
    }
}

predictor.predict(workflow_json=json.dumps(workflow))
# ✅ Works automatically
```

### Example 2: Custom Model

```python
workflow = {
    "checkpoint": {
        "inputs": {"ckpt_name": "my_finetuned_model_v3.safetensors"},  # NOT in weights.json
        "class_type": "CheckpointLoaderSimple"
    }
}

# ❌ This will fail:
# predictor.predict(workflow_json=json.dumps(workflow))
# ValueError: my_finetuned_model_v3.safetensors unavailable

# ✅ This works:
predictor.predict(
    workflow_json=json.dumps(workflow),
    skip_weight_check=True
)
```

### Example 3: Custom Model + All Features

```python
workflow = {
    "checkpoint": {
        "inputs": {"ckpt_name": "custom_model.safetensors"},
        "class_type": "CheckpointLoaderSimple"
    },
    "prompt": {
        "inputs": {"text": "{{my_prompt}}"},
        "class_type": "CLIPTextEncode"
    }
}

predictor.predict(
    workflow_json=json.dumps(workflow),
    input_file=Path("input.png"),
    input_file_2=Path("control.png"),
    workflow_params='{"my_prompt": "beautiful sunset"}',
    skip_weight_check=True,  # For custom model
    randomise_seeds=True
)
```

## What Models Are Supported By Default?

See [supported_weights.md](supported_weights.md) for the complete list:

**Categories:**
- 900+ Checkpoints (SD 1.5, SDXL, Flux, etc.)
- 400+ LoRAs
- 100+ ControlNet models
- VAEs, CLIPs, Upscalers
- And more...

**Popular models included:**
- Stable Diffusion 1.5, SDXL
- Flux (dev, schnell)
- DreamShaper, Juggernaut
- Realistic Vision
- And hundreds more

## File Structure for Custom Models

Place models in correct directories:

```
ComfyUI/models/
├── checkpoints/          # Main models (.safetensors, .ckpt)
│   └── my_model.safetensors
├── loras/                # LoRA models
│   └── my_lora.safetensors
├── controlnet/           # ControlNet models
├── vae/                  # VAE models
├── embeddings/           # Textual inversions
└── ...
```

## Decision Tree

```
Do you want to use a specific model?
│
├─ Is it in supported_weights.md?
│  ├─ YES → Use normally, no special flags needed
│  └─ NO → Continue below
│
└─ Is the model in ComfyUI/models/ already?
   ├─ YES → Use skip_weight_check=True
   └─ NO → Provide via weights parameter + skip_weight_check=True
```

## Common Errors

### Error 1: Model Not in Manifest

```
ValueError: custom_model.safetensors unavailable. 
View the list of available weights: https://...
```

**Solution:** Add `skip_weight_check=True`

### Error 2: Model File Not Found

```
Error: Could not find checkpoint at 
ComfyUI/models/checkpoints/custom_model.safetensors
```

**Solutions:**
1. Place model in correct directory
2. Check filename matches exactly
3. Provide via `weights` parameter in setup
4. Bake into Docker image

### Error 3: Wrong Directory

```
Model loads but doesn't work correctly
```

**Solution:** Ensure model type matches directory:
- Checkpoints → `checkpoints/`
- LoRAs → `loras/`
- ControlNet → `controlnet/`

## Best Practices

### ✅ DO:

- Use supported models when possible (faster, cached)
- Set `skip_weight_check=True` for any custom models
- Test workflows in ComfyUI first
- Organize models in correct directories
- Document which custom models your workflow needs

### ❌ DON'T:

- Try custom models without `skip_weight_check=True`
- Assume all models auto-download
- Mix up model directories
- Forget to check supported_weights.md first

## Summary

| What You Want | What To Do | Flag Needed |
|---------------|------------|-------------|
| Use supported model | Just use it | None |
| Use custom model (in ComfyUI/models/) | Ensure it's there | `skip_weight_check=True` |
| Use custom model (from URL) | Provide in setup() | `skip_weight_check=True` |
| Use custom model (in Docker) | Bake into image | `skip_weight_check=True` |
| Any workflow structure | Use enhanced predict.py | None (built-in) |
| Multiple inputs | Use input_file_2/3 | None (built-in) |
| Dynamic parameters | Use workflow_params | None (built-in) |

## Documentation

- **[CUSTOM_MODELS_GUIDE.md](CUSTOM_MODELS_GUIDE.md)** - Complete custom model guide
- **[ARBITRARY_WORKFLOWS_GUIDE.md](ARBITRARY_WORKFLOWS_GUIDE.md)** - Workflow features guide
- **[QUICKSTART_ARBITRARY_WORKFLOWS.md](QUICKSTART_ARBITRARY_WORKFLOWS.md)** - Quick start
- **[supported_weights.md](supported_weights.md)** - List of default models
- **[weights.json](weights.json)** - Machine-readable manifest

## Final Notes

**Yes, you can run arbitrary ComfyUI workflows!** ✅

**But for arbitrary models, use `skip_weight_check=True`** ⚠️

The system is now fully flexible - you just need to know which flag to use when. 🎉
