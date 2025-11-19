#!/usr/bin/env python3
"""
Generate progressively broader articles and questions for levels 1-4.

This script implements hierarchical expansion of Wikipedia knowledge:
- Level 0: Base articles from original dataset
- Level 1: Broader concepts from level 0
- Level 2: Even broader concepts from level 1
- Level N: Progressively more general/abstract

Process:
1. Load level_{N-1}_concepts.json
2. Ask GPT-5-nano for broader Wikipedia articles (1-3 per concept)
3. Download suggested articles
4. Generate embeddings using sentence-transformers
5. Project to UMAP space
6. Extract concepts from new articles
7. Generate questions from concepts
8. Track parent relationships
9. Save outputs with level metadata

Requirements:
    pip install sentence-transformers scikit-learn numpy wikipediaapi openai
"""

import os
import json
import pickle
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import utility modules
from utils.wikipedia_utils import create_wikipedia_api, download_articles_batch, validate_articles
from utils.api_utils import create_openai_client
from utils.openai_batch import batch_with_cache


# Fix for macOS
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


# ============================================================================
# System Prompts
# ============================================================================

ARTICLE_SUGGESTION_SYSTEM_PROMPT = """You are an expert at identifying broader conceptual connections in Wikipedia.

Given a specific concept and source article, suggest 1-3 Wikipedia article titles that:
- Cover the concept from a more general/abstract perspective
- Connect to broader themes or principles
- Are more comprehensive than the source article

Format your response as pipe-delimited lines (one per suggestion):
TITLE|Reasoning why this is broader

Guidelines:
- Suggest REAL Wikipedia articles (verify titles exist)
- Move up the conceptual hierarchy (specific → general)
- Avoid lateral connections (stay focused on broadening)
- Return 1-3 suggestions per concept (quality over quantity)

Example:
Cellular respiration|Provides broader context for mitochondrial function
Bioenergetics|Covers energy transformations across biological systems
"""

CONCEPT_EXTRACTION_SYSTEM_PROMPT = """You are an expert at analyzing educational content to identify conceptual vs. factual material.

You distinguish between articles that test understanding of principles (suitable) vs. memorization of facts (unsuitable).

Extract 1-3 core concepts/principles from the article that could be tested with "why/how" questions.

Format your response as:
SUITABLE: yes/no
REASONING: Brief explanation
CONCEPTS:
- Concept 1
- Concept 2
- Concept 3

If unsuitable, you may omit the CONCEPTS section.
"""

QUESTION_GENERATION_SYSTEM_PROMPT = """You are an expert educator who creates conceptual questions testing understanding of WHY and HOW, not WHAT or WHEN.

Your questions test principles and mechanisms, never definitions or facts.

Your questions are completely self-contained and never reference source material.

Format your response as:
QUESTION: [question text]
A: [option A]
B: [option B]
C: [option C]
D: [option D]
CORRECT: [A/B/C/D]

Generate questions that:
- Test understanding of WHY or HOW a principle/mechanism works
- Are expert-level but test CONCEPTUAL understanding (not memorization)
- Are completely self-contained (no references to "the article", "the text", etc.)
- Have a clear, unambiguous correct answer
- Include 4 plausible answer options (A, B, C, D)
"""


# ============================================================================
# Data Loading
# ============================================================================

def load_previous_level_concepts(level: int) -> List[Dict[str, Any]]:
    """
    Load concepts from previous level.

    Args:
        level: Current level (1-4)

    Returns:
        List of concept dicts from level_{N-1}_concepts.json

    Raises:
        FileNotFoundError: If previous level file doesn't exist
    """
    prev_level = level - 1
    if prev_level == 0:
        # Level 0 is the base - try multiple possible locations
        possible_paths = [
            'level_0_concepts.json',
            'data/level_0_concepts.json',
            'cell_questions.json'  # May contain concepts
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"Loading level 0 concepts from {path}...")
                with open(path, 'r') as f:
                    data = json.load(f)

                # Handle different formats
                if isinstance(data, list):
                    return data
                elif 'concepts' in data:
                    return data['concepts']
                elif 'cells' in data:
                    # Extract from cell_questions format
                    concepts = []
                    for cell in data['cells']:
                        for question in cell.get('questions', []):
                            for concept in question.get('concepts_tested', []):
                                concepts.append({
                                    'concept': concept,
                                    'source_article': question.get('source_article', ''),
                                    'cell_x': question.get('cell_x', 0),
                                    'cell_y': question.get('cell_y', 0)
                                })
                    return concepts

        raise FileNotFoundError(
            f"Could not find level 0 concepts. Tried: {possible_paths}\n"
            f"Run generate_cell_questions.py first to create level 0."
        )
    else:
        # Level 1+ use standard format
        path = f'level_{prev_level}_concepts.json'
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Previous level file not found: {path}\n"
                f"Run with --level {prev_level} first."
            )

        print(f"Loading level {prev_level} concepts from {path}...")
        with open(path, 'r') as f:
            return json.load(f)


