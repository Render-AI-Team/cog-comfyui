# Temporary Cache Directories

This document explains the temporary directories used for downloaded content and how they're managed.

## Cache Structure

```
.cache/
├── workflows/          # Downloaded workflow JSON files
├── manifests/          # Downloaded weight manifests
└── (other cache files)

.downloads/            # Alternative temp directory (if needed)

.temp_workflows/       # Alternative temp directory for workflows

ComfyUI/models/        # ComfyUI auto-downloaded weights
├── checkpoints/       # Model checkpoint files
├── clip/             # CLIP model files
├── vae/              # VAE model files
└── (other model types)

downloaded_user_models/  # User-provided weight archives
└── weights.json       # User weights manifest
```

## Git Exclusions

All temporary/cache directories are excluded from git via `.gitignore`:

```gitignore
# Temporary cache directories for downloaded weights, workflows, and manifests
.cache/
.downloads/
.temp_workflows/

# ComfyUI models cache (auto-downloaded weights)
ComfyUI/models/

# User weights
downloaded_user_models/
```

## Directory Purposes

### `.cache/workflows/`
- Stores downloaded workflow JSON files from remote URLs
- Used when `PRELOAD_WORKFLOWS` environment variable points to remote URL
- Safe to delete - will be re-downloaded on next run

### `.cache/manifests/`
- Stores downloaded weight manifests from remote sources
- Used when `DOWNLOAD_LATEST_WEIGHTS_MANIFEST=true`
- Safe to delete - will be re-downloaded on next run

### `ComfyUI/models/`
- Auto-downloaded model weights during prediction
- Created by ComfyUI itself
- Excluded from git to avoid committing large model files
- Safe to delete - models will be re-downloaded when needed

### `downloaded_user_models/`
- User-provided weight archives (via `weights` parameter)
- Contains extracted weight files and manifest
- Excluded from git to avoid committing custom model files

## Configuration

Cache directory locations are configured in `config.py`:

```python
config = {
    # ... other config ...
    "DOWNLOADED_WORKFLOWS_PATH": ".cache/workflows",
    "DOWNLOADED_MANIFESTS_PATH": ".cache/manifests",
}
```

## Cleanup

All cache directories are safe to delete. They will be automatically recreated when needed:

```bash
# Remove all cached downloads
rm -rf .cache/
rm -rf .downloads/
rm -rf .temp_workflows/
rm -rf downloaded_user_models/

# Or selectively:
rm -rf .cache/workflows/      # Remove cached workflows only
rm -rf .cache/manifests/      # Remove cached manifests only
rm -rf ComfyUI/models/        # Remove downloaded models
```

## Benefits

✅ **Clean Repository** - No large binary files committed to git
✅ **Organized Structure** - Clear separation of concerns
✅ **Automatic Management** - Directories created as needed
✅ **Easy Cleanup** - Can safely delete cache without affecting code
✅ **CI/CD Friendly** - Cache ignored in version control

## Environment Variables

To use custom cache locations, you can modify `config.py`:

```python
config = {
    "DOWNLOADED_WORKFLOWS_PATH": "/tmp/workflows",        # Custom location
    "DOWNLOADED_MANIFESTS_PATH": "/tmp/manifests",        # Custom location
    "USER_WEIGHTS_PATH": "/tmp/downloaded_models",        # Custom location
}
```

Or use environment variables (if implemented):

```bash
export CACHE_DIR="/custom/cache/path"
export WORKFLOWS_CACHE="$CACHE_DIR/workflows"
export MANIFESTS_CACHE="$CACHE_DIR/manifests"
```

## Verification

Check which directories are ignored:

```bash
# Show ignored directories
grep -E "^\.cache|^ComfyUI/models|^downloaded_user_models" .gitignore

# Check status of cache files
git status .cache/
git status ComfyUI/models/
git status downloaded_user_models/
```

All should show as "not tracked" or be absent from git status.

## Performance Notes

- Cache directories use local SSD storage for fast access
- Large model files (multi-GB) live in `ComfyUI/models/`
- Manifest files are small JSON (< 1MB)
- Workflows JSON files are typically < 100KB

## Troubleshooting

### "Permission denied" when creating cache
- Ensure process has write permissions in repository directory
- Check filesystem permissions: `ls -la | grep .cache`

### Cache grows too large
- Delete specific subdirectories: `rm -rf .cache/manifests/*`
- Monitor with: `du -sh .cache/* ComfyUI/models/`

### Files not being cached
- Verify config.py has correct path settings
- Check that directories were created: `ls -la .cache/`
- Review logs for download operations
