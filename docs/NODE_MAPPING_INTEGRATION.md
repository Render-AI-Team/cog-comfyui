# ComfyUI Node Mapping Integration

## Overview
Integrated ComfyUI-Manager's comprehensive `extension-node-map.json` (29,231+ node mappings) to enable automatic installation of custom nodes required by any workflow.

## Changes Made

### 1. New Script: `fetch_manager_node_map.py`
- Downloads ComfyUI-Manager's maintained `extension-node-map.json` from GitHub
- Converts Manager's format (repo URL → [class names]) to our format (class name → repo URL)
- Merges with existing mappings (existing entries take priority)
- Saves to `custom_node_class_map.json`

**Run to update:**
```bash
python fetch_manager_node_map.py
```

### 2. Updated `comfyui.py`
- **`_install_mapped_missing_nodes()`** now:
  - Extracts all node class names from workflow
  - Looks up each class in the expanded `custom_node_class_map.json` (29k+ mappings)
  - Collects all unique repos needed
  - Clones repos in parallel (one pass instead of per-class)
  - Reports any truly unmapped nodes (rare with Manager's map)
  - **Removed fallback install-all** (unnecessary with comprehensive coverage)

### 3. Node Coverage
- **Before**: ~2 manual mappings + fallback install-all
- **After**: 29,231 pre-mapped nodes + smart error reporting

## Workflow
When `install_custom_nodes=true`:
1. Extract node class names from workflow
2. Query expanded map (29k nodes)
3. Install only required repos
4. Report any unresolved nodes (informational, rare)
5. Cleanup after run

## Benefits
✅ **Fast**: Install only what's needed (no full install)  
✅ **Reliable**: Manager's map is actively maintained  
✅ **Scalable**: Handles virtually any public ComfyUI workflow  
✅ **Clean**: Removes nodes after each run  
✅ **Lean**: Small footprint (no full node suite)  

## Maintenance
To keep mappings fresh (optional, recommended monthly):
```bash
python fetch_manager_node_map.py
```
This updates `custom_node_class_map.json` with latest Manager catalog.
