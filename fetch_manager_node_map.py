#!/usr/bin/env python3
"""
Fetch and convert ComfyUI-Manager's extension-node-map.json to our custom_node_class_map.json format.
This expands our node → repo mapping dramatically.

Usage:
    python fetch_manager_node_map.py                    # Use latest (main branch)
    python fetch_manager_node_map.py --sha <commit>     # Use specific commit SHA
    python fetch_manager_node_map.py --sha v1.0.0       # Use specific tag/release
"""

import json
import urllib.request
import os
import argparse

def fetch_extension_node_map(sha="main"):
    """Fetch the extension-node-map.json from ComfyUI-Manager at a specific commit/tag/branch"""
    url = f"https://raw.githubusercontent.com/Comfy-Org/ComfyUI-Manager/{sha}/extension-node-map.json"
    try:
        print(f"Fetching extension-node-map.json from {sha}...")
        print(f"  URL: {url}")
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Warning: Failed to fetch extension-node-map.json: {e}")
        return None

def convert_to_class_map(extension_map):
    """
    Convert extension-node-map.json format:
      {"url": [["Class1", "Class2"], {...}]}
    To our class_map format:
      {"Class1": "url", "Class2": "url"}
    """
    class_map = {}
    for repo_url, (classes, metadata) in extension_map.items():
        if isinstance(classes, list):
            for class_name in classes:
                if class_name and isinstance(class_name, str):
                    class_map[class_name] = repo_url
    return class_map

def merge_maps(existing_map, new_map):
    """Merge maps with fetched entries taking precedence over existing local entries."""
    merged = existing_map.copy()
    merged.update(new_map)  # fetched entries win
    return merged

def save_class_map(class_map, filepath="custom_node_class_map.json"):
    """Save class map to JSON file"""
    with open(filepath, "w") as f:
        json.dump(class_map, f, indent=2, sort_keys=True)
    print(f"Saved {len(class_map)} node mappings to {filepath}")

def main():
    parser = argparse.ArgumentParser(
        description="Fetch ComfyUI-Manager node mappings and convert to our class map format"
    )
    parser.add_argument(
        "--sha",
        default="main",
        help="Git commit SHA, branch, or tag to fetch from (default: main)"
    )
    args = parser.parse_args()

    print(f"Fetching node mappings from ComfyUI-Manager ({args.sha})")
    print()

    # Load existing map if it exists
    existing_map = {}
    if os.path.exists("custom_node_class_map.json"):
        try:
            with open("custom_node_class_map.json") as f:
                existing_map = json.load(f)
            print(f"Loaded {len(existing_map)} existing mappings")
        except Exception as e:
            print(f"Warning: Could not load existing map: {e}")

    # Fetch Manager's map
    extension_map = fetch_extension_node_map(args.sha)
    if not extension_map:
        print("Could not fetch extension map, using existing map only")
        if existing_map:
            save_class_map(existing_map)
        return

    # Convert Manager's format to ours
    manager_map = convert_to_class_map(extension_map)
    print(f"Fetched {len(manager_map)} node mappings from ComfyUI-Manager ({args.sha})")

    # Merge (existing takes priority for conflicts)
    merged_map = merge_maps(existing_map, manager_map)
    print(f"Merged to {len(merged_map)} total mappings")

    # Save
    save_class_map(merged_map)

if __name__ == "__main__":
    main()
