# Scripts Directory

Utility scripts for ComfyUI management and testing.

## Validation & Testing

### validate_implementation.py
Validates the robust weight loading implementation.

```bash
python scripts/validate_implementation.py
```

Checks:
- ✓ Cache paths configured in config.py
- ✓ All extraction methods present in comfyui.py
- ✓ All preload methods present in predict.py
- ✓ setup() creates cache directories
- ✓ .gitignore has all exclusions
- ✓ Python syntax is valid

## Examples

### example_multiple_workflows.sh
Demonstrates loading weights from multiple workflows at once.

```bash
./scripts/example_multiple_workflows.sh
```

Shows:
- Loading from `workflows.json` with multiple workflows
- Weight deduplication across workflows
- Progress reporting
- Error handling

### example_robust_loading.sh
Demonstrates robust weight loading with preload strategy.

```bash
./scripts/example_robust_loading.sh
```

Shows:
- Base model kit preloading (sd15, sdxl, flux)
- Single workflow weight preloading
- Environment variable usage
- Setup vs predict phase separation

## Weight Management

### get_weights.py
Download and manage model weights.

```bash
python scripts/get_weights.py [weight_name]
```

### sort_weights.py
Organize and sort weight files.

```bash
python scripts/sort_weights.py
```

### push_weights.py
Upload weights to storage backend.

```bash
python scripts/push_weights.py [weights_dir]
```

### push_weights_from_hf.py
Download and push weights from Hugging Face.

```bash
python scripts/push_weights_from_hf.py [hf_repo_id]
```

## Custom Nodes

### install_custom_nodes.py
Install custom nodes from git repositories.

```bash
python scripts/install_custom_nodes.py
```

### upgrade_custom_nodes.py
Update all installed custom nodes.

```bash
python scripts/upgrade_custom_nodes.py
```

### add_custom_node.py
Add a new custom node to the registry.

```bash
python scripts/add_custom_node.py [node_url] [name]
```

## ComfyUI Management

### upgrade_comfyui.py
Update ComfyUI to the latest version.

```bash
python scripts/upgrade_comfyui.py
```

### run_default_workflows.sh
Run a set of default test workflows.

```bash
./scripts/run_default_workflows.sh
```

### start.sh
Quick start script.

```bash
./scripts/start.sh
```

### reset.py
Reset the environment to clean state.

```bash
python scripts/reset.py
```

### push_comfyui_manager_weights.py
Sync weights with ComfyUI Manager.

```bash
python scripts/push_comfyui_manager_weights.py
```

## Folder Operations

### push_folder.py
Upload entire folders to storage.

```bash
python scripts/push_folder.py [folder_path]
```

### prepare_template.py
Prepare a template for distribution.

```bash
python scripts/prepare_template.py
```

## Shell Utilities

### get_weights_completion.sh
Bash completion for weight names.

```bash
source scripts/get_weights_completion.sh
```

---

**All scripts are executable** - use `python scripts/name.py` or `./scripts/name.sh` to run.

**Cache Management:** Downloaded content goes to git-excluded directories - see [Git Exclusions](../docs/GIT_EXCLUSIONS.md).
