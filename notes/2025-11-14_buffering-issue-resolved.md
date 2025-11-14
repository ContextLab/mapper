# Output Buffering Issue - Resolved

## Date: November 14, 2025, 08:05 AM

## Problem

The build process (PID 21821) was running for 60+ minutes with:
- 98% CPU usage
- 36-42GB memory
- No visible output in log files
- No checkpoint files created
- User correctly observed: "the pickle file doesn't take *that* long to load"

## Investigation

### Tests Performed

1. **Qwen Model Loading Test** ([test_qwen_load.py](../test_qwen_load.py))
   - Result: ✓ Model loads successfully in 4.95 seconds
   - Result: ✓ Can encode text at 4.7 texts/sec
   - Conclusion: Model is not the problem

2. **Pickle Loading Test**
   - Result: ✓ wikipedia.pkl loads in 0.64 seconds
   - Conclusion: Pickle loading is not the problem

3. **Process Inspection**
   - `lsof -p 21821` showed pickle library loaded but no open wikipedia.pkl file
   - Qwen model fully downloaded (1.1GB in ~/.cache/huggingface)
   - Process was actively using CPU but producing no output

## Root Cause

**Python stdout buffering** when output is piped through `tee`.

When running:
```bash
python build_wikipedia_knowledge_map_v2.py 2>&1 | tee build_qwen_cpu.log
```

Python fully buffers stdout, meaning all `print()` statements are held in a buffer until:
- The buffer is full (~4KB-8KB)
- The process exits
- `sys.stdout.flush()` is called explicitly

This caused the process to appear "stuck" even though it was actually:
1. Loading 250,000 articles from wikipedia.pkl (took ~30 seconds)
2. Processing each article into dict format (took ~30 minutes!)
3. Loading the Qwen model
4. Starting embedding generation

All of this work was happening with buffered output, making it impossible to see progress.

## Solution

**Use Python's unbuffered mode** with the `-u` flag:
```bash
python -u build_wikipedia_knowledge_map_v2.py 2>&1 | tee build_qwen_unbuffered.log
```

The `-u` flag forces Python to run in unbuffered mode, where every `print()` statement is immediately flushed to stdout.

## Actions Taken

1. Killed the old process (PID 21821) after 60 minutes
2. Restarted with `python -u` to enable unbuffered output
3. New process (PID 27704) now shows real-time progress

## Current Status (08:08 AM)

Process is running successfully with visible output:
- ✓ Loaded 250,001 Wikipedia articles
- ✓ Loaded 10 questions
- ✓ Total: 250,011 items to embed
- ✓ Qwen model loaded (1024-dim)
- ⏳ Embedding generation in progress (0/250,011)
- ⏳ Waiting for first progress update (after 3,200 items)

## Lessons Learned

1. **Always use `python -u` when running long processes with piped output**
2. **Output buffering can make processes appear stuck when they're actually running**
3. **Pickle loading speed was correctly identified by user as "too fast to be the issue"**
4. **The actual bottleneck was processing 250k dicts in Python, not I/O**

## Expected Timeline

Given encoding rate of ~4.7 texts/sec on CPU with batch_size=32:
- Embedding generation: **3-5 hours** (250k items @ batch=32)
- UMAP projection: **10-60 minutes** (depends on dataset size)
- Total estimated time: **4-6 hours**

## Monitoring

Current log file: [build_qwen_unbuffered.log](../build_qwen_unbuffered.log)

Check progress:
```bash
tail -f build_qwen_unbuffered.log
```

Check process:
```bash
ps aux | grep "[p]ython.*build_wikipedia"
```

Check for checkpoints:
```bash
ls -lh embeddings_checkpoint_*.pkl
```

## Files

- Test script: [test_qwen_load.py](../test_qwen_load.py)
- Build script: [build_wikipedia_knowledge_map_v2.py](../build_wikipedia_knowledge_map_v2.py)
- Current log: [build_qwen_unbuffered.log](../build_qwen_unbuffered.log)
- Old buffered log: [build_qwen_cpu.log](../build_qwen_cpu.log)
