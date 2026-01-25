#!/usr/bin/env python3
"""
Quick test to verify the enhanced predict.py works correctly
This doesn't actually run predictions but validates the code structure
"""

import json
import sys
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    try:
        from predict import Predictor
        print("✓ Successfully imported Predictor")
        return True
    except Exception as e:
        print(f"✗ Failed to import: {e}")
        return False

def test_workflow_builder():
    """Test the workflow helper utilities"""
    print("\nTesting workflow helpers...")
    try:
        from workflow_helpers import WorkflowBuilder, WorkflowValidator, create_txt2img_workflow
        
        # Test creating a workflow
        workflow = create_txt2img_workflow(
            checkpoint="test.safetensors",
            prompt="test prompt"
        )
        
        # Test validation
        is_valid, error = WorkflowValidator.validate_structure(workflow)
        if is_valid:
            print("✓ Created and validated workflow successfully")
            return True
        else:
            print(f"✗ Workflow validation failed: {error}")
            return False
    except Exception as e:
        print(f"✗ Failed workflow test: {e}")
        return False

def test_parameter_substitution():
    """Test parameter substitution logic"""
    print("\nTesting parameter substitution...")
    try:
        from workflow_helpers import WorkflowParameterizer
        
        workflow = {
            "1": {
                "inputs": {"text": "{{prompt}}", "value": "{{number}}"},
                "class_type": "TestNode"
            }
        }
        
        # Add placeholders
        placeholders = WorkflowParameterizer.extract_placeholders(json.dumps(workflow))
        
        if "prompt" in placeholders and "number" in placeholders:
            print(f"✓ Found placeholders: {placeholders}")
            return True
        else:
            print(f"✗ Didn't find expected placeholders: {placeholders}")
            return False
    except Exception as e:
        print(f"✗ Failed parameter test: {e}")
        return False

def test_workflow_template():
    """Test loading the workflow template"""
    print("\nTesting workflow template...")
    try:
        template_path = Path(__file__).parent / "examples/api_workflows/arbitrary_txt2img_template.json"
        
        if template_path.exists():
            with open(template_path) as f:
                workflow = json.load(f)
            
            # Check for placeholders
            workflow_str = json.dumps(workflow)
            if "{{" in workflow_str and "}}" in workflow_str:
                print("✓ Template contains placeholders")
                return True
            else:
                print("✗ Template missing placeholders")
                return False
        else:
            print(f"✗ Template not found at {template_path}")
            return False
    except Exception as e:
        print(f"✗ Failed template test: {e}")
        return False

def main():
    print("="*60)
    print("TESTING ARBITRARY WORKFLOW ENHANCEMENTS")
    print("="*60)
    
    tests = [
        test_imports,
        test_workflow_builder,
        test_parameter_substitution,
        test_workflow_template
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("="*60)
    
    if all(results):
        print("\n✅ All tests passed! The enhancements are working correctly.")
        print("\nNext steps:")
        print("1. Read QUICKSTART_ARBITRARY_WORKFLOWS.md")
        print("2. Check examples/arbitrary_workflow_examples.py")
        print("3. Try running your own ComfyUI workflows!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
