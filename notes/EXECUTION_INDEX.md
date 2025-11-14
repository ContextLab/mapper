# Execution Documentation Index

Complete guide to executing the Wikipedia embedding generation project.

**Created:** 2025-11-14
**Project:** Wikipedia Knowledge Map Embeddings
**Goal:** Generate 250,000 article embeddings on 16 GPUs

---

## Document Overview

This directory contains comprehensive documentation for executing the distributed GPU embedding generation pipeline. Start here and follow the links.

---

## Quick Start Path

**For experienced users who want minimal guidance:**

1. **Read:** [EXECUTION_PLAN_SUMMARY.md](./EXECUTION_PLAN_SUMMARY.md) (5 min)
2. **Print:** [EXECUTION_CHECKLIST.md](./EXECUTION_CHECKLIST.md) (track progress)
3. **Run:** Commands from summary
4. **If issues:** Consult [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)

**Estimated Time:** 20-35 minutes total

---

## Detailed Execution Path

**For first-time execution or when thoroughness is critical:**

1. **Read:** [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) (30 min)
   - Complete pre-flight checklist (page 1-5)
   - Understand each phase before starting
   - Note all verification steps

2. **Print:** [EXECUTION_CHECKLIST.md](./EXECUTION_CHECKLIST.md)
   - Physical checklist to mark off items
   - Documents actual times and metrics
   - Creates execution record

3. **Execute:** Follow EXECUTION_PLAN.md step-by-step
   - Run each command exactly as specified
   - Verify output matches expected
   - Document any deviations

4. **Troubleshoot:** Use [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)
   - Quick reference for common issues
   - Indexed by symptom/error message
   - Copy-paste solutions

**Estimated Time:** 45-60 minutes (including reading)

---

## Document Descriptions

### Core Documents

#### [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) - 67KB, ~1,800 lines
**The comprehensive execution guide.**

Contains:
- Pre-flight checklist (30+ items)
- Step-by-step launch procedure
- Monitoring procedures with checkpoints
- Failure recovery procedures
- Download and validation procedures
- Success criteria checklist
- Quick reference commands
- Timeline estimates

**Use when:**
- First time running the pipeline
- Need detailed verification steps
- Want to understand each phase
- Need recovery procedures

**Structure:**
1. Pre-flight Checklist (30+ checks)
2. Launch Procedure (5 steps)
3. Monitoring Procedure (continuous)
4. Failure Recovery (6+ scenarios)
5. Download and Validation (5 phases)
6. Success Criteria (10 checks)

---

#### [EXECUTION_PLAN_SUMMARY.md](./EXECUTION_PLAN_SUMMARY.md) - 4KB, ~330 lines
**Quick reference for experienced users.**

Contains:
- Essential commands only
- Expected outputs
- Quick troubleshooting
- Timeline overview

**Use when:**
- Already familiar with pipeline
- Need quick command reference
- Want to see overview
- Executing second+ time

**Structure:**
1. Pre-flight (condensed)
2. Launch (commands only)
3. Download & Validate (streamlined)
4. Success Criteria (brief)

---

#### [EXECUTION_CHECKLIST.md](./EXECUTION_CHECKLIST.md) - 4KB, ~360 lines
**Physical checklist for tracking execution.**

Contains:
- Checkbox list of all tasks
- Space for recording times
- Space for documenting issues
- Final summary section

**Use when:**
- Executing the pipeline
- Need to track progress
- Want permanent record
- Multiple people involved

**Format:**
- Print and use physically
- Or keep open in text editor
- Check off items as completed
- Record actual metrics

---

#### [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) - ~16KB, ~700 lines
**Solutions to common problems.**

Contains:
- Issue descriptions
- Diagnostic commands
- Step-by-step solutions
- Emergency procedures

**Use when:**
- Encounter an error
- Something doesn't work as expected
- Need quick fix
- Unclear what went wrong

**Structure:**
- Organized by phase (pre-flight, launch, runtime, download, merge, validation)
- Each issue has:
  - Symptoms
  - Diagnosis command
  - Solution steps
  - Prevention tips

---

### Supporting Documents

#### [distributed-gpu-plan.md](./distributed-gpu-plan.md)
**Original architectural plan.**

Contains:
- System architecture
- Performance estimates
- File structure
- Script dependencies

**Use when:**
- Want to understand design decisions
- Need to modify scripts
- Debugging architectural issues

---

#### Session Notes (2025-11-14_*.md)
**Historical context from development.**

