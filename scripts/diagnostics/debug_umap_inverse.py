#!/usr/bin/env python3
"""
Debug UMAP inverse transform to understand why cosine similarities are negative.
"""

import os
import json
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Fix for macOS
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

def load_questions(filepath='questions.json'):
    """Load questions from JSON."""
    with open(filepath) as f:
        return json.load(f)

def load_umap_model(filepath='data/umap_reducer.pkl'):
    """Load UMAP model."""
    with open(filepath, 'rb') as f:
        return pickle.load(f)

def load_umap_bounds(filepath='data/umap_bounds.pkl'):
    """Load UMAP bounds."""
    with open(filepath, 'rb') as f:
        return pickle.load(f)

print("=" * 80)
print("DEBUGGING UMAP INVERSE TRANSFORM")
print("=" * 80)

# Load data
questions = load_questions('questions.json')
reducer = load_umap_model('data/umap_reducer.pkl')
bounds = load_umap_bounds('data/umap_bounds.pkl')

print(f"\nLoaded {len(questions)} questions")
print(f"Embedding dimension: {len(questions[0]['embedding_full'])}")
print(f"\nUMAP bounds: {bounds}")

# Extract embeddings and coordinates
original_embeddings = np.array([q['embedding_full'] for q in questions])
stored_coords = np.array([[q['x'], q['y']] for q in questions])

print(f"\nOriginal embeddings shape: {original_embeddings.shape}")
print(f"Stored coordinates shape: {stored_coords.shape}")

# Check what UMAP was actually fitted on
print("\n" + "=" * 80)
print("CHECKING UMAP FITTING DATA")
print("=" * 80)

if hasattr(reducer, 'embedding_'):
    print(f"\nUMAP embedding_ shape: {reducer.embedding_.shape}")
    print(f"This is what UMAP produced during fit_transform")

    # Check if stored coordinates match UMAP's internal embedding
    if reducer.embedding_.shape[0] == len(questions):
        print("\n✓ UMAP has same number of points as questions")

        # Compare UMAP's internal 2D coords to our stored coords
        # UMAP's embedding_ is NOT normalized, but our stored coords are [0, 1]

        # Denormalize our stored coords back to UMAP space
        x_range = bounds['x_max'] - bounds['x_min']
        y_range = bounds['y_max'] - bounds['y_min']
        denormalized_coords = np.zeros_like(stored_coords)
        denormalized_coords[:, 0] = stored_coords[:, 0] * x_range + bounds['x_min']
        denormalized_coords[:, 1] = stored_coords[:, 1] * y_range + bounds['y_min']

        print(f"\nUMAP internal coords (first 3):")
        print(reducer.embedding_[:3])

        print(f"\nOur stored coords denormalized (first 3):")
        print(denormalized_coords[:3])

        # Check if they match
        coord_diff = np.abs(reducer.embedding_ - denormalized_coords).max()
        print(f"\nMax difference between UMAP coords and our stored coords: {coord_diff:.6f}")

        if coord_diff < 1e-6:
            print("✓ Coordinates match perfectly")
        else:
            print("✗ Coordinates DON'T match - this could be the problem!")

# Test UMAP inverse transform directly
print("\n" + "=" * 80)
print("TESTING UMAP INVERSE TRANSFORM")
print("=" * 80)

print("\nTest 1: Inverse transform of UMAP's own embedding_")
print("-" * 80)

# Use UMAP's internal coordinates (not our normalized ones)
if hasattr(reducer, 'embedding_'):
    recovered_from_internal = reducer.inverse_transform(reducer.embedding_)

    print(f"Recovered embeddings shape: {recovered_from_internal.shape}")

    # Compare to original embeddings
    for i in range(min(3, len(questions))):
        cos_sim = cosine_similarity(
            original_embeddings[i:i+1],
            recovered_from_internal[i:i+1]
        )[0, 0]

        print(f"\nQuestion {i+1}: {questions[i]['question'][:60]}...")
        print(f"  Cosine similarity (internal coords): {cos_sim:.4f}")

        # Also check L2 norm
        orig_norm = np.linalg.norm(original_embeddings[i])
        recovered_norm = np.linalg.norm(recovered_from_internal[i])
        print(f"  Original norm: {orig_norm:.2f}")
        print(f"  Recovered norm: {recovered_norm:.2f}")

print("\n" + "-" * 80)
print("Test 2: Inverse transform of our denormalized coordinates")
print("-" * 80)

# Denormalize our stored coords and try inverse transform
x_range = bounds['x_max'] - bounds['x_min']
y_range = bounds['y_max'] - bounds['y_min']
denormalized_coords = np.zeros_like(stored_coords)
denormalized_coords[:, 0] = stored_coords[:, 0] * x_range + bounds['x_min']
denormalized_coords[:, 1] = stored_coords[:, 1] * y_range + bounds['y_min']

recovered_from_denormalized = reducer.inverse_transform(denormalized_coords)

for i in range(min(3, len(questions))):
    cos_sim = cosine_similarity(
        original_embeddings[i:i+1],
        recovered_from_denormalized[i:i+1]
    )[0, 0]

    print(f"\nQuestion {i+1}")
    print(f"  Cosine similarity (denormalized coords): {cos_sim:.4f}")

print("\n" + "=" * 80)
print("CHECKING IF UMAP WAS FITTED ON CORRECT EMBEDDINGS")
print("=" * 80)

# Check if UMAP has _raw_data attribute (original high-dim data)
if hasattr(reducer, '_raw_data'):
    print(f"\nUMAP _raw_data shape: {reducer._raw_data.shape}")

    # Compare to our original embeddings
    data_match = np.allclose(reducer._raw_data, original_embeddings, atol=1e-6)

    if data_match:
        print("✓ UMAP was fitted on the same embeddings we have")
    else:
        print("✗ UMAP was fitted on DIFFERENT embeddings!")

        # Check if at least the norms match
        our_norms = np.linalg.norm(original_embeddings, axis=1)
        umap_norms = np.linalg.norm(reducer._raw_data, axis=1)

        print(f"\nOur embedding norms (first 3): {our_norms[:3]}")
        print(f"UMAP data norms (first 3): {umap_norms[:3]}")

        # Check first embedding in detail
        print(f"\nFirst few values of our embedding[0]: {original_embeddings[0][:5]}")
        print(f"First few values of UMAP data[0]: {reducer._raw_data[0][:5]}")
else:
    print("\nUMAP doesn't have _raw_data attribute")

# Summary
print("\n" + "=" * 80)
print("DIAGNOSIS SUMMARY")
print("=" * 80)

print("\nPossible issues to investigate:")
print("1. UMAP was fitted on different embeddings than what we have")
print("2. Coordinate normalization/denormalization is incorrect")
print("3. UMAP inverse_transform has numerical instability")
print("4. Embedding repair is inadvertently flipping the embeddings")

print("\nNext steps:")
print("- Regenerate UMAP model using current embeddings")
print("- Verify coordinate normalization matches what UMAP expects")
print("- Test inverse transform without embedding repair")
