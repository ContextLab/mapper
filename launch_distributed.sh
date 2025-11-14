#!/bin/bash
# Launch distributed GPU workers on a cluster
# Run this on each cluster after setup_cluster.sh completes

CLUSTER_ID=$1  # "1" or "2"
TOTAL_GPUS=8
WORK_DIR="$HOME/mapper_embeddings"
REPO_DIR="$WORK_DIR/mapper.io"

if [ -z "$CLUSTER_ID" ]; then
    echo "Usage: $0 <cluster_id>"
    echo "  cluster_id: 1 or 2"
    exit 1
fi

echo "================================================================================"
echo "LAUNCHING DISTRIBUTED WORKERS: Cluster $CLUSTER_ID"
echo "================================================================================"
echo ""

# Activate conda environment
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate mapper_gpu

# Change to repo directory
cd "$REPO_DIR"

# Launch workers in screen sessions
for gpu_id in $(seq 0 $((TOTAL_GPUS - 1))); do
    SESSION_NAME="mapper_gpu${gpu_id}"
    LOG_FILE="$WORK_DIR/logs/gpu${gpu_id}.log"

    echo "Launching GPU $gpu_id..."
    echo "  Screen session: $SESSION_NAME"
    echo "  Log file: $LOG_FILE"

    # Kill existing session if it exists
    screen -S "$SESSION_NAME" -X quit 2>/dev/null || true

    # Create new screen session and run worker
    screen -dmS "$SESSION_NAME" bash -c "
        source $(conda info --base)/etc/profile.d/conda.sh
        conda activate mapper_gpu
        cd $REPO_DIR
        export CUDA_VISIBLE_DEVICES=$gpu_id
        echo 'Starting GPU worker $gpu_id on cluster $CLUSTER_ID'
        echo 'Started at: \$(date)'
        python generate_embeddings_gpu.py --cluster $CLUSTER_ID --gpu $gpu_id 2>&1 | tee $LOG_FILE
        echo 'Completed at: \$(date)'
        echo 'Press any key to close...'
        read
    "

    echo "  ✓ Launched"
    echo ""

    # Small delay between launches
    sleep 1
done

echo "================================================================================"
echo "ALL WORKERS LAUNCHED"
echo "================================================================================"
echo ""
echo "Monitor workers:"
echo "  screen -ls                      # List all screen sessions"
echo "  screen -r mapper_gpu0           # Attach to GPU 0 session"
echo "  tail -f $WORK_DIR/logs/gpu0.log # Watch GPU 0 log file"
echo ""
echo "Check progress:"
echo "  cat $WORK_DIR/embeddings/progress.json"
echo ""
echo "Kill all workers:"
echo "  for i in {0..7}; do screen -S mapper_gpu\$i -X quit; done"
echo ""
