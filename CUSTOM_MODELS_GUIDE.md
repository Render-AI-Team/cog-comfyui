# Using Arbitrary/Custom Models and Weights

## The Weight Restriction System

By default, this Cog-ComfyUI setup **restricts which models can be used** to a predefined list in `weights.json` (~900+ models). This is by design to:

- Ensure models are cached and available
- Provide consistent, reliable inference
- Manage storage and download bandwidth
- Comply with licensing requirements

## How to Use Arbitrary/Unsupported Models

There are **3 methods** to use models not in the supported weights list:

### Method 1: Skip Weight Checks (Simplest)

Use the `skip_weight_check` parameter to bypass the weight validation:

```python
predictor.predict(
    workflow_json=your_workflow,
    skip_weight_check=True  # <-- This bypasses the weights.json check
)
```

**Requirements:**
- Models must already exist in `ComfyUI/models/` directories
- You need to provide models via the `weights` parameter in setup OR
- Models are baked into your Docker image

**Example:**
```python
# In cog.yaml, provide custom weights
build:
  python_version: "3.11"
predict: "predict.py:Predictor"
train: "train.py:train"
```

Then run with:
```python
predictor.predict(
    workflow_json=workflow_with_custom_model,
    skip_weight_check=True
)
```

### Method 2: Add Models to weights.json

Add your custom models to the manifest:

1. **Local weights.json**

   Edit `weights.json` and add your model:
   ```json
   {
     "CHECKPOINTS": [
       "my_custom_model.safetensors",
       ...existing models...
     ]
   }
   ```
2. **User weights manifest**

   Create `downloaded_user_models/weights.json`:
   ```json
   {
     "CHECKPOINTS": [
       "my_custom_model.safetensors"
     ],
     "LORAS": [
       "my_custom_lora.safetensors"
     ]
   }
   ```

The system will merge these with the main weights.json.

### Method 3: Provide Weights via Setup

Use the `weights` parameter in the Predictor setup:

```python
class Predictor(BasePredictor):
    def setup(self, weights: str):
        # weights should be a URL to a tar file with your models
        # Structure: tar file containing model folders
        # Example: checkpoints/my_model.safetensors
        #          loras/my_lora.safetensors
        if weights:
            self.handle_user_weights(weights)
        ...
```

Then call with weights URL:
```python
predictor = Predictor()
predictor.setup(weights="https://example.com/my_models.tar")

predictor.predict(
    workflow_json=workflow,
    skip_weight_check=True
)
```

## Model File Organization

ComfyUI expects models in specific directories:

```
ComfyUI/models/
├── checkpoints/          # Main models (.safetensors, .ckpt)
├── loras/                # LoRA models
├── vae/                  # VAE models
├── clip/                 # CLIP models
├── clip_vision/          # CLIP Vision models
├── controlnet/           # ControlNet models
├── embeddings/           # Textual inversions/embeddings
├── upscale_models/       # Upscale models
├── unet/                 # U-Net models
├── diffusion_models/     # Diffusion models
└── ...and more
```

Place your custom models in the appropriate directory.

## Complete Example: Custom Model Workflow

### Scenario: Using a custom Stable Diffusion model

```python
# 1. Create your workflow in ComfyUI with your custom model
workflow = {
    "checkpoint_loader": {
        "inputs": {
            "ckpt_name": "my_awesome_model_v2.safetensors"  # Not in weights.json
        },
        "class_type": "CheckpointLoaderSimple"
    },
    # ... rest of workflow
}

# 2. Option A: Skip weight check (model must already exist)
predictor.predict(
    workflow_json=json.dumps(workflow),
    skip_weight_check=True
)

# 2. Option B: Provide models in setup
predictor.setup(weights="https://myserver.com/models.tar")
predictor.predict(
    workflow_json=json.dumps(workflow),
    skip_weight_check=True
)
```

## Combining with Other Features

You can combine `skip_weight_check` with all other arbitrary workflow features:

