"""
Example Python script demonstrating how to use the enhanced predict.py
with arbitrary ComfyUI workflows
"""

import json
from pathlib import Path

# Example 1: Simple text-to-image with parameter substitution
def example_txt2img_with_params():
    """Generate an image using parameter substitution"""
    
    with open("examples/api_workflows/arbitrary_txt2img_template.json", "r") as f:
        workflow = json.load(f)
    
    # Define parameters to substitute
    params = {
        "prompt": "a majestic dragon flying over mountains, photorealistic, 4k",
        "negative_prompt": "ugly, blurry, distorted, low quality",
        "steps": 30,
        "cfg": 7.5,
        "sampler": "euler_ancestral",
        "width": 1024,
        "height": 1024,
        "model": "sd_xl_base_1.0.safetensors"
    }
    
    # In your actual code, you would call:
    # predictor.predict(
    #     workflow_json=json.dumps(workflow),
    #     workflow_params=json.dumps(params),
    #     randomise_seeds=True
    # )
    
    print("Example 1: Text-to-Image with Parameters")
    print(f"Workflow: {workflow}")
    print(f"Parameters: {params}")
    return workflow, params


# Example 2: Image-to-image with ControlNet
def example_img2img_controlnet():
    """Process an image with ControlNet"""
    
    # This is a simplified example - your actual workflow would be more complex
    workflow = {
        "1": {
            "inputs": {"image": "input_image.png"},
            "class_type": "LoadImage"
        },
        "2": {
            "inputs": {"image": "control_image.png"},
            "class_type": "LoadImage"
        },
        # ... rest of ControlNet workflow
    }
    
    # In your actual code:
    # predictor.predict(
    #     workflow_json=json.dumps(workflow),
    #     input_file=Path("my_image.png"),
    #     input_file_2=Path("my_control.png"),
    #     input_filename_1="input_image.png",
    #     input_filename_2="control_image.png"
    # )
    
    print("\nExample 2: Image-to-Image with ControlNet")
    print("Using two input files with custom names")
    return workflow


# Example 3: Video processing
def example_video_processing():
    """Process a video file"""
    
    workflow = {
        "1": {
            "inputs": {"video": "input_video.mp4"},
            "class_type": "LoadVideo"
        },
        # ... rest of video processing workflow
    }
    
    # In your actual code:
    # predictor.predict(
    #     workflow_json=json.dumps(workflow),
    #     input_file=Path("my_video.mp4"),
    #     input_filename_1="input_video.mp4",
    #     return_temp_files=True  # Get intermediate frames
    # )
    
    print("\nExample 3: Video Processing")
    print("Using video input with temp files")
    return workflow


# Example 4: Batch processing with archive
def example_batch_with_archive():
    """Process multiple images from an archive"""
    
    workflow = {
        # Workflow that processes multiple images
        # Images will be extracted from the tar/zip automatically
    }
    
    # In your actual code:
    # predictor.predict(
    #     workflow_json=json.dumps(workflow),
    #     input_file=Path("images.tar")  # Contains multiple images
    # )
    
    print("\nExample 4: Batch Processing with Archive")
    print("Upload tar/zip with multiple files")
    return workflow


# Example 5: Using workflow from URL
def example_workflow_from_url():
    """Load workflow from a URL"""
    
    workflow_url = "https://example.com/my_workflow.json"
    
    # In your actual code:
    # predictor.predict(
    #     workflow_json=workflow_url,  # URL instead of JSON string
    #     randomise_seeds=True
    # )
    
    print("\nExample 5: Workflow from URL")
    print(f"Loading workflow from: {workflow_url}")
    return workflow_url


# Example 6: Complex multi-input workflow
def example_complex_multi_input():
    """Use all three input slots"""
    
    workflow = {
        "1": {"inputs": {"image": "source.png"}, "class_type": "LoadImage"},
        "2": {"inputs": {"image": "style.png"}, "class_type": "LoadImage"},
        "3": {"inputs": {"image": "mask.png"}, "class_type": "LoadImage"},
        # ... rest of workflow
    }
    
    # In your actual code:
    # predictor.predict(
    #     workflow_json=json.dumps(workflow),
    #     input_file=Path("my_source.png"),
    #     input_file_2=Path("my_style.png"),
    #     input_file_3=Path("my_mask.png"),
    #     input_filename_1="source.png",
    #     input_filename_2="style.png",
    #     input_filename_3="mask.png"
    # )
    
    print("\nExample 6: Complex Multi-Input Workflow")
    print("Using all three input file slots")
    return workflow


# Example 7: Dynamic workflow construction
def example_dynamic_workflow():
    """Build a workflow programmatically"""
    
    def create_txt2img_workflow(checkpoint, prompt, size):
        return {
            "checkpoint": {
                "inputs": {"ckpt_name": checkpoint},
                "class_type": "CheckpointLoaderSimple"
            },
            "prompt": {
                "inputs": {"text": prompt, "clip": ["checkpoint", 1]},
                "class_type": "CLIPTextEncode"
            },
            "latent": {
                "inputs": {"width": size[0], "height": size[1], "batch_size": 1},
                "class_type": "EmptyLatentImage"
            },
            # ... rest of workflow
        }
    
    workflow = create_txt2img_workflow(
        checkpoint="sd_xl_base_1.0.safetensors",
        prompt="a beautiful sunset",
        size=(1024, 768)
    )
    
    print("\nExample 7: Dynamic Workflow Construction")
    print("Programmatically building workflows")
    return workflow


# Example 8: Using workflow with custom nodes
def example_custom_nodes():
    """Use custom nodes in workflow"""
    
    workflow = {
        "1": {
            "inputs": {
                "image": "input.png"
            },
            "class_type": "LoadImage"
        },
        "2": {
            "inputs": {
                "image": ["1", 0],
                "model": "BiRefNet",
                # ... custom node specific parameters
            },
            "class_type": "BiRefNet_Remove_Background"  # Custom node
        },
        # ... rest of workflow
    }
    
    # In your actual code:
    # predictor.predict(
    #     workflow_json=json.dumps(workflow),
    #     input_file=Path("photo.png"),
    #     input_filename_1="input.png"
    # )
    
    print("\nExample 8: Using Custom Nodes")
    print("Any installed custom node can be used")
    return workflow


if __name__ == "__main__":
    print("="*60)
    print("ARBITRARY COMFYUI WORKFLOW EXAMPLES")
    print("="*60)
    
    example_txt2img_with_params()
    example_img2img_controlnet()
    example_video_processing()
    example_batch_with_archive()
    example_workflow_from_url()
    example_complex_multi_input()
    example_dynamic_workflow()
    example_custom_nodes()
    
    print("\n" + "="*60)
    print("See ARBITRARY_WORKFLOWS_GUIDE.md for detailed documentation")
    print("="*60)