def load_umap_reducer() -> Any:
    """Load pre-fitted UMAP model for projecting new embeddings."""
    reducer_path = 'data/umap_reducer.pkl'
    if not os.path.exists(reducer_path):
        raise FileNotFoundError(
            f"UMAP reducer not found at {reducer_path}\n"
            f"Run generate_embeddings.py or rebuild_umap.py first."
        )

    print(f"Loading UMAP reducer from {reducer_path}...")
    with open(reducer_path, 'rb') as f:
        return pickle.load(f)


def load_embedding_model(model_name: str = 'google/embeddinggemma-300m'):
    """Load sentence-transformers model for embedding generation.

    Default model is google/embeddinggemma-300m (768 dims) to match the
    pre-trained UMAP reducer which was trained on 768-dimensional embeddings.
    """
    from sentence_transformers import SentenceTransformer

    print(f"Loading embedding model: {model_name}...")
    return SentenceTransformer(model_name)


# ============================================================================
# Article Suggestion (GPT-5-nano via Batch API)
# ============================================================================

def suggest_broader_articles_batch(
    concepts: List[Dict[str, Any]],
    client: Any,
    max_suggestions_per_concept: int = 3
) -> Dict[str, List[Dict[str, str]]]:
    """
    Use GPT-5-nano batch API to suggest broader Wikipedia articles.

    Args:
        concepts: List of concept dicts with 'concept' and 'source_article' keys
        client: OpenAI client
        max_suggestions_per_concept: Max suggestions per concept (1-3)

    Returns:
        Dict mapping concept_id to list of suggestion dicts
    """
    print("="*80)
    print("STEP 1: Suggesting Broader Articles")
    print("="*80)
    print()

    # Create batch requests
    requests = []
    for i, concept_data in enumerate(concepts):
        concept = concept_data.get('concept', '')
        source_article = concept_data.get('source_article', '')

        prompt = f"""Concept: "{concept}"
Source article: "{source_article}"

Suggest 1-3 Wikipedia article titles that cover this concept from a MORE GENERAL/ABSTRACT perspective.

The suggested articles should:
1. Be BROADER than the source article
2. Cover the concept at a higher level of abstraction
3. Connect to overarching themes or principles
4. Actually exist on Wikipedia (use real article titles)

Example:
- Concept: "mitochondrial ATP synthesis"
- Source: "Mitochondrion"
- Broader suggestions: ["Cellular respiration", "Bioenergetics", "Metabolism"]

Return 1-3 suggestions."""

        requests.append({
            'custom_id': f'concept-{i}',
            'user_prompt': prompt
        })

    # Submit batch (NO response_format for GPT-5-nano)
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=ARTICLE_SUGGESTION_SYSTEM_PROMPT,
        description=f"Level N article suggestions ({len(concepts)} concepts)",
        response_format=None,  # GPT-5-nano doesn't support structured outputs
        temperature=1.0,  # GPT-5-nano only supports temp=1
        max_tokens=1500,  # Higher limit for reasoning tokens
        timeout=None  # No timeout - wait indefinitely for batch to complete
    )

    # Parse plain text results
    suggestions_by_concept = {}
    for i, concept_data in enumerate(concepts):
        custom_id = f'concept-{i}'
        if custom_id in results:
            # Parse pipe-delimited format
            suggestions = []
            text = results[custom_id]
            for line in text.strip().split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        suggestions.append({
                            'title': parts[0].strip(),
                            'reasoning': parts[1].strip()
                        })
            suggestions_by_concept[custom_id] = suggestions
        else:
            suggestions_by_concept[custom_id] = []

    print()
    print(f"✓ Generated suggestions for {len(suggestions_by_concept)}/{len(concepts)} concepts")
    total_suggestions = sum(len(s) for s in suggestions_by_concept.values())
    print(f"  Total suggestions: {total_suggestions}")
    print()

    return suggestions_by_concept


# ============================================================================
# Article Download
# ============================================================================

