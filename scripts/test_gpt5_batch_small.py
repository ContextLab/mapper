#!/usr/bin/env python3
"""
Quick test script to verify GPT-5-nano batch API parameters are correct.
Tests with just 5 cells to iterate quickly.
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

# Get first 5 cells
test_cells = labels_data['cells'][:5]
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
"""

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

Generate a semantic label for this region."""

    requests.append({
        'custom_id': f"test-cell-{cell['gx']}-{cell['gy']}",
        'user_prompt': user_prompt
    })

print(f"Created {len(requests)} batch requests")
print()

# Response format (structured output)
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "cell_label",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "description": "Short semantic label (2-5 words)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of why this label fits"
                }
            },
            "required": ["label", "reasoning"],
            "additionalProperties": False
        }
    }
}

# Run batch with cache
print("Submitting batch to OpenAI...")
print("This will:")
print("  1. Upload batch file")
print("  2. Submit to Batch API")
print("  3. Poll every 60s until complete")
print("  4. Download and parse results")
print()

client = create_openai_client()

try:
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=SYSTEM_PROMPT,
        description="GPT-5-nano parameter test (5 cells)",
        model="gpt-5-nano",
        temperature=0.7,  # This should NOT be included in requests
        max_tokens=300,
        response_format=response_format,
        poll_interval=60,
        timeout=600  # 10 minute timeout for test
    )

    print()
    print("=" * 80)
    print("SUCCESS! Batch completed")
    print("=" * 80)
    print()
    print(f"Results: {len(results)}/{len(requests)} successful")
    print()

    # Show first result
    if results:
        first_id = list(results.keys())[0]
        first_result = results[first_id]
        print(f"Sample result ({first_id}):")
        print(f"  Label: {first_result['label']}")
        print(f"  Reasoning: {first_result['reasoning']}")

except Exception as e:
    print()
    print("=" * 80)
    print("ERROR")
    print("=" * 80)
    print(f"{e}")
    sys.exit(1)