Contains:
- Issues encountered during development
- Solutions that worked
- Performance metrics
- Edge cases discovered

**Use when:**
- Encountering similar issues
- Understanding why something is designed a certain way
- Learning from previous iterations

---

## Workflow Diagrams

### Standard Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Pre-Flight Checklist (10-15 min)                            │
│ - Local files                                               │
│ - Dependencies                                              │
│ - Connectivity                                              │
│ - Disk space                                                │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Launch Phase (2-3 min)                                      │
│ - Upload files to clusters                                  │
│ - Create conda environments                                 │
│ - Launch 16 workers (8 per cluster)                         │
│ - Verify workers started                                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Monitoring Phase (3-10 min)                                 │
│ - Check progress every 30s                                  │
│ - Verify rate > 500 items/sec                               │
│ - Watch for stuck/crashed workers                           │
│ - Wait for "ALL WORKERS COMPLETE"                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Download Phase (5-10 min)                                   │
│ - Verify remote files (16 files)                            │
│ - Download via SSH (~2.4GB)                                 │
│ - Verify local files                                        │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Merge Phase (2-3 min)                                       │
│ - Load 16 checkpoint files                                  │
│ - Verify index ranges                                       │
│ - Concatenate embeddings                                    │
│ - Extract 250K articles (exclude 10 questions)              │
│ - Quality checks (NaN, Inf, norms)                          │
│ - Save merged file (1.9GB)                                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Validation Phase (2-3 min)                                  │
│ - File exists and correct size                              │
│ - 250,000 embeddings × 768 dimensions                       │
│ - No NaN or Inf values                                      │
│ - Article metadata complete                                 │
│ - Embedding norms reasonable                                │
│ - Create backup                                             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                          SUCCESS
              embeddings/wikipedia_merged.pkl
                        (1.9GB)
```

---

### Failure Recovery Flow

```
                       Failure Detected
                             │
                             ▼
              ┌──────────────┴──────────────┐
              │                             │
         Single Worker                 Multiple/System
         Failure                        Failure
              │                             │
              ▼                             ▼
      ┌──────────────┐             ┌──────────────┐
      │ Check Logs   │             │ Assess Scope │
      └──────┬───────┘             └──────┬───────┘
             │                             │
             ▼                             ▼
      ┌──────────────┐             ┌──────────────┐
      │ Identify     │             │ All Workers  │
      │ Issue        │             │ or Partial?  │
      └──────┬───────┘             └──────┬───────┘
             │                             │
             ▼                    ┌────────┴────────┐
      ┌──────────────┐            │                 │
      │ Fix Issue    │         Partial           All
      │ (OOM, CUDA,  │            │                 │
      │  Network)    │            ▼                 ▼
      └──────┬───────┘     ┌──────────────┐ ┌──────────────┐
             │             │ Partial      │ │ Nuclear      │
             ▼             │ Recovery     │ │ Option:      │
      ┌──────────────┐     │ - Download   │ │ Complete     │
      │ Restart      │     │   completed  │ │ Restart      │
      │ Worker       │     │ - Re-run     │ │              │
      │ (Resume from │     │   failed     │ │ - Kill all   │
      │  Checkpoint) │     └──────┬───────┘ │ - Clean up   │
      └──────┬───────┘            │         │ - Re-launch  │
             │                    │         └──────┬───────┘
             │                    │                │
             └────────────────────┴────────────────┘
                                  │
                                  ▼
                          Continue Monitoring
