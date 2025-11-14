# GPU Cluster Job Monitoring System Design

## Executive Summary

This document describes a robust monitoring system for GPU cluster jobs that provides real-time visibility, automatic failure detection, and accurate progress tracking. The system monitors worker processes, verifies output integrity, parses logs for progress metrics, and provides actionable alerts.

---

## 1. System Architecture

### 1.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Orchestrator                   │
│  - Launch verification                                       │
│  - State management                                          │
│  - Alert coordination                                        │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──────────────┬──────────────┬──────────────┐
             │              │              │              │
             ▼              ▼              ▼              ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Process   │  │   File     │  │    Log     │  │  Progress  │
    │  Monitor   │  │  Monitor   │  │   Parser   │  │ Estimator  │
    └────────────┘  └────────────┘  └────────────┘  └────────────┘
         │               │               │               │
         │               │               │               │
         ▼               ▼               ▼               ▼
    ┌──────────────────────────────────────────────────────────┐
    │                    Alert Manager                          │
    │  - Terminal display (real-time)                           │
    │  - Email notifications                                    │
    │  - Slack/Discord webhooks                                 │
    │  - Log file recording                                     │
    └──────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
Job Launch
    ↓
Launch Verification (0-30 seconds)
    ↓
Real-Time Monitoring Loop (every 5-30 seconds)
    ├→ Check worker processes (ps, nvidia-smi)
    ├→ Verify output files (stat, size changes)
    ├→ Parse log files (tail, grep patterns)
    ├→ Update progress metrics
    ├→ Calculate ETA
    └→ Display status / Send alerts
    ↓
Completion Detection
    ↓
Final Verification
    ↓
Summary Report
```

---

## 2. Detailed Component Design

### 2.1 Process Monitor

**Purpose**: Verify worker processes are running and using GPU resources

**Checks**:
1. Process existence (by PID or job name)
2. Process state (running vs zombie vs sleeping)
3. GPU utilization per worker
4. Memory usage (system + GPU)
5. CPU usage
6. Process uptime
7. Child process count

**Implementation Details**:
```python
class ProcessMonitor:
    def __init__(self, job_name, expected_workers, gpu_ids):
        self.job_name = job_name
        self.expected_workers = expected_workers
        self.gpu_ids = gpu_ids
        self.worker_pids = []
        self.last_seen = {}

    def verify_launch(self, timeout=30):
        """
        Wait for all workers to start within timeout period.
        Returns: (success, missing_workers, error_message)
        """

    def check_workers(self):
        """
        Returns worker status for each expected worker:
        {
            'worker_0': {
                'pid': 12345,
                'status': 'running',  # running, dead, zombie, not_found
                'gpu_id': 0,
                'gpu_util': 95.3,     # percent
                'gpu_memory': 15234,  # MB
                'cpu_percent': 180.5,
                'uptime': 3600,       # seconds
                'last_activity': timestamp
            }
        }
        """

    def detect_crash(self, worker_id):
        """
        Distinguish between:
        - Normal completion (exit code 0, output complete)
        - Crash (non-zero exit, incomplete output)
        - OOM kill (dmesg check)
        - Timeout kill (check job scheduler logs)
        """
```

**Detection Methods**:
- `ps aux | grep <job_name>` - Basic process check
- `nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv` - GPU usage
- `/proc/<pid>/status` - Detailed process state
- `/proc/<pid>/stat` - CPU time, state, uptime
- `dmesg | grep -i oom` - OOM killer events
- Job scheduler logs (SLURM: `sacct`, PBS: `qstat -f`)

### 2.2 File Monitor

**Purpose**: Verify output files exist, are growing, and are valid

**Checks**:
1. Output file existence
2. File size and growth rate
3. File modification time (detect stalls)
4. Checkpoint file creation pattern
5. File integrity (not corrupted/truncated)
6. Disk space availability

**Implementation Details**:
```python
class FileMonitor:
    def __init__(self, output_patterns, checkpoint_patterns, min_growth_rate=1024):
        self.output_patterns = output_patterns  # glob patterns
        self.checkpoint_patterns = checkpoint_patterns
        self.min_growth_rate = min_growth_rate  # bytes per check interval
        self.file_history = {}  # track size over time

    def check_outputs(self):
        """
        Returns output file status:
        {
            '/path/to/output_worker_0.json': {
                'exists': True,
                'size': 1048576,
                'last_modified': timestamp,
                'growth_rate': 1024,  # bytes/second
                'stalled': False,
                'valid': True,        # can be parsed
                'num_records': 1000   # domain-specific
            }
        }
        """

    def check_checkpoints(self):
        """
        Returns checkpoint status:
        {
            'last_checkpoint': '/path/to/ckpt_epoch_5.pt',
            'checkpoint_count': 5,
            'checkpoint_interval': 600,  # seconds
            'last_checkpoint_age': 120,  # seconds since last
            'expected_next': 480         # seconds until next expected
        }
        """

    def verify_disk_space(self):
        """
        Check available disk space in output directory.
        Alert if < 10% or < 10GB remaining.
        """

    def validate_file_integrity(self, filepath):
        """
        Attempt to parse/read file to verify it's not corrupted.
        For JSON: try json.load()
        For CSV: try pandas.read_csv() with nrows=10
        For HDF5/PT: check file magic numbers
        """
