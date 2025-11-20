#!/usr/bin/env python3
"""
Estimate GPT-5-nano Regeneration Cost

This script estimates the cost of regenerating heatmap labels and cell questions
using GPT-5-nano via OpenAI API, by measuring token usage with Qwen3-14B as a
stand-in (running locally via LM Studio on port 1234).

The estimate helps decide whether to:
1. Use GPT-5-nano for fast regeneration (~hours via parallel API calls)
2. Rebuild UMAP and regenerate with local Qwen3-14B (~2-3 days)

GPT-5-nano Pricing (OpenAI):
- Input: $0.05 per 1M tokens ($0.005 per 1M cached)
- Output: $0.40 per 1M tokens

Usage:
    python scripts/estimate_gpt5nano_cost.py [--num-samples N]

Outputs:
    - Token count statistics
    - Cost estimates for full regeneration
    - Comparison with UMAP rebuild timeline
"""

import requests
import json
import pickle
import numpy as np
from pathlib import Path
import argparse
import random


def count_tokens_in_text(text):
    """
    Estimate token count using simple heuristic.
    GPT models use ~1.3 tokens per word on average.
    """
    words = text.split()
    return int(len(words) * 1.3)


def generate_heatmap_label_with_qwen(cell, k_neighbors, track_tokens=True):
    """
    Generate a heatmap cell label using Qwen3-14B via LM Studio.
    Returns label text and token counts (input, output).
    """
    # Build prompt for label generation
    neighbor_texts = "\n".join([
        f"  - {n['title']}: {n['text'][:100]}..."
        for n in k_neighbors[:10]  # Top 10 neighbors
    ])

    prompt = f"""You are labeling a region of a knowledge map. This region contains the following Wikipedia articles:

{neighbor_texts}

Based on these articles, generate a concise semantic label (2-4 words) that describes the common theme or topic of this region.

Return ONLY the label, nothing else."""

    # Count input tokens
    input_tokens = count_tokens_in_text(prompt)

    # Call Qwen3-14B via LM Studio
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "qwen/qwen3-14b",
                "messages": [
                    {"role": "system", "content": "You generate concise semantic labels for knowledge map regions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 50
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            label = result['choices'][0]['message']['content'].strip()

            # Count output tokens
            output_tokens = count_tokens_in_text(label)

            return label, input_tokens, output_tokens
        else:
            return None, input_tokens, 0

    except Exception as e:
        print(f"  Error calling LM Studio: {e}")
        return None, input_tokens, 0


def generate_question_with_qwen(cell, article, concepts, track_tokens=True):
    """
    Generate a conceptual question using Qwen3-14B via LM Studio.
    Uses two-step process: concept extraction already done, just generate question.
    Returns question data and token counts.
    """
    # Build prompt for question generation
    concept_list = "\n".join([f"  - {c}" for c in concepts[:5]])

    prompt = f"""You are generating a conceptual multiple-choice question for a knowledge assessment.

Article: {article['title']}
Text excerpt: {article['excerpt'][:200]}...

Key concepts in this region:
{concept_list}

Generate a conceptual question that tests understanding of relationships, implications, or applications of these concepts. The question should:
- Be thought-provoking and require conceptual understanding
- NOT be a simple factual recall question
- Have 4 plausible answer choices
- Have one clearly correct answer

Return ONLY a JSON object with this structure:
{{
  "question": "The question text",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correctIndex": 0
}}"""

    # Count input tokens
    input_tokens = count_tokens_in_text(prompt)

    # Call Qwen3-14B via LM Studio
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "qwen/qwen3-14b",
                "messages": [
                    {"role": "system", "content": "You generate conceptual multiple-choice questions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 400
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Count output tokens
            output_tokens = count_tokens_in_text(content)

            # Try to parse JSON
            try:
                question_data = json.loads(content)
                return question_data, input_tokens, output_tokens
            except:
                return None, input_tokens, output_tokens
        else:
            return None, input_tokens, 0

    except Exception as e:
        print(f"  Error calling LM Studio: {e}")
        return None, input_tokens, 0


def load_sample_data(num_samples=10):
    """Load sample cells and articles for cost estimation."""
    print("=" * 80)
    print("Loading Sample Data")
    print("=" * 80)
    print()

    # Load heatmap cell labels (for cell structure)
    print("Loading heatmap cell labels...")
    with open('heatmap_cell_labels.json', 'r') as f:
        labels_data = json.load(f)

    all_cells = labels_data['cells']
    print(f"  Total cells: {len(all_cells)}")
    print()

    # Load Wikipedia articles
    print("Loading Wikipedia articles...")
    with open('wikipedia_articles.json', 'r') as f:
        articles = json.load(f)

    print(f"  Total articles: {len(articles)}")
    print()

    # Sample random cells
    print(f"Sampling {num_samples} random cells...")
    sample_cells = random.sample(all_cells, min(num_samples, len(all_cells)))
    print(f"  Sampled {len(sample_cells)} cells")
    print()

    return sample_cells, articles


def estimate_label_generation_cost(sample_cells, articles, num_samples=10):
    """Estimate cost for regenerating all heatmap labels."""
    print("=" * 80)
    print(f"Estimating Label Generation Cost ({num_samples} samples)")
    print("=" * 80)
    print()

    total_input_tokens = 0
    total_output_tokens = 0
    successful_generations = 0

    for i, cell in enumerate(sample_cells[:num_samples]):
        print(f"Cell {i+1}/{num_samples}: ({cell['gx']}, {cell['gy']}) - \"{cell['label']}\"")

        # Get k nearest articles for this cell
        # Simplified: just get articles near this cell's center
        cell_x = cell['center_x']
        cell_y = cell['center_y']

        # Find nearest articles
        distances = []
        for article in articles:
            dist = np.sqrt((article['x'] - cell_x)**2 + (article['y'] - cell_y)**2)
            distances.append((dist, article))

        distances.sort(key=lambda x: x[0])
        k_neighbors = [
            {'title': a['title'], 'text': a['excerpt']}
            for _, a in distances[:10]
        ]

        # Generate label and track tokens
        label, input_tokens, output_tokens = generate_heatmap_label_with_qwen(
            cell, k_neighbors, track_tokens=True
        )

        if label:
            print(f"  Generated: \"{label}\"")
            print(f"  Tokens: {input_tokens} input, {output_tokens} output")
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            successful_generations += 1
        else:
            print(f"  Failed to generate label")

        print()

    # Calculate averages
    if successful_generations > 0:
        avg_input = total_input_tokens / successful_generations
        avg_output = total_output_tokens / successful_generations
    else:
        avg_input = 0
        avg_output = 0

    print(f"Label Generation Summary:")
    print(f"  Successful: {successful_generations}/{num_samples}")
    print(f"  Average input tokens: {avg_input:.1f}")
    print(f"  Average output tokens: {avg_output:.1f}")
    print()

    return avg_input, avg_output


def estimate_question_generation_cost(sample_cells, articles, num_samples=10):
    """Estimate cost for regenerating all cell questions."""
    print("=" * 80)
    print(f"Estimating Question Generation Cost ({num_samples} samples)")
    print("=" * 80)
    print()

    total_input_tokens = 0
    total_output_tokens = 0
    successful_generations = 0

    for i, cell in enumerate(sample_cells[:num_samples]):
        print(f"Cell {i+1}/{num_samples}: ({cell['gx']}, {cell['gy']}) - \"{cell['label']}\"")

        # Get nearest article for this cell
        cell_x = cell['center_x']
        cell_y = cell['center_y']

        distances = []
        for article in articles:
            dist = np.sqrt((article['x'] - cell_x)**2 + (article['y'] - cell_y)**2)
            distances.append((dist, article))

        distances.sort(key=lambda x: x[0])

        if len(distances) > 0:
            nearest_article = distances[0][1]

            # Mock concepts (normally extracted from neighbors)
            concepts = [cell['label'], "related concept", "another concept"]

            # Generate question and track tokens
            question, input_tokens, output_tokens = generate_question_with_qwen(
                cell, nearest_article, concepts, track_tokens=True
            )

            if question:
                print(f"  Generated: \"{question.get('question', 'N/A')[:60]}...\"")
                print(f"  Tokens: {input_tokens} input, {output_tokens} output")
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                successful_generations += 1
            else:
                print(f"  Failed to generate question")
        else:
            print(f"  No articles found near cell")

        print()

    # Calculate averages
    if successful_generations > 0:
        avg_input = total_input_tokens / successful_generations
        avg_output = total_output_tokens / successful_generations
    else:
        avg_input = 0
        avg_output = 0

    print(f"Question Generation Summary:")
    print(f"  Successful: {successful_generations}/{num_samples}")
    print(f"  Average input tokens: {avg_input:.1f}")
    print(f"  Average output tokens: {avg_output:.1f}")
    print()

    return avg_input, avg_output


def calculate_full_cost(avg_label_input, avg_label_output, avg_q_input, avg_q_output):
    """Calculate total cost for full regeneration."""
    print("=" * 80)
    print("Full Regeneration Cost Estimate")
    print("=" * 80)
    print()

    # Grid size: 39x39 = 1,521 cells (from heatmap_cell_labels.json)
    total_cells = 1521

    # Assume 4 questions per cell on average
    avg_questions_per_cell = 4
    total_questions = total_cells * avg_questions_per_cell

    print(f"Scale:")
    print(f"  Total cells: {total_cells:,}")
    print(f"  Total questions: {total_questions:,} ({avg_questions_per_cell} per cell)")
    print()

    # Label generation tokens
    total_label_input = avg_label_input * total_cells
    total_label_output = avg_label_output * total_cells

    print(f"Heatmap Label Generation:")
    print(f"  Input tokens: {total_label_input:,.0f} ({total_label_input/1_000_000:.3f}M)")
    print(f"  Output tokens: {total_label_output:,.0f} ({total_label_output/1_000_000:.3f}M)")
    print()

    # Question generation tokens
    total_q_input = avg_q_input * total_questions
    total_q_output = avg_q_output * total_questions

    print(f"Question Generation:")
    print(f"  Input tokens: {total_q_input:,.0f} ({total_q_input/1_000_000:.3f}M)")
    print(f"  Output tokens: {total_q_output:,.0f} ({total_q_output/1_000_000:.3f}M)")
    print()

    # Total tokens
    total_input = total_label_input + total_q_input
    total_output = total_label_output + total_q_output

    print(f"Combined Totals:")
    print(f"  Input tokens: {total_input:,.0f} ({total_input/1_000_000:.3f}M)")
    print(f"  Output tokens: {total_output:,.0f} ({total_output/1_000_000:.3f}M)")
    print()

    # GPT-5-nano pricing
    input_cost_per_1m = 0.05  # $0.05 per 1M input tokens
    cached_input_cost_per_1m = 0.005  # $0.005 per 1M cached input
    output_cost_per_1m = 0.40  # $0.40 per 1M output tokens

    # Cost without caching
    cost_input = (total_input / 1_000_000) * input_cost_per_1m
    cost_output = (total_output / 1_000_000) * output_cost_per_1m
    total_cost = cost_input + cost_output

    print("=" * 80)
    print("GPT-5-nano Cost Estimate (OpenAI API)")
    print("=" * 80)
    print()
    print(f"Without Caching:")
    print(f"  Input cost: ${cost_input:.2f} ({total_input/1_000_000:.3f}M tokens @ $0.05/1M)")
    print(f"  Output cost: ${cost_output:.2f} ({total_output/1_000_000:.3f}M tokens @ $0.40/1M)")
    print(f"  Total cost: ${total_cost:.2f}")
    print()

    # Cost with 90% caching (optimistic estimate for parallel batches)
    cached_ratio = 0.9
    cost_input_cached = ((total_input * (1 - cached_ratio)) / 1_000_000 * input_cost_per_1m +
                        (total_input * cached_ratio) / 1_000_000 * cached_input_cost_per_1m)
    total_cost_cached = cost_input_cached + cost_output

    print(f"With 90% Prompt Caching (optimistic):")
    print(f"  Input cost: ${cost_input_cached:.2f}")
    print(f"  Output cost: ${cost_output:.2f}")
    print(f"  Total cost: ${total_cost_cached:.2f}")
    print()

    # Timeline comparison
    print("=" * 80)
    print("Timeline Comparison")
    print("=" * 80)
    print()
    print(f"Option 1: UMAP Rebuild + Local Regeneration")
    print(f"  Timeline: 2-3 days")
    print(f"  Cost: $0 (local compute only)")
    print()
    print(f"Option 2: GPT-5-nano Regeneration")
    print(f"  Timeline: ~4-8 hours (parallel API batches)")
    print(f"  Cost: ${total_cost_cached:.2f} (with caching)")
    print()

    # Recommendation
    if total_cost_cached < 10:
        print("RECOMMENDATION: GPT-5-nano regeneration is cost-effective")
        print(f"  - Low cost (${total_cost_cached:.2f})")
        print(f"  - Fast turnaround (hours vs days)")
    elif total_cost_cached < 50:
        print("RECOMMENDATION: GPT-5-nano is viable but consider budget")
        print(f"  - Moderate cost (${total_cost_cached:.2f})")
        print(f"  - Significant time savings")
    else:
        print("RECOMMENDATION: UMAP rebuild may be more cost-effective")
        print(f"  - High cost (${total_cost_cached:.2f})")
        print(f"  - Local regeneration is free")

    print()


def main():
    parser = argparse.ArgumentParser(description="Estimate GPT-5-nano regeneration cost")
    parser.add_argument('--num-samples', type=int, default=10,
                       help='Number of sample cells to test (default: 10)')
    args = parser.parse_args()

    print()
    print("=" * 80)
    print("GPT-5-NANO COST ESTIMATION")
    print("=" * 80)
    print()
    print("This script estimates the cost of regenerating heatmap labels and")
    print("questions using GPT-5-nano via OpenAI API.")
    print()
    print("Method: Use Qwen3-14B (local LM Studio) to measure token counts")
    print(f"Samples: {args.num_samples} random cells")
    print()

    # Check LM Studio connectivity
    print("Checking LM Studio connectivity...")
    try:
        response = requests.get('http://localhost:1234/v1/models', timeout=5)
        if response.status_code == 200:
            print("  ✓ LM Studio is running on port 1234")
        else:
            print("  ✗ LM Studio responded with error")
            print("  Please start LM Studio and load Qwen3-14B")
            return
    except:
        print("  ✗ Cannot connect to LM Studio on port 1234")
        print("  Please start LM Studio and load Qwen3-14B")
        return

    print()

    # Load sample data
    sample_cells, articles = load_sample_data(num_samples=args.num_samples)

    # Estimate label generation cost
    avg_label_input, avg_label_output = estimate_label_generation_cost(
        sample_cells, articles, num_samples=args.num_samples
    )

    # Estimate question generation cost
    avg_q_input, avg_q_output = estimate_question_generation_cost(
        sample_cells, articles, num_samples=args.num_samples
    )

    # Calculate full cost
    calculate_full_cost(
        avg_label_input, avg_label_output,
        avg_q_input, avg_q_output
    )


if __name__ == '__main__':
    main()