```

---

## Command Quick Reference

### Pre-Flight
```bash
cd /Users/jmanning/mapper.io
ls -lh wikipedia.pkl .credentials/*.credentials
python3 -c "import paramiko, numpy; print('OK')"
```

### Launch
```bash
./launch_distributed.sh --clusters "tensor01 tensor02"
python3 monitor_clusters.py --interval 30
```

### Download & Merge
```bash
python3 sync_and_merge_embeddings.py --sync-only
python3 sync_and_merge_embeddings.py --merge-only
```

### Validation
```bash
python3 -c "import pickle; data=pickle.load(open('embeddings/wikipedia_merged.pkl','rb')); print(f'Embeddings: {data[\"embeddings\"].shape}')"
```

### Emergency
```bash
# Stop everything
ssh user@tensor01 "killall python3; screen -wipe"
ssh user@tensor02 "killall python3; screen -wipe"

# Restart
./launch_distributed.sh --clusters "tensor01 tensor02"
```

---

## File Locations

```
/Users/jmanning/mapper.io/
├── notes/
│   ├── EXECUTION_INDEX.md                    # ← You are here
│   ├── EXECUTION_PLAN.md                     # Complete guide (67KB)
│   ├── EXECUTION_PLAN_SUMMARY.md             # Quick reference (4KB)
│   ├── EXECUTION_CHECKLIST.md                # Printable checklist (4KB)
│   ├── TROUBLESHOOTING_GUIDE.md              # Problem solutions (16KB)
│   ├── distributed-gpu-plan.md               # Architecture (5KB)
│   └── 2025-11-14_*.md                       # Session notes
│
├── wikipedia.pkl                              # Input data (752MB)
├── generate_embeddings_gpu.py                 # GPU worker script
├── launch_distributed.sh                      # Launch automation
├── monitor_clusters.py                        # Progress monitoring
├── sync_and_merge_embeddings.py               # Download & merge
│
├── .credentials/
│   ├── tensor01.credentials                   # Cluster 1 SSH
│   ├── tensor02.credentials                   # Cluster 2 SSH
│   └── hf.token                               # HuggingFace auth
│
└── embeddings/
    ├── cluster*.pkl                           # Downloaded (temp)
    ├── wikipedia_merged.pkl                   # Final output (1.9GB)
    └── backups/                               # Timestamped backups
```

---

## FAQ

### Q: Which document should I read first?
**A:** For first-time execution, read EXECUTION_PLAN.md completely. For subsequent runs, use EXECUTION_PLAN_SUMMARY.md.

### Q: Do I need to read all documents?
**A:** No. EXECUTION_PLAN.md contains everything. Other documents are for quick reference or troubleshooting.

### Q: How long will this take?
**A:** 20-35 minutes for the actual execution. Add 30 minutes if reading documentation for the first time.

### Q: What if something goes wrong?
**A:** Check TROUBLESHOOTING_GUIDE.md first. Most common issues have copy-paste solutions.

### Q: Can I run this on different hardware?
**A:** The plan is specific to 16 GPUs across 2 clusters. For different configurations, adjust the `--total-clusters` parameter and worker distribution.

### Q: How do I verify success?
**A:** Run the final validation script in EXECUTION_PLAN.md (Section 6). All 10 checks must pass.

### Q: Can I pause and resume?
**A:** Yes. Workers use checkpointing. If interrupted, re-run launch_distributed.sh and workers will resume from checkpoints.

### Q: What if I need help?
**A:**
1. Check TROUBLESHOOTING_GUIDE.md
2. Review session notes in notes/2025-11-14_*.md
3. Check CLAUDE.md for project-specific instructions
4. Document your issue in notes/issues.log

---

## Success Metrics

Upon successful completion, you will have:

✓ **File:** `embeddings/wikipedia_merged.pkl` (1.9GB)
✓ **Contents:** 250,000 Wikipedia articles × 768 dimensions
✓ **Quality:** No NaN/Inf values, reasonable norms (mean ~1.2)
✓ **Metadata:** Article titles, IDs, URLs
✓ **Backup:** Timestamped copy in embeddings/backups/
✓ **Documentation:** Execution report with metrics
✓ **Ready for:** UMAP projection and visualization

---

## Next Steps After Success

1. **Generate UMAP projections** using build_wikipedia_knowledge_map_v2.py
2. **Create interactive visualization** with knowledge_map_heatmap.html
3. **Deploy demo** to GitHub Pages or hosting service
4. **Archive embeddings** for reproducibility
5. **Document results** in project README

---

## Version History

- **2025-11-14:** Initial creation
  - EXECUTION_PLAN.md (comprehensive guide)
  - EXECUTION_PLAN_SUMMARY.md (quick reference)
  - EXECUTION_CHECKLIST.md (tracking)
  - TROUBLESHOOTING_GUIDE.md (solutions)
  - EXECUTION_INDEX.md (this file)

---

## Document Maintenance

These documents should be updated when:
- New failure modes discovered
- Performance characteristics change
- Hardware/cluster configuration changes
- Script behavior changes
- Better solutions found

**Last Updated:** 2025-11-14
**Maintained by:** Check git log for recent contributors
**Location:** /Users/jmanning/mapper.io/notes/

---

**Ready to begin? Start with one of these:**

→ [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) (Complete guide)
→ [EXECUTION_PLAN_SUMMARY.md](./EXECUTION_PLAN_SUMMARY.md) (Quick start)
→ [EXECUTION_CHECKLIST.md](./EXECUTION_CHECKLIST.md) (Print this)
