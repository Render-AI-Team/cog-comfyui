#!/usr/bin/env python3
"""
Automatically fix invalid commit hashes in custom_nodes.json
by updating them to the latest commits on their main/master branches.
"""

import json
import subprocess
import sys
import time

def check_commit_exists(repo_url, commit):
    """Check if a commit exists in the repository."""
    try:
        result = subprocess.run(
            ['git', 'ls-remote', repo_url, commit], 
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0 and result.stdout.strip()
    except:
        return False

def get_latest_commit(repo_url):
    """Get the latest commit from main/master branch."""
    for branch in ['main', 'master', 'Main', 'Master']:
        try:
            result = subprocess.run(
                ['git', 'ls-remote', repo_url, f'refs/heads/{branch}'], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.split()[0][:8], branch  # First 8 chars
        except:
            continue
    return None, None

def main():
    print("🔧 Automatically fixing invalid commit hashes in custom_nodes.json...")
    
    # Load custom_nodes.json
    try:
        with open('custom_nodes.json', 'r') as f:
            repos = json.load(f)
    except Exception as e:
        print(f"❌ Error loading custom_nodes.json: {e}")
        return 1
    
    print(f"📋 Checking {len(repos)} repositories...")
    
    updated_count = 0
    error_count = 0
    
    for i, repo in enumerate(repos):
        repo_url = repo['repo']
        current_commit = repo['commit']
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        print(f"[{i+1}/{len(repos)}] Checking {repo_name}...", end=" ", flush=True)
        
        # Check if current commit exists
        if check_commit_exists(repo_url, current_commit):
            print(f"✅ {current_commit[:8]}")
            continue
        
        # Commit doesn't exist, find latest
        print(f"❌ {current_commit[:8]} not found, updating...", end=" ", flush=True)
        
        latest_commit, branch = get_latest_commit(repo_url)
        if latest_commit:
            repo['commit'] = latest_commit
            updated_count += 1
            print(f"✅ {latest_commit} ({branch})")
        else:
            error_count += 1
            print(f"❌ No main/master branch found")
    
    # Save updated custom_nodes.json
    try:
        with open('custom_nodes.json', 'w') as f:
            json.dump(repos, f, indent=2)
        print(f"\n💾 Saved updated custom_nodes.json")
    except Exception as e:
        print(f"❌ Error saving custom_nodes.json: {e}")
        return 1
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Updated: {updated_count} repositories")
    print(f"   ❌ Errors: {error_count} repositories")
    print(f"   📋 Total: {len(repos)} repositories")
    
    if error_count > 0:
        print(f"\n⚠️  {error_count} repositories could not be updated automatically.")
        print(f"   You may need to check these manually or remove them from custom_nodes.json")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
