# Execution Checklist - Wikipedia Embedding Generation

**Print this page and check off items as you complete them**

Date: ________________  Start Time: __________

---

## Pre-Flight Checks (MUST COMPLETE ALL)

- [ ] **Local Files**
  - [ ] wikipedia.pkl exists (752MB)
  - [ ] .credentials/tensor01.credentials exists
  - [ ] .credentials/tensor02.credentials exists
  - [ ] .credentials/hf.token exists
  - [ ] All scripts executable (generate_embeddings_gpu.py, launch_distributed.sh, etc.)

- [ ] **Dependencies**
  - [ ] Python 3 installed
  - [ ] paramiko installed (`python3 -c "import paramiko"`)
  - [ ] numpy installed (`python3 -c "import numpy"`)

- [ ] **Connectivity**
  - [ ] Can SSH to tensor01
  - [ ] Can SSH to tensor02
  - [ ] Both clusters have 8 GPUs available
  - [ ] Both clusters have conda or Python 3.10+

- [ ] **Disk Space**
  - [ ] tensor01 has 4GB+ free
  - [ ] tensor02 has 4GB+ free
  - [ ] Local machine has 5GB+ free (for downloads)

**STOP: Do not proceed until ALL boxes checked**

---

## Launch Phase

### Launch Workers
- [ ] Run: `./launch_distributed.sh --clusters "tensor01 tensor02"`
- [ ] Verify: "✓ ALL CLUSTERS LAUNCHED" appears
- [ ] Verify: 8 workers running on tensor01
- [ ] Verify: 8 workers running on tensor02

**Time:** __________

### Start Monitoring
- [ ] Run: `python3 monitor_clusters.py --interval 30`
- [ ] Verify: Progress updates appear
- [ ] Verify: Combined rate > 500 items/sec

**Time:** __________

### Initial Progress Check (wait 2 min)
- [ ] GPU memory shows model loaded (>3GB per GPU)
- [ ] Items being processed (count increasing)
- [ ] No error messages in logs

**Time:** __________

---

## Monitoring Phase

**Check every 5 minutes:**

Check 1 - Time: __________ Progress: ______%
- [ ] All 16 workers showing progress
- [ ] No stuck workers (0 items/sec)
- [ ] Rate still > 500 items/sec

Check 2 - Time: __________ Progress: ______%
- [ ] Progress increasing
- [ ] Some workers may be completing
- [ ] ETA reasonable

Check 3 - Time: __________ Progress: ______%
- [ ] More workers complete
- [ ] No crashes detected

**Issues Encountered:**
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

## Completion Phase

- [ ] Monitor shows: "✓ ALL WORKERS COMPLETE!"
- [ ] Total items: 250,010/250,010
- [ ] Workers completed: 16/16
- [ ] No error messages

**Completion Time:** __________
**Total Generation Time:** __________

---

## Download Phase

### Verify Remote Files
- [ ] Run verification script (see EXECUTION_PLAN.md)
- [ ] 16 files exist on clusters
- [ ] All files ~150MB each

### Download Files
- [ ] Run: `python3 sync_and_merge_embeddings.py --sync-only`
- [ ] 16 files downloaded to embeddings/
- [ ] Total size ~2.4GB
- [ ] No download errors

**Download Time:** __________

---

## Merge Phase

### Merge Files
- [ ] Run: `python3 sync_and_merge_embeddings.py --merge-only`
- [ ] All 16 files loaded successfully
- [ ] No gaps in index ranges
- [ ] "✓ MERGE COMPLETE!" appears

### Verify Output
- [ ] File exists: embeddings/wikipedia_merged.pkl
- [ ] File size: ~1.9 GB
- [ ] No NaN or Inf values
- [ ] 250,000 embeddings
- [ ] 768 dimensions

**Merge Time:** __________

---

## Validation Phase

### Run Final Checks
- [ ] Run final validation script (see EXECUTION_PLAN.md)
- [ ] All 10 checks pass
- [ ] "✓✓✓ ALL CHECKS PASSED ✓✓✓" appears

### Create Backup
- [ ] Run: `cp embeddings/wikipedia_merged.pkl embeddings/backups/wikipedia_merged_$(date +%Y%m%d_%H%M%S).pkl`
- [ ] Backup exists in embeddings/backups/

**Validation Time:** __________

---

## Post-Completion

### Documentation
- [ ] Record actual execution time: __________
- [ ] Note any issues encountered (above)
- [ ] Create execution report (see EXECUTION_PLAN.md)

### Cleanup (Optional)
- [ ] Delete individual GPU files: `rm embeddings/cluster*.pkl`
- [ ] Clean remote clusters: `ssh user@cluster "rm ~/mapper_embeddings/embeddings/*.pkl"`

### Git Commit (Optional)
- [ ] Add execution report to git
- [ ] Commit with descriptive message
- [ ] Push to remote

---

## Final Summary

**Project Status:** ☐ SUCCESS  ☐ PARTIAL  ☐ FAILED

**Total Time:** From __________ to __________ = __________ minutes

**Output File:** embeddings/wikipedia_merged.pkl

**File Size:** __________

**Quality Metrics:**
- Embeddings: __________
- Dimensions: __________
- Mean norm: __________

**Ready for Next Phase:** ☐ YES  ☐ NO

**Notes:**
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

## Emergency Contacts / Resources

- Full Plan: `/Users/jmanning/mapper.io/notes/EXECUTION_PLAN.md`
- Quick Summary: `/Users/jmanning/mapper.io/notes/EXECUTION_PLAN_SUMMARY.md`
- Project Docs: `/Users/jmanning/mapper.io/CLAUDE.md`
- Session Notes: `/Users/jmanning/mapper.io/notes/`

**SSH Quick Reference:**
```bash
# Check tensor01 status
ssh user@tensor01 "screen -ls; tail ~/mapper_embeddings/logs/gpu0.log"

# Check tensor02 status
ssh user@tensor02 "screen -ls; tail ~/mapper_embeddings/logs/gpu0.log"

# Emergency stop all
ssh user@tensor01 "killall python3; screen -wipe"
ssh user@tensor02 "killall python3; screen -wipe"
```

---

**Completion Signature:** ________________________  Date: __________
