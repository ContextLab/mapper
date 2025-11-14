#!/bin/bash
# Setup script for distributed GPU embedding generation
# Run this on each cluster to prepare the environment

set -e  # Exit on error

CLUSTER_ID=$1  # "cluster1" or "cluster2"
WORK_DIR="$HOME/mapper_embeddings"

echo "================================================================================"
echo "CLUSTER SETUP: $CLUSTER_ID"
echo "================================================================================"

# Create working directory
echo ""
echo "[1/6] Creating working directory..."
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
echo "  ✓ Working directory: $WORK_DIR"

# Download wikipedia.pkl if needed
WIKI_FILE="wikipedia.pkl"
if [ ! -f "$WIKI_FILE" ]; then
    echo ""
    echo "[2/6] Downloading wikipedia.pkl (752MB)..."
    echo "  Note: This should already be uploaded via scp"
    echo "  If missing, please upload manually:"
    echo "  scp wikipedia.pkl <username>@<cluster>:$WORK_DIR/"
    if [ ! -f "$WIKI_FILE" ]; then
        echo "  ✗ ERROR: wikipedia.pkl not found!"
        echo "  Please upload it manually before running this script"
        exit 1
    fi
else
    echo ""
    echo "[2/6] Wikipedia dataset found"
    ls -lh "$WIKI_FILE"
fi

# Clone or update mapper.io repo
REPO_DIR="mapper.io"
if [ ! -d "$REPO_DIR" ]; then
    echo ""
    echo "[3/6] Cloning mapper.io repository..."
    git clone https://github.com/jeremymanning/mapper.io.git
    echo "  ✓ Repository cloned"
else
    echo ""
    echo "[3/6] Updating mapper.io repository..."
    cd "$REPO_DIR"
    git pull
    cd ..
    echo "  ✓ Repository updated"
fi

# Setup conda environment
ENV_NAME="mapper_gpu"
echo ""
echo "[4/6] Setting up conda environment: $ENV_NAME"

if conda env list | grep -q "^$ENV_NAME "; then
    echo "  Environment exists, updating..."
    conda activate "$ENV_NAME"
else
    echo "  Creating new environment..."
    conda create -y -n "$ENV_NAME" python=3.10
    conda activate "$ENV_NAME"
fi

# Install dependencies
echo ""
echo "[5/6] Installing dependencies..."
pip install --upgrade pip
pip install sentence-transformers torch numpy scikit-learn paramiko

# Verify GPU access
echo ""
echo "[6/6] Verifying GPU access..."
python -c "import torch; print(f'  CUDA available: {torch.cuda.is_available()}'); print(f'  GPU count: {torch.cuda.device_count()}'); [print(f'  GPU {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())]"

# Create output directories
mkdir -p "$WORK_DIR/embeddings"
mkdir -p "$WORK_DIR/logs"

echo ""
echo "================================================================================"
echo "SETUP COMPLETE: $CLUSTER_ID"
echo "================================================================================"
echo ""
echo "Working directory: $WORK_DIR"
echo "Wikipedia dataset: $WORK_DIR/$WIKI_FILE"
echo "Repository: $WORK_DIR/$REPO_DIR"
echo "Conda environment: $ENV_NAME"
echo ""
echo "Next steps:"
echo "  1. Run launch_distributed.sh to start GPU workers"
echo "  2. Monitor progress with monitor_clusters.py from local machine"
echo ""
