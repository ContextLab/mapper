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

Return JSON with this exact structure:
{
  "suggestions": [
    {"title": "Article Title 1", "reasoning": "Why this is broader..."},
    {"title": "Article Title 2", "reasoning": "Why this is broader..."}
  ]
}

Guidelines:
- Suggest REAL Wikipedia articles (verify titles exist)
- Move up the conceptual hierarchy (specific → general)
- Avoid lateral connections (stay focused on broadening)
- Return 1-3 suggestions per concept (quality over quantity)
"""

CONCEPT_EXTRACTION_SYSTEM_PROMPT = """You are an expert at analyzing educational content to identify conceptual vs. factual material.

You distinguish between articles that test understanding of principles (suitable) vs. memorization of facts (unsuitable).

Extract 1-3 core concepts/principles from the article that could be tested with "why/how" questions.

Return JSON with this exact structure:
{
  "suitable": true/false,
  "concepts": ["concept 1", "concept 2", "concept 3"],
  "reasoning": "Brief explanation of suitability"
}
"""

QUESTION_GENERATION_SYSTEM_PROMPT = """You are an expert educator who creates conceptual questions testing understanding of WHY and HOW, not WHAT or WHEN.

Your questions test principles and mechanisms, never definitions or facts.

Your questions are completely self-contained and never reference source material.

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


def load_embedding_model(model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
    """Load sentence-transformers model for embedding generation."""
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

    # Define response format
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "article_suggestions",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "reasoning": {"type": "string"}
                            },
                            "required": ["title", "reasoning"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["suggestions"],
                "additionalProperties": False
            }
        }
    }

    # Submit batch
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=ARTICLE_SUGGESTION_SYSTEM_PROMPT,
        description=f"Level N article suggestions ({len(concepts)} concepts)",
        response_format=response_format,
        temperature=0.7,
        max_tokens=500
    )

    # Parse results
    suggestions_by_concept = {}
    for i, concept_data in enumerate(concepts):
        custom_id = f'concept-{i}'
        if custom_id in results:
            suggestions_by_concept[custom_id] = results[custom_id].get('suggestions', [])
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

    print(f"Projecting to UMAP space...")
    umap_coords = umap_reducer.transform(embeddings)

    # Normalize to [0, 1] range
    x_min, x_max = umap_coords[:, 0].min(), umap_coords[:, 0].max()
    y_min, y_max = umap_coords[:, 1].min(), umap_coords[:, 1].max()

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
    print(f"  Coord range: x=[{x_norm.min():.3f}, {x_norm.max():.3f}], y=[{y_norm.min():.3f}, {y_norm.max():.3f}]")
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

    # Define response format
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "concept_extraction",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "suitable": {"type": "boolean"},
                    "concepts": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "reasoning": {"type": "string"}
                },
                "required": ["suitable", "concepts", "reasoning"],
                "additionalProperties": False
            }
        }
    }

    # Submit batch
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=CONCEPT_EXTRACTION_SYSTEM_PROMPT,
        description=f"Level N concept extraction ({len(articles)} articles)",
        response_format=response_format,
        temperature=0.3,
        max_tokens=400
    )

    print()
    print(f"✓ Extracted concepts from {len(results)}/{len(articles)} articles")

    # Count suitable articles
    suitable = sum(1 for r in results.values() if r.get('suitable', False))
    print(f"  Suitable articles: {suitable}/{len(results)}")
    print()

    return results


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

    # Define response format
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "conceptual_question",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "A": {"type": "string"},
                            "B": {"type": "string"},
                            "C": {"type": "string"},
                            "D": {"type": "string"}
                        },
                        "required": ["A", "B", "C", "D"],
                        "additionalProperties": False
                    },
                    "correct_answer": {"type": "string"}
                },
                "required": ["question", "options", "correct_answer"],
                "additionalProperties": False
            }
        }
    }

    # Submit batch
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
        description=f"Level N question generation ({len(requests)} articles)",
        response_format=response_format,
        temperature=0.7,
        max_tokens=500
    )

    # Organize results by article
    questions_by_article = {}
    for request_id, question_data in results.items():
        article_idx = article_id_map.get(request_id)
        if article_idx is not None:
            article_id = f'article-{article_idx}'
            article = articles[article_idx]
            concepts = concept_data[article_id].get('concepts', [])

            # Add metadata
            question_data['source_article'] = article['title']
            question_data['x'] = article['x']
            question_data['y'] = article['y']
            question_data['concepts_tested'] = concepts
            question_data['parent_concepts'] = article.get('parent_concepts', [])
            question_data['parent_articles'] = article.get('parent_articles', [])

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

def generate_level_n(
    level: int,
    checkpoint_interval: int = 50,
    resume_from_checkpoint: bool = True
):
    """
    Main pipeline for generating level N.

    Args:
        level: Level to generate (1-4)
        checkpoint_interval: Save checkpoint every N articles
        resume_from_checkpoint: Resume from checkpoint if exists
    """
    if level < 1 or level > 4:
        raise ValueError(f"Level must be 1-4, got {level}")

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

    # Step 1: Suggest broader articles
    suggestions = suggest_broader_articles_batch(prev_concepts, client)

    # Step 2: Download articles
    articles = download_suggested_articles(suggestions, prev_concepts)

    # Checkpoint
    save_checkpoint(level, articles, [], [], 'after_download')

    # Step 3: Generate embeddings and project to UMAP
    articles = generate_and_project_embeddings(articles, embedding_model, umap_reducer)

    # Checkpoint
    save_checkpoint(level, articles, [], [], 'after_umap')

    # Step 4: Extract concepts
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


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate progressively broader articles and questions for levels 1-4',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
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
        """
    )

    parser.add_argument(
        '--level',
        type=int,
        required=True,
        choices=[1, 2, 3, 4],
        help='Level to generate (1-4)'
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
