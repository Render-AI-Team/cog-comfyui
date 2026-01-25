# Running Arbitrary ComfyUI Workflows Guide

This Cog model has been enhanced to support running **any** ComfyUI workflow with maximum flexibility.

## ⚠️ IMPORTANT: Model/Weight Restrictions

By default, this system **only supports models listed in [weights.json](weights.json)**. If your workflow uses custom or unsupported models:

1. **Use `skip_weight_check=True`** in your predict call
2. **Ensure models exist** in `ComfyUI/models/` directories
3. **See [CUSTOM_MODELS_GUIDE.md](CUSTOM_MODELS_GUIDE.md)** for complete instructions

```python
# For workflows with custom/unsupported models
predictor.predict(
    workflow_json=your_workflow,
    skip_weight_check=True  # <-- Required for non-listed models
)
```

## Key Features

### 1. **Multiple Input Files**

You can now provide up to 3 separate input files with custom filenames:
- `input_file` - Primary input file
- `input_file_2` - Second input file  
- `input_file_3` - Third input file

Each can have a custom filename specified via:
- `input_filename_1`, `input_filename_2`, `input_filename_3`

### 2. **Dynamic Parameter Substitution**

Use placeholders in your workflow JSON and substitute them at runtime using the `workflow_params` input.

### 3. **Flexible Input Types**

Supports:
- Images (jpg, jpeg, png, webp)
- Videos (mp4, mov, avi, mkv, webm)
- Archives (tar, zip) - automatically extracted
- URLs in workflow JSON - automatically downloaded

### 4. **Any ComfyUI Node**

The model supports all ComfyUI nodes including:
- Custom nodes
- ControlNet
- IPAdapter
- AnimateDiff
- Video processing
- Any installed custom node

## Usage Examples

### Example 1: Basic Image Generation

```python
from cog import Path

workflow = {
    "3": {
        "inputs": {
            "seed": 42,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    },
    "4": {"inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"},
    "5": {"inputs": {"width": 1024, "height": 1024, "batch_size": 1}, "class_type": "EmptyLatentImage"},
    "6": {"inputs": {"text": "a beautiful landscape", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
    "7": {"inputs": {"text": "ugly, blurry", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
    "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
    "9": {"inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]}, "class_type": "SaveImage"}
}

predictor.predict(
    workflow_json=json.dumps(workflow),
    randomise_seeds=True
)
```

### Example 2: Multiple Input Files

```python
# ControlNet with reference image
predictor.predict(
    workflow_json=json.dumps(controlnet_workflow),
    input_file=Path("main_image.png"),
    input_file_2=Path("controlnet_image.png"),
    input_filename_1="input_image.png",
    input_filename_2="control_image.png"
)
```

### Example 3: Dynamic Parameter Substitution

```python
# Workflow with placeholders
workflow_template = {
    "6": {
        "inputs": {
            "text": "{{prompt}}",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "5": {
        "inputs": {
            "width": "{{width}}",
            "height": "{{height}}",
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    }
}

# Substitute parameters at runtime
predictor.predict(
    workflow_json=json.dumps(workflow_template),
    workflow_params=json.dumps({
        "prompt": "a cyberpunk city at night",
        "width": 1024,
        "height": 768
    })
)
```

### Example 4: Video Processing

```python
predictor.predict(
    workflow_json=json.dumps(video_workflow),
    input_file=Path("video.mp4"),
    input_filename_1="input_video.mp4",
    return_temp_files=True  # Get intermediate frames
)
```

### Example 5: Face Swap with Multiple Images

```python
predictor.predict(
    workflow_json=json.dumps(face_swap_workflow),
    input_file=Path("source_face.jpg"),
    input_file_2=Path("target_image.jpg"),
    input_filename_1="source.jpg",
    input_filename_2="target.jpg"
)
```

## Advanced Techniques

### Using URLs Instead of Files

You can embed URLs directly in your workflow JSON:

```python
workflow = {
    "1": {
        "inputs": {
            "image": "https://example.com/image.png"
        },
        "class_type": "LoadImage"
    }
}
```

### Batch Processing with Archives

Upload a tar or zip file with multiple images:

```python
predictor.predict(
    workflow_json=json.dumps(batch_workflow),
    input_file=Path("images.tar")  # Contains img1.png, img2.png, etc.
)
```

### Custom Nodes

Any custom node installed in ComfyUI is automatically available:

```python
workflow = {
    "1": {
        "inputs": {...},
        "class_type": "AnyCustomNode"  # Works with any custom node
    }
}
```

## Workflow JSON Format

Your workflow must be in **API format**. To get this from ComfyUI:

1. Create your workflow in ComfyUI UI
2. Click "Save (API Format)" instead of regular "Save"
3. This gives you the JSON that this model needs

The API format looks like:

```json
{
  "node_id": {
    "inputs": {
      "param1": "value1",
      "param2": ["other_node_id", output_index]
    },
    "class_type": "NodeClassName"
  }
}
```

## Input Parameters Reference

| Parameter           | Type | Description                                         |
| ------------------- | ---- | --------------------------------------------------- |
| `workflow_json`     | str  | ComfyUI workflow in API format (JSON string or URL) |
| `input_file`        | Path | Primary input file                                  |
| `input_file_2`      | Path | Second input file                                   |
| `input_file_3`      | Path | Third input file                                    |
| `input_filename_1`  | str  | Custom name for input_file                          |
| `input_filename_2`  | str  | Custom name for input_file_2                        |
| `input_filename_3`  | str  | Custom name for input_file_3                        |
| `workflow_params`   | str  | JSON object for parameter substitution              |
| `return_temp_files` | bool | Include temporary/intermediate files in output      |
| `output_format`     | str  | Output image format (webp, jpg, png)                |
| `output_quality`    | int  | Output quality (0-100)                              |
| `randomise_seeds`   | bool | Auto-randomize seed values                          |
| `force_reset_cache` | bool | Clear cache before running                          |
| `skip_weight_check` | bool | Skip weight validation for custom models            |

## Tips for Success

### 1. Test in ComfyUI First

Always test your workflow in ComfyUI before using it here.

### 2. Use Descriptive Filenames

Match the filenames your workflow expects:
```python
input_filename_1="input_image.png"  # If workflow uses LoadImage with "input_image.png"
```

### 3. Check Node Names

Ensure all nodes in your workflow use their correct `class_type` names.

### 4. Handle Seeds

- Set `randomise_seeds=True` for varied outputs
- Set `randomise_seeds=False` for reproducible results

### 5. Debugging

- Use `return_temp_files=True` to see intermediate outputs
- Use `force_reset_cache=True` if you get unexpected results

## Common Use Cases

### Text-to-Image

```python
predictor.predict(workflow_json=txt2img_workflow)
```

### Image-to-Image  

```python
predictor.predict(
    workflow_json=img2img_workflow,
    input_file=Path("input.png")
)
```

### ControlNet

```python
predictor.predict(
    workflow_json=controlnet_workflow,
    input_file=Path("source.png"),
    input_file_2=Path("control.png")
)
```

### Upscaling

```python
predictor.predict(
    workflow_json=upscale_workflow,
    input_file=Path("low_res.png")
)
```

### Video Generation

```python
predictor.predict(
    workflow_json=video_workflow,
    input_file=Path("init_frame.png")
)
```

### Face Restoration

```python
predictor.predict(
    workflow_json=face_restore_workflow,
    input_file=Path("face.jpg")
)
```

## Troubleshooting

### "Node not found" Error

- Ensure the custom node is installed
- Check the `class_type` is correct

### "File not found" Error  

- Verify `input_filename_*` matches what your workflow expects
- Check the file was uploaded correctly

### Missing Outputs

- Ensure your workflow has a SaveImage node
- Check `return_temp_files=True` to see all outputs

### Workflow Runs But No Output

- Verify the SaveImage node's `filename_prefix`
- Check for errors in ComfyUI logs

## Examples Repository

Check the `examples/` directory for ready-to-use workflow templates:
- `examples/api_workflows/` - Various workflow JSON files
- `examples/ui_workflows/` - UI workflows (need conversion to API format)

## Need More Input Files?

If you need more than 3 input files, you can:
1. Use a tar/zip archive with all files
2. Use URLs in your workflow JSON
3. Modify `predict.py` to add more `input_file_*` parameters