def download_suggested_articles(
    suggestions_by_concept: Dict[str, List[Dict[str, str]]],
    concepts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Download Wikipedia articles from suggestions (with deduplication).

    Args:
        suggestions_by_concept: Dict mapping concept_id to suggestion list
        concepts: Original concept list (for parent tracking)

    Returns:
        List of article dicts with parent_concepts and parent_articles fields
    """
    print("="*80)
    print("STEP 2: Downloading Suggested Articles")
    print("="*80)
    print()

    # Collect all unique titles and track parents
    title_to_parents = {}  # title -> list of (concept, source_article) tuples

    for i, concept_data in enumerate(concepts):
        custom_id = f'concept-{i}'
        concept = concept_data.get('concept', '')
        source_article = concept_data.get('source_article', '')

        suggestions = suggestions_by_concept.get(custom_id, [])
        for suggestion in suggestions:
            title = suggestion['title']

            if title not in title_to_parents:
                title_to_parents[title] = []

            title_to_parents[title].append({
                'concept': concept,
                'source_article': source_article,
                'reasoning': suggestion.get('reasoning', '')
            })

    unique_titles = list(title_to_parents.keys())
    print(f"Unique articles to download: {len(unique_titles)}")
    print()

    # Download articles
    articles = download_articles_batch(unique_titles, delay=0.1)

    # Validate articles
    articles = validate_articles(articles, min_text_length=500)

    # Add parent tracking
    for article in articles:
        title = article['title']
        article['parent_concepts'] = [p['concept'] for p in title_to_parents.get(title, [])]
        article['parent_articles'] = [p['source_article'] for p in title_to_parents.get(title, [])]
        article['parent_reasoning'] = [p['reasoning'] for p in title_to_parents.get(title, [])]

    print()
    print(f"✓ Downloaded {len(articles)} valid articles")
    print()

    return articles


# ============================================================================
# Embedding Generation and UMAP Projection
# ============================================================================

def generate_and_project_embeddings(
    articles: List[Dict[str, Any]],
    embedding_model: Any,
    umap_reducer: Any
) -> List[Dict[str, Any]]:
    """
    Generate embeddings and project to UMAP space.

    Args:
        articles: List of article dicts with 'text' field
        embedding_model: Sentence-transformers model
        umap_reducer: Pre-fitted UMAP reducer

    Returns:
        Articles with added 'x', 'y', 'embedding' fields
    """
    print("="*80)
    print("STEP 3: Generating Embeddings and UMAP Projection")
    print("="*80)
    print()

    # Extract texts
    texts = [article['text'] for article in articles]

    print(f"Generating embeddings for {len(texts)} articles...")
    embeddings = embedding_model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        normalize_embeddings=True
    )
    print(f"  ✓ Generated {len(embeddings)} embeddings with shape {embeddings.shape}")

    # Save embeddings to temp file for subprocess
    import tempfile
    import subprocess
    import sys

    temp_embeddings_file = tempfile.NamedTemporaryFile(mode='w+b', suffix='.npy', delete=False)
    temp_coords_file = tempfile.NamedTemporaryFile(mode='w+b', suffix='.npy', delete=False)

    try:
        # Save embeddings
        print(f"  Saving embeddings to temp file...")
        np.save(temp_embeddings_file.name, embeddings)
        temp_embeddings_file.close()

        # Run UMAP transform in subprocess to avoid library conflicts
        print(f"Projecting to UMAP space (running in subprocess to avoid segfaults)...")

        umap_subprocess_code = f"""
import os
import numpy as np
import pickle

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Load embeddings
embeddings = np.load('{temp_embeddings_file.name}')
print(f"  Loaded embeddings: {{embeddings.shape}}")

# Load UMAP reducer
with open('data/umap_reducer.pkl', 'rb') as f:
    umap_reducer = pickle.load(f)

print(f"  UMAP expects {{umap_reducer._raw_data.shape[1]}}-dim input")

# Transform embeddings to 2D coordinates
coords = umap_reducer.transform(embeddings)
print(f"  ✓ Projected {{len(coords)}} embeddings to 2D")

# Save coordinates
np.save('{temp_coords_file.name}', coords)
"""

        result = subprocess.run(
            [sys.executable, '-c', umap_subprocess_code],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"✗ UMAP subprocess failed with exit code {result.returncode}")
            print(f"stderr: {result.stderr}")
            raise RuntimeError(f"UMAP transform failed: {result.stderr}")

        # Load coordinates from temp file
        temp_coords_file.close()
        umap_coords = np.load(temp_coords_file.name)
        print(f"  ✓ Loaded {len(umap_coords)} coordinates")

    finally:
        # Clean up temp files
        import os as os_module
        try:
            os_module.unlink(temp_embeddings_file.name)
            os_module.unlink(temp_coords_file.name)
        except:
            pass

    # Load level 0 normalization bounds from wikipedia_articles.json
    # (so all levels use the same coordinate space as the heatmap)
    print(f"Loading level 0 coordinate bounds for normalization...")
    with open('wikipedia_articles.json', 'r') as f:
        level_0_articles = json.load(f)

    level_0_umap_x = [a['umap_x'] for a in level_0_articles]
    level_0_umap_y = [a['umap_y'] for a in level_0_articles]
    x_min, x_max = min(level_0_umap_x), max(level_0_umap_x)
    y_min, y_max = min(level_0_umap_y), max(level_0_umap_y)

    print(f"  Level 0 UMAP bounds: x=[{x_min:.3f}, {x_max:.3f}], y=[{y_min:.3f}, {y_max:.3f}]")

    # Normalize new articles to [0, 1] range using level 0 bounds
    x_norm = (umap_coords[:, 0] - x_min) / (x_max - x_min)
    y_norm = (umap_coords[:, 1] - y_min) / (y_max - y_min)

    # Add coordinates and embeddings to articles
    for i, article in enumerate(articles):
        article['x'] = float(x_norm[i])
        article['y'] = float(y_norm[i])
        article['umap_x'] = float(umap_coords[i, 0])
        article['umap_y'] = float(umap_coords[i, 1])
        article['embedding'] = embeddings[i].tolist()
        article['index'] = i

    print()
    print(f"✓ Generated embeddings and projected to UMAP space")
    print(f"  New articles coord range: x=[{x_norm.min():.3f}, {x_norm.max():.3f}], y=[{y_norm.min():.3f}, {y_norm.max():.3f}]")
    print(f"  (Note: May extend beyond [0,1] if articles are broader than level 0)")
    print()

    return articles


# ============================================================================
# Concept Extraction (GPT-5-nano via Batch API)
# ============================================================================

def extract_concepts_batch(
    articles: List[Dict[str, Any]],
    client: Any
) -> Dict[str, Dict[str, Any]]:
    """
    Extract concepts from articles using GPT-5-nano batch API.

    Args:
        articles: List of article dicts with 'text' and 'title'
        client: OpenAI client

    Returns:
        Dict mapping article_id to concept data (suitable, concepts, reasoning)
    """
    print("="*80)
    print("STEP 4: Extracting Concepts from Articles")
    print("="*80)
    print()

    # Create batch requests
    requests = []
    for i, article in enumerate(articles):
        title = article.get('title', 'Untitled')
        text = article.get('text', '')

        # Truncate long articles
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars]
            last_period = text.rfind('.')
            if last_period > max_chars * 0.8:
                text = text[:last_period + 1]

        prompt = f"""Analyze this Wikipedia article about "{title}" to determine if it contains substantial CONCEPTUAL content.

Article text:
{text}

Your task:
1. Determine if this article discusses PRINCIPLES, MECHANISMS, or RELATIONSHIPS (not just facts, definitions, lists)
2. If yes, extract 1-3 CORE CONCEPTS that could be tested with "why/how" questions
3. If no, explain why it's unsuitable

SUITABLE articles discuss:
- Underlying principles or mechanisms
- Cause-and-effect relationships
- Conceptual connections between ideas
- Theoretical frameworks or models

UNSUITABLE articles are primarily:
- Lists, indices, or timelines
- Pure biographical facts
- Purely definitional
- Historical events without exploring WHY they occurred"""

        requests.append({
            'custom_id': f'article-{i}',
            'user_prompt': prompt
        })

    # Submit batch (NO response_format for GPT-5-nano)
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=CONCEPT_EXTRACTION_SYSTEM_PROMPT,
        description=f"Level N concept extraction ({len(articles)} articles)",
        response_format=None,  # GPT-5-nano doesn't support structured outputs
        temperature=1.0,  # GPT-5-nano only supports temp=1
        max_tokens=1500,  # Higher limit for reasoning tokens
        timeout=None  # No timeout - wait indefinitely for batch to complete
    )

    # Parse plain text results
    parsed_results = {}
    for article_id, text in results.items():
        # Parse structured text format
        suitable = False
        concepts = []
        reasoning = ""

        lines = text.strip().split('\n')
        in_concepts = False

        for line in lines:
            line = line.strip()
            if line.startswith('SUITABLE:'):
                suitable_text = line.split(':', 1)[1].strip().lower()
                suitable = suitable_text in ['yes', 'true', 'y']
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
            elif line.startswith('CONCEPTS:'):
                in_concepts = True
            elif in_concepts and line.startswith('-'):
                concept = line[1:].strip()
                if concept:
                    concepts.append(concept)

        parsed_results[article_id] = {
            'suitable': suitable,
            'concepts': concepts,
            'reasoning': reasoning
        }

    print()
    print(f"✓ Extracted concepts from {len(parsed_results)}/{len(articles)} articles")

    # Count suitable articles
    suitable = sum(1 for r in parsed_results.values() if r.get('suitable', False))
    print(f"  Suitable articles: {suitable}/{len(parsed_results)}")
    print()

    return parsed_results


# ============================================================================
# Question Generation (GPT-5-nano via Batch API)
# ============================================================================

def generate_questions_batch(
    articles: List[Dict[str, Any]],
    concept_data: Dict[str, Dict[str, Any]],
    client: Any
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate questions from article concepts using GPT-5-nano batch API.

    Args:
        articles: List of article dicts
        concept_data: Dict mapping article_id to concept extraction results
        client: OpenAI client

    Returns:
        Dict mapping article_id to list of question dicts
    """
    print("="*80)
    print("STEP 5: Generating Questions from Concepts")
    print("="*80)
    print()

    # Create batch requests (only for suitable articles)
    requests = []
    article_id_map = {}  # request_id -> article_index

    for i, article in enumerate(articles):
        article_id = f'article-{i}'

        # Skip unsuitable articles
        if article_id not in concept_data:
            continue
        if not concept_data[article_id].get('suitable', False):
            continue

        title = article.get('title', 'Untitled')
        text = article.get('text', '')
        concepts = concept_data[article_id].get('concepts', [])

        if not concepts:
            continue

        # Truncate text
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars]
            last_period = text.rfind('.')
            if last_period > max_chars * 0.8:
                text = text[:last_period + 1]

        # Format concepts
        concepts_str = '\n'.join(f"- {c}" for c in concepts)

        prompt = f"""Generate ONE multiple choice question that tests CONCEPTUAL UNDERSTANDING about "{title}".

Core concepts to test (choose one):
{concepts_str}

Article text (for context):
{text}

CRITICAL REQUIREMENTS:

1. TEST PRINCIPLES, NOT FACTS: Ask "WHY does X work?" or "HOW does A relate to B?" - NOT "WHAT is X?"

2. EXPERT-LEVEL IS OK: The question can require domain expertise, as long as it tests understanding of PRINCIPLES and MECHANISMS.

3. SELF-CONTAINED: Do NOT reference "the article" or "the text". The question must stand alone.

Generate ONE question that:
- Tests understanding of WHY or HOW a principle/mechanism works
- Is completely self-contained
- Has a clear, unambiguous correct answer
- Includes 4 plausible answer options (A, B, C, D)"""

        request_id = f'question-{i}'
        requests.append({
            'custom_id': request_id,
            'user_prompt': prompt
        })
        article_id_map[request_id] = i

    # Submit batch (NO response_format for GPT-5-nano)
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
        description=f"Level N question generation ({len(requests)} articles)",
        response_format=None,  # GPT-5-nano doesn't support structured outputs
        temperature=1.0,  # GPT-5-nano only supports temp=1
        max_tokens=2000,  # Higher limit for reasoning tokens
        timeout=None  # No timeout - wait indefinitely for batch to complete
    )

    # Parse plain text results and organize by article
    questions_by_article = {}
    for request_id, text in results.items():
        article_idx = article_id_map.get(request_id)
        if article_idx is None:
            continue

        # Parse structured text format
        question = ""
        options = {}
        correct_answer = ""

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('QUESTION:'):
                question = line.split(':', 1)[1].strip()
            elif line.startswith('A:'):
                options['A'] = line.split(':', 1)[1].strip()
            elif line.startswith('B:'):
                options['B'] = line.split(':', 1)[1].strip()
            elif line.startswith('C:'):
                options['C'] = line.split(':', 1)[1].strip()
            elif line.startswith('D:'):
                options['D'] = line.split(':', 1)[1].strip()
            elif line.startswith('CORRECT:'):
                correct_answer = line.split(':', 1)[1].strip()

        # Only add if we got all required fields
        if question and len(options) == 4 and correct_answer:
            article_id = f'article-{article_idx}'
            article = articles[article_idx]
            concepts = concept_data[article_id].get('concepts', [])

            question_data = {
                'question': question,
                'options': options,
                'correct_answer': correct_answer,
                'source_article': article['title'],
                'x': article['x'],
                'y': article['y'],
                'concepts_tested': concepts,
                'parent_concepts': article.get('parent_concepts', []),
                'parent_articles': article.get('parent_articles', [])
            }

            questions_by_article[article_id] = [question_data]

    print()
    print(f"✓ Generated {len(questions_by_article)} questions")
    print()

    return questions_by_article


