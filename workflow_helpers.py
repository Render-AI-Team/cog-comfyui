"""
Utility helpers for working with arbitrary ComfyUI workflows

These helper functions make it easier to construct, modify, and validate
ComfyUI workflows programmatically.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class WorkflowBuilder:
    """Helper class for building ComfyUI workflows programmatically"""
    
    def __init__(self):
        self.workflow = {}
        self.node_counter = 1
    
    def add_node(self, class_type: str, inputs: Dict[str, Any], title: str = None) -> str:
        """Add a node to the workflow
        
        Args:
            class_type: The ComfyUI node class type
            inputs: Dictionary of input parameters
            title: Optional title for the node
            
        Returns:
            The node ID (as string)
        """
        node_id = str(self.node_counter)
        self.node_counter += 1
        
        node = {
            "inputs": inputs,
            "class_type": class_type
        }
        
        if title:
            node["_meta"] = {"title": title}
        
        self.workflow[node_id] = node
        return node_id
    
    def connect_nodes(self, from_node: str, to_node: str, input_name: str, output_index: int = 0):
        """Connect one node's output to another node's input
        
        Args:
            from_node: Source node ID
            to_node: Destination node ID
            input_name: Name of the input parameter on the destination node
            output_index: Output index from the source node (default 0)
        """
        if to_node in self.workflow:
            self.workflow[to_node]["inputs"][input_name] = [from_node, output_index]
    
    def get_workflow(self) -> Dict[str, Any]:
        """Get the complete workflow dictionary"""
        return self.workflow
    
    def to_json(self, indent: int = 2) -> str:
        """Convert workflow to JSON string"""
        return json.dumps(self.workflow, indent=indent)
    
    def save(self, filepath: str):
        """Save workflow to file"""
        with open(filepath, 'w') as f:
            f.write(self.to_json())


class WorkflowParameterizer:
    """Helper for adding and managing parameters in workflows"""
    
    @staticmethod
    def add_placeholders(workflow: Dict[str, Any], replacements: Dict[str, str]) -> Dict[str, Any]:
        """Replace specific values with placeholders
        
        Args:
            workflow: The workflow dictionary
            replacements: Dict mapping original values to placeholder names
            
        Returns:
            Workflow with placeholders
            
        Example:
            workflow = {...}
            replacements = {
                "a beautiful landscape": "prompt",
                "1024": "width"
            }
            parameterized = WorkflowParameterizer.add_placeholders(workflow, replacements)
        """
        workflow_str = json.dumps(workflow)
        
        for original, placeholder in replacements.items():
            workflow_str = workflow_str.replace(
                json.dumps(original),
                json.dumps(f"{{{{{placeholder}}}}}")
            )
        
        return json.loads(workflow_str)
    
    @staticmethod
    def extract_placeholders(workflow_str: str) -> List[str]:
        """Extract all placeholder names from a workflow
        
        Args:
            workflow_str: Workflow as JSON string
            
        Returns:
            List of placeholder names
        """
        import re
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, workflow_str)))


class WorkflowValidator:
    """Validate ComfyUI workflows"""
    
    @staticmethod
    def validate_structure(workflow: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate basic workflow structure
        
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(workflow, dict):
            return False, "Workflow must be a dictionary"
        
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                return False, f"Node {node_id} is not a dictionary"
            
            if "class_type" not in node:
                return False, f"Node {node_id} missing 'class_type'"
            
            if "inputs" not in node:
                return False, f"Node {node_id} missing 'inputs'"
            
            if not isinstance(node["inputs"], dict):
                return False, f"Node {node_id} 'inputs' is not a dictionary"
        
        return True, None
    
    @staticmethod
    def find_input_files(workflow: Dict[str, Any]) -> List[str]:
        """Find all file inputs referenced in workflow
        
        Returns:
            List of filenames referenced in workflow
        """
        filenames = []
        workflow_str = json.dumps(workflow)
        
        # Common patterns for file inputs
        import re
        patterns = [
            r'"image":\s*"([^"]+)"',
            r'"video":\s*"([^"]+)"',
            r'"audio":\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, workflow_str)
            filenames.extend(matches)
        
        return list(set(filenames))


# Example usage functions

def create_txt2img_workflow(
    checkpoint: str,
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    cfg: float = 7.0,
    sampler: str = "euler"
) -> Dict[str, Any]:
    """Create a basic text-to-image workflow
    
    Args:
        checkpoint: Model checkpoint filename
        prompt: Positive prompt
        negative_prompt: Negative prompt
        width: Image width
        height: Image height
        steps: Number of sampling steps
        cfg: CFG scale
        sampler: Sampler name
        
    Returns:
        ComfyUI workflow dictionary
    """
    builder = WorkflowBuilder()
    
    # Add checkpoint loader
    checkpoint_node = builder.add_node(
        "CheckpointLoaderSimple",
        {"ckpt_name": checkpoint},
        "Load Checkpoint"
    )
    
    # Add empty latent
    latent_node = builder.add_node(
        "EmptyLatentImage",
        {"width": width, "height": height, "batch_size": 1},
        "Empty Latent"
    )
    
    # Add positive prompt
    positive_node = builder.add_node(
        "CLIPTextEncode",
        {"text": prompt, "clip": [checkpoint_node, 1]},
        "Positive Prompt"
    )
    
    # Add negative prompt
    negative_node = builder.add_node(
        "CLIPTextEncode",
        {"text": negative_prompt, "clip": [checkpoint_node, 1]},
        "Negative Prompt"
    )
    
    # Add sampler
    sampler_node = builder.add_node(
        "KSampler",
        {
            "seed": 0,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": "normal",
            "denoise": 1,
            "model": [checkpoint_node, 0],
            "positive": [positive_node, 0],
            "negative": [negative_node, 0],
            "latent_image": [latent_node, 0]
        },
        "KSampler"
    )
    
    # Add VAE decode
    decode_node = builder.add_node(
        "VAEDecode",
        {
            "samples": [sampler_node, 0],
            "vae": [checkpoint_node, 2]
        },
        "VAE Decode"
    )
    
    # Add save image
    builder.add_node(
        "SaveImage",
        {
            "filename_prefix": "ComfyUI",
            "images": [decode_node, 0]
        },
        "Save Image"
    )
    
    return builder.get_workflow()


def load_and_parameterize_workflow(
    workflow_file: str,
    parameters: Dict[str, str]
) -> Dict[str, Any]:
    """Load a workflow and add parameters
    
    Args:
        workflow_file: Path to workflow JSON file
        parameters: Dict mapping values to replace with placeholder names
        
    Returns:
        Parameterized workflow
    """
    with open(workflow_file, 'r') as f:
        workflow = json.load(f)
    
    return WorkflowParameterizer.add_placeholders(workflow, parameters)


if __name__ == "__main__":
    # Example 1: Build a workflow programmatically
    print("Example 1: Building a workflow")
    workflow = create_txt2img_workflow(
        checkpoint="sd_xl_base_1.0.safetensors",
        prompt="a beautiful landscape",
        width=1024,
        height=768
    )
    print(json.dumps(workflow, indent=2))
    
    # Example 2: Validate a workflow
    print("\nExample 2: Validating workflow")
    is_valid, error = WorkflowValidator.validate_structure(workflow)
    print(f"Valid: {is_valid}, Error: {error}")
    
    # Example 3: Extract placeholders
    print("\nExample 3: Working with placeholders")
    parameterized = WorkflowParameterizer.add_placeholders(
        workflow,
        {"a beautiful landscape": "prompt", "1024": "width"}
    )
    workflow_str = json.dumps(parameterized)
    placeholders = WorkflowParameterizer.extract_placeholders(workflow_str)
    print(f"Found placeholders: {placeholders}")