```

**Detection Methods**:
- `os.stat()` - File metadata (size, mtime)
- `glob.glob()` - Find files matching patterns
- `os.statvfs()` - Disk space
- Format-specific validators (json.load, etc.)

### 2.3 Log Parser

**Purpose**: Extract progress metrics and error messages from log files

**Checks**:
1. Parse progress indicators (items processed, batch number, epoch)
2. Extract error messages and warnings
3. Track performance metrics (throughput, latency)
4. Detect error patterns (OOM, connection errors, data errors)
5. Monitor custom application metrics

**Implementation Details**:
```python
class LogParser:
    def __init__(self, log_patterns, progress_patterns, error_patterns):
        self.log_patterns = log_patterns
        self.progress_patterns = progress_patterns  # regex patterns
        self.error_patterns = error_patterns
        self.log_positions = {}  # track file position for incremental read

    def parse_progress(self):
        """
        Extract progress from logs:
        {
            'worker_0': {
                'items_processed': 15000,
                'total_items': 100000,
                'current_batch': 500,
                'total_batches': 5000,
                'epoch': 2,
                'loss': 0.345,
                'throughput': 250.5,  # items/second
                'last_update': timestamp
            }
        }
        """

    def parse_errors(self):
        """
        Extract errors and warnings:
        [
            {
                'timestamp': '2025-01-15 10:23:45',
                'worker': 'worker_0',
                'level': 'ERROR',
                'message': 'CUDA out of memory',
                'full_context': '...'
            }
        ]
        """

    def tail_logs(self, num_lines=100):
        """
        Return recent log lines for each worker.
        Used for final crash diagnosis.
        """
```

**Pattern Examples**:
```python
PROGRESS_PATTERNS = {
    'items_processed': r'Processed (\d+)/(\d+) items',
    'batch_number': r'Batch (\d+)/(\d+)',
    'epoch': r'Epoch (\d+)',
    'throughput': r'(\d+\.?\d*) items?/s',
    'loss': r'loss:\s*(\d+\.?\d*)',
}

ERROR_PATTERNS = {
    'oom': r'(out of memory|OOM|CUDA error)',
    'connection': r'(connection refused|timeout|network error)',
    'data_error': r'(corrupt|invalid data|parse error)',
    'cuda_error': r'CUDA error: (.+)',
}
```

### 2.4 Progress Estimator

**Purpose**: Calculate accurate completion estimates and ETAs

**Calculations**:
1. Overall progress percentage
2. Time elapsed
3. Time remaining (ETA)
4. Current throughput
5. Average throughput
6. Completion timestamp estimate

**Implementation Details**:
```python
class ProgressEstimator:
    def __init__(self):
        self.start_time = None
        self.progress_history = []  # [(timestamp, progress_pct)]
        self.throughput_history = []

    def update(self, current_progress, total_items):
        """
        Update progress and calculate new estimates.
        """

    def estimate_eta(self):
        """
        Calculate ETA using multiple methods:
        1. Linear extrapolation from overall progress
        2. Recent throughput average (last 5 minutes)
        3. Moving average throughput

        Returns most conservative estimate with confidence interval.

        Returns:
        {
            'progress_pct': 35.2,
            'elapsed': 3600,           # seconds
            'eta_seconds': 6825,       # seconds remaining
            'eta_timestamp': '2025-01-15 18:45:00',
            'current_throughput': 250.5,
            'avg_throughput': 245.8,
            'confidence': 'high'       # high, medium, low
        }
        """

    def detect_slowdown(self):
        """
        Detect if job is slowing down over time.
        Alert if throughput drops > 20% from peak.
        """
```

### 2.5 Alert Manager

**Purpose**: Notify user of important events in real-time

**Alert Types**:
1. **CRITICAL**: Worker crash, OOM, disk full
2. **WARNING**: Stalled output, slowdown detected, high memory
3. **INFO**: Job started, checkpoint saved, job completed
4. **PROGRESS**: Periodic progress updates

**Implementation Details**:
```python
class AlertManager:
    def __init__(self, alert_config):
        self.config = alert_config
        self.alert_history = []
        self.terminal_display = TerminalDisplay()

    def send_alert(self, level, message, details=None):
        """
        Send alert through configured channels.
        """

    def update_display(self, status_dict):
        """
        Update terminal with real-time status.
        Use curses or rich library for formatted display.
        """
```

**Terminal Display Format**:
```
╔══════════════════════════════════════════════════════════════╗
║              GPU Cluster Job Monitor v1.0                    ║
║  Job: embedding_generation_batch_5                           ║
║  Started: 2025-01-15 10:00:00 (2h 34m ago)                  ║
╠══════════════════════════════════════════════════════════════╣
║  Progress: ████████████████░░░░░░░░  67.3% (67,300/100,000) ║
║  ETA: 1h 15m (2025-01-15 13:49:32)                          ║
║  Throughput: 251.3 items/s (avg: 245.8 items/s)             ║
╠══════════════════════════════════════════════════════════════╣
║  Worker Status:                                              ║
║    worker_0  [GPU 0]  ✓ Running  95% GPU  14.2GB  251 it/s  ║
║    worker_1  [GPU 1]  ✓ Running  94% GPU  14.5GB  248 it/s  ║
║    worker_2  [GPU 2]  ✓ Running  96% GPU  14.0GB  253 it/s  ║
║    worker_3  [GPU 3]  ✓ Running  93% GPU  14.8GB  246 it/s  ║
╠══════════════════════════════════════════════════════════════╣
║  Output Files:                                               ║
║    output_0.json  ✓ Growing  245 MB  (+512 KB/min)          ║
║    output_1.json  ✓ Growing  243 MB  (+508 KB/min)          ║
║    output_2.json  ✓ Growing  246 MB  (+515 KB/min)          ║
║    output_3.json  ✓ Growing  244 MB  (+510 KB/min)          ║
╠══════════════════════════════════════════════════════════════╣
║  Checkpoints: 5 saved, last 12m ago, next expected in 18m   ║
║  Disk Space: 234 GB available (82%)                          ║
╠══════════════════════════════════════════════════════════════╣
║  Recent Events:                                              ║
║    [13:22:15] INFO: Checkpoint saved (epoch_5.pt)           ║
║    [13:15:00] INFO: 60% complete milestone reached           ║
║    [13:10:23] WARNING: GPU 3 memory spike (15.2 GB)         ║
╚══════════════════════════════════════════════════════════════╝