# ============================================================================
# Checkpoint and Save
# ============================================================================

def save_checkpoint(
    level: int,
    articles: List[Dict[str, Any]],
    concepts: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    checkpoint_name: str = 'checkpoint'
):
    """Save checkpoint data."""
    checkpoint_dir = Path('checkpoints')
    checkpoint_dir.mkdir(exist_ok=True)

    checkpoint_path = checkpoint_dir / f'level_{level}_{checkpoint_name}.json'

    checkpoint_data = {
        'level': level,
        'timestamp': datetime.now().isoformat(),
        'articles': articles,
        'concepts': concepts,
        'questions': questions
    }

    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    print(f"💾 Checkpoint saved: {checkpoint_path}")


def save_level_outputs(
    level: int,
    articles: List[Dict[str, Any]],
    concepts: List[Dict[str, Any]],
    questions: List[Dict[str, Any]]
):
    """
    Save final outputs for level N.

    Outputs:
    - wikipedia_articles_level_{N}.json
    - level_{N}_concepts.json
    - cell_questions_level_{N}.json
    """
    print("="*80)
    print(f"STEP 6: Saving Level {level} Outputs")
    print("="*80)
    print()

    # Save articles
    articles_path = f'wikipedia_articles_level_{level}.json'
    with open(articles_path, 'w') as f:
        json.dump(articles, f, indent=2)
    print(f"✓ Saved {len(articles)} articles to {articles_path}")

    # Save concepts
    concepts_path = f'level_{level}_concepts.json'
    with open(concepts_path, 'w') as f:
        json.dump(concepts, f, indent=2)
    print(f"✓ Saved {len(concepts)} concepts to {concepts_path}")

    # Save questions
    questions_output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'level': level,
            'num_articles': len(articles),
            'num_concepts': len(concepts),
            'num_questions': len(questions),
            'model': 'gpt-5-nano',
            'method': 'hierarchical-expansion'
        },
        'questions': questions
    }

    questions_path = f'cell_questions_level_{level}.json'
    with open(questions_path, 'w') as f:
        json.dump(questions_output, f, indent=2)
    print(f"✓ Saved {len(questions)} questions to {questions_path}")

    print()
    print("="*80)
    print(f"✓ Level {level} Generation Complete")
    print("="*80)
    print(f"  Articles: {len(articles)}")
    print(f"  Concepts: {len(concepts)}")
    print(f"  Questions: {len(questions)}")
    print()


