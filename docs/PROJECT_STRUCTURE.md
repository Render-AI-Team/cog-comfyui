# Project Structure

This document explains the organization of the cog-comfyui project.

## Root Directory

### Core Application Files

- `predict.py` - Main prediction entry point with weight preloading
- `comfyui.py` - ComfyUI interface and weight management
- `config.py` - Central configuration for all paths and settings
- `cog.yaml` - Cog configuration for Replicate deployment
- `requirements.txt` - Python dependencies

### Example & Demo Files

- `example_predict.py` - Example usage of the predictor
- `workflows.json.example` - Example multiple workflows file
- `reset.json` - Reset configuration

### Weight Management

- `weights.json` - Index of available weights
- `weight_synonyms.json` - Aliases for model names
- `updated_weights.json` - Auto-updated weight manifest (generated)
- `supported_weights.md` - Documentation of supported models
- `weights_licenses.md` - License information for models
- `weights_manifest.py` - Manifest downloading and caching
- `weights_downloader.py` - Weight downloading logic

### Workflow & Node Management

- `workflow_converter.py` - Convert between workflow formats
- `workflow_helpers.py` - Utility functions for workflows
- `custom_nodes.json` - Custom node configurations
- `custom_node_helper.py` - Helper for custom node management
- `custom_node_class_map.json` - Mapping of node classes
- `fetch_manager_node_map.py` - Fetch node mapping from ComfyUI Manager

### Training & Utilities

- `train.py` - Model training script
- `node.py` - Node definitions

### System Files

- `.gitignore` - Git exclusions (all dynamic content)
- `LICENSE` - Project license
- `README.md` - Main project documentation
- `CHANGELOG.md` - Version history

---

## `/docs` Directory

**Documentation and guides** - organized by topic.

### Getting Started

- `INDEX.md` - Documentation index (START HERE)
- `QUICKSTART_ARBITRARY_WORKFLOWS.md` - Quick start guide

### Guides

- `CUSTOM_MODELS_GUIDE.md` - Adding custom models
- `MAKING_A_MODEL_GUIDE.md` - Creating models
- `ARBITRARY_MODELS_EXPLAINED.md` - Understanding model loading
- `ARBITRARY_WORKFLOWS_GUIDE.md` - Running arbitrary workflows

### Weight Loading System

- `WEIGHT_LOADING_STRATEGY.md` - Overall design strategy
- `ROBUST_WEIGHT_LOADING.md` - Implementation details
- `WEIGHT_LOADING_QUICK_REF.md` - Quick reference

### Multiple Workflows

- `MULTIPLE_WORKFLOWS.md` - Multi-workflow support
- `MULTIPLE_WORKFLOWS_SUMMARY.md` - Overview
- `MULTIPLE_WORKFLOWS_COMPLETE.md` - Full guide
- `MULTIPLE_WORKFLOWS_QUICK_REF.md` - Quick reference

### Cache & Git Management

- `GIT_EXCLUSIONS.md` - What's excluded from git and why
- `CACHE_CONFIGURATION_SUMMARY.md` - Full cache setup details
- `CACHE_DIRECTORIES.md` - Cache structure and cleanup
- `CACHE_QUICK_REF.md` - Quick cache reference

### Integration & Migration

- `NODE_MAPPING_INTEGRATION.md` - Custom node mapping
- `MIGRATION_GUIDE.md` - Migration from previous versions

---

## `/scripts` Directory

**Utility scripts** - organized by purpose.

### Validation

- `validate_implementation.py` - Check implementation completeness

### Examples

- `example_multiple_workflows.sh` - Multi-workflow loading demo
- `example_robust_loading.sh` - Robust loading strategy demo

### Weight Management

- `get_weights.py` - Download model weights
- `sort_weights.py` - Organize weight files
- `push_weights.py` - Upload weights to storage
- `push_weights_from_hf.py` - Download from Hugging Face and upload

### Custom Nodes