Last updated: 2025-01-15 13:34:12 | Press Ctrl+C to stop monitoring
```

---

## 3. Main Monitoring Script

### 3.1 Pseudocode

```python
#!/usr/bin/env python3
"""
GPU Cluster Job Monitor
Real-time monitoring with failure detection and progress tracking
"""

import time
import sys
import argparse
from dataclasses import dataclass
from enum import Enum

class JobState(Enum):
    LAUNCHING = "launching"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    STALLED = "stalled"

@dataclass
class MonitorConfig:
    job_name: str
    num_workers: int
    gpu_ids: list
    output_dir: str
    log_dir: str
    checkpoint_dir: str
    total_items: int

    # Monitoring parameters
    check_interval: int = 10  # seconds
    launch_timeout: int = 60
    stall_timeout: int = 300  # 5 minutes without progress

    # Alert configuration
    alert_email: str = None
    alert_slack_webhook: str = None

    # Patterns
    output_pattern: str = "output_worker_*.json"
    checkpoint_pattern: str = "checkpoint_epoch_*.pt"
    log_pattern: str = "worker_*.log"

def main():
    # Parse command line arguments
    config = parse_args()

    # Initialize components
    process_monitor = ProcessMonitor(
        job_name=config.job_name,
        expected_workers=config.num_workers,
        gpu_ids=config.gpu_ids
    )

    file_monitor = FileMonitor(
        output_patterns=[f"{config.output_dir}/{config.output_pattern}"],
        checkpoint_patterns=[f"{config.checkpoint_dir}/{config.checkpoint_pattern}"]
    )

    log_parser = LogParser(
        log_patterns=[f"{config.log_dir}/{config.log_pattern}"],
        progress_patterns=PROGRESS_PATTERNS,
        error_patterns=ERROR_PATTERNS
    )

    progress_estimator = ProgressEstimator()
    alert_manager = AlertManager(config)

    # Phase 1: Launch Verification
    alert_manager.send_alert("INFO", "Starting job launch verification...")

    success, missing, error = process_monitor.verify_launch(
        timeout=config.launch_timeout
    )

    if not success:
        alert_manager.send_alert(
            "CRITICAL",
            f"Job launch failed: {error}",
            {"missing_workers": missing}
        )
        return 1

    alert_manager.send_alert("INFO", "All workers launched successfully!")
    progress_estimator.start_time = time.time()

    job_state = JobState.RUNNING
    last_progress = 0
    last_progress_time = time.time()
    consecutive_errors = 0

    # Phase 2: Real-Time Monitoring Loop
    try:
        while job_state in [JobState.RUNNING, JobState.COMPLETING]:

            # 1. Check worker processes
            worker_status = process_monitor.check_workers()

            # Detect crashes
            for worker_id, status in worker_status.items():
                if status['status'] == 'dead':
                    crash_info = process_monitor.detect_crash(worker_id)
                    alert_manager.send_alert(
                        "CRITICAL",
                        f"{worker_id} crashed!",
                        crash_info
                    )
                    job_state = JobState.FAILED
                    break

                elif status['status'] == 'zombie':
                    alert_manager.send_alert(
                        "WARNING",
                        f"{worker_id} is in zombie state",
                        status
                    )

            if job_state == JobState.FAILED:
                break

            # 2. Check output files
            output_status = file_monitor.check_outputs()

            for filepath, status in output_status.items():
                if not status['exists']:
                    alert_manager.send_alert(
                        "WARNING",
                        f"Output file missing: {filepath}"
                    )

                elif status['stalled']:
                    alert_manager.send_alert(
                        "WARNING",
                        f"Output file stalled: {filepath}",
                        {"last_modified": status['last_modified']}
                    )

            # Check disk space
            disk_status = file_monitor.verify_disk_space()
            if disk_status['percent_free'] < 10:
                alert_manager.send_alert(
                    "CRITICAL",
                    f"Low disk space: {disk_status['gb_free']} GB remaining"
                )

            # 3. Parse logs for progress
            progress_data = log_parser.parse_progress()
            error_data = log_parser.parse_errors()

            # Alert on new errors
            for error in error_data:
                if error['level'] == 'ERROR':
                    alert_manager.send_alert(
                        "CRITICAL" if 'oom' in error['message'].lower() else "WARNING",
                        f"Error in {error['worker']}: {error['message']}",
                        error
                    )

            # Calculate overall progress
            total_processed = sum(
                w['items_processed']
                for w in progress_data.values()
            )

            # 4. Update progress estimates
            progress_estimator.update(total_processed, config.total_items)
            estimates = progress_estimator.estimate_eta()

            # Detect stalls
            if total_processed == last_progress:
                stall_duration = time.time() - last_progress_time
                if stall_duration > config.stall_timeout:
                    alert_manager.send_alert(
                        "CRITICAL",
                        f"Job stalled! No progress for {stall_duration/60:.1f} minutes"
                    )
                    job_state = JobState.STALLED
            else:
                last_progress = total_processed
                last_progress_time = time.time()

            # Detect slowdown
            slowdown = progress_estimator.detect_slowdown()
            if slowdown:
                alert_manager.send_alert(
                    "WARNING",
                    f"Job slowdown detected: {slowdown['percent_drop']:.1f}% drop in throughput"
                )

            # 5. Check for completion
            if estimates['progress_pct'] >= 99.9:
                job_state = JobState.COMPLETING
                alert_manager.send_alert("INFO", "Job nearing completion, verifying...")

            # Check if all workers finished
            all_finished = all(
                status['status'] != 'running'
                for status in worker_status.values()
            )

            if job_state == JobState.COMPLETING and all_finished:
                job_state = JobState.COMPLETED
                break

            # 6. Update display
            display_data = {
                'job_state': job_state,
                'worker_status': worker_status,
                'output_status': output_status,
                'progress_data': progress_data,
                'estimates': estimates,
                'checkpoint_status': file_monitor.check_checkpoints(),
                'disk_status': disk_status,
                'recent_errors': error_data[-5:]
            }

            alert_manager.update_display(display_data)

            # 7. Sleep until next check
            time.sleep(config.check_interval)

    except KeyboardInterrupt:
        alert_manager.send_alert("INFO", "Monitoring stopped by user")
        return 0

    # Phase 3: Final Verification
    if job_state == JobState.COMPLETED:
        alert_manager.send_alert("INFO", "Verifying job completion...")

        # Verify all outputs are complete and valid
        verification_passed = True

        for filepath, status in output_status.items():
            if not file_monitor.validate_file_integrity(filepath):
                alert_manager.send_alert(
                    "CRITICAL",
                    f"Output file corrupted: {filepath}"
                )
                verification_passed = False

        # Check if total processed matches expected
        if total_processed < config.total_items * 0.99:
            alert_manager.send_alert(
                "WARNING",
                f"Job completed but processed fewer items than expected: "
                f"{total_processed}/{config.total_items}"
            )
            verification_passed = False

        if verification_passed:
            alert_manager.send_alert(
                "INFO",
                "Job completed successfully!",
                {
                    'total_time': time.time() - progress_estimator.start_time,
                    'items_processed': total_processed,
                    'avg_throughput': estimates['avg_throughput']
                }
            )
            return 0
        else:
            return 1

    elif job_state == JobState.FAILED:
        # Gather diagnostic information
        diagnostics = {
            'worker_status': worker_status,
            'recent_logs': log_parser.tail_logs(num_lines=50),
            'output_status': output_status,
            'checkpoint_status': file_monitor.check_checkpoints()
        }

        alert_manager.send_alert(
            "CRITICAL",
            "Job failed! See diagnostics for details.",
            diagnostics
        )

        # Save diagnostics to file
        save_diagnostics(diagnostics, config)

        return 1

    elif job_state == JobState.STALLED:
        alert_manager.send_alert(
            "CRITICAL",
            "Job stalled! Manual intervention required."
        )
        return 1

    return 0

