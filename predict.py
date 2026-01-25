import os
import shutil
import tarfile
import zipfile
import mimetypes
import json
from PIL import Image
from typing import List, Optional, Dict, Any
from cog import BasePredictor, Input, Path
from comfyui import ComfyUI
from weights_downloader import WeightsDownloader
from cog_model_helpers import optimise_images
from config import config
import requests
import base64


os.environ["DOWNLOAD_LATEST_WEIGHTS_MANIFEST"] = "true"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("video/webm", ".webm")

OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
COMFYUI_TEMP_OUTPUT_DIR = "ComfyUI/temp"
ALL_DIRECTORIES = [OUTPUT_DIR, INPUT_DIR, COMFYUI_TEMP_OUTPUT_DIR]

IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".webp"]
VIDEO_TYPES = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

with open("examples/api_workflows/birefnet_api.json", "r") as file:
    EXAMPLE_WORKFLOW_JSON = file.read()


class Predictor(BasePredictor):
    def setup(self, weights: str):
        if bool(weights):
            self.handle_user_weights(weights)

        for directory in ALL_DIRECTORIES:
            os.makedirs(directory, exist_ok=True)
        os.makedirs(os.environ.get("YOLO_CONFIG_DIR", "/tmp/Ultralytics"), exist_ok=True)

        self.comfyUI = ComfyUI("127.0.0.1:8188")
        self.comfyUI.start_server(OUTPUT_DIR, INPUT_DIR)

    def handle_user_weights(self, weights: str):
        if hasattr(weights, "url"):
            if weights.url.startswith("http"):
                weights_url = weights.url
            else:
                weights_url = "https://replicate.delivery/" + weights.url
        else:
            weights_url = weights

        print(f"Downloading user weights from: {weights_url}")
        WeightsDownloader.download("weights.tar", weights_url, config["USER_WEIGHTS_PATH"])
        for item in os.listdir(config["USER_WEIGHTS_PATH"]):
            source = os.path.join(config["USER_WEIGHTS_PATH"], item)
            destination = os.path.join(config["MODELS_PATH"], item)
            if os.path.isdir(source):
                if not os.path.exists(destination):
                    print(f"Moving {source} to {destination}")
                    shutil.move(source, destination)
                else:
                    for root, _, files in os.walk(source):
                        for file in files:
                            if not os.path.exists(os.path.join(destination, file)):
                                print(
                                    f"Moving {os.path.join(root, file)} to {destination}"
                                )
                                shutil.move(os.path.join(root, file), destination)
                            else:
                                print(
                                    f"Skipping {file} because it already exists in {destination}"
                                )

    def handle_input_file(self, input_file: Path, custom_filename: str = None):
        """Handle a single input file with optional custom filename"""
        file_extension = self.get_file_extension(input_file)

        if file_extension == ".tar":
            with tarfile.open(input_file, "r") as tar:
                tar.extractall(INPUT_DIR)
        elif file_extension == ".zip":
            with zipfile.ZipFile(input_file, "r") as zip_ref:
                zip_ref.extractall(INPUT_DIR)
        elif file_extension in IMAGE_TYPES + VIDEO_TYPES:
            if custom_filename:
                filename = custom_filename if custom_filename.endswith(file_extension) else f"{custom_filename}{file_extension}"
            else:
                filename = f"input{file_extension}"
            shutil.copy(input_file, os.path.join(INPUT_DIR, filename))
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        print("====================================")
        print(f"Inputs uploaded to {INPUT_DIR}:")
        self.comfyUI.get_files(INPUT_DIR)
        print("=====================================")

    def handle_multiple_input_files(self, input_files: Dict[str, Path]):
        """Handle multiple input files with custom names
        
        Args:
            input_files: Dictionary mapping desired filenames to Path objects
        """
        for filename, file_path in input_files.items():
            self.handle_input_file(file_path, custom_filename=filename)

    def get_file_extension(self, input_file: Path) -> str:
        file_extension = os.path.splitext(input_file)[1].lower()
        if not file_extension:
            with open(input_file, "rb") as f:
                file_signature = f.read(4)
            if file_signature.startswith(b"\x1f\x8b"):  # gzip signature
                file_extension = ".tar"
            elif file_signature.startswith(b"PK"):  # zip signature
                file_extension = ".zip"
            else:
                try:
                    with Image.open(input_file) as img:
                        file_extension = f".{img.format.lower()}"
                        print(f"Determined file type: {file_extension}")
                except Exception as e:
                    raise ValueError(
                        f"Unable to determine file type for: {input_file}, {e}"
                    )
        return file_extension

    def substitute_workflow_params(self, workflow: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute parameters in workflow JSON
        
        Allows dynamic parameter substitution in workflows using placeholder syntax.
        Example: {"inputs": {"text": "{{prompt}}"}} with params={"prompt": "a cat"}
        
        Args:
            workflow: The workflow dictionary
            params: Dictionary of parameter names to values
            
        Returns:
            Modified workflow with substituted parameters
        """
        workflow_str = json.dumps(workflow)
        
        for key, value in params.items():
            # Support both {{key}} and {key} placeholder syntax
            workflow_str = workflow_str.replace(f"{{{{{key}}}}}", str(value))
            workflow_str = workflow_str.replace(f"{{{key}}}", str(value))
        
        return json.loads(workflow_str)

    def predict(
        self,
        workflow_json: str = Input(
            description="Your ComfyUI workflow as JSON string or URL. You must use the API version of your workflow. Get it from ComfyUI using 'Save (API format)'. Instructions here: https://github.com/replicate/cog-comfyui",
            default="",
        ),
        input_file: Optional[Path] = Input(
            description="Input image, video, tar or zip file. Read guidance on workflows and input files here: https://github.com/replicate/cog-comfyui. Alternatively, you can replace inputs with URLs in your JSON workflow and the model will download them.",
            default=None,
        ),
        input_file_2: Optional[Path] = Input(
            description="Optional second input file (image, video, etc.)",
            default=None,
        ),
        input_file_3: Optional[Path] = Input(
            description="Optional third input file (image, video, etc.)",
            default=None,
        ),
        input_filename_1: str = Input(
            description="Custom filename for input_file (e.g., 'image.png', 'video.mp4'). If not specified, defaults to 'input' with appropriate extension.",
            default="",
        ),
        input_filename_2: str = Input(
            description="Custom filename for input_file_2",
            default="",
        ),
        input_filename_3: str = Input(
            description="Custom filename for input_file_3",
            default="",
        ),
        workflow_params: str = Input(
            description="JSON string of parameters to substitute in workflow. Use {{param_name}} in your workflow JSON, then pass {\"param_name\": \"value\"} here.",
            default="",
        ),
        return_temp_files: bool = Input(
            description="Return any temporary files, such as preprocessed controlnet images. Useful for debugging.",
            default=False,
        ),
        output_format: str = optimise_images.predict_output_format(),
        output_quality: int = optimise_images.predict_output_quality(),
        randomise_seeds: bool = Input(
            description="Automatically randomise seeds (seed, noise_seed, rand_seed)",
            default=True,
        ),
        force_reset_cache: bool = Input(
            description="Force reset the ComfyUI cache before running the workflow. Useful for debugging.",
            default=False,
        ),
        skip_weight_check: bool = Input(
            description="Skip checking if weights are in the supported manifest. Use this to run workflows with custom/arbitrary models. Note: You must provide the model files via the 'weights' parameter in setup or ensure they exist in ComfyUI/models.",
            default=False,
        ),
        skip_node_checks: bool = Input(
            description="Skip checks for unsupported nodes. Use this to run workflows with nodes that are flagged as unsupported by helper modules.",
            default=False,
        ),
    ) -> List[Path]:
        """Run a single prediction on the model"""
        self.comfyUI.cleanup(ALL_DIRECTORIES)

        # Handle multiple input files with custom filenames
        if input_file:
            self.handle_input_file(input_file, custom_filename=input_filename_1 or None)
        if input_file_2:
            self.handle_input_file(input_file_2, custom_filename=input_filename_2 or None)
        if input_file_3:
            self.handle_input_file(input_file_3, custom_filename=input_filename_3 or None)

        workflow_json_content = workflow_json
        if workflow_json.startswith("data:") and ";base64," in workflow_json:
            try:
                base64_part = workflow_json.split(",", 1)[1]
                decoded_bytes = base64.b64decode(base64_part)
                workflow_json_content = decoded_bytes.decode("utf-8")
            except Exception as e:
                raise ValueError(f"Failed to decode base64 workflow JSON: {e}")
        elif workflow_json.startswith(("http://", "https://")):
            try:
                response = requests.get(workflow_json)
                response.raise_for_status()
                workflow_json_content = response.text
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Failed to download workflow JSON from URL: {e}")

        wf = self.comfyUI.load_workflow(
            workflow_json_content or EXAMPLE_WORKFLOW_JSON,
            skip_weight_check=skip_weight_check,
            skip_node_checks=skip_node_checks,
        )
        
        # Apply parameter substitution if provided
        if workflow_params:
            try:
                params_dict = json.loads(workflow_params)
                wf = self.substitute_workflow_params(wf, params_dict)
                print(f"Applied workflow parameter substitutions: {list(params_dict.keys())}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid workflow_params JSON: {e}")

        self.comfyUI.connect()

        if force_reset_cache or not randomise_seeds:
            self.comfyUI.reset_execution_cache()

        if randomise_seeds:
            self.comfyUI.randomise_seeds(wf)

        self.comfyUI.run_workflow(wf)

        output_directories = [OUTPUT_DIR]
        if return_temp_files:
            output_directories.append(COMFYUI_TEMP_OUTPUT_DIR)

        optimised_files = optimise_images.optimise_image_files(
            output_format, output_quality, self.comfyUI.get_files(output_directories)
        )
        return [Path(p) for p in optimised_files]
