# Migration Guide: Using the Enhanced predict.py

## For Existing Users

### Good News: Nothing Breaks! 🎉

Your existing code continues to work exactly as before. All enhancements are **additive** and **optional**.

### Before (Still Works)
```python
# Your existing code
predictor.predict(
    workflow_json=my_workflow,
    input_file=Path("image.png"),
    randomise_seeds=True
)
```

### After (Same + More Options)
```python
# Exact same call still works
predictor.predict(
    workflow_json=my_workflow,
    input_file=Path("image.png"),
    randomise_seeds=True
)

# OR use new features if needed
predictor.predict(
    workflow_json=my_workflow,
    input_file=Path("image1.png"),
    input_file_2=Path("image2.png"),  # NEW
    input_filename_1="source.png",     # NEW
    workflow_params='{"steps": 30}',   # NEW
    randomise_seeds=True
)
```

## What's New?

### 1. Multiple Input Files (Optional)

**Before:** Only one input file
```python
predictor.predict(
    workflow_json=workflow,
    input_file=Path("image.png")
)
```

**Now:** Up to 3 input files
```python
predictor.predict(
    workflow_json=workflow,
    input_file=Path("image1.png"),
    input_file_2=Path("image2.png"),
    input_file_3=Path("mask.png")
)
```

### 2. Custom Filenames (Optional)

**Before:** Files named automatically (`input.png`, etc.)
```python
predictor.predict(
    workflow_json=workflow,
    input_file=Path("my_photo.png")
)
# Saved as: input.png
```

**Now:** Specify custom names
```python
predictor.predict(
    workflow_json=workflow,
    input_file=Path("my_photo.png"),
    input_filename_1="source_image.png"
)
# Saved as: source_image.png
```

### 3. Dynamic Parameters (New)

**Before:** Had to create different workflow JSONs
```python
workflow1 = make_workflow(prompt="a cat")
workflow2 = make_workflow(prompt="a dog")

predictor.predict(workflow_json=workflow1)
predictor.predict(workflow_json=workflow2)
```

**Now:** Use one template with parameters
```python
# Workflow template with placeholders
workflow_template = {
    "node": {
        "inputs": {"text": "{{prompt}}"},
        "class_type": "CLIPTextEncode"
    }
}

# Use with different prompts
predictor.predict(
    workflow_json=json.dumps(workflow_template),
    workflow_params='{"prompt": "a cat"}'
)

predictor.predict(
    workflow_json=json.dumps(workflow_template),
    workflow_params='{"prompt": "a dog"}'
)
```

## Common Migration Scenarios

### Scenario 1: You're Happy With Current Setup
**Action Required:** None! Keep using it as before.

### Scenario 2: You Need Multiple Input Images
**Action Required:** Add `input_file_2`, `input_file_3` parameters

Example: ControlNet with source + control image
```python
# Old way: Had to use archive or URLs
predictor.predict(
    workflow_json=workflow,
    input_file=Path("images.tar")  # Both images in tar
)

# New way: Pass files separately
predictor.predict(
    workflow_json=workflow,
    input_file=Path("source.png"),
    input_file_2=Path("control.png"),
    input_filename_1="input_image.png",
    input_filename_2="control_image.png"
)
```

### Scenario 3: You Want to Reuse Workflows with Different Parameters
**Action Required:** Add placeholders to workflow, use `workflow_params`

```python
# 1. Add placeholders to your workflow JSON
workflow = {
    "prompt_node": {
        "inputs": {
            "text": "{{my_prompt}}",  # Placeholder
            "clip": ["checkpoint", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "size_node": {
        "inputs": {
            "width": "{{width}}",     # Placeholder
            "height": "{{height}}"    # Placeholder
        },
        "class_type": "EmptyLatentImage"
    }
}

# 2. Use with different parameters
predictor.predict(
    workflow_json=json.dumps(workflow),
    workflow_params=json.dumps({
        "my_prompt": "a sunset",
        "width": 1024,
        "height": 768
    })
)
```

