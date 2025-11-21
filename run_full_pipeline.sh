#!/bin/bash
#
# Full Pipeline for Knowledge Map Question Simplification
# ========================================================
#
# This script runs the complete pipeline for simplifying questions at all levels
# and merging them into the final knowledge map data files.
#
# Steps:
# 1. Run simplification for levels 4, 3, 2 (levels 1 and 0 don't need simplification)
# 2. Merge all level data into final output files
#
# Usage:
#   ./run_full_pipeline.sh              # Run full pipeline
#   ./run_full_pipeline.sh --pilot 20   # Run with pilot mode (20 questions per level)
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
PILOT_FLAG=""
if [ "$1" = "--pilot" ]; then
    PILOT_FLAG="--pilot $2"
    echo -e "${YELLOW}Running in PILOT mode with $2 questions per level${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Knowledge Map Question Simplification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Simplify Level 4 (Middle School)
echo -e "${GREEN}Step 1/5: Simplifying Level 4 (Middle School)${NC}"
python3 scripts/simplify_questions.py --level 4 $PILOT_FLAG
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Level 4 simplification failed${NC}"
    exit 1
fi
echo ""

# Step 2: Simplify Level 3 (High School)
echo -e "${GREEN}Step 2/5: Simplifying Level 3 (High School)${NC}"
python3 scripts/simplify_questions.py --level 3 $PILOT_FLAG
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Level 3 simplification failed${NC}"
    exit 1
fi
echo ""

# Step 3: Simplify Level 2 (Undergraduate)
echo -e "${GREEN}Step 3/5: Simplifying Level 2 (Undergraduate)${NC}"
python3 scripts/simplify_questions.py --level 2 $PILOT_FLAG
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Level 2 simplification failed${NC}"
    exit 1
fi
echo ""

# Note: Levels 1 and 0 don't need simplification - they're already at graduate/expert level

# Step 4: Merge all data
echo -e "${GREEN}Step 4/5: Merging all level data${NC}"
python3 scripts/merge_multi_level_data.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Data merge failed${NC}"
    exit 1
fi
echo ""

# Step 5: Summary
echo -e "${GREEN}Step 5/5: Pipeline Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Pipeline completed successfully!${NC}"
echo ""
echo "Output files:"
echo "  - cell_questions_level_4_simplified.json"
echo "  - cell_questions_level_3_simplified.json"
echo "  - cell_questions_level_2_simplified.json"
echo "  - wikipedia_articles.json (merged articles)"
echo "  - cell_questions.json (merged questions)"
echo ""
echo "Exclusion reports:"
echo "  - notes/excluded_questions_level_4.json"
echo "  - notes/excluded_questions_level_3.json"
echo "  - notes/excluded_questions_level_2.json"
echo "  - notes/merge_validation_report.json"
echo ""
echo -e "${BLUE}========================================${NC}"
