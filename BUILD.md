# Building with Automatic Workflow Dependencies

When you run `cog build`, the system automatically detects and installs workflow dependencies (custom nodes and models) before initializing ComfyUI. This eliminates manual setup steps.

## Quick Start

### Option 1: Auto-Detection (Recommended)

Place a `workflows.json` file in your project root with your ComfyUI workflows. Everything installs automatically:

```bash
cog build
```

The builder will:
1. Detect `workflows.json`
2. Auto-install all required custom nodes
3. Auto-download all required models to correct directories
4. Initialize ComfyUI with everything ready

### Option 2: With Environment Variables

```bash
export PRELOAD_WORKFLOWS="workflows.json"
export BASE_MODEL_KIT="flux"  # optional: sd15, sdxl, flux, or none
cog build
```

Installs the same way as Option 1.

### Option 3: Manual Installation (No Auto-Setup)

If you don't have `workflows.json` or environment variables set:

```bash
# Just run normal build (no automatic installer)
cog build

# Manually install dependencies if needed
python workflow_dependency_installer.py
```

## How It Works

When `cog build` runs:

```
1. Predictor.setup() is called
2. Detects if workflows will be used
3. If workflows found → Auto-runs dependency installer
   - Extracts custom node requirements
   - Downloads and installs custom nodes
   - Extracts model requirements  
   - Downloads and categorizes models
4. ComfyUI initializes (all dependencies ready)
5. Build completes
```

## What Gets Installed

### Custom Nodes
- Installed to `ComfyUI/custom_nodes/`
- Auto-detects base nodes (never reinstalled)
- Fetches additional nodes from ComfyUI Manager

### Models  
- Auto-categorized to correct directories:
  - `checkpoints/` - Main diffusion models (SD, SDXL, Flux)
  - `loras/` - LoRA adapters
  - `controlnet/` - ControlNet models
  - `upscale_models/` - Super-resolution
  - `vae/` - VAE models
  - Plus 13+ more categories

## Features

✅ **Automatic** - Runs during `cog build`, zero manual steps  
✅ **Smart Detection** - Identifies 18+ model types  
✅ **Resumable** - Tracks progress in `.installation_progress.json`  
✅ **Robust** - Retries failed downloads, multiple fallback downloaders  
✅ **Backward Compatible** - Manual script still works standalone  

## Troubleshooting

**Installer not running?**
- Confirm `workflows.json` exists OR env vars are set
- Check logs for "Auto-installing workflow dependencies..."

**Models not in right place?**
- Check `ComfyUI/models/{type}/` for downloaded files
- Check `.installation_progress.json` for what was installed

**Interrupted build?**
- Re-run `cog build` - resumes from progress checkpoint
- Or manually run: `python workflow_dependency_installer.py`

## Files

- `workflow_dependency_installer.py` - Standalone dependency installer
- `predict.py` - Integrated with automatic detection
- `workflows.json` - Your workflows (auto-detected)
