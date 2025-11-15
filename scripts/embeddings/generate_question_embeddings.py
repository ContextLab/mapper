#!/usr/bin/env python3
"""
Generate embeddings for quiz questions using google/embeddinggemma-300m model.

This script:
- Loads questions from questions.json
- Uses the same model as Wikipedia articles (google/embeddinggemma-300m)
- Generates embeddings for all question texts
- Saves to embeddings/question_embeddings.pkl with metadata
- Verifies dimensions match Wikipedia embeddings (768)
"""

import pickle
import json
import os
import time
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from datetime import datetime

def generate_question_embeddings(batch_size=32, use_mps=True):
    """
    Generate embeddings for all questions in questions.json.

    Args:
        batch_size: Batch size for embedding generation
        use_mps: Whether to use Metal Performance Shaders (for Mac)
    """

    print("="*80)
    print("QUESTION EMBEDDING GENERATION")
    print("="*80)
    print(f"Started: {datetime.now()}")
    print("")

    # Setup paths
    questions_file = Path("questions.json")
    output_dir = Path("embeddings")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "question_embeddings.pkl"

    # Load questions
    print("[1/5] Loading questions...")
    if not questions_file.exists():
        raise FileNotFoundError(f"Questions file not found: {questions_file}")

    with open(questions_file, 'r') as f:
        questions_data = json.load(f)

    print(f"  ✓ Loaded {len(questions_data)} questions")
    print("")

    # Extract question texts
    print("[2/5] Extracting question texts...")
    question_texts = []
    for i, q in enumerate(questions_data):
        if isinstance(q, dict) and 'question' in q:
            question_texts.append(q['question'])
        else:
            print(f"  ⚠ Warning: Question {i} has unexpected format")
            question_texts.append(str(q))

    print(f"  ✓ Extracted {len(question_texts)} question texts")
    print("")

    # Determine device
    print("[3/5] Setting up device...")
    if use_mps and torch.backends.mps.is_available():
        device = "mps"
        print(f"  ✓ Metal Performance Shaders (MPS) available")
    elif torch.cuda.is_available():
        device = "cuda"
        print(f"  ✓ CUDA available")
    else:
        device = "cpu"
        print(f"  ⚠ Using CPU (no GPU acceleration)")
    print(f"  Device: {device}")
    print("")

    # Authenticate with HuggingFace if credentials exist
    hf_token_file = Path(".credentials/hf.token")
    if hf_token_file.exists():
        print("  Authenticating with HuggingFace...")
        with open(hf_token_file, 'r') as f:
            hf_token = f.read().strip()
        from huggingface_hub import login
        login(token=hf_token)
        print("  ✓ Authenticated")
        print("")

    # Load embedding model (same as Wikipedia articles)
    print(f"[4/5] Loading google/embeddinggemma-300m on {device}...")
    model_start = time.time()
    model = SentenceTransformer('google/embeddinggemma-300m', device=device)
    model_time = time.time() - model_start
    dim = model.get_sentence_embedding_dimension()
    print(f"  ✓ Model loaded in {model_time:.2f}s")
    print(f"  Embedding dimension: {dim}")

    # Verify dimension matches Wikipedia (768)
    if dim != 768:
        print(f"  ⚠ Warning: Expected dimension 768, got {dim}")
    else:
        print(f"  ✓ Dimension matches Wikipedia embeddings (768)")
    print("")

    # Generate embeddings
    print(f"[5/5] Generating embeddings for {len(question_texts)} questions...")
    embed_start = time.time()

    embeddings = model.encode(
        question_texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        device=device
    )

    embed_time = time.time() - embed_start
    rate = len(question_texts) / embed_time if embed_time > 0 else 0

    print(f"  ✓ Generated {len(embeddings)} embeddings ({dim}-dim)")
    print(f"  Time: {embed_time:.2f}s")
    print(f"  Rate: {rate:.2f} questions/sec")
    print("")

    # Prepare output data
    print("[6/6] Saving embeddings...")
    output_data = {
        'embeddings': embeddings,
        'questions': question_texts,
        'dimension': dim,
        'model': 'google/embeddinggemma-300m',
        'num_questions': len(question_texts),
        'timestamp': datetime.now().isoformat(),
        'device': device
    }

    with open(output_file, 'wb') as f:
        pickle.dump(output_data, f)

    file_size_kb = output_file.stat().st_size / 1024
    print(f"  ✓ Saved to {output_file}")
    print(f"  File size: {file_size_kb:.2f} KB")
    print("")

    # Verify embeddings
    print("="*80)
    print("VERIFICATION")
    print("="*80)
    norms = np.linalg.norm(embeddings, axis=1)
    print(f"Embedding statistics:")
    print(f"  Shape: {embeddings.shape}")
    print(f"  Dimension: {embeddings.shape[1]} (expected: 768)")
    print(f"  Number of questions: {embeddings.shape[0]}")
    print(f"  Norms - mean: {norms.mean():.4f}, std: {norms.std():.4f}")
    print(f"  Norms - min: {norms.min():.4f}, max: {norms.max():.4f}")
    print("")

    # Test loading
    print("Testing reload...")
    with open(output_file, 'rb') as f:
        test_data = pickle.load(f)
    print(f"  ✓ Successfully reloaded {test_data['num_questions']} question embeddings")
    print(f"  ✓ Model: {test_data['model']}")
    print(f"  ✓ Dimension: {test_data['dimension']}")
    print("")

    print("="*80)
    print("✓ QUESTION EMBEDDING GENERATION COMPLETE")
    print("="*80)
    print(f"Output: {output_file.absolute()}")
    print(f"Questions embedded: {len(question_texts)}")
    print(f"Embedding dimension: {dim}")
    print(f"Total time: {embed_time:.2f}s")
    print(f"Completed: {datetime.now()}")
    print("")

    return output_data

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate embeddings for quiz questions')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size for embedding generation (default: 32)')
    parser.add_argument('--cpu-only', action='store_true',
                        help='Force CPU-only mode (disable Metal/GPU)')

    args = parser.parse_args()

    generate_question_embeddings(
        batch_size=args.batch_size,
        use_mps=not args.cpu_only
    )
