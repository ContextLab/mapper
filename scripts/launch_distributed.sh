#!/bin/bash
# Local launcher script for distributed GPU embedding generation
# This script runs LOCALLY and SSHs to clusters to launch workers

set -e

# Parse command line arguments
CLUSTERS="tensor01 tensor02"  # Default: both clusters
if [ "$1" == "--clusters" ]; then
    CLUSTERS="$2"
fi

echo "================================================================================"
echo "DISTRIBUTED GPU LAUNCHER"
echo "================================================================================"
echo "Clusters: $CLUSTERS"
echo ""

# Function to setup and launch on a single cluster
launch_cluster() {
    local CLUSTER_NAME=$1
    local CLUSTER_ID=$2
    local CREDS_FILE=".credentials/${CLUSTER_NAME}.credentials"

    if [ ! -f "$CREDS_FILE" ]; then
        echo "✗ Credentials file not found: $CREDS_FILE"
        return 1
    fi

    # Parse credentials
    ADDRESS=$(python3 -c "import json; print(json.load(open('$CREDS_FILE'))['address'])")
    USERNAME=$(python3 -c "import json; print(json.load(open('$CREDS_FILE'))['username'])")
    PASSWORD=$(python3 -c "import json; print(json.load(open('$CREDS_FILE'))['password'])")

    echo "================================================================================"
    echo "LAUNCHING ON $CLUSTER_NAME (Cluster $CLUSTER_ID)"
    echo "================================================================================"
    echo "Address: $ADDRESS"
    echo "Username: $USERNAME"
    echo ""

    # Upload necessary files
    echo "[1/5] Uploading files..."

    # Check if wikipedia.pkl exists on remote
    WIKI_EXISTS=$(sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${USERNAME}@${ADDRESS} \
        'test -f ~/mapper_embeddings/wikipedia.pkl && echo "yes" || echo "no"' 2>/dev/null)

    if [ "$WIKI_EXISTS" == "yes" ]; then
        echo "  ✓ wikipedia.pkl already exists, skipping upload"
        # Upload only small files
        sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
            scripts/generate_embeddings_gpu.py \
            questions.json \
            ${USERNAME}@${ADDRESS}:~/mapper_embeddings/ 2>/dev/null
    else
        echo "  Uploading all files (including 752MB wikipedia.pkl)..."
        sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
            scripts/generate_embeddings_gpu.py \
            questions.json \
            wikipedia.pkl \
            ${USERNAME}@${ADDRESS}:~/mapper_embeddings/ 2>/dev/null
    fi

    # Upload HuggingFace token for authentication
    echo "  Uploading HuggingFace token..."
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${USERNAME}@${ADDRESS} \
        "mkdir -p ~/mapper_embeddings/.credentials" 2>/dev/null
    sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
        .credentials/hf.token \
        ${USERNAME}@${ADDRESS}:~/mapper_embeddings/.credentials/ 2>/dev/null

    echo "  ✓ Files uploaded"

    # Create conda environment if needed
    echo ""
    echo "[2/5] Setting up conda environment..."
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${USERNAME}@${ADDRESS} 'bash -s' << 'REMOTE_SCRIPT'
cd ~/mapper_embeddings
mkdir -p embeddings logs

# Recreate environment to fix dependency issues
if [ -d "$HOME/.conda/envs/mapper_gpu" ]; then
    echo "  Removing existing mapper_gpu environment..."
    conda env remove -n mapper_gpu -y 2>&1 | tail -2
fi

echo "  Creating fresh mapper_gpu environment..."
conda create -y -n mapper_gpu python=3.10 2>&1 | tail -3

# Install packages with specific version constraints
conda run -n mapper_gpu pip install torch numpy scikit-learn 2>&1 | grep -E "(Successfully|Requirement)" | tail -5
conda run -n mapper_gpu pip install 'transformers<5.0' 'huggingface_hub<1.0' 2>&1 | grep -E "(Successfully|Requirement)" | tail -5
conda run -n mapper_gpu pip install sentence-transformers 2>&1 | grep -E "(Successfully|Requirement)" | tail -5

echo "  ✓ Environment created"
REMOTE_SCRIPT

    # Launch GPU workers
    echo ""
    echo "[3/5] Launching 8 GPU workers..."
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${USERNAME}@${ADDRESS} bash << REMOTE_LAUNCH
cd ~/mapper_embeddings
PYTHON_PATH="\$HOME/.conda/envs/mapper_gpu/bin/python"

# Kill existing workers
for i in {0..7}; do
    screen -S mapper_gpu\$i -X quit 2>/dev/null || true
done

# Launch new workers
for gpu_id in {0..7}; do
    screen -dmS mapper_gpu\$gpu_id bash -c "
        cd ~/mapper_embeddings
        export CUDA_VISIBLE_DEVICES=\$gpu_id
        echo 'GPU worker \$gpu_id starting at \$(date)' | tee logs/gpu\${gpu_id}.log
        \$PYTHON_PATH generate_embeddings_gpu.py --cluster $CLUSTER_ID --gpu \$gpu_id --total-clusters $TOTAL_CLUSTERS 2>&1 | tee -a logs/gpu\${gpu_id}.log
        echo 'GPU worker \$gpu_id completed at \$(date)' | tee -a logs/gpu\${gpu_id}.log
    "
    echo "  ✓ Launched GPU \$gpu_id"
done
REMOTE_LAUNCH

    # Verify workers started
    echo ""
    echo "[4/5] Verifying workers..."
    sleep 2
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${USERNAME}@${ADDRESS} 'screen -ls | grep mapper_gpu | wc -l' | \
        xargs -I {} echo "  ✓ {} workers running"

    # Check initial logs
    echo ""
    echo "[5/5] Initial log check..."
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no ${USERNAME}@${ADDRESS} \
        'tail -5 ~/mapper_embeddings/logs/gpu0.log 2>&1 || echo "  (log file not yet created)"'

    echo ""
    echo "✓ $CLUSTER_NAME launch complete"
    echo ""
}

# Count total clusters
TOTAL_CLUSTERS=$(echo $CLUSTERS | wc -w | tr -d ' ')

echo "Total active clusters: $TOTAL_CLUSTERS"
echo ""

# Launch on specified clusters (0-indexed cluster IDs)
CLUSTER_ID=0
for CLUSTER in $CLUSTERS; do
    launch_cluster $CLUSTER $CLUSTER_ID
    CLUSTER_ID=$((CLUSTER_ID + 1))
done

echo "================================================================================"
echo "✓ ALL CLUSTERS LAUNCHED"
echo "================================================================================"
echo ""
echo "Monitor progress:"
echo "  python monitor_clusters.py"
echo ""
echo "Manual checks:"
echo "  ssh <cluster> 'screen -ls'"
echo "  ssh <cluster> 'tail -f ~/mapper_embeddings/logs/gpu0.log'"
echo "  ssh <cluster> 'cat ~/mapper_embeddings/embeddings/progress.json'"
echo ""