# ============================================================================
# Main Pipeline
# ============================================================================

def load_level_0_articles() -> List[Dict[str, Any]]:
    """
    Load existing wikipedia_articles.json for level 0.

    Merges coordinate data from wikipedia_articles.json with full text
    from data/wikipedia.pkl.

    Returns:
        List of article dicts with coordinates and full text
    """
    articles_path = 'wikipedia_articles.json'
    if not os.path.exists(articles_path):
        raise FileNotFoundError(
            f"Level 0 articles not found: {articles_path}\n"
            f"Run export_wikipedia_articles.py first to create level 0 articles."
        )

    print(f"Loading level 0 articles from {articles_path}...")
    with open(articles_path, 'r') as f:
        articles = json.load(f)

    # Load full article text from wikipedia_filtered.pkl (faster than loading all 250K articles)
    wikipedia_pkl_path = 'data/wikipedia_filtered.pkl'
    if not os.path.exists(wikipedia_pkl_path):
        raise FileNotFoundError(
            f"Wikipedia data not found: {wikipedia_pkl_path}\n"
            f"This file contains full article text needed for concept extraction.\n"
            f"Run: python3 scripts/create_filtered_wikipedia.py to generate it."
        )

    print(f"Loading full article text from {wikipedia_pkl_path}...")
    with open(wikipedia_pkl_path, 'rb') as f:
        all_wikipedia_articles = pickle.load(f)

    # Create title -> article mapping for fast lookup
    title_to_article = {article['title']: article for article in all_wikipedia_articles}

    # Merge text into articles
    articles_with_text = []
    missing_text_count = 0
    for i, article in enumerate(articles):
        title = article['title']

        # Get full article text if available
        if title in title_to_article:
            full_article = title_to_article[title]
            article['text'] = full_article['text']
        else:
            # Fall back to excerpt if full text not found
            article['text'] = article.get('excerpt', '')
            missing_text_count += 1

        # Ensure articles have required fields
        if 'index' not in article:
            article['index'] = i

        # Level 0 articles have no parents
        article['parent_concepts'] = []
        article['parent_articles'] = []
        article['parent_reasoning'] = []

        articles_with_text.append(article)

    print(f"  Loaded {len(articles_with_text)} articles")
    if missing_text_count > 0:
        print(f"  Warning: {missing_text_count} articles missing full text (using excerpts)")

    return articles_with_text


