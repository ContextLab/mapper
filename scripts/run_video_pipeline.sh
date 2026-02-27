#!/usr/bin/env bash
# T-V006: Run the full video recommendation pipeline end-to-end.
#
# Orchestrates: embed windows → project coords → export catalog
#
# Stages 1-2 (scrape + transcripts) are typically run separately on tensor02.
# This script runs stages 3-5 locally, using whatever transcripts are available.
#
# NOTE: Must re-run after new transcripts arrive or UMAP is re-fit.
#
# Usage:
#   ./scripts/run_video_pipeline.sh
#   ./scripts/run_video_pipeline.sh --reducer embeddings/umap_reducer.pkl --bounds embeddings/umap_bounds.pkl
#   ./scripts/run_video_pipeline.sh --skip-embed   # skip embedding if already done
#   ./scripts/run_video_pipeline.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

# Defaults
REDUCER="${PROJECT_ROOT}/embeddings/umap_reducer.pkl"
BOUNDS="${PROJECT_ROOT}/embeddings/umap_bounds.pkl"
SKIP_EMBED=false
DRY_RUN=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reducer)   REDUCER="$2"; shift 2 ;;
        --bounds)    BOUNDS="$2"; shift 2 ;;
        --skip-embed) SKIP_EMBED=true; shift ;;
        --dry-run)   DRY_RUN=true; shift ;;
        --force)     FORCE=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--reducer PATH] [--bounds PATH] [--skip-embed] [--dry-run] [--force]"
            echo ""
            echo "Runs stages 3-5 of the video pipeline:"
            echo "  Stage 3: Sliding-window embeddings (embed_video_windows.py)"
            echo "  Stage 4: UMAP projection (project_video_coords.py)"
            echo "  Stage 5: Video catalog export (export_video_catalog.py)"
            echo ""
            echo "Options:"
            echo "  --reducer PATH   Path to UMAP reducer pkl (default: embeddings/umap_reducer.pkl)"
            echo "  --bounds PATH    Path to UMAP bounds pkl (default: embeddings/umap_bounds.pkl)"
            echo "  --skip-embed     Skip stage 3 (use existing embeddings)"
            echo "  --dry-run        Dry-run all stages"
            echo "  --force          Force re-process all (ignore existing files)"
            exit 0
            ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "======================================================================"
echo "VIDEO RECOMMENDATION PIPELINE"
echo "======================================================================"
echo "Started: $(date)"
echo "Project root: ${PROJECT_ROOT}"
echo ""

PIPELINE_START=$(date +%s)

# Validate prerequisites
if [[ ! -f "$PYTHON" ]]; then
    echo "ERROR: Python venv not found at $PYTHON"
    echo "  Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [[ ! -f "$REDUCER" ]]; then
    echo "ERROR: UMAP reducer not found at $REDUCER"
    exit 1
fi

if [[ ! -f "$BOUNDS" ]]; then
    echo "ERROR: UMAP bounds not found at $BOUNDS"
    exit 1
fi

TRANSCRIPT_DIR="${PROJECT_ROOT}/data/videos/.working/transcripts"
TRANSCRIPT_COUNT=$(find "$TRANSCRIPT_DIR" -name '*.txt' 2>/dev/null | wc -l | tr -d ' ')
echo "Transcripts available: ${TRANSCRIPT_COUNT}"
echo ""

if [[ "$TRANSCRIPT_COUNT" -eq 0 ]]; then
    echo "ERROR: No transcripts found in ${TRANSCRIPT_DIR}"
    echo "  Run the transcript pipeline on tensor02 first."
    exit 1
fi

# ─── Stage 3: Sliding-Window Embeddings ──────────────────────────

STAGE3_START=$(date +%s)
echo "----------------------------------------------------------------------"
echo "STAGE 3: Sliding-Window Embeddings"
echo "----------------------------------------------------------------------"

if [[ "$SKIP_EMBED" == true ]]; then
    echo "  Skipped (--skip-embed)"
    EMB_COUNT=$(find "${PROJECT_ROOT}/data/videos/.working/embeddings" -name '*.npy' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Existing embeddings: ${EMB_COUNT}"
else
    EMBED_ARGS=""
    if [[ "$DRY_RUN" == true ]]; then EMBED_ARGS="--dry-run"; fi
    if [[ "$FORCE" == true ]]; then EMBED_ARGS="${EMBED_ARGS} --force"; fi

    "$PYTHON" scripts/embed_video_windows.py $EMBED_ARGS

    if [[ $? -ne 0 ]]; then
        echo "ERROR: Stage 3 failed"
        exit 1
    fi
fi

STAGE3_END=$(date +%s)
echo "  Stage 3 time: $(( STAGE3_END - STAGE3_START ))s"
echo ""

# ─── Stage 4: UMAP Projection ───────────────────────────────────

STAGE4_START=$(date +%s)
echo "----------------------------------------------------------------------"
echo "STAGE 4: UMAP Projection"
echo "----------------------------------------------------------------------"

PROJECT_ARGS="--reducer $REDUCER --bounds $BOUNDS"
if [[ "$DRY_RUN" == true ]]; then PROJECT_ARGS="${PROJECT_ARGS} --dry-run"; fi
if [[ "$FORCE" == true ]]; then PROJECT_ARGS="${PROJECT_ARGS} --force"; fi

"$PYTHON" scripts/project_video_coords.py $PROJECT_ARGS

if [[ $? -ne 0 ]]; then
    echo "ERROR: Stage 4 failed"
    exit 1
fi

STAGE4_END=$(date +%s)
echo "  Stage 4 time: $(( STAGE4_END - STAGE4_START ))s"
echo ""

# ─── Stage 5: Video Catalog Export ───────────────────────────────

STAGE5_START=$(date +%s)
echo "----------------------------------------------------------------------"
echo "STAGE 5: Video Catalog Export"
echo "----------------------------------------------------------------------"

EXPORT_ARGS=""
if [[ "$DRY_RUN" == true ]]; then EXPORT_ARGS="--dry-run"; fi

"$PYTHON" scripts/export_video_catalog.py $EXPORT_ARGS

if [[ $? -ne 0 ]]; then
    echo "ERROR: Stage 5 failed"
    exit 1
fi

STAGE5_END=$(date +%s)
echo "  Stage 5 time: $(( STAGE5_END - STAGE5_START ))s"
echo ""

# ─── Summary ─────────────────────────────────────────────────────

PIPELINE_END=$(date +%s)
TOTAL_TIME=$(( PIPELINE_END - PIPELINE_START ))

echo "======================================================================"
echo "PIPELINE COMPLETE"
echo "======================================================================"
echo "  Total time: ${TOTAL_TIME}s"
echo "  Stage 3 (embed):   $(( STAGE3_END - STAGE3_START ))s"
echo "  Stage 4 (project): $(( STAGE4_END - STAGE4_START ))s"
echo "  Stage 5 (catalog): $(( STAGE5_END - STAGE5_START ))s"
echo "  Finished: $(date)"
echo "======================================================================"