def parse_args():
    parser = argparse.ArgumentParser(
        description="Monitor GPU cluster jobs with real-time progress tracking"
    )

    parser.add_argument('--job-name', required=True,
                       help='Name of the job to monitor')
    parser.add_argument('--num-workers', type=int, required=True,
                       help='Expected number of worker processes')
    parser.add_argument('--gpu-ids', nargs='+', type=int, required=True,
                       help='GPU IDs used by workers')
    parser.add_argument('--output-dir', required=True,
                       help='Directory containing output files')
    parser.add_argument('--log-dir', required=True,
                       help='Directory containing log files')
    parser.add_argument('--checkpoint-dir',
                       help='Directory containing checkpoint files')
    parser.add_argument('--total-items', type=int,
                       help='Total items to process (for ETA calculation)')

    parser.add_argument('--check-interval', type=int, default=10,
                       help='Seconds between status checks (default: 10)')
    parser.add_argument('--launch-timeout', type=int, default=60,
                       help='Seconds to wait for job launch (default: 60)')
    parser.add_argument('--stall-timeout', type=int, default=300,
                       help='Seconds without progress before alerting (default: 300)')

    parser.add_argument('--alert-email',
                       help='Email address for alerts')
    parser.add_argument('--alert-slack',
                       help='Slack webhook URL for alerts')

    parser.add_argument('--output-pattern', default='output_worker_*.json',
                       help='Glob pattern for output files')
    parser.add_argument('--log-pattern', default='worker_*.log',
                       help='Glob pattern for log files')
    parser.add_argument('--checkpoint-pattern', default='checkpoint_*.pt',
                       help='Glob pattern for checkpoint files')

    args = parser.parse_args()

    # Convert to config object
    config = MonitorConfig(
        job_name=args.job_name,
        num_workers=args.num_workers,
        gpu_ids=args.gpu_ids,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        checkpoint_dir=args.checkpoint_dir or args.output_dir,
        total_items=args.total_items or 0,
        check_interval=args.check_interval,
        launch_timeout=args.launch_timeout,
        stall_timeout=args.stall_timeout,
        alert_email=args.alert_email,
        alert_slack_webhook=args.alert_slack,
        output_pattern=args.output_pattern,
        log_pattern=args.log_pattern,
        checkpoint_pattern=args.checkpoint_pattern
    )

    return config

if __name__ == '__main__':
    sys.exit(main())
```

### 3.2 Usage Examples

```bash
# Basic monitoring
python monitor_job.py \
    --job-name embedding_generation \
    --num-workers 4 \
    --gpu-ids 0 1 2 3 \
    --output-dir /scratch/outputs \
    --log-dir /scratch/logs \
    --total-items 100000

