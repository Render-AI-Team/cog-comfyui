# Cache Configuration - Quick Reference

## TL;DR

All downloaded weights and workflows are stored in **git-excluded cache directories**:

```
.cache/                          ← Downloaded manifests and workflows
ComfyUI/models/                  ← Auto-downloaded model weights
downloaded_user_models/          ← User-provided weights
```

All are excluded from git via `.gitignore` - they won't be committed to version control.

## Cache Paths

| Path | Contents | Git Status |
|------|----------|-----------|
| `.cache/workflows/` | Downloaded workflow JSONs | Excluded ❌ |
| `.cache/manifests/` | Downloaded weight manifests | Excluded ❌ |
| `ComfyUI/models/` | Model weights (auto-downloaded) | Excluded ❌ |
| `downloaded_user_models/` | User-provided weights | Excluded ❌ |

## What's Configured

### config.py
```python
"DOWNLOADED_WORKFLOWS_PATH": ".cache/workflows"
"DOWNLOADED_MANIFESTS_PATH": ".cache/manifests"
```

### .gitignore
```
.cache/
ComfyUI/models/
downloaded_user_models/
```

### predict.py - setup()
```python
os.makedirs(config["DOWNLOADED_WORKFLOWS_PATH"], exist_ok=True)
os.makedirs(config["DOWNLOADED_MANIFESTS_PATH"], exist_ok=True)
```

### weights_manifest.py
```python
REMOTE_WEIGHTS_MANIFEST_PATH = os.path.join(DOWNLOADED_MANIFESTS_PATH, "updated_weights.json")
```

## Safe to Delete

These are all temporary/cache - safe to delete anytime:

```bash
rm -rf .cache/              # Clear all cache
rm -rf .cache/workflows/    # Clear workflow cache only
rm -rf .cache/manifests/    # Clear manifest cache only
rm -rf ComfyUI/models/      # Clear model cache
```

They'll be recreated automatically when needed.

## Repository Impact

✅ **No large files in git**
✅ **Clean repository**
✅ **Fast clones**
✅ **CI/CD friendly**

## Verification

Check git isn't tracking cache files:

```bash
git status .cache/
git status ComfyUI/models/
git status downloaded_user_models/

# All should show as not tracked or absent
```

## Details

See [CACHE_CONFIGURATION_SUMMARY.md](CACHE_CONFIGURATION_SUMMARY.md) for full documentation.

---

**Status:** ✅ **Cache properly configured and excluded from git**
