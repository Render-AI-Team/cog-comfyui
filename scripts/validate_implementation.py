#!/usr/bin/env python3
"""
Simple syntax validation for weight loading implementation.
This just checks that the files parse correctly without running them.
"""

import ast
import sys


def check_syntax(filename):
    """Check if a Python file has valid syntax."""
    print(f"\\n🔍 Checking {filename}...")
    try:
        with open(filename, 'r') as f:
            code = f.read()
        ast.parse(code)
        print(f"   ✅ Syntax OK")
        return True
    except SyntaxError as e:
        print(f"   ❌ Syntax Error: {e}")
        print(f"      Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_for_methods(filename, required_methods):
    """Check if required methods exist in a file."""
    print(f"\\n🔍 Checking methods in {filename}...")
    try:
        with open(filename, 'r') as f:
            code = f.read()
        tree = ast.parse(code)
        
        # Find all method definitions
        methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.add(node.name)
        
        missing = set(required_methods) - methods
        if missing:
            print(f"   ❌ Missing methods: {missing}")
            return False
        else:
            print(f"   ✅ All required methods present:")
            for method in required_methods:
                print(f"      - {method}")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 Weight Loading Implementation - Syntax Validation")
    print("=" * 60)
    
    results = []
    
    # Check syntax of key files
    results.append(check_syntax("comfyui.py"))
    results.append(check_syntax("predict.py"))
    results.append(check_syntax("weights_downloader.py"))
    results.append(check_syntax("weights_manifest.py"))
    
    # Check for required methods in comfyui.py
    results.append(check_for_methods("comfyui.py", [
        "extract_required_weights",
        "extract_weights_from_multiple_workflows",
        "validate_weights_exist",
        "validate_weights_from_multiple_workflows",
        "handle_weights"
    ]))
    
    # Check for required methods in predict.py
    results.append(check_for_methods("predict.py", [
        "setup",
        "preload_base_kit",
        "preload_workflow_weights",
        "preload_all_workflows",
        "predict"
    ]))
    
    # Summary
    print("\\n" + "=" * 60)
    print("📊 Validation Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    print(f"\\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\\n✅ All validation checks passed!")
        print("\\nImplementation is syntactically correct and includes all required methods.")
        return 0
    else:
        print(f"\\n❌ {total - passed} check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