# With alerts and custom patterns
python monitor_job.py \
    --job-name training_run \
    --num-workers 8 \
    --gpu-ids 0 1 2 3 4 5 6 7 \
    --output-dir /data/results \
    --log-dir /data/logs \
    --checkpoint-dir /data/checkpoints \
    --total-items 1000000 \
    --check-interval 15 \
    --stall-timeout 600 \
    --alert-email user@example.com \
    --alert-slack https://hooks.slack.com/... \
    --output-pattern "results_gpu_*.jsonl" \
    --checkpoint-pattern "model_step_*.pt"

# Monitor already-running job
python monitor_job.py \
    --job-name inference_batch_5 \
    --num-workers 4 \
    --gpu-ids 0 1 2 3 \
    --output-dir /results \
    --log-dir /logs
```

---

## 4. Job Launch Verification Checklist

### 4.1 Pre-Launch Checks

```
┌─────────────────────────────────────────────────────────────┐
│              PRE-LAUNCH VERIFICATION CHECKLIST               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [ ] 1. Environment Setup                                   │
│      [ ] Conda/virtualenv activated                         │
│      [ ] Required packages installed                        │
│      [ ] CUDA version compatible                            │
│      [ ] Environment variables set                          │
│                                                              │
│  [ ] 2. Resource Availability                               │
│      [ ] GPUs available (nvidia-smi)                        │
│      [ ] Sufficient GPU memory                              │
│      [ ] Sufficient disk space (>20% free)                  │
│      [ ] Network connectivity (if needed)                   │
│                                                              │
│  [ ] 3. Input Data                                          │
│      [ ] Input files exist                                  │
│      [ ] Input files readable                               │
│      [ ] Input data valid format                            │
│      [ ] Data split correctly across workers                │
│                                                              │
│  [ ] 4. Output Configuration                                │
│      [ ] Output directory exists and writable               │
│      [ ] Output directory empty (or resume mode set)        │
│      [ ] Checkpoint directory configured                    │
│      [ ] Log directory configured                           │
│                                                              │
│  [ ] 5. Job Script Review                                   │
│      [ ] Worker count matches GPU count                     │
│      [ ] GPU IDs specified correctly                        │
│      [ ] Batch size appropriate for GPU memory              │
│      [ ] Checkpoint frequency set                           │
│      [ ] Logging enabled and configured                     │
│      [ ] Error handling implemented                         │
│                                                              │
│  [ ] 6. Monitoring Setup                                    │
│      [ ] Monitor script ready                               │
│      [ ] Alert endpoints configured                         │
│      [ ] Progress patterns defined                          │
│      [ ] Expected output patterns defined                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Post-Launch Verification (0-60 seconds)

```python
def verify_job_launch(config):
    """
    Comprehensive launch verification within first 60 seconds.
    Returns: (success: bool, issues: list, warnings: list)
    """

    issues = []
    warnings = []

    # Wait for processes to start (0-30 seconds)
    print("Waiting for workers to start...")
    time.sleep(5)

    for attempt in range(6):  # Check every 5 seconds for 30 seconds
        workers_found = find_worker_processes(config.job_name)
        if len(workers_found) >= config.num_workers:
            print(f"✓ All {config.num_workers} workers started")
            break
        time.sleep(5)
    else:
        issues.append(
            f"Only {len(workers_found)}/{config.num_workers} workers started"
        )

    # Check GPU assignment (30-35 seconds)
    print("Verifying GPU assignment...")
    gpu_processes = get_gpu_processes()

    for gpu_id in config.gpu_ids:
        processes_on_gpu = [p for p in gpu_processes if p['gpu_id'] == gpu_id]
        if not processes_on_gpu:
            issues.append(f"No process found on GPU {gpu_id}")
        elif len(processes_on_gpu) > 1:
            warnings.append(f"Multiple processes on GPU {gpu_id}")

    # Check initial GPU utilization (35-45 seconds)
    print("Waiting for GPU utilization...")
    time.sleep(10)

    gpu_stats = get_gpu_utilization()
    for gpu_id in config.gpu_ids:
        if gpu_stats[gpu_id]['utilization'] < 10:
            warnings.append(
                f"Low GPU utilization on GPU {gpu_id}: "
                f"{gpu_stats[gpu_id]['utilization']}%"
            )

    # Check log files created (45-50 seconds)
    print("Checking log files...")
    log_files = glob.glob(f"{config.log_dir}/{config.log_pattern}")

    if len(log_files) < config.num_workers:
        issues.append(
            f"Only {len(log_files)}/{config.num_workers} log files created"
        )

    # Check initial log content
    for log_file in log_files:
        if os.path.getsize(log_file) == 0:
            warnings.append(f"Log file empty: {log_file}")

    # Check output directory (50-55 seconds)
    print("Checking output directory...")

    if not os.path.exists(config.output_dir):
        issues.append(f"Output directory missing: {config.output_dir}")
    elif not os.access(config.output_dir, os.W_OK):
        issues.append(f"Output directory not writable: {config.output_dir}")

    # Final wait for initial output (55-60 seconds)
    print("Waiting for initial output...")
    time.sleep(5)

    output_files = glob.glob(f"{config.output_dir}/{config.output_pattern}")
    if len(output_files) == 0:
        warnings.append("No output files created yet")

    # Summary
    success = len(issues) == 0

    if success:
        print("\n✓ Job launch verification PASSED")
    else:
        print("\n✗ Job launch verification FAILED")
        print("\nIssues:")
        for issue in issues:
            print(f"  - {issue}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    return success, issues, warnings
```