def generate_level_0(
    checkpoint_interval: int = 50,
    resume_from_checkpoint: bool = True
):
    """
    Generate level 0 (base level) from existing wikipedia_articles.json.

    Level 0 is special - it uses existing articles and skips:
    - Article suggestion (step 1)
    - Article download (step 2)
    - Embedding/UMAP projection (step 3)

    It only performs:
    - Step 4: Extract concepts from existing articles
    - Step 5: Generate questions from concepts
    - Step 6: Save outputs

    Args:
        checkpoint_interval: Save checkpoint every N articles
        resume_from_checkpoint: Resume from checkpoint if exists
    """
    level = 0

    print("="*80)
    print(f"LEVEL {level} GENERATION PIPELINE")
    print("="*80)
    print()
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Level: {level} (BASE LEVEL)")
    print()

    # Load dependencies
    articles = load_level_0_articles()
    client = create_openai_client()

    print(f"Loaded {len(articles)} articles for level 0")
    print()

    # Step 4: Extract concepts (skip steps 1-3 for level 0)
    concept_results = extract_concepts_batch(articles, client)

    # Build concept list (no parent tracking for level 0)
    new_concepts = []
    for i, article in enumerate(articles):
        article_id = f'article-{i}'
        if article_id in concept_results and concept_results[article_id].get('suitable', False):
            for concept in concept_results[article_id].get('concepts', []):
                new_concepts.append({
                    'concept': concept,
                    'source_article': article['title'],
                    'level': level,
                    'x': article['x'],
                    'y': article['y'],
                    'parent_concepts': [],  # No parents for level 0
                    'parent_articles': [],
                    'reasoning': concept_results[article_id].get('reasoning', '')
                })

    # Checkpoint
    save_checkpoint(level, articles, new_concepts, [], 'after_concepts')

    # Step 5: Generate questions
    questions_by_article = generate_questions_batch(articles, concept_results, client)

    # Flatten to question list
    all_questions = []
    for article_questions in questions_by_article.values():
        all_questions.extend(article_questions)

    # Checkpoint
    save_checkpoint(level, articles, new_concepts, all_questions, 'final')

    # Step 6: Save outputs
    save_level_outputs(level, articles, new_concepts, all_questions)

    return {
        'articles': articles,
        'concepts': new_concepts,
        'questions': all_questions
    }