```python
predictor.predict(
    workflow_json=workflow_with_custom_model,
    input_file=Path("image.png"),
    input_file_2=Path("control.png"),
    workflow_params='{"steps": 30}',
    skip_weight_check=True,  # Use custom model
    randomise_seeds=True
)
```

## Using ComfyUI Custom Nodes with Custom Models

Many custom nodes come with their own models. Example:

```python
# Workflow using custom node that downloads its own models
workflow = {
    "face_restoration": {
        "inputs": {
            "image": ["load_image", 0],
            "model": "CodeFormer"  # Custom node's model
        },
        "class_type": "FaceRestoration"  # Custom node
    }
}

predictor.predict(
    workflow_json=json.dumps(workflow),
    input_file=Path("face.jpg"),
    skip_weight_check=True  # Custom node handles its own models
)
```

## What Models Are Currently Supported?

See these files for supported models:
- [supported_weights.md](supported_weights.md) - Full list with categories
- [weights.json](weights.json) - Machine-readable manifest

Categories include:
- 900+ Checkpoints (SD, SDXL, Flux, etc.)
- 400+ LoRAs
- 100+ ControlNet models
- VAEs, CLIPs, Upscalers, and more

## Adding Models to Your Docker Image

To bake custom models into your Docker image:

```dockerfile
# In your Dockerfile or cog.yaml
FROM r8.im/replicate/cog-comfyui

# Copy your models
COPY my_models/checkpoints/*.safetensors /src/ComfyUI/models/checkpoints/
COPY my_models/loras/*.safetensors /src/ComfyUI/models/loras/
```

Then use with `skip_weight_check=True`.

## Troubleshooting

### Error: "weight_str unavailable"

```
ValueError: my_model.safetensors unavailable. View the list of available weights...
```

**Solution:** Use `skip_weight_check=True` in your predict call.

### Error: Model file not found

```
Error: Could not find checkpoint at ComfyUI/models/checkpoints/my_model.safetensors
```

**Solutions:**
1. Ensure model is in correct directory
2. Check filename spelling matches workflow exactly
3. Provide models via `weights` parameter in setup
4. Verify model was included in Docker image

### Model downloads but isn't used

**Solution:** Make sure `skip_weight_check=True` is set, AND the model filename in your workflow matches the actual file.

### Custom node can't find its models

**Solution:** 
1. Check if the custom node downloads models automatically
2. Use `skip_weight_check=True`
3. Ensure custom node's model directory exists

## Best Practices

### ✅ DO:

- Use `skip_weight_check=True` for any custom models
- Organize models in correct ComfyUI directories
- Test workflows in ComfyUI first
- Document which custom models your workflow needs
- Provide models via weights.tar if deploying

### ❌ DON'T:

- Try to use unsupported models without `skip_weight_check=True`
- Put models in wrong directories
- Assume models will auto-download (unless using supported weights)
- Mix up model filenames

## Summary Table

| Scenario                     | Method        | skip_weight_check | Requirements             |
| ---------------------------- | ------------- | ----------------- | ------------------------ |
| Use supported model          | Default       | `False`           | Model in weights.json    |
| Use custom model (baked in)  | Skip check    | `True`            | Model in ComfyUI/models/ |
| Use custom model (from URL)  | Setup + Skip  | `True`            | Provide via setup()      |
| Use custom model (in Docker) | Skip check    | `True`            | Built into image         |
| Add to supported list        | Edit manifest | `False`           | Edit weights.json        |
| Custom node's models         | Skip check    | `True`            | Node handles downloads   |

## Quick Reference

```python
# Supported model (default behavior)
predictor.predict(workflow_json=workflow)

# Custom model (already in ComfyUI/models/)
predictor.predict(workflow_json=workflow, skip_weight_check=True)

# Custom model (from URL)
predictor.setup(weights="https://example.com/models.tar")
predictor.predict(workflow_json=workflow, skip_weight_check=True)

# Custom model (with all features)
predictor.predict(
    workflow_json=workflow,
    input_file=Path("input.png"),
    workflow_params='{"steps": 30}',
    skip_weight_check=True
)
```

---

Now you can use **truly arbitrary** models and workflows! 🎉