---

## 5. Troubleshooting Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│                  TROUBLESHOOTING FLOW                        │
└─────────────────────────────────────────────────────────────┘

Is the job running?
│
├─ NO → Check process status
│   │
│   ├─ No processes found
│   │   ├─ Check job scheduler status (squeue, qstat)
│   │   ├─ Check launch script errors
│   │   └─ Review submission logs
│   │
│   ├─ Processes exist but zombie/dead
│   │   ├─ Check exit codes (SLURM: sacct)
│   │   ├─ Review worker logs (last 50 lines)
│   │   ├─ Check OOM events (dmesg)
│   │   └─ Check disk space
│   │
│   └─ Process count mismatch
│       ├─ Some workers failed to start
│       ├─ Check resource limits
│       └─ Review individual worker logs
│
└─ YES → Check GPU utilization
    │
    ├─ Low GPU utilization (<20%)
    │   ├─ Data loading bottleneck?
    │   │   └─ Check I/O wait (iostat)
    │   ├─ CPU preprocessing bottleneck?
    │   │   └─ Check CPU usage
    │   ├─ Network bottleneck?
    │   │   └─ Check network I/O (iftop)
    │   └─ Code issue?
    │       └─ Profile code (py-spy)
    │
    ├─ GPU utilization normal (>80%)
    │   │
    │   ├─ Are output files growing?
    │   │   │
    │   │   ├─ NO → Check for silent failures
    │   │   │   ├─ Review logs for errors
    │   │   │   ├─ Check file permissions
    │   │   │   └─ Check disk space
    │   │   │
    │   │   └─ YES → Check progress in logs
    │   │       │
    │   │       ├─ Progress increasing
    │   │       │   └─ Job healthy! Continue monitoring
    │   │       │
    │   │       └─ No progress or stuck
    │   │           ├─ Deadlock?
    │   │           ├─ Infinite loop?
    │   │           └─ Waiting on resource?
    │   │
    │   └─ GPU memory issues
    │       ├─ OOM errors in logs?
    │       │   ├─ Reduce batch size
    │       │   ├─ Enable gradient checkpointing
    │       │   └─ Use mixed precision
    │       │
    │       └─ Memory leak?
    │           └─ Monitor memory over time
    │
    └─ Intermittent GPU utilization
        ├─ Checkpointing overhead?
        │   └─ Increase checkpoint interval
        ├─ Data loading gaps?
        │   └─ Increase num_workers in DataLoader
        └─ Network fetches?
            └─ Implement caching
```

### 5.1 Common Issues and Solutions

| Issue | Symptoms | Diagnosis | Solution |
|-------|----------|-----------|----------|
| **Worker Not Starting** | Process missing, no log file | Check scheduler logs, environment | Fix environment, resubmit job |
| **OOM Kill** | Process dies, "OOM" in dmesg, exit code 137 | Check GPU memory usage, batch size | Reduce batch size, use mixed precision |
| **Data Loading Bottleneck** | Low GPU util, high CPU I/O wait | Profile data loading, check disk speed | Increase DataLoader workers, use SSD |
| **Output Stalled** | Processes running, files not growing | Check logs for errors, file permissions | Fix errors, check disk space |
| **Checkpoint Corruption** | Crashes when loading checkpoint | Try loading checkpoint manually | Implement atomic writes, keep backups |
| **Network Timeout** | Connection errors in logs | Check network connectivity | Implement retry logic, increase timeout |
| **Slow Progress** | Low throughput, increasing runtime | Compare with baseline, profile code | Optimize bottlenecks, scale resources |
| **Silent Crash** | Processes gone, no clear error | Check scheduler logs, dmesg, core dumps | Enable better error logging, use try-except |
| **Disk Full** | Write errors, processes crash | Check disk space (df -h) | Clean up old files, use larger disk |
| **GPU Hang** | GPU util stuck at 100%, no progress | Check nvidia-smi, look for hung kernel | Kill process, reset GPU, investigate code |

### 5.2 Diagnostic Commands

```bash
# Process Status
ps aux | grep <job_name>
pstree -p <pid>  # Show process tree

# GPU Status
nvidia-smi
nvidia-smi dmon -i 0 -s puct  # Continuous monitoring
nvidia-smi pmon -i 0  # Per-process monitoring

# Resource Usage
top -u $USER
htop
iostat -x 5  # Disk I/O
iftop  # Network I/O

# Memory
free -h
cat /proc/<pid>/status | grep -i mem
dmesg | grep -i oom  # OOM kills

# Job Scheduler (SLURM)
squeue -u $USER
sacct -j <job_id> --format=JobID,JobName,State,ExitCode
scontrol show job <job_id>

# Job Scheduler (PBS)
qstat -u $USER
qstat -f <job_id>

# Disk Space
df -h
du -sh <directory>
find <directory> -type f -exec du -h {} + | sort -rh | head -20

# File Activity
lsof +D <directory>  # Open files
watch -n 5 'ls -lh <directory>'  # Monitor file sizes

# Logs
tail -f <log_file>
tail -100 <log_file> | grep -i error
journalctl -u <service> -f  # System logs

# Network
netstat -tupln | grep <port>
ss -tuln | grep <port>
ping <host>
traceroute <host>

