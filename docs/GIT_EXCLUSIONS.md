# Git Exclusions - What's Not Committed

This document explains what files and directories are excluded from git and why.

## Dynamically Installed Content

All files downloaded or generated at runtime are excluded from git to keep the repository clean.

### ComfyUI Generated Files

| Path                    | Contents                    | Notes                         |
| ----------------------- | --------------------------- | ----------------------------- |
| `ComfyUI/models/`       | Model weights               | Auto-downloaded when needed   |
| `ComfyUI/custom_nodes/` | Custom node implementations | Auto-installed from git repos |
| `ComfyUI/input/`        | Input images/data           | User-provided or generated    |
| `ComfyUI/output/`       | Generated images/videos     | Outputs from predictions      |
| `ComfyUI/temp/`         | Temporary processing files  | Cleaned up after execution    |

### Cache & Download Directories

| Path                      | Contents                   | Notes                       |
| ------------------------- | -------------------------- | --------------------------- |
| `.cache/workflows/`       | Downloaded workflow JSONs  | From PRELOAD_WORKFLOWS      |
| `.cache/manifests/`       | Weight manifests           | Index of available models   |
| `downloaded_user_models/` | User-provided weights      | Via `weights` parameter     |
| `.downloads/`             | Work-in-progress downloads | Cleaned up after completion |
| `.temp_workflows/`        | Temporary workflow files   | Short-lived processing      |

### Additional Dynamic Content

| Path          | Contents         | Notes                |
| ------------- | ---------------- | -------------------- |
| `loras/`      | LoRA model files | Downloaded on demand |
| `embeddings/` | Text embeddings  | Downloaded on demand |

## Why Exclude These?

1. **Repository Size** - Model files are huge (GB+), would bloat the repo
2. **Redundancy** - Can be downloaded/installed at runtime
3. **Clean Clones** - New clones are fast without cached files
4. **CI/CD Friendly** - No large file transfers in pipelines
5. **Local Storage** - Different users may have different model sets

## What IS Committed

✅ **Source Code**
- `*.py` files (Python code)
- `cog.yaml` (Cog configuration)
- `requirements.txt` (Dependencies)

✅ **Configuration**
- `config.py` (Settings)
- `custom_nodes.json` (Node configuration)
- `weights.json` (Weight manifest index)
- `weight_synonyms.json` (Model aliases)

✅ **Documentation**
- All `.md` files (guides and docs)
- README, guides, changelogs

✅ **Examples**
- `scripts/` directory (example scripts)
- Workflow examples
- Configuration examples

## Safe to Delete

All excluded directories can be safely deleted - they'll be recreated automatically when needed:

```bash
# Clear specific cache
rm -rf .cache/
rm -rf downloaded_user_models/
rm -rf ComfyUI/models/
rm -rf ComfyUI/custom_nodes/

# Clear all (aggressive)
rm -rf .cache/ .downloads/ .temp_workflows/ \
       downloaded_user_models/ loras/ embeddings/ \
       ComfyUI/models/ ComfyUI/custom_nodes/ \
       ComfyUI/input/ ComfyUI/output/ ComfyUI/temp/
```

Then the system will regenerate them on next run.

## Verify Git Isn't Tracking Them

Check that git isn't tracking these directories:

```bash
# These should all show empty or "not tracked"
git status .cache/
git status ComfyUI/models/
git status ComfyUI/custom_nodes/
git status downloaded_user_models/

# Or list all ignored files
git check-ignore -v .cache/ ComfyUI/models/ downloaded_user_models/ ComfyUI/custom_nodes/
```

## Current .gitignore Rules

The project's `.gitignore` file contains:

```ignore
# Cache directories
.cache/
.downloads/
.temp_workflows/

# ComfyUI dynamic content
ComfyUI/models/
ComfyUI/custom_nodes/
ComfyUI/input/
ComfyUI/output/
ComfyUI/temp/

# User weights and additional models
downloaded_user_models/
loras/
embeddings/
```

## Adding New Excluded Content

If you add new directories for downloaded/generated content:

1. Add them to `.gitignore`
2. Document them here
3. Prefer paths inside existing directories (cleaner structure)
4. Use clear naming (e.g., `.cache/` prefix, `downloaded_*` prefix)

---

**Status:** ✅ All dynamic content properly excluded from git  
**Repository Impact:** Clean, fast clones, no large files committed  
**Reference:** See also [Cache Directory Configuration](CACHE_CONFIGURATION_SUMMARY.md)
