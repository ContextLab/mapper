#!/bin/bash
# Monitor the knowledge map build progress

while true; do
    clear
    echo "================================"
    echo "Knowledge Map Build Monitor"
    echo "Time: $(date)"
    echo "================================"
    echo ""

    # Check if process is running
    if pgrep -f "build_wikipedia_knowledge_map_v2.py" > /dev/null; then
        echo "✓ Build process is RUNNING"
        echo ""

        # Show last 30 lines of log
        echo "--- Last 30 lines of log ---"
        tail -30 build_knowledge_map.log
        echo ""

        # Check for generated files
        echo "--- Generated Files ---"
        ls -lh embeddings*.pkl umap_coords.pkl knowledge_map.pkl 2>/dev/null || echo "No output files yet"
        echo ""

    else
        echo "✗ Build process is NOT RUNNING"
        echo ""

        # Check if it completed or crashed
        if [ -f "knowledge_map.pkl" ]; then
            echo "✓ SUCCESS - knowledge_map.pkl found!"
            ls -lh knowledge_map.pkl embeddings.pkl umap_coords.pkl
            echo ""
            echo "Build completed successfully!"
            break
        else
            echo "⚠️  Process stopped but no knowledge_map.pkl found"
            echo "Check build_knowledge_map.log for errors"
            echo ""
            echo "--- Last 50 lines of log ---"
            tail -50 build_knowledge_map.log
            break
        fi
    fi

    # Wait 5 minutes before next check
    echo "Sleeping for 5 minutes... (Ctrl+C to stop monitoring)"
    sleep 300
done