# Profiling
py-spy top --pid <pid>
py-spy dump --pid <pid>
strace -p <pid>  # System calls
```

---

## 6. Implementation Guidelines

### 6.1 Required Python Packages

```
requirements.txt:
----------------
psutil>=5.9.0        # Process and system monitoring
GPUtil>=1.4.0        # GPU monitoring
py3nvml>=0.2.7       # NVIDIA driver interface
rich>=13.0.0         # Terminal formatting
click>=8.0.0         # CLI framework
pyyaml>=6.0          # Config files
requests>=2.28.0     # Alert webhooks
python-dateutil      # Time parsing
```

### 6.2 Configuration File Format

```yaml
# monitor_config.yaml
job:
  name: "embedding_generation_v2"
  num_workers: 4
  gpu_ids: [0, 1, 2, 3]
  total_items: 100000

paths:
  output_dir: "/scratch/outputs"
  log_dir: "/scratch/logs"
  checkpoint_dir: "/scratch/checkpoints"

patterns:
  output: "output_worker_*.json"
  logs: "worker_*.log"
  checkpoints: "checkpoint_epoch_*.pt"

monitoring:
  check_interval: 10
  launch_timeout: 60
  stall_timeout: 300

progress_patterns:
  items_processed: 'Processed (\d+)/(\d+) items'
  throughput: '(\d+\.?\d*) items/s'
  epoch: 'Epoch (\d+)/(\d+)'

error_patterns:
  - pattern: '(out of memory|OOM)'
    severity: 'critical'
  - pattern: '(CUDA error)'
    severity: 'critical'
  - pattern: '(connection refused|timeout)'
    severity: 'warning'

alerts:
  email:
    enabled: true
    address: "user@example.com"
    smtp_server: "smtp.gmail.com"
    smtp_port: 587

  slack:
    enabled: true
    webhook: "https://hooks.slack.com/services/..."

  terminal:
    enabled: true
    refresh_rate: 1  # seconds
```

### 6.3 Integration with Job Launcher

```bash
#!/bin/bash
# launch_and_monitor.sh
# Integrated job launch and monitoring script

set -e

# Configuration
JOB_NAME="embedding_generation"
NUM_WORKERS=4
GPU_IDS=(0 1 2 3)
OUTPUT_DIR="/scratch/outputs"
LOG_DIR="/scratch/logs"

# Create directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# Launch job
echo "Launching job: $JOB_NAME"

for i in $(seq 0 $((NUM_WORKERS - 1))); do
    CUDA_VISIBLE_DEVICES=${GPU_IDS[$i]} \
    python worker.py \
        --worker-id $i \
        --output-file "$OUTPUT_DIR/output_worker_$i.json" \
        --log-file "$LOG_DIR/worker_$i.log" \
        > "$LOG_DIR/worker_${i}_stdout.log" \
        2> "$LOG_DIR/worker_${i}_stderr.log" &

    WORKER_PIDS[$i]=$!
    echo "Started worker $i (PID: ${WORKER_PIDS[$i]}) on GPU ${GPU_IDS[$i]}"
done

# Save PIDs for monitoring
echo "${WORKER_PIDS[@]}" > "$LOG_DIR/worker_pids.txt"

# Wait a moment for workers to initialize
sleep 5

# Launch monitoring in foreground
echo "Starting real-time monitoring..."
python monitor_job.py \
    --job-name "$JOB_NAME" \
    --num-workers $NUM_WORKERS \
    --gpu-ids ${GPU_IDS[@]} \
    --output-dir "$OUTPUT_DIR" \
    --log-dir "$LOG_DIR" \
    --total-items 100000 \
    --alert-email "user@example.com"

# Capture monitoring exit code
MONITOR_EXIT=$?

# Cleanup
if [ $MONITOR_EXIT -eq 0 ]; then
    echo "Job completed successfully!"
else
    echo "Job failed! Check logs in $LOG_DIR"
    exit 1
fi
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

Test each component independently:

```python
# test_process_monitor.py
def test_process_detection():
    """Test that running processes are detected correctly."""

def test_gpu_assignment():
    """Test GPU assignment verification."""

def test_crash_detection():
    """Test differentiation between crash types."""

# test_file_monitor.py
def test_file_growth_detection():
    """Test detection of file growth."""

def test_stall_detection():
    """Test detection of stalled output."""

def test_integrity_validation():
    """Test file integrity checks."""

# test_log_parser.py
def test_progress_extraction():
    """Test extraction of progress metrics."""

def test_error_pattern_matching():
    """Test error pattern detection."""

# test_progress_estimator.py
def test_eta_calculation():
    """Test ETA estimation accuracy."""

def test_slowdown_detection():
    """Test throughput degradation detection."""
```

### 7.2 Integration Tests

Test complete monitoring workflow:

```python
def test_full_monitoring_cycle():
    """
    Launch a test job and verify monitoring detects:
    - Process launch
    - GPU utilization
    - Output file creation
    - Progress updates
    - Completion
    """

def test_crash_handling():
    """
    Launch job that crashes and verify:
    - Crash detection
    - Error extraction
    - Alert generation
    """

def test_stall_detection():
    """
    Launch job that stalls and verify:
    - Stall detection after timeout
    - Alert generation
    """
```

### 7.3 Load Tests

Test monitoring overhead:

```python
def test_monitoring_overhead():
    """
    Verify monitoring adds <1% overhead to job runtime.
    """

def test_large_scale():
    """
    Test monitoring with 32+ workers across 8 GPUs.
    """

def test_long_duration():
    """
    Test monitoring for multi-hour jobs.
    """
```

---

## 8. Future Enhancements

### 8.1 Advanced Features

1. **Predictive Failure Detection**
   - Machine learning model to predict failures before they occur
   - Based on historical patterns (memory growth, throughput decline)