def generate_level_n(
    level: int,
    checkpoint_interval: int = 50,
    resume_from_checkpoint: bool = True
):
    """
    Main pipeline for generating level N.

    Args:
        level: Level to generate (0-4, where 0 is base level)
        checkpoint_interval: Save checkpoint every N articles
        resume_from_checkpoint: Resume from checkpoint if exists
    """
    if level < 0 or level > 4:
        raise ValueError(f"Level must be 0-4, got {level}")

    # Level 0 is special - uses existing articles
    if level == 0:
        return generate_level_0(checkpoint_interval, resume_from_checkpoint)

    print("="*80)
    print(f"LEVEL {level} GENERATION PIPELINE")
    print("="*80)
    print()
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Level: {level}")
    print()

    # Load dependencies
    prev_concepts = load_previous_level_concepts(level)
    client = create_openai_client()
    embedding_model = load_embedding_model()
    umap_reducer = load_umap_reducer()

    print(f"Loaded {len(prev_concepts)} concepts from level {level - 1}")
    print()

    # Check for existing checkpoints to resume from
    articles = None
    new_concepts = []
    all_questions = []
    resume_from_step = 1

    if resume_from_checkpoint:
        # Check checkpoints in reverse order (most recent first)
        checkpoint_stages = ['final', 'after_questions', 'after_concepts', 'after_umap', 'after_download']
        for stage in checkpoint_stages:
            checkpoint_path = f'checkpoints/level_{level}_{stage}.json'
            if Path(checkpoint_path).exists():
                print(f"Found checkpoint: {checkpoint_path}")
                print(f"Resuming from {stage}...")
                with open(checkpoint_path, 'r') as f:
                    checkpoint_data = json.load(f)

                articles = checkpoint_data.get('articles', [])
                new_concepts = checkpoint_data.get('concepts', [])
                all_questions = checkpoint_data.get('questions', [])

                # Determine which step to resume from
                if stage == 'final':
                    print("  ✓ All steps completed! Nothing to do.")
                    return {'articles': articles, 'concepts': new_concepts, 'questions': all_questions}
                elif stage == 'after_questions':
                    resume_from_step = 6  # Save outputs
                elif stage == 'after_concepts':
                    resume_from_step = 5  # Generate questions
                elif stage == 'after_umap':
                    resume_from_step = 4  # Extract concepts
                elif stage == 'after_download':
                    resume_from_step = 3  # Generate embeddings

                print(f"  Loaded {len(articles)} articles, {len(new_concepts)} concepts, {len(all_questions)} questions")
                print(f"  Resuming from step {resume_from_step}")
                print()
                break

    # Step 1: Suggest broader articles
    if resume_from_step <= 1:
        suggestions = suggest_broader_articles_batch(prev_concepts, client)
    else:
        print(f"Skipping step 1 (suggest articles) - resuming from checkpoint")

    # Step 2: Download articles
    if resume_from_step <= 2:
        articles = download_suggested_articles(suggestions, prev_concepts)
        save_checkpoint(level, articles, [], [], 'after_download')
    else:
        print(f"Skipping step 2 (download articles) - resuming from checkpoint")

    # Step 3: Generate embeddings and project to UMAP
    if resume_from_step <= 3:
        articles = generate_and_project_embeddings(articles, embedding_model, umap_reducer)
        save_checkpoint(level, articles, [], [], 'after_umap')
    else:
        print(f"Skipping step 3 (embeddings/UMAP) - resuming from checkpoint")

    # Step 4: Extract concepts
    if resume_from_step <= 4:
        concept_results = extract_concepts_batch(articles, client)

        # Build concept list with parent tracking
        new_concepts = []
        for i, article in enumerate(articles):
            article_id = f'article-{i}'
            if article_id in concept_results and concept_results[article_id].get('suitable', False):
                for concept in concept_results[article_id].get('concepts', []):
                    new_concepts.append({
                        'concept': concept,
                        'source_article': article['title'],
                        'level': level,
                        'x': article['x'],
                        'y': article['y'],
                        'parent_concepts': article.get('parent_concepts', []),
                        'parent_articles': article.get('parent_articles', []),
                        'reasoning': concept_results[article_id].get('reasoning', '')
                    })

        save_checkpoint(level, articles, new_concepts, [], 'after_concepts')
    else:
        print(f"Skipping step 4 (extract concepts) - resuming from checkpoint")
        # Still need concept_results for question generation
        concept_results = {}

    # Step 5: Generate questions
    if resume_from_step <= 5:
        questions_by_article = generate_questions_batch(articles, concept_results, client)

        # Flatten to question list
        all_questions = []
        for article_questions in questions_by_article.values():
            all_questions.extend(article_questions)

        save_checkpoint(level, articles, new_concepts, all_questions, 'final')
    else:
        print(f"Skipping step 5 (generate questions) - resuming from checkpoint")

    # Step 6: Save outputs
    if resume_from_step <= 6:
        save_level_outputs(level, articles, new_concepts, all_questions)
    else:
        print(f"Skipping step 6 (save outputs) - resuming from checkpoint")

    return {
        'articles': articles,
        'concepts': new_concepts,
        'questions': all_questions
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate progressively broader articles and questions for levels 0-4',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate level 0 (base level from existing wikipedia_articles.json)
  python generate_level_n.py --level 0

  # Generate level 1 from level 0
  python generate_level_n.py --level 1

  # Generate level 2 from level 1
  python generate_level_n.py --level 2

  # Generate level 3 with custom checkpoint interval
  python generate_level_n.py --level 3 --checkpoint-interval 25

Output files:
  - wikipedia_articles_level_{N}.json: Articles with parent tracking
  - level_{N}_concepts.json: Concepts extracted from articles
  - cell_questions_level_{N}.json: Questions with parent relationships

Note: Level 0 uses existing wikipedia_articles.json and only extracts concepts
and generates questions (no article suggestion/download/embedding needed).
        """
    )

    parser.add_argument(
        '--level',
        type=int,
        required=True,
        choices=[0, 1, 2, 3, 4],
        help='Level to generate (0-4, where 0 is base level)'
    )

    parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=50,
        help='Save checkpoint every N articles (default: 50)'
    )

    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Do not resume from checkpoint (start fresh)'
    )

    args = parser.parse_args()

    try:
        results = generate_level_n(
            level=args.level,
            checkpoint_interval=args.checkpoint_interval,
            resume_from_checkpoint=(not args.no_resume)
        )

        print()
        print("="*80)
        print("✅ SUCCESS")
        print("="*80)
        print(f"Level {args.level} generation completed successfully!")
        print()
        print("Output files:")
        print(f"  - wikipedia_articles_level_{args.level}.json")
        print(f"  - level_{args.level}_concepts.json")
        print(f"  - cell_questions_level_{args.level}.json")
        print()

    except Exception as e:
        print()
        print("="*80)
        print("❌ ERROR")
        print("="*80)
        print(f"Level {args.level} generation failed: {e}")
        print()

        import traceback
        traceback.print_exc()

        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
