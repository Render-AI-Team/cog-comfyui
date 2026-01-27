# Robust Weight Loading Strategy

## Core Principles

1. **Preload during setup()** - Download all required weights before any predict() calls
2. **Fail-fast validation** - Verify all weights exist before workflow execution
3. **Local manifest** - No runtime fetching of remote manifests
4. **Explicit dependencies** - Declare required weights in workflow metadata or cog.yaml

## Implementation Options

### Option 1: Workflow Metadata Declaration (Recommended)

Add a `required_weights` field to workflow JSON that declares all needed models upfront.

```json
{
  "_meta": {
    "required_weights": [
      "flux1-dev.safetensors",
      "clip_l.safetensors",
      "t5xxl_fp8_e4m3fn.safetensors",
      "ae.safetensors"
    ]
  },
  "nodes": { ... }
}
```

**Benefits:**
- Self-documenting workflows
- Can validate weights before accepting workflow
- Enables pre-downloading on setup
- Clear error messages about missing dependencies

### Option 2: Pre-bake Common Weight Sets

Create multiple container images with different weight bundles pre-installed.

**Variants:**
- `base`: Core SD 1.5 models
- `sdxl`: SDXL models
- `flux`: Flux models
- `video`: Video generation models (SVD, AnimateDiff, etc.)
- `all`: Everything (large image)

**Benefits:**
- Zero download time at runtime
- Guaranteed availability
- Predictable performance

**Drawbacks:**
- Large image sizes
- Multiple images to maintain
- Less flexible for custom models

### Option 3: Required Weights in cog.yaml

Declare weight dependencies in cog.yaml for static analysis.

```yaml
build:
  python_version: "3.11"
  run:
    - ...

predict:
  weights:
    - flux1-dev.safetensors
    - clip_l.safetensors
```

**Benefits:**
- Build-time validation possible
- Clear dependency declaration
- Works with existing cog tooling

### Option 4: Aggressive Setup Preloading

Parse workflow during setup() and download all weights before server starts.

**Implementation:**
```python
def setup(self, weights: str, workflow_json: str = None):
    # Download user weights
    if weights:
        self.handle_user_weights(weights)
    
    # Parse and preload workflow weights
    if workflow_json:
        workflow = json.loads(workflow_json)
        required_weights = self.extract_all_weights(workflow)
        self.download_all_weights_sync(required_weights)
    
    # Start ComfyUI server
    self.comfyUI = ComfyUI("127.0.0.1:8188")
```

**Benefits:**
- No runtime downloads
- Clear setup phase errors
- Works with existing workflow format

**Drawbacks:**
- Requires workflow at setup time (not always available)
- Less flexible for dynamic workflows

## Recommended Hybrid Approach

**Best of all worlds:**

1. **Setup Phase:**
   - Download "base kit" of common models (configurable)
   - Support optional workflow pre-loading via setup parameter
   - Validate local weights manifest
2. **Predict Phase:**
   - Parse workflow and extract ALL weight requirements
   - **Validate** all weights exist locally (fast check)
   - If any missing: fail fast with clear error listing missing weights
   - Only download if explicitly flagged with `allow_runtime_downloads=True`
3. **Workflow Metadata:**
   - Encourage (but don't require) `required_weights` in workflows
   - Use for pre-validation and better error messages

## Implementation Code

See the updated predict.py implementation that:
- Separates weight validation from downloading
- Provides clear error messages about missing weights
- Supports opt-in runtime downloads
- Fails fast before expensive ComfyUI processing

## Migration Path

1. Update `handle_weights()` to separate validate vs. download
2. Add `validate_weights_exist()` method that's fast and deterministic
3. Add setup parameter for workflow pre-loading
4. Update documentation to recommend pre-loading strategies
5. Provide clear error messages guiding users to solutions