2. **Automatic Recovery**
   - Automatic restart of crashed workers
   - Checkpoint-based resume
   - Dynamic resource reallocation

3. **Multi-Job Coordination**
   - Monitor multiple related jobs
   - Dependency tracking
   - Resource sharing optimization

4. **Web Dashboard**
   - Real-time web interface
   - Historical job analytics
   - Cluster utilization visualization

5. **Cost Tracking**
   - GPU-hour usage
   - Cost per item processed
   - Budget alerts

### 8.2 Advanced Metrics

1. **Performance Profiling**
   - Per-batch timing
   - Bottleneck identification
   - Memory profiling

2. **Data Quality Monitoring**
   - Output validation
   - Anomaly detection
   - Statistical summaries

3. **Resource Efficiency**
   - GPU utilization distribution
   - Idle time tracking
   - Power consumption

### 8.3 Integration Opportunities

1. **Job Schedulers**
   - Native SLURM/PBS integration
   - Kubernetes jobs
   - Cloud platform APIs (AWS, GCP, Azure)

2. **Experiment Tracking**
   - Weights & Biases integration
   - MLflow integration
   - TensorBoard integration

3. **Alerting Systems**
   - PagerDuty integration
   - Opsgenie integration
   - Custom webhook support

---

## 9. Best Practices

### 9.1 Job Design

1. **Enable Detailed Logging**
   ```python
   # Example logging setup
   import logging

   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s [%(levelname)s] %(message)s',
       handlers=[
           logging.FileHandler(f'worker_{worker_id}.log'),
           logging.StreamHandler()
       ]
   )

   # Log progress regularly
   if batch_idx % 10 == 0:
       logging.info(f"Processed {batch_idx * batch_size}/{total_items} items "
                   f"({throughput:.1f} items/s)")
   ```

2. **Implement Graceful Shutdown**
   ```python
   import signal
   import sys

   def signal_handler(sig, frame):
       logging.info("Received shutdown signal, saving checkpoint...")
       save_checkpoint(current_state)
       sys.exit(0)

   signal.signal(signal.SIGINT, signal_handler)
   signal.signal(signal.SIGTERM, signal_handler)
   ```

3. **Use Atomic File Writes**
   ```python
   import tempfile
   import shutil

   def atomic_write(filepath, data):
       # Write to temporary file first
       with tempfile.NamedTemporaryFile('w', delete=False) as tf:
           json.dump(data, tf)
           temp_name = tf.name

       # Atomic rename
       shutil.move(temp_name, filepath)
   ```

4. **Regular Checkpointing**
   ```python
   # Save checkpoint every N batches
   if batch_idx % checkpoint_interval == 0:
       checkpoint = {
           'batch_idx': batch_idx,
           'model_state': model.state_dict(),
           'optimizer_state': optimizer.state_dict(),
           'processed_items': processed_items
       }
       torch.save(checkpoint, f'checkpoint_batch_{batch_idx}.pt')
   ```

### 9.2 Monitoring Configuration

1. **Choose Appropriate Check Intervals**
   - Short jobs (<10 min): 5-10 second checks
   - Medium jobs (10 min - 1 hour): 10-30 second checks
   - Long jobs (>1 hour): 30-60 second checks

2. **Set Realistic Timeouts**
   - Launch timeout: 2-3x expected startup time
   - Stall timeout: 3-5x checkpoint interval
   - Alert throttling: Avoid alert spam

3. **Configure Alert Priorities**
   - CRITICAL: Immediate attention required (crash, OOM)
   - WARNING: Monitor closely (slowdown, high memory)
   - INFO: Informational (progress milestones)

### 9.3 Operational Procedures

1. **Pre-Launch**
   - Run pre-launch checklist
   - Test with small dataset first
   - Verify monitoring configuration

2. **During Job**
   - Monitor actively for first 5-10 minutes
   - Check periodically for long jobs
   - Respond immediately to CRITICAL alerts

3. **Post-Completion**
   - Verify output integrity
   - Review performance metrics
   - Archive logs and checkpoints
   - Document issues for future reference

---

## 10. Summary

This GPU cluster job monitoring system addresses all key requirements:

1. **Real-Time Foreground Monitoring**: Continuous active monitoring with live terminal display
2. **Process Verification**: Multi-layer checks (existence, state, GPU usage)
3. **Output Verification**: File growth tracking and integrity validation
4. **Checkpoint Monitoring**: Track checkpoint creation and timing
5. **Progress Parsing**: Extract actual progress from logs with regex patterns
6. **Crash Detection**: Distinguish crash types (OOM, timeout, error)
7. **Immediate Alerts**: Real-time notifications through multiple channels
8. **Accurate ETA**: Based on actual throughput with confidence intervals

The system provides comprehensive visibility into job health and progress, enabling rapid response to failures and confident execution of long-running GPU cluster jobs.

### Key Benefits

- **Reduced Wasted Compute**: Detect failures within minutes, not hours
- **Increased Confidence**: Know exactly what's happening at all times
- **Better Debugging**: Rich diagnostics for troubleshooting
- **Improved Planning**: Accurate ETAs enable better resource scheduling
- **Lower Stress**: Automated monitoring reduces manual checking burden

### Implementation Timeline

1. **Week 1**: Core monitoring components (Process, File, Log monitors)
2. **Week 2**: Progress estimation and alert system
3. **Week 3**: Terminal display and integration testing
4. **Week 4**: Documentation, testing, and deployment

### Success Metrics

- Zero undetected failures
- <2 minute detection time for crashes
- <5% monitoring overhead
- ±10% ETA accuracy
- 100% output validation rate
