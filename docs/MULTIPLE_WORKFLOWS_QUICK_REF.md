# Multiple Workflows - Quick Reference

## TL;DR

Load and preload weights for **multiple workflows** from a single `workflows.json` file.

## Quick Start

```bash
# 1. Create workflows.json
cp workflows.json.example workflows.json

# 2. Edit with your workflows (see examples below)

# 3. Deploy - auto-loads during setup
cog predict -i workflow_json=@myworkflow.json
```

No environment variables needed - auto-detection just works!

## JSON Formats

### Format 1: Named Object (Recommended ⭐)
```json
{
  "flux_schnell": {
    "1": {"inputs": {"ckpt_name": "flux1-schnell.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  },
  "sdxl": {
    "1": {"inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple"}
  }
}
```

### Format 2: Explicit Array
```json
{
  "workflows": [
    {"name": "flux_schnell", "workflow": {...}},
    {"name": "sdxl", "workflow": {...}}
  ]
}
```

### Format 3: Implicit Array
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

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PRELOAD_WORKFLOWS` | (none) | Explicitly load workflows file |
| `PRELOAD_WORKFLOW` | (none) | Single workflow (fallback) |
| `BASE_MODEL_KIT` | `none` | Preload model kit (sd15, sdxl, flux) |

## Loading Priority

1. **Auto-detection**: If `workflows.json` exists → load it
2. **Env var**: If `PRELOAD_WORKFLOWS` set → load it
3. **Single workflow**: If `PRELOAD_WORKFLOW` set → load it
4. **None**: No preloading (load on-demand)

## Features

✅ **Auto-detection** - Just create `workflows.json` and it auto-loads
✅ **Deduplication** - Shared weights downloaded only once
✅ **Multiple formats** - Flexible JSON structure options
✅ **Progress tracking** - Clear output of what's being loaded
✅ **Validation** - Fast checks that all weights exist

## Output Example

```
📄 Found workflows.json, auto-loading...
⏳ Preloading weights from all workflows...
  📄 flux_schnell: 5 weight(s)
  📄 sdxl: 2 weight(s)

Found 6 unique weight(s) across 2 workflow(s)
⏳ Downloading 6 weight(s)...
  [1/6] flux1-schnell.safetensors... ✅
  [2/6] flux1-dev.safetensors... ✅
  [3/6] clip_l.safetensors... ✅
  [4/6] ae.safetensors... ✅
  [5/6] sd_xl_base_1.0.safetensors... ✅
  [6/6] sd_xl_refiner_1.0.safetensors... ✅

✅ All workflows preloaded
```

## Methods

### Extract weights from multiple workflows
```python
weights = comfyui.extract_weights_from_multiple_workflows(workflows_data)
# Returns set of all unique weights
```

### Validate weights exist
```python
all_exist, missing = comfyui.validate_weights_from_multiple_workflows(workflows_data)
if not all_exist:
    print(f"Missing: {missing}")
```

### Preload from file
```python
predictor.preload_all_workflows("workflows.json")
# or
predictor.preload_all_workflows("https://example.com/workflows.json")
```

## Common Workflows

### Multi-Model Inference
```json
{
  "fast": {"1": {"ckpt_name": "flux1-schnell.safetensors"}},
  "quality": {"1": {"ckpt_name": "flux1-dev.safetensors"}},
  "sdxl": {"1": {"ckpt_name": "sd_xl_base_1.0.safetensors"}}
}
```

### Image + Video Generation
```json
{
  "image": {"1": {"ckpt_name": "flux1-dev.safetensors"}},
  "video": {"1": {"ckpt_name": "svd.safetensors"}},
  "upscale": {"1": {"model_name": "RealESRGAN_x2.onnx"}}
}
```

### Production Pipeline
```json
{
  "preprocess": {...},
  "inference": {...},
  "postprocess": {...}
}
```

## cog.yaml Configuration

```yaml
build:
  python_version: "3.11"
  run:
    - cp workflows.json.example workflows.json
    # Optional: download from remote
    # - curl -o workflows.json https://example.com/workflows.json
```

## Tips

### Performance
- Order workflows by size (largest first)
- Shared weights are deduped automatically
- All downloads happen during setup

### Debugging
- Check logs during setup for which workflows are found
- Validate JSON with `python -m json.tool workflows.json`
- Use verbose output to track weight downloads

### Best Practices
- Use Format 1 (named object) for clarity
- Add metadata for documentation
- Keep workflows.json in version control
- Test locally before deploying

## Troubleshooting

| Issue | Solution |
|-------|----------|
| workflows.json not found | Check path, must be in repo root |
| No weights extracted | Validate workflow structure and node types |
| JSON parse error | Check syntax: `python -m json.tool workflows.json` |
| Wrong format detected | Use explicit "workflows" key if ambiguous |

## Examples

See:
- [workflows.json.example](workflows.json.example) - Example file
- [example_multiple_workflows.sh](example_multiple_workflows.sh) - Usage guide
- [MULTIPLE_WORKFLOWS.md](MULTIPLE_WORKFLOWS.md) - Full documentation

## Status

✅ **Fully implemented and tested**
- Auto-detection works
- All formats supported
- Deduplication working
- Validation present

---

**For more details:** [MULTIPLE_WORKFLOWS.md](MULTIPLE_WORKFLOWS.md)