- `install_custom_nodes.py` - Install custom nodes
- `upgrade_custom_nodes.py` - Update custom nodes
- `add_custom_node.py` - Add new custom nodes

### ComfyUI Management

- `upgrade_comfyui.py` - Update ComfyUI
- `run_default_workflows.sh` - Test default workflows
- `start.sh` - Quick start script
- `reset.py` - Reset environment

### Utilities

- `push_folder.py` - Upload folders
- `prepare_template.py` - Prepare templates
- `push_comfyui_manager_weights.py` - Sync with ComfyUI Manager
- `get_weights_completion.sh` - Bash completion

---

## `/ComfyUI` Directory

**ComfyUI installation and extensions**

- `main.py` - ComfyUI entry point
- `server.py` - ComfyUI web server
- `nodes.py` - Core node definitions
- `requirements.txt` - ComfyUI dependencies

### Subdirectories

- `models/` - ✗ Excluded from git - model weights storage
- `custom_nodes/` - ✗ Excluded from git - custom node implementations
- `input/` - ✗ Excluded from git - input files
- `output/` - ✗ Excluded from git - generated outputs
- `temp/` - ✗ Excluded from git - temporary files
- `comfy/` - Core ComfyUI library
- `comfy_api/` - API implementation
- `comfy_execution/` - Execution engine
- `comfy_extras/` - Extra utilities
- `utils/` - Utility modules
- `tests/` - Test suite

---

## `/cog_model_helpers` Directory

**Helper utilities for models**

- `seed.py` - Random seed management
- `optimise_images.py` - Image optimization

---

## `/cog-safe-push-configs` Directory

**Configuration for safe pushing**

- `default.yaml` - Default push configuration

---

## `/custom_node_helpers` Directory

**Helper modules for custom nodes**

- Various custom node implementations and helpers

---

## `/custom_node_configs` Directory

**Configuration for custom nodes**

- `comfy.settings.json` - ComfyUI settings
- `rgthree_config.json` - rgthree configuration
- `was_suite_config.json` - WAS suite configuration

---

## `/examples` Directory

**Example workflows and configurations**

---

## Cache & Excluded Directories (Not in git)

### `.cache/` - Git Excluded

- `workflows/` - Downloaded workflow JSONs
- `manifests/` - Weight availability manifests

### `ComfyUI/models/` - Git Excluded

Model weights storage (auto-downloaded)

### `ComfyUI/custom_nodes/` - Git Excluded

Custom node installations

### `ComfyUI/input/` - Git Excluded

Input images and data

### `ComfyUI/output/` - Git Excluded

Generated images and videos

### `ComfyUI/temp/` - Git Excluded

Temporary processing files

### `downloaded_user_models/` - Git Excluded

User-provided weights

### `loras/` - Git Excluded

LoRA model files

### `embeddings/` - Git Excluded

Text embedding files

---

## Quick Navigation

| Need                   | Location                                                           |
| ---------------------- | ------------------------------------------------------------------ |
| **Get Started**        | [docs/INDEX.md](docs/INDEX.md)                                     |
| **Usage Examples**     | [scripts/example_*.sh](scripts/)                                   |
| **Weight Loading**     | [docs/WEIGHT_LOADING_STRATEGY.md](docs/WEIGHT_LOADING_STRATEGY.md) |
| **Multiple Workflows** | [docs/MULTIPLE_WORKFLOWS.md](docs/MULTIPLE_WORKFLOWS.md)           |
| **Git Exclusions**     | [docs/GIT_EXCLUSIONS.md](docs/GIT_EXCLUSIONS.md)                   |
| **Validate Setup**     | `python scripts/validate_implementation.py`                        |
| **Main Code**          | `predict.py`, `comfyui.py`                                         |
| **Configuration**      | `config.py`, `cog.yaml`                                            |

---

**Status:** ✅ Well-organized project structure  
**Docs:** All in `/docs` for easy browsing  
**Scripts:** All in `/scripts` with utilities  
**Cache:** All excluded from git in designated directories  
