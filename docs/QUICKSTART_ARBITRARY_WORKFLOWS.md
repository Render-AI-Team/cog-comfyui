# Quick Start: Running Arbitrary ComfyUI Workflows

## What Changed?

Your `predict.py` has been enhanced to support **ANY** ComfyUI workflow. Here's what's new:

### ⚠️ Critical: Using Custom Models

**By default, only ~900 pre-approved models work.** For custom models:

```python
predictor.predict(
    workflow_json=your_workflow,
    skip_weight_check=True  # Required for custom models!
)
```

📖 **See [CUSTOM_MODELS_GUIDE.md](CUSTOM_MODELS_GUIDE.md) for full details**

### New Features

1. **Multiple Input Files** (3 total)
   - `input_file`, `input_file_2`, `input_file_3`
   - Custom filenames: `input_filename_1`, `input_filename_2`, `input_filename_3`

2. **Dynamic Parameter Substitution**
   - Use `{{placeholder}}` in workflow JSON
   - Substitute via `workflow_params` parameter

3. **Enhanced Flexibility**
   - Any ComfyUI node/custom node supported
   - Workflow from URL or JSON string
   - Archive extraction (tar/zip)

## Quick Examples

### 1. Simple Usage (No Changes Needed)
```python
# Your existing workflows still work exactly as before
predictor.predict(workflow_json='{"node": {...}}')
```

### 2. Multiple Input Files
```python
predictor.predict(
    workflow_json=json.dumps(workflow),
    input_file=Path("image1.png"),
    input_file_2=Path("image2.png"),
    input_filename_1="source.png",
    input_filename_2="target.png"
)
```

### 3. Dynamic Parameters
```python
# Workflow with {{placeholders}}
workflow = {
    "prompt_node": {
        "inputs": {"text": "{{my_prompt}}"},
        "class_type": "CLIPTextEncode"
    }
}

predictor.predict(
    workflow_json=json.dumps(workflow),
    workflow_params='{"my_prompt": "a beautiful landscape"}'
)
```

## Files Created

1. **[ARBITRARY_WORKFLOWS_GUIDE.md](ARBITRARY_WORKFLOWS_GUIDE.md)** - Complete documentation
2. **[examples/arbitrary_workflow_examples.py](examples/arbitrary_workflow_examples.py)** - Code examples
3. **[examples/api_workflows/arbitrary_txt2img_template.json](examples/api_workflows/arbitrary_txt2img_template.json)** - Template workflow

## Key Points

✅ **Backward Compatible** - All existing workflows still work  
✅ **No Breaking Changes** - Original functionality preserved  
✅ **Fully Flexible** - Supports any ComfyUI workflow  
✅ **Well Documented** - See guide for detailed examples  

## What You Can Do Now

- ✨ Run **any** ComfyUI workflow (txt2img, img2img, video, etc.)
- 🎯 Use **any** custom nodes installed in ComfyUI
- 🔧 Pass **multiple input files** with custom names
- ⚡ Substitute **parameters dynamically** at runtime
- 📦 Upload **archives** with multiple files
- 🌐 Load workflows from **URLs**

## Next Steps

1. Read [ARBITRARY_WORKFLOWS_GUIDE.md](ARBITRARY_WORKFLOWS_GUIDE.md) for full documentation
2. Check [examples/arbitrary_workflow_examples.py](examples/arbitrary_workflow_examples.py) for code samples
3. Test with your own ComfyUI workflows!

## Need Help?

- See the guide for troubleshooting tips
- Check examples for common use cases
- Test workflows in ComfyUI first before using them here
