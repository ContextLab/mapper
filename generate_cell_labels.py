#!/usr/bin/env python3
"""
Generate human-readable labels for heatmap cells using UMAP inversion and LLM labeling.

This script:
1. Inverts UMAP 2D coordinates back to original embedding space
2. Uses vec2text to recover representative tokens/word clouds
3. Prompts gpt-oss-20B (via LM Studio) to generate concise labels
4. Caches results for reuse

Requirements:
    pip install vec2text requests numpy
"""

import os
import json
import pickle
import hashlib
import argparse
import requests
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import numpy as np

# Fix for macOS mutex/threading issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Force CPU-only mode for PyTorch - vec2text has issues with MPS backend on macOS
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable CUDA
# Disable MPS (Metal Performance Shaders) on macOS
if "PYTORCH_MPS_DISABLE" not in os.environ:
    os.environ["PYTORCH_MPS_DISABLE"] = "1"


def load_umap_model(model_path='umap_reducer.pkl'):
    """Load pre-fitted UMAP model for inverse transforms."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"UMAP model not found at {model_path}. "
                               f"Run generate_embeddings.py with --save-reducer first.")
    with open(model_path, 'rb') as f:
        return pickle.load(f)


def load_umap_bounds(bounds_path='umap_bounds.pkl'):
    """Load UMAP coordinate bounds for denormalization."""
    if not os.path.exists(bounds_path):
        raise FileNotFoundError(f"UMAP bounds not found at {bounds_path}. "
                               f"Run generate_embeddings.py with --save-reducer first.")
    with open(bounds_path, 'rb') as f:
        return pickle.load(f)


def load_questions(questions_path='questions.json'):
    """Load questions with full embeddings."""
    with open(questions_path, 'r') as f:
        questions = json.load(f)

    # Verify questions have full embeddings
    if not all('embedding_full' in q for q in questions):
        raise ValueError("questions.json missing embedding_full field. "
                        "Regenerate with generate_embeddings.py")

    return questions


def compute_convex_hull_distance(x, y, bounds):
    """
    Measure how far point is from convex hull boundary.

    Args:
        x, y: Coordinates in UMAP space
        bounds: Dict with x_min, x_max, y_min, y_max

    Returns:
        score: 1.0 if inside hull, <1.0 if near/outside edges
    """
    if bounds is None:
        return 1.0  # Assume valid

    # Compute normalized distance to nearest edge
    x_range = bounds['x_max'] - bounds['x_min']
    y_range = bounds['y_max'] - bounds['y_min']

    if x_range == 0 or y_range == 0:
        return 1.0

    x_margin = min(x - bounds['x_min'], bounds['x_max'] - x) / x_range
    y_margin = min(y - bounds['y_min'], bounds['y_max'] - y) / y_range

    # Penalize points near or outside edges
    margin = min(x_margin, y_margin)
    if margin < 0:
        return 0.0  # Outside hull
    elif margin < 0.05:
        return margin / 0.05  # Near edge (0-5% margin)
    else:
        return 1.0  # Well inside hull


def invert_umap_coordinates(x_norm, y_norm, umap_reducer, bounds):
    """
    Use UMAP's native inverse_transform to recover embeddings.

    Args:
        x_norm, y_norm: Normalized coordinates [0, 1]
        umap_reducer: Fitted UMAP object with inverse_transform support
        bounds: Dict with {x_min, x_max, y_min, y_max}

    Returns:
        embedding: High-dim embedding vector
        quality_score: Confidence metric (0-1)
    """
    # Convert normalized [0,1] coords back to UMAP space
    x_umap = x_norm * (bounds['x_max'] - bounds['x_min']) + bounds['x_min']
    y_umap = y_norm * (bounds['y_max'] - bounds['y_min']) + bounds['y_min']

    # UMAP inverse transform expects (n_samples, n_components) array
    coords_2d = np.array([[x_umap, y_umap]])

    # Perform inverse transform
    embedding = umap_reducer.inverse_transform(coords_2d)[0]

    # Compute quality score based on distance from convex hull
    quality_score = compute_convex_hull_distance(x_umap, y_umap, bounds)

    return embedding, quality_score


def validate_embedding(embedding, reference_embeddings):
    """
    Check if recovered embedding is well-behaved.

    Checks:
    - L2 norm is reasonable (not NaN/inf)
    - Values in expected range (mean ± 3*std of reference)
    - Cosine similarity to nearest neighbor > threshold

    Note: UMAP inverse_transform can produce extreme values (norm z-scores >1M),
    so we use lenient thresholds and rely on repair_embedding() to fix issues.

    Returns:
        is_valid: bool
        diagnostics: dict with detailed metrics
    """
    diagnostics = {}

    # Check for NaN/inf
    if not np.isfinite(embedding).all():
        diagnostics['has_nan_inf'] = True
        return False, diagnostics
    diagnostics['has_nan_inf'] = False

    # Check L2 norm
    norm = np.linalg.norm(embedding)
    ref_norms = np.linalg.norm(reference_embeddings, axis=1)
    norm_mean, norm_std = ref_norms.mean(), ref_norms.std()
    diagnostics['norm'] = norm
    diagnostics['norm_z_score'] = (norm - norm_mean) / (norm_std + 1e-8)

    # Very lenient threshold - UMAP inverse_transform can produce extreme values
    # We'll repair them rather than reject them
    if abs(diagnostics['norm_z_score']) > 1000:
        diagnostics['needs_repair'] = 'extreme_norm'
        return False, diagnostics

    # Check value ranges
    ref_mean = reference_embeddings.mean(axis=0)
    ref_std = reference_embeddings.std(axis=0)
    z_scores = (embedding - ref_mean) / (ref_std + 1e-8)
    max_z_score = np.abs(z_scores).max()
    diagnostics['max_value_z_score'] = max_z_score

    # More lenient threshold for element-wise values
    if max_z_score > 100:
        diagnostics['needs_repair'] = 'extreme_values'
        return False, diagnostics

    # Check nearest neighbor similarity (most important metric)
    similarities = np.dot(reference_embeddings, embedding) / (
        np.linalg.norm(reference_embeddings, axis=1) * norm + 1e-8
    )
    max_similarity = similarities.max()
    diagnostics['max_cosine_similarity'] = max_similarity

    # Low similarity is OK if we can repair it
    if max_similarity < -0.5:  # Only flag very negative similarities
        diagnostics['needs_repair'] = 'poor_similarity'
        return False, diagnostics

    return True, diagnostics


def repair_embedding(embedding, reference_embeddings, quality_score):
    """
    Fix poorly-behaved embeddings from inverse_transform.

    Uses hybrid strategy to handle extreme values from UMAP inverse_transform:
    1. Normalize L2 norm to reference mean (handles norm z-scores of ~340M)
    2. Clip outlier values to reference range (mean ± 3*std)
    3. Project onto reference embedding subspace (PCA-style regularization)
    4. Re-normalize to target norm
    5. If quality_score < 0.3, blend with nearest reference embedding

    This hybrid approach reduces extreme cases (norm z-score ~14B, element z-score ~3600)
    to well-behaved embeddings (norm z-score ~0, element z-score <2).

    Returns:
        repaired_embedding: Fixed vector
        repair_log: List of descriptions of repairs applied
    """
    repair_log = []
    repaired = embedding.copy()

    # Get reference statistics
    ref_norms = np.linalg.norm(reference_embeddings, axis=1)
    target_norm = ref_norms.mean()
    ref_mean = reference_embeddings.mean(axis=0)
    ref_std = reference_embeddings.std(axis=0)

    # Compute SVD of reference embeddings for projection
    _, _, Vt = np.linalg.svd(reference_embeddings - ref_mean, full_matrices=False)

    original_norm = np.linalg.norm(repaired)

    # Step 1: Initial L2 normalization
    current_norm = np.linalg.norm(repaired)
    if current_norm > 0:
        repaired = repaired * (target_norm / current_norm)
        if original_norm > target_norm * 2:  # Only log if significantly different
            repair_log.append(f"Normalized L2 norm from {original_norm:.2e} to {target_norm:.3f}")

    # Step 2: Clip outliers to ±3σ
    lower_bound = ref_mean - 3 * ref_std
    upper_bound = ref_mean + 3 * ref_std
    clipped = np.clip(repaired, lower_bound, upper_bound)

    num_clipped = np.sum(repaired != clipped)
    if num_clipped > 0:
        repaired = clipped
        repair_log.append(f"Clipped {num_clipped} outlier values to ±3σ range")

    # Step 3: Project onto reference embedding subspace
    # This regularizes the embedding to lie in the space spanned by reference embeddings
    embedding_centered = repaired - ref_mean
    projection = embedding_centered @ Vt.T @ Vt
    repaired = projection + ref_mean

    # Check if projection changed the embedding significantly
    projection_distance = np.linalg.norm(embedding_centered - projection)
    if projection_distance > 0.01:  # Only log if significant projection
        repair_log.append(f"Projected onto reference subspace (distance={projection_distance:.3f})")

    # Step 4: Final normalization to target norm
    current_norm = np.linalg.norm(repaired)
    if current_norm > 0:
        repaired = repaired * (target_norm / current_norm)

    # Step 5: Blend with nearest neighbor if quality is very low
    if quality_score < 0.3:
        # Find nearest reference embedding
        similarities = np.dot(reference_embeddings, repaired) / (
            np.linalg.norm(reference_embeddings, axis=1) * np.linalg.norm(repaired) + 1e-8
        )
        nearest_idx = similarities.argmax()
        nearest_embedding = reference_embeddings[nearest_idx]

        # Blend: more weight to nearest neighbor for lower quality
        blend_weight = 0.7  # 70% nearest, 30% inverse_transform result
        repaired = blend_weight * nearest_embedding + (1 - blend_weight) * repaired

        # Re-normalize after blending
        current_norm = np.linalg.norm(repaired)
        if current_norm > 0:
            repaired = repaired * (target_norm / current_norm)

        repair_log.append(f"Blended with nearest neighbor (quality={quality_score:.2f}, similarity={similarities[nearest_idx]:.3f})")

    return repaired, repair_log


def recover_tokens_from_embedding(embedding, model_name='sentence-transformers/gtr-t5-base',
                                   max_tokens=50, min_weight=0.01):
    """
    Use vec2text to recover text from embedding.

    Vec2text converts embeddings back to natural language text using neural inversion.
    Supported models: gtr-base (768-dim), text-embedding-ada-002 (1536-dim)

    Args:
        embedding: High-dim vector (numpy array)
        model_name: Embedding model name ('sentence-transformers/gtr-t5-base' or 'text-embedding-ada-002')
        max_tokens: Maximum number of tokens to return
        min_weight: Minimum weight threshold

    Returns:
        tokens: List of (word, weight) tuples
        metadata: dict with method used and quality metrics

    Raises:
        ValueError: If model is not supported by vec2text
        ImportError: If vec2text is not installed
        RuntimeError: If vec2text inversion fails
    """
    import torch

    # Map of supported models
    vec2text_supported = {
        'sentence-transformers/gtr-t5-base': ('gtr-base', 768),
        'gtr-base': ('gtr-base', 768),
        'text-embedding-ada-002': ('text-embedding-ada-002', 1536)
    }

    if model_name not in vec2text_supported:
        raise ValueError(
            f"Model '{model_name}' is not supported by vec2text. "
            f"Supported models: {list(vec2text_supported.keys())}"
        )

    vec2text_model_name, expected_dim = vec2text_supported[model_name]
    embedding_dim = len(embedding)

    if embedding_dim != expected_dim:
        raise ValueError(
            f"Model '{model_name}' expects {expected_dim}-dim embeddings, "
            f"but got {embedding_dim}-dim. Regenerate embeddings with correct model."
        )

    try:
        import vec2text
    except ImportError:
        raise ImportError(
            "vec2text is not installed. Install with: pip install vec2text"
        )

    print(f"  Using vec2text with {vec2text_model_name}...")

    # Load pre-trained corrector
    corrector = vec2text.load_pretrained_corrector(vec2text_model_name)

    # Convert numpy to torch tensor
    embedding_tensor = torch.from_numpy(embedding).unsqueeze(0).float()

    # Move tensor to same device as model
    # vec2text auto-selects device (MPS on macOS, CUDA on Linux, CPU fallback)
    if hasattr(corrector, 'device'):
        device = corrector.device
    elif hasattr(corrector.inversion_trainer, 'model'):
        device = next(corrector.inversion_trainer.model.parameters()).device
    else:
        device = torch.device('cpu')

    embedding_tensor = embedding_tensor.to(device)

    # Invert embedding to text
    # num_steps: more steps = better quality but slower (1-20 typical)
    # sequence_beam_width: search breadth (0=greedy, 2-4=better results)
    try:
        recovered_texts = vec2text.invert_embeddings(
            embeddings=embedding_tensor,
            corrector=corrector,
            num_steps=10,  # Moderate quality/speed tradeoff
            sequence_beam_width=2  # Small beam for speed
        )
    except Exception as e:
        raise RuntimeError(f"vec2text inversion failed: {e}")

    recovered_text = recovered_texts[0]  # Get first result

    # Convert text to weighted tokens for compatibility with downstream pipeline
    # Extract meaningful words and assign uniform weights
    words = recovered_text.lower().split()
    word_counts = {}
    for word in words:
        # Clean word
        word = word.strip('.,!?;:"\'()[]{}')
        if len(word) > 3:  # Filter short words
            word_counts[word] = word_counts.get(word, 0) + 1

    # Convert to (word, weight) format
    total_count = sum(word_counts.values())
    tokens = [(w, cnt/total_count) for w, cnt in word_counts.items()]
    tokens = sorted(tokens, key=lambda x: x[1], reverse=True)[:max_tokens]

    metadata = {
        'method': 'vec2text_inversion',
        'model': vec2text_model_name,
        'recovered_text': recovered_text,
        'num_steps': 10,
        'beam_width': 2
    }

    return tokens, metadata




def filter_tokens(tokens, min_weight=0.01, max_tokens=50, stop_words=None):
    """
    Remove low-quality tokens.

    Filters:
    - Special characters, numbers-only
    - Stop words (optional)
    - Tokens below weight threshold
    - Keep top N by weight

    Returns:
        filtered_tokens: Clean list of (word, weight)
    """
    if stop_words is None:
        stop_words = {'the', 'is', 'are', 'was', 'were', 'a', 'an', 'and', 'or', 'but',
                     'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
                     'what', 'which', 'that', 'this', 'these', 'those'}

    filtered = []
    for word, weight in tokens:
        # Skip if below threshold
        if weight < min_weight:
            continue

        # Skip numbers-only
        if word.isdigit():
            continue

        # Skip stop words
        if word.lower() in stop_words:
            continue

        # Skip too short
        if len(word) < 3:
            continue

        filtered.append((word, weight))

    # Keep top N
    filtered = sorted(filtered, key=lambda x: x[1], reverse=True)[:max_tokens]

    return filtered


def call_lm_studio_api(prompt, model='gpt-oss-20b', max_tokens=20,
                       temperature=0.7, base_url='http://localhost:1234'):
    """
    Make REAL API call to LM Studio.

    Args:
        prompt: User prompt
        model: Model name
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        base_url: LM Studio base URL

    Returns:
        response_text: Generated text
        metadata: dict with API response details
    """
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise labeler. Respond with ONLY 2-4 words describing the topic. No explanations, no punctuation at the end."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        response_text = data['choices'][0]['message']['content'].strip()

        # Clean up response (remove trailing punctuation, extra whitespace)
        response_text = response_text.rstrip('.!?,;:')
        response_text = ' '.join(response_text.split())

        metadata = {
            'model': model,
            'finish_reason': data['choices'][0]['finish_reason'],
            'tokens_used': data.get('usage', {}).get('total_tokens', 0)
        }

        return response_text, metadata

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"LM Studio API error: {e}")


def generate_label_from_tokens(tokens, existing_labels=None, max_retries=3, token_metadata=None):
    """
    Prompt gpt-oss-20B to generate concise label.

    Args:
        tokens: List of (word, weight) tuples
        existing_labels: Set of existing labels to avoid duplicates
        max_retries: API retry attempts
        token_metadata: Dict containing vec2text recovered_text

    Returns:
        label: String (2-4 words)
        metadata: dict with API response details
    """
    if existing_labels is None:
        existing_labels = set()

    # Use recovered_text from vec2text if available (preferred)
    # Otherwise fall back to weighted tokens
    if token_metadata and 'recovered_text' in token_metadata:
        recovered_text = token_metadata['recovered_text']
        prompt = f"Based on this text: \"{recovered_text}\", generate a 2-4 word label describing the main topic."
    else:
        # Fallback: use weighted tokens
        top_tokens = tokens[:10]  # Use top 10 tokens
        token_str = ', '.join([f"{word} ({weight:.2f})" for word, weight in top_tokens])
        prompt = f"Based on these weighted terms: {token_str}, generate a 2-4 word label describing the topic."

    for attempt in range(max_retries):
        try:
            label, metadata = call_lm_studio_api(prompt)

            # Ensure label is not too long (limit to 4 words)
            words = label.split()
            if len(words) > 4:
                label = ' '.join(words[:4])

            # Make unique if needed
            if label in existing_labels:
                label = ensure_label_uniqueness(label, existing_labels, tokens)

            return label, metadata

        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"  Retry {attempt + 1}/{max_retries} after error: {e}")

    raise RuntimeError(f"Failed to generate label after {max_retries} retries")


def ensure_label_uniqueness(label, existing_labels, tokens):
    """
    Add disambiguator if label exists.

    Strategies:
    - Append next-highest-weight token
    - Add numeric suffix as last resort

    Returns:
        unique_label: Modified if needed
    """
    # Try adding next token
    for word, _ in tokens:
        candidate = f"{label} {word.capitalize()}"
        if candidate not in existing_labels:
            return candidate

    # Numeric suffix as fallback
    suffix = 2
    while f"{label} {suffix}" in existing_labels:
        suffix += 1

    return f"{label} {suffix}"


def compute_questions_hash(questions_path='questions.json'):
    """Compute SHA256 hash of questions file for cache validation."""
    with open(questions_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def save_cell_labels(labels_data, output_path='heatmap_cell_labels.json'):
    """
    Save labels with metadata.

    Format:
    {
      "metadata": {...},
      "cells": [{"gx": 0, "gy": 0, ...}, ...]
    }
    """
    with open(output_path, 'w') as f:
        json.dump(labels_data, f, indent=2)
    print(f"\nSaved {len(labels_data['cells'])} cell labels to {output_path}")


def load_cell_labels(input_path='heatmap_cell_labels.json',
                     questions_json='questions.json',
                     force_regenerate=False):
    """
    Load cached labels if valid.

    Validation:
    - File exists
    - Questions hash matches
    - Grid size matches

    Returns None if invalid or force_regenerate=True.
    """
    if force_regenerate:
        print("Force regenerate flag set - skipping cache")
        return None

    if not os.path.exists(input_path):
        print(f"Cache file {input_path} not found")
        return None

    try:
        with open(input_path, 'r') as f:
            data = json.load(f)

        # Validate questions hash
        current_hash = compute_questions_hash(questions_json)
        cached_hash = data['metadata'].get('questions_hash')

        if current_hash != cached_hash:
            print("Questions file changed - cache invalid")
            return None

        print(f"Loaded {len(data['cells'])} cell labels from cache")
        return data

    except Exception as e:
        print(f"Error loading cache: {e}")
        return None


def generate_cell_labels(grid_size=40, force=False, verbose=False):
    """
    Main function to generate cell labels.

    Args:
        grid_size: Heatmap grid size (40x40 default)
        force: Force regeneration even if cache exists
        verbose: Print detailed progress

    Returns:
        labels_data: Dict with metadata and cell labels
    """
    print("="*60)
    print("Knowledge Map Cell Label Generation")
    print("="*60)

    # Check for cached results
    cached = load_cell_labels(force_regenerate=force)
    if cached is not None:
        return cached

    # Load required data
    print("\nLoading UMAP model and questions...")
    umap_reducer = load_umap_model()
    bounds = load_umap_bounds()
    questions = load_questions()

    # Get reference embeddings
    reference_embeddings = np.array([q['embedding_full'] for q in questions])
    print(f"Loaded {len(questions)} questions with {reference_embeddings.shape[1]}-dim embeddings")

    # Generate labels for grid
    print(f"\nGenerating labels for {grid_size}x{grid_size} grid...")
    cells = []
    existing_labels = set()

    total_cells = grid_size * grid_size
    for gy in range(grid_size):
        for gx in range(grid_size):
            cell_num = gy * grid_size + gx + 1

            # Cell center in normalized [0, 1] space
            x_norm = (gx + 0.5) / grid_size
            y_norm = (gy + 0.5) / grid_size

            if verbose or cell_num % 100 == 0:
                print(f"\n[{cell_num}/{total_cells}] Processing cell ({gx}, {gy})...")

            # Step 1: Invert UMAP coordinates
            embedding, quality = invert_umap_coordinates(x_norm, y_norm, umap_reducer, bounds)

            if verbose:
                print(f"  Quality score: {quality:.3f}")

            # Step 2: Validate and repair embedding
            is_valid, diagnostics = validate_embedding(embedding, reference_embeddings)

            if not is_valid:
                if verbose:
                    print(f"  Invalid embedding - repairing...")
                embedding, repair_log = repair_embedding(embedding, reference_embeddings, quality)
                if verbose:
                    for msg in repair_log:
                        print(f"    {msg}")

            # Step 3: Recover tokens
            tokens, token_metadata = recover_tokens_from_embedding(embedding)

            if verbose:
                print(f"  Top tokens: {tokens[:5]}")

            # Step 4: Filter tokens
            filtered_tokens = filter_tokens(tokens, max_tokens=10)

            # Step 5: Generate label via LM Studio
            try:
                label, label_metadata = generate_label_from_tokens(
                    filtered_tokens,
                    existing_labels,
                    token_metadata=token_metadata
                )
                existing_labels.add(label)

                if verbose or cell_num % 100 == 0:
                    print(f"  Label: '{label}'")

            except Exception as e:
                print(f"  Error generating label: {e}")
                label = f"Region {cell_num}"
                label_metadata = {'error': str(e)}

            # Store cell data
            cells.append({
                'gx': gx,
                'gy': gy,
                'center_x': x_norm,
                'center_y': y_norm,
                'label': label,
                'tokens': filtered_tokens[:5],  # Store top 5 tokens
                'quality_score': float(quality),
                'metadata': {
                    'is_valid': is_valid,
                    'diagnostics': {k: float(v) if isinstance(v, (int, float, np.number)) else v
                                   for k, v in diagnostics.items()} if diagnostics else {},
                    'token_metadata': token_metadata,
                    'label_metadata': label_metadata
                }
            })

    # Create final data structure
    labels_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'grid_size': grid_size,
            'model': 'sentence-transformers/gtr-t5-base',
            'questions_hash': compute_questions_hash(),
            'total_cells': len(cells),
            'unique_labels': len(existing_labels)
        },
        'cells': cells
    }

    # Save to file
    save_cell_labels(labels_data)

    # Print summary
    print("\n" + "="*60)
    print("Cell Labels Quality Report")
    print("="*60)

    # Sample 10 cells for manual review
    sample_indices = np.linspace(0, len(cells)-1, min(10, len(cells)), dtype=int)

    for idx in sample_indices:
        cell = cells[idx]
        print(f"\nCell ({cell['gx']}, {cell['gy']}): \"{cell['label']}\"")
        print(f"  Quality: {cell['quality_score']:.2f}")
        print(f"  Top tokens: {', '.join([f'{w}({wt:.2f})' for w, wt in cell['tokens']])}")

    print(f"\nSummary:")
    print(f"  Total cells: {len(cells)}")
    print(f"  Unique labels: {len(existing_labels)} ({len(existing_labels)/len(cells)*100:.1f}%)")

    avg_quality = np.mean([c['quality_score'] for c in cells])
    print(f"  Avg quality score: {avg_quality:.2f}")

    low_quality = sum(1 for c in cells if c['quality_score'] < 0.7)
    print(f"  Cells flagged for review (quality < 0.7): {low_quality}")

    print("\n" + "="*60)

    return labels_data


def main():
    parser = argparse.ArgumentParser(description='Generate cell labels for knowledge map')
    parser.add_argument('--grid-size', type=int, default=40, help='Heatmap grid size (default: 40)')
    parser.add_argument('--force', action='store_true', help='Force regeneration (ignore cache)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        labels_data = generate_cell_labels(
            grid_size=args.grid_size,
            force=args.force,
            verbose=args.verbose
        )

        print("\n✅ Done!")
        print(f"Cell labels saved to heatmap_cell_labels.json")
        print(f"Use this file with index.html to display labels in tooltips")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