### Scenario 4: You Want to Use Any ComfyUI Workflow
**Action Required:** None! This already worked, but now it's more flexible

```python
# Take ANY workflow from ComfyUI (API format)
# and it will work directly

predictor.predict(
    workflow_json=any_comfyui_api_workflow
)
```

## Upgrade Checklist

- [ ] Existing workflows still work? **Yes, no changes needed**
- [ ] Need multiple input files? **Use new `input_file_2`, `input_file_3`**
- [ ] Need custom filenames? **Use `input_filename_*` parameters**
- [ ] Want reusable workflows? **Add `{{placeholders}}` and use `workflow_params`**
- [ ] Want to build workflows in code? **Use `workflow_helpers.py`**

## Examples by Use Case

### Use Case: Basic Image Generation
```python
# No changes needed
predictor.predict(workflow_json=txt2img_workflow)
```

### Use Case: Image-to-Image
```python
# No changes needed if using one image
predictor.predict(
    workflow_json=img2img_workflow,
    input_file=Path("input.png")
)
```

### Use Case: ControlNet
```python
# NEW: Can pass both images separately
predictor.predict(
    workflow_json=controlnet_workflow,
    input_file=Path("source.png"),
    input_file_2=Path("control.png"),
    input_filename_1="input.png",
    input_filename_2="control.png"
)
```

### Use Case: Face Swap
```python
# NEW: Pass source and target separately
predictor.predict(
    workflow_json=faceswap_workflow,
    input_file=Path("face.jpg"),
    input_file_2=Path("target.jpg"),
    input_filename_1="source_face.jpg",
    input_filename_2="target_image.jpg"
)
```

### Use Case: Batch Processing
```python
# Still works with archives
predictor.predict(
    workflow_json=batch_workflow,
    input_file=Path("images.tar")
)
```

### Use Case: Parameterized Generation
```python
# NEW: Use templates
predictor.predict(
    workflow_json=template_workflow,
    workflow_params='{"style": "anime", "quality": "high"}'
)
```

## Troubleshooting

### Q: Will my existing code break?
**A:** No! All changes are backward compatible.

### Q: Do I need to update my workflows?
**A:** No! Existing workflows work as-is. New features are optional.

### Q: What if I don't want to use the new features?
**A:** Don't! Everything works exactly as before.

### Q: How do I know which features to use?
**A:** 
- Single input file? Keep using as before
- Multiple inputs? Use new `input_file_2/3`
- Need flexibility? Use `workflow_params`
- Complex workflows? Check `workflow_helpers.py`

## Testing Your Migration

1. **Test existing code first**
   ```python
   # Your current code - should work unchanged
   predictor.predict(workflow_json=your_workflow)
   ```

2. **Try new features incrementally**
   ```python
   # Add one new feature at a time
   predictor.predict(
       workflow_json=your_workflow,
       input_file_2=Path("extra.png")  # Try one new thing
   )
   ```

3. **Use the test script**
   ```bash
   python test_enhancements.py
   ```

## Getting Help

1. **Quick Start:** Read [QUICKSTART_ARBITRARY_WORKFLOWS.md](QUICKSTART_ARBITRARY_WORKFLOWS.md)
2. **Full Guide:** See [ARBITRARY_WORKFLOWS_GUIDE.md](ARBITRARY_WORKFLOWS_GUIDE.md)
3. **Examples:** Check [examples/arbitrary_workflow_examples.py](examples/arbitrary_workflow_examples.py)
4. **Utilities:** Explore [workflow_helpers.py](workflow_helpers.py)

## Summary

| What | Changed? | Action Required |
|------|----------|----------------|
| Existing workflows | No | None - keep using as-is |
| Single input file | No | None - works same way |
| Basic parameters | No | None - works same way |
| Multiple inputs | **New** | Optional - use if needed |
| Custom filenames | **New** | Optional - use if needed |
| Parameter substitution | **New** | Optional - use if needed |
| Any ComfyUI workflow | Enhanced | Already worked, now more flexible |

**Bottom Line:** Your code works as-is. New features are there when you need them. 🚀
