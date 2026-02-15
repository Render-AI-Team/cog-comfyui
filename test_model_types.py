#!/usr/bin/env python3
"""Test model type detection for ComfyUI directory placement."""

from workflow_dependency_installer import detect_model_type

test_cases = [
    ('model.safetensors', 'https://stable-diffusion.example.com'),
    ('lora_v1.safetensors', 'https://example.com'),
    ('vae.safetensors', 'https://example.com'),
    ('flux1-dev-fp8.safetensors', 'checkpoint'),
    ('controlnet-canny.safetensors', 'https://example.com'),
    ('upscale_x4.pth', 'https://example.com'),
    ('gfpgan_model.pth', 'https://example.com'),
    ('clip_vision.safetensors', 'https://example.com'),
    ('style_model.pt', 'https://example.com'),
    ('hypernetwork.pt', 'https://example.com'),
    ('unet_model.safetensors', 'https://example.com'),
    ('photomaker.safetensors', 'https://example.com'),
    ('textual_inversion.pt', 'https://example.com'),
    ('audio_encoder.pt', 'https://example.com'),
]

print('Model type detection results (ComfyUI-standard paths):')
for filename, url in test_cases:
    model_type = detect_model_type(filename, url)
    print(f'  {filename:35} → ComfyUI/models/{model_type}')
