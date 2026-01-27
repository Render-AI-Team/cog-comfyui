#!/usr/bin/env python3
"""
Test script for robust weight loading implementation.

Usage:
    python test_weight_loading.py
"""

import json
import sys
import os

# Add ComfyUI to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comfyui import ComfyUI
from weights_downloader import WeightsDownloader


def test_extract_required_weights():
    """Test extracting weights from workflow."""
    print("\\n🧪 Test 1: Extract Required Weights")
    print("=" * 50)
    
    # Sample workflow with various loaders
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "flux1-dev.safetensors"}
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "clip_l.safetensors"}
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        },
        "4": {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": "my_lora.safetensors"}
        }
    }
    
    comfyui = ComfyUI("127.0.0.1:8188")
    weights = comfyui.extract_required_weights(workflow)
    
    print(f"✅ Extracted {len(weights)} weights:")
    for w in sorted(weights):
        print(f"   - {w}")
    
    expected = {"flux1-dev.safetensors", "clip_l.safetensors", "ae.safetensors", "my_lora.safetensors"}
    if set(weights) == expected:
        print("\\n✅ PASS: All expected weights extracted")
        return True
    else:
        print(f"\\n❌ FAIL: Expected {expected}, got {set(weights)}")
        return False


def test_validate_weights_exist():
    """Test weight validation."""
    print("\\n🧪 Test 2: Validate Weights Exist")
    print("=" * 50)
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "nonexistent-model.safetensors"}
        }
    }
    
    comfyui = ComfyUI("127.0.0.1:8188")
    all_exist, missing = comfyui.validate_weights_exist(workflow, skip_check=False)
    
    if not all_exist:
        print(f"✅ Correctly detected missing weights:")
        for w in missing:
            print(f"   - {w}")
        print("\\n✅ PASS: Validation working correctly")
        return True
    else:
        print("❌ FAIL: Should have detected missing weights")
        return False


def test_skip_validation():
    """Test skipping validation."""
    print("\\n🧪 Test 3: Skip Validation")
    print("=" * 50)
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "any-model.safetensors"}
        }
    }
    
    comfyui = ComfyUI("127.0.0.1:8188")
    all_exist, missing = comfyui.validate_weights_exist(workflow, skip_check=True)
    
    if all_exist and len(missing) == 0:
        print("✅ PASS: Validation skipped correctly")
        return True
    else:
        print("❌ FAIL: Skip check not working")
        return False


def test_canonical_weight_names():
    """Test weight synonym conversion."""
    print("\\n🧪 Test 4: Canonical Weight Names")
    print("=" * 50)
    
    downloader = WeightsDownloader()
    
    test_cases = [
        ("model.sft", "model.safetensors"),  # .sft -> .safetensors
    ]
    
    passed = True
    for input_name, expected in test_cases:
        result = downloader.get_canonical_weight_str(input_name)
        if result == expected:
            print(f"✅ {input_name} -> {result}")
        else:
            print(f"❌ {input_name} -> {result} (expected {expected})")
            passed = False
    
    if passed:
        print("\\n✅ PASS: Canonical name conversion working")
    else:
        print("\\n❌ FAIL: Some conversions failed")
    
    return passed


def test_empty_workflow():
    """Test handling empty workflow."""
    print("\\n🧪 Test 5: Empty Workflow")
    print("=" * 50)
    
    workflow = {}
    
    comfyui = ComfyUI("127.0.0.1:8188")
    weights = comfyui.extract_required_weights(workflow)
    
    if len(weights) == 0:
        print("✅ PASS: Empty workflow handled correctly")
        return True
    else:
        print(f"❌ FAIL: Expected 0 weights, got {len(weights)}")
        return False


def test_dual_clip_loader():
    """Test DualCLIPLoader weight extraction."""
    print("\\n🧪 Test 6: DualCLIPLoader")
    print("=" * 50)
    
    workflow = {
        "1": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "clip_g.safetensors"
            }
        }
    }
    
    comfyui = ComfyUI("127.0.0.1:8188")
    weights = comfyui.extract_required_weights(workflow)
    
    expected = {"clip_l.safetensors", "clip_g.safetensors"}
    if set(weights) == expected:
        print(f"✅ PASS: Extracted both CLIP models")
        for w in sorted(weights):
            print(f"   - {w}")
        return True
    else:
        print(f"❌ FAIL: Expected {expected}, got {set(weights)}")
        return False


def main():
    """Run all tests."""
    print("\\n" + "=" * 50)
    print("🧪 Robust Weight Loading - Test Suite")
    print("=" * 50)
    
    tests = [
        test_extract_required_weights,
        test_validate_weights_exist,
        test_skip_validation,
        test_canonical_weight_names,
        test_empty_workflow,
        test_dual_clip_loader,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"\\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\\n✅ All tests passed!")
        return 0
    else:
        print(f"\\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
