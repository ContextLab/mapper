#!/usr/bin/env python3
"""
Test GPT-5-nano without structured outputs to see if it works.
"""

import json
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from api_utils import create_openai_client
from openai_batch import batch_with_cache

# Load heatmap cell labels
print("Loading heatmap labels...")
with open('heatmap_cell_labels.json', 'r') as f:
    labels_data = json.load(f)

# Get first 3 cells
test_cells = labels_data['cells'][:3]
print(f"Testing with {len(test_cells)} cells")
print()

# System prompt for label generation
SYSTEM_PROMPT = """You are an expert at generating semantic labels for regions in a knowledge map.

Given:
- A grid cell position (gx, gy) in a 39x39 heatmap
- Titles of nearby Wikipedia articles

Your task:
Generate a short, descriptive label (2-5 words) that captures the main topic or theme of the articles in this region.

Guidelines:
- Use broad, intuitive concepts (e.g., "Biology", "European History", "Computer Science")
- Be specific enough to distinguish from neighboring regions
- Use title case
- Focus on the dominant theme, not every article

Respond ONLY with the label, nothing else."""

# Create batch requests
requests = []
for cell in test_cells:
    # Format nearby articles
    articles_text = "\n".join([
        f"- {neighbor['title']}"
        for neighbor in cell['neighbors'][:10]
    ])

    user_prompt = f"""Grid cell: ({cell['gx']}, {cell['gy']})

Nearby articles:
{articles_text}

Label:"""

    requests.append({
        'custom_id': f"test-cell-{cell['gx']}-{cell['gy']}",
        'user_prompt': user_prompt
    })

print(f"Created {len(requests)} batch requests")
print()

# Run batch WITHOUT structured outputs and with much higher token limit
print("Submitting batch to OpenAI...")
print("Testing with:")
print("  - NO response_format (no structured outputs)")
print("  - max_tokens=1500 (to account for reasoning tokens)")
print()

client = create_openai_client()

try:
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=SYSTEM_PROMPT,
        description="GPT-5-nano simple test (no structured outputs)",
        model="gpt-5-nano",
        temperature=0.7,  # Should be ignored for gpt-5-nano
        max_tokens=1500,  # Much higher to allow for reasoning tokens
        response_format=None,  # NO structured outputs
        poll_interval=60,
        timeout=600  # 10 minute timeout
    )

    print()
    print("=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print()
    print(f"Results: {len(results)}/{len(requests)} successful")
    print()

    # Show all results
    for i, (custom_id, label) in enumerate(results.items(), 1):
        print(f"{i}. {custom_id}: \"{label.strip()}\"")

except Exception as e:
    print()
    print("=" * 80)
    print("ERROR")
    print("=" * 80)
    print(f"{e}")
    sys.exit(1)
