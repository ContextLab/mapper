# Distributed GPU Processing Plan

## Overview

Process 250,000 Wikipedia articles across 2 clusters with 8 A6000 GPUs each (16 GPUs total) using Qwen/Qwen3-Embedding-0.6B.

## Architecture

### Data Distribution
- **Total items**: 250,010 (250k articles + 10 questions)
- **Cluster 1** (tensor01): 125,005 items (indices 0-125,004)
- **Cluster 2** (tensor02): 125,005 items (indices 125,005-250,009)
- Each cluster: 8 GPUs process ~15,626 items each

### Performance Estimate
- **Current CPU rate**: 0.12 items/sec → 564 hours
- **Expected GPU rate** (conservative): ~50-100 items/sec per GPU
- **With 16 GPUs**: ~800-1600 items/sec total
- **Estimated time**: 2.6-5.2 minutes (3-4 minutes realistic)

## Implementation Plan

### Phase 1: Setup Scripts (Parallel)
Create the following scripts simultaneously:

1. **`setup_cluster.sh`** - Main setup script for each cluster
   - Download wikipedia.pkl if needed
   - Clone/update mapper.io repo
   - Create conda environment
   - Install dependencies

2. **`generate_embeddings_gpu.py`** - GPU embedding script
   - Load subset of articles based on GPU ID
   - Generate embeddings on specific GPU
   - Save to individual checkpoint files
   - Report progress

3. **`launch_distributed.sh`** - Launch script for cluster
   - Start 8 GPU workers in screen sessions
   - One worker per GPU (CUDA_VISIBLE_DEVICES)
   - Monitor and log each worker

4. **`monitor_clusters.py`** - Monitoring script (local)
   - SSH to both clusters
   - Check progress files
   - Report combined status
   - Estimate time remaining

5. **`merge_embeddings.py`** - Merge script (local)
   - Download all embedding chunks from clusters
   - Merge into single embeddings.pkl
   - Verify count and dimensions

### Phase 2: Deployment (Sequential per cluster)
For each cluster:
1. Upload wikipedia.pkl to cluster (scp)
2. Upload setup scripts to cluster
3. Run setup_cluster.sh via SSH
4. Launch distributed processing
5. Verify workers started

### Phase 3: Monitoring (Continuous)
- Run monitor_clusters.py locally
- Check every 30 seconds
- Report progress to console

### Phase 4: Collection (After completion)
1. Download all embedding chunks
2. Merge embeddings
3. Continue with UMAP locally

## File Structure on Clusters

```
~/mapper_embeddings/
├── wikipedia.pkl              # Wikipedia dataset (752MB)
├── mapper.io/                 # Git repo
│   ├── generate_embeddings_gpu.py
│   ├── questions.json
│   └── ...
├── embeddings/                # Output directory
│   ├── cluster1_gpu0.pkl
│   ├── cluster1_gpu1.pkl
│   ├── ...
│   ├── cluster1_gpu7.pkl
│   └── progress.json         # Progress tracking
└── logs/                      # Log files
    ├── gpu0.log
    ├── gpu1.log
    └── ...
```

## Script Dependencies

### setup_cluster.sh
- Bash script
- Uses conda, git, wget/curl

### generate_embeddings_gpu.py
- Python 3.8+
- sentence-transformers
- torch with CUDA
- numpy, pickle

### launch_distributed.sh
- Bash script
- Uses screen
- Sets CUDA_VISIBLE_DEVICES

### monitor_clusters.py
- Python 3.8+
- paramiko (SSH)
- json

### merge_embeddings.py
- Python 3.8+
- numpy, pickle
- paramiko (SSH/SCP)

## Execution Order

1. Create all 5 scripts (parallel)
2. Test scripts locally if possible
3. Upload wikipedia.pkl to both clusters (parallel)
4. Run setup on both clusters (parallel)
5. Launch distributed workers on both clusters (parallel)
6. Monitor progress (continuous)
7. Download and merge results (sequential)
8. Verify merged embeddings
9. Continue with UMAP processing locally

## Risk Mitigation

- **Worker failure**: Each worker saves checkpoints, can be restarted
- **Network issues**: Progress files track completion, can resume
- **GPU memory**: Use batch_size=32, monitor GPU memory
- **SSH timeout**: Use screen sessions for long-running processes

## Success Criteria

- All 250,010 items processed
- Embeddings shape: (250010, 1024)
- All embeddings have norm ≈ 1.0
- Merged file size ≈ 1GB
- Total time < 10 minutes
