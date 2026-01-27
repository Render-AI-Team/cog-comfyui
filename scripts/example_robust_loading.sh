#!/bin/bash
# Example: Preload Flux models and run a workflow
# This demonstrates the robust weight loading strategy

echo "🚀 Robust Weight Loading Example"
echo "=================================="
echo ""

# Method 1: Using environment variables
echo "📦 Setting up environment..."
export BASE_MODEL_KIT="flux"
export PRELOAD_WORKFLOW="examples/api_workflows/flux_schnell_api.json"

echo "✅ Environment configured:"
echo "   BASE_MODEL_KIT=${BASE_MODEL_KIT}"
echo "   PRELOAD_WORKFLOW=${PRELOAD_WORKFLOW}"
echo ""

# Method 2: In cog.yaml (show example)
echo "💡 Alternative: Add to cog.yaml build section:"
echo ""
echo "  build:"
echo "    python_version: \"3.11\""
echo "    run:"
echo "      - export BASE_MODEL_KIT=\"flux\""
echo "      - export PRELOAD_WORKFLOW=\"examples/api_workflows/flux_schnell_api.json\""
echo ""

# Method 3: At runtime
echo "🏃 Running prediction..."
echo ""
echo "# During setup(), these weights will be preloaded:"
echo "# - flux1-dev.safetensors"
echo "# - clip_l.safetensors"
echo "# - t5xxl_fp8_e4m3fn.safetensors"
echo "# - ae.safetensors"
echo ""

echo "# During predict(), validation will be fast:"
echo "# - Check weights exist (< 1ms per file)"
echo "# - Fail fast if missing"
echo "# - No network calls"
echo ""

# Actual command (commented out - requires cog)
# cog predict -i workflow_json=@examples/api_workflows/flux_schnell_api.json

echo "✅ Example complete!"
echo ""
echo "📚 For more info, see:"
echo "   - IMPLEMENTATION_SUMMARY.md"
echo "   - WEIGHT_LOADING_QUICK_REF.md"
echo "   - ROBUST_WEIGHT_LOADING.md"
