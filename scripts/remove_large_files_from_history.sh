#!/bin/bash
# Remove large checkpoint files from git history while keeping them locally

echo "================================================================"
echo "Removing Large Files from Git History"
echo "================================================================"

# Files to remove from history
FILES_TO_REMOVE=(
    "checkpoints/level_0_after_concepts.json"
    "checkpoints/level_0_final.json"
    "checkpoints/level_1_after_download.json"
)

echo ""
echo "Files to remove from git history:"
for file in "${FILES_TO_REMOVE[@]}"; do
    echo "  - $file"
done

echo ""
echo "These files will be kept locally but removed from git history."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create temporary backup
echo ""
echo "Creating backup..."
mkdir -p /tmp/mapper_io_backup
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" /tmp/mapper_io_backup/
        echo "  Backed up: $file"
    fi
done

# Remove files from git history using git-filter-repo
echo ""
echo "Removing files from git history..."

# Build the command
FILTER_CMD="git-filter-repo --force --invert-paths"
for file in "${FILES_TO_REMOVE[@]}"; do
    FILTER_CMD="$FILTER_CMD --path $file"
done

echo "Running: $FILTER_CMD"
eval $FILTER_CMD

if [ $? -ne 0 ]; then
    echo "ERROR: git-filter-repo failed!"
    echo "Restoring files from backup..."
    cp /tmp/mapper_io_backup/* checkpoints/
    exit 1
fi

# Restore local files
echo ""
echo "Restoring local copies of files..."
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "/tmp/mapper_io_backup/$(basename $file)" ]; then
        mkdir -p "$(dirname $file)"
        cp "/tmp/mapper_io_backup/$(basename $file)" "$file"
        echo "  Restored: $file"
    fi
done

echo ""
echo "================================================================"
echo "SUCCESS!"
echo "================================================================"
echo ""
echo "Files have been removed from git history but kept locally."
echo ""
echo "Next steps:"
echo "1. Review the changes: git log --all --oneline"
echo "2. Force push to remote: git push origin --force --all"
echo "3. Force push tags: git push origin --force --tags"
echo ""
echo "WARNING: Force pushing will rewrite history on the remote."
echo "Make sure all collaborators are aware and re-clone the repo."
