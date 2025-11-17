#!/usr/bin/env python3
"""
Generate multiple choice questions for heatmap cells using Qwen3-14B via LM Studio.

For each cell in the heatmap grid:
1. Select 1-2 random nearby Wikipedia articles
2. Prompt Qwen3-14B with full article text to generate conceptual questions
3. Generate 4 multiple choice questions per cell
4. Use structured outputs to ensure consistent format
5. Save to cell_questions.json

The questions focus on testing conceptual understanding rather than rote memorization.
"""

import json
import os
import random
import requests
import numpy as np
from datetime import datetime
from pathlib import Path


def load_cell_labels():
    """Load heatmap cell labels with neighbor information"""
    print("Loading heatmap cell labels...")
    with open('heatmap_cell_labels.json', 'r') as f:
        data = json.load(f)

    print(f"  Loaded {len(data['cells'])} cells with labels")
    return data['cells']


def load_wikipedia_articles():
    """Load Wikipedia articles with full text"""
    print("Loading Wikipedia articles...")
    with open('wikipedia_articles.json', 'r') as f:
        articles_data = json.load(f)

    # Create a mapping from title to article data
    articles_by_title = {a['title']: a for a in articles_data}

    print(f"  Loaded {len(articles_by_title):,} articles")
    return articles_by_title


def load_full_wikipedia_data():
    """Load full Wikipedia article data with complete text from data/wikipedia.pkl"""
    print("Loading full Wikipedia article data...")
    import pickle

    with open('data/wikipedia.pkl', 'rb') as f:
        articles = pickle.load(f)

    # Create mapping from title to full article
    full_articles_by_title = {a['title']: a for a in articles}

    print(f"  Loaded {len(full_articles_by_title):,} full articles")
    return full_articles_by_title


def is_suitable_article(article):
    """
    Check if an article is suitable for question generation.

    Args:
        article: Article dict with title and text

    Returns:
        bool: True if article is suitable, False otherwise
    """
    article_title = article.get('title', '').lower()
    article_text = article.get('text', '').lower()

    # Skip disambiguation pages
    if 'disambiguation' in article_title:
        return False
    if 'may refer to:' in article_text[:500]:  # Check first 500 chars
        return False

    # Skip very short articles (likely stubs or redirects)
    # Increased from 200 to 500 for better content quality
    if len(article_text) < 500:
        return False

    # Skip list-type articles (unlikely to have conceptual content)
    list_indicators = ['list of', 'index of', 'timeline of', 'glossary of']
    if any(indicator in article_title for indicator in list_indicators):
        return False

    return True


def select_random_article(cell, full_articles):
    """
    Select one random nearby Wikipedia article for a cell.

    Filters out disambiguation pages and other unsuitable articles.
    If no suitable articles are found in the nearest neighbors, expands
    the search to find the next closest suitable article.

    Args:
        cell: Cell data with neighbors list
        full_articles: Dict mapping title to full article data

    Returns:
        Single article dict with full text, or None if no articles available
    """
    # Get neighbor titles from cell (sorted by distance, closest first)
    neighbor_titles = [n['title'] for n in cell['neighbors']]

    # Filter to articles we have full text for
    available_titles = [t for t in neighbor_titles if t in full_articles]

    # Filter out disambiguation pages and other unsuitable articles
    suitable_titles = []
    for title in available_titles:
        article = full_articles[title]
        if is_suitable_article(article):
            suitable_titles.append(title)

    # If we found suitable articles in the neighbors, randomly select one
    if suitable_titles:
        selected_title = random.choice(suitable_titles)
        return full_articles[selected_title]

    # If no suitable articles found in neighbors, expand search
    # This happens when all neighbors are disambiguation pages or too short
    # In this case, find the closest suitable article from all available articles
    print(f"    ⚠ No suitable articles in nearest neighbors, expanding search...")

    # Calculate cell center coordinates
    cell_center = np.array([cell['center_x'], cell['center_y']])

    # Find all suitable articles with their distances
    suitable_candidates = []
    for title, article in full_articles.items():
        if is_suitable_article(article):
            # Get article coordinates (assuming they have x, y fields)
            article_x = article.get('x')
            article_y = article.get('y')

            if article_x is not None and article_y is not None:
                article_pos = np.array([article_x, article_y])
                distance = np.linalg.norm(cell_center - article_pos)
                suitable_candidates.append((distance, title))

    if not suitable_candidates:
        print(f"    ✗ No suitable articles found anywhere")
        return None

    # Sort by distance and take the closest one
    suitable_candidates.sort(key=lambda x: x[0])
    closest_title = suitable_candidates[0][1]
    closest_distance = suitable_candidates[0][0]

    print(f"    ✓ Found suitable article at distance {closest_distance:.4f}: \"{closest_title[:60]}...\"")

    return full_articles[closest_title]


def truncate_text(text, max_chars=3000):
    """Truncate article text to fit in prompt without losing too much context"""
    if len(text) <= max_chars:
        return text

    # Truncate at sentence boundary if possible
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')

    if last_period > max_chars * 0.8:  # If we have a sentence ending in last 20%
        return truncated[:last_period + 1]
    else:
        return truncated + '...'


def is_question_self_contained(question_text):
    """
    Check if a question is self-contained (doesn't reference source material).

    Args:
        question_text: The question text to check

    Returns:
        bool: True if self-contained, False otherwise
    """
    question_lower = question_text.lower()

    # Phrases that indicate the question references source material
    reference_phrases = [
        'based on',
        'information provided',
        'the article',
        'text above',
        'as described in',
        'according to the',
        'in the passage',
        'from the text',
        'the reading',
        'this article'
    ]

    for phrase in reference_phrases:
        if phrase in question_lower:
            return False

    return True


def is_mitochondria_placeholder(question_text, article_text):
    """
    Check if the question appears to be using "mitochondria" as a placeholder
    (i.e., mentions mitochondria but article doesn't discuss it).

    Args:
        question_text: The question text to check
        article_text: The source article text

    Returns:
        bool: True if this appears to be a placeholder, False otherwise
    """
    question_lower = question_text.lower()
    article_lower = article_text.lower()

    # If question mentions mitochondria but article doesn't, it's likely a placeholder
    if 'mitochondria' in question_lower or 'mitochondrion' in question_lower:
        if 'mitochondria' not in article_lower and 'mitochondrion' not in article_lower:
            return True

    return False


def is_concept_question(question_text):
    """
    Check if a question tests conceptual understanding vs. factual memorization.

    Conceptual questions ask "why" or "how" - testing principles and understanding.
    Factual questions ask "what", "when", "who", "where" - testing memorization.

    Args:
        question_text: The question text to check

    Returns:
        bool: True if conceptual, False if factual
    """
    question_lower = question_text.lower().strip()

    # Factual question indicators (immediate rejection)
    factual_starters = [
        'what is the',
        'what was the',
        'what are the',
        'what were the',
        'when did',
        'when was',
        'when were',
        'who was',
        'who is',
        'who were',
        'where is',
        'where was',
        'where are',
        'which of the following is the definition',
        'what does the term',
        'what is defined as'
    ]

    for starter in factual_starters:
        if question_lower.startswith(starter):
            return False

    # Conceptual question indicators (strong positive signals)
    conceptual_indicators = [
        'why does',
        'why do',
        'why is',
        'why are',
        'why would',
        'how does',
        'how do',
        'how is',
        'how are',
        'how can',
        'what explains',
        'what principle',
        'what mechanism',
        'what relationship',
        'what causes',
        'what results from',
        'what happens when',
        'what would happen if',
        'which principle',
        'which mechanism',
        'which process explains'
    ]

    for indicator in conceptual_indicators:
        if indicator in question_lower:
            return True

    # Default: accept if not clearly factual
    # (allows for creative conceptual questions with varied phrasing)
    return True


def extract_concepts_from_article(article, lm_studio_url="http://localhost:1234/v1/chat/completions"):
    """
    STEP 1 of two-step process: Extract core concepts from article and assess suitability.

    Uses LLM to:
    1. Identify if article contains substantial conceptual content (vs. purely factual/lists)
    2. Extract 1-3 core concepts/principles that could be tested
    3. Determine if conceptual "why/how" questions are possible

    Args:
        article: Wikipedia article dict with title and text
        lm_studio_url: URL of LM Studio API endpoint

    Returns:
        dict with 'suitable' (bool), 'concepts' (list of strings), 'reasoning' (string)
        Returns None if article is unsuitable for conceptual questions
    """
    if not article:
        return None

    title = article.get('title', 'Untitled')
    text = article.get('text', '')
    truncated_text = truncate_text(text, max_chars=3000)

    prompt = f"""Analyze this Wikipedia article about "{title}" to determine if it contains substantial CONCEPTUAL content suitable for "why/how" questions.

Article text:
{truncated_text}

Your task:
1. Determine if this article discusses PRINCIPLES, MECHANISMS, or RELATIONSHIPS (not just facts, definitions, lists, or historical details)
2. If yes, extract 1-3 CORE CONCEPTS that could be tested with "why does X work?" or "how does A relate to B?" questions
3. If no, explain why it's unsuitable

SUITABLE articles discuss:
- Underlying principles or mechanisms (e.g., "why does this process occur?")
- Cause-and-effect relationships (e.g., "how does X lead to Y?")
- Conceptual connections between ideas (e.g., "what principle explains Z?")
- Theoretical frameworks or models

UNSUITABLE articles are primarily:
- Lists, indices, or timelines (no conceptual depth)
- Pure biographical facts ("born in...", "died in...")
- Purely definitional ("X is a type of Y")
- Administrative/organizational details with no underlying principles
- Historical events without exploring WHY they occurred

Respond with your analysis."""

    # Define JSON schema for concept extraction
    response_schema = {
        "type": "object",
        "properties": {
            "suitable": {
                "type": "boolean",
                "description": "True if article has conceptual content suitable for why/how questions"
            },
            "concepts": {
                "type": "array",
                "description": "List of 1-3 core concepts/principles to test (empty if unsuitable)",
                "items": {"type": "string"}
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why article is suitable/unsuitable"
            }
        },
        "required": ["suitable", "concepts", "reasoning"]
    }

    try:
        response = requests.post(
            lm_studio_url,
            json={
                "model": "qwen/qwen3-14b",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing educational content to identify conceptual vs. factual material. You distinguish between articles that test understanding of principles (suitable) vs. memorization of facts (unsuitable)."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "max_tokens": 400,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "concept_extraction",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0]['message']
            content = message.get('content', '{}')
            parsed = json.loads(content)

            # If unsuitable, return None
            if not parsed.get('suitable', False):
                return None

            # Return concept data
            return {
                'suitable': True,
                'concepts': parsed.get('concepts', []),
                'reasoning': parsed.get('reasoning', ''),
                'article_title': title
            }
        else:
            print(f"  Error from LM Studio (concept extraction): {response.status_code}")
            return None

    except Exception as e:
        print(f"  Concept extraction failed: {e}")
        return None


def generate_question_for_article(article, cell, concepts_data, lm_studio_url="http://localhost:1234/v1/chat/completions"):
    """
    STEP 2 of two-step process: Generate conceptual question based on extracted concepts.

    Args:
        article: Wikipedia article dict with full text
        cell: Cell data with grid coordinates and center position
        concepts_data: Dict from extract_concepts_from_article() with 'concepts' list
        lm_studio_url: URL of LM Studio API endpoint

    Returns:
        dict with 'question' data and generation metadata
    """
    if not article or not concepts_data:
        return {
            'question': None,
            'error': 'No article or concepts provided',
            'finish_reason': 'error'
        }

    # Get article content and extracted concepts
    title = article.get('title', 'Untitled')
    text = article.get('text', '')
    truncated_text = truncate_text(text, max_chars=3000)
    concepts = concepts_data.get('concepts', [])

    if not concepts:
        return {
            'question': None,
            'error': 'No concepts extracted',
            'finish_reason': 'error'
        }

    # Format concepts for prompt
    concepts_str = '\n'.join(f"- {c}" for c in concepts)

    # Construct prompt for conceptual question generation
    prompt = f"""Generate ONE multiple choice question that tests CONCEPTUAL UNDERSTANDING (not memorized facts) about "{title}".

Core concepts to test (choose one):
{concepts_str}

Article text (for context):
{truncated_text}

CRITICAL REQUIREMENTS:

1. TEST PRINCIPLES, NOT FACTS: Ask "WHY does X work?" or "HOW does A relate to B?" - NOT "WHAT is X?" or "WHEN did Y happen?"

2. EXPERT-LEVEL IS OK: The question can require domain expertise, as long as it tests understanding of PRINCIPLES and MECHANISMS rather than memorization of facts or definitions.

3. SELF-CONTAINED: Do NOT reference "the article", "the text", or "based on the information provided". The question must stand alone completely.

GOOD EXAMPLES (conceptual understanding):
- "Why does increasing temperature generally speed up chemical reactions?"
- "How do monopolies maintain market power despite producing less than the competitive quantity?"
- "What principle explains why island species are more vulnerable to extinction than mainland species?"
- "Why do enzymes become less effective at very high temperatures?"

BAD EXAMPLES (factual memorization):
- "What is the primary purpose of a 'hundred' in English administrative geography?" (definitional - WHAT IS)
- "When was the Shoalhaven News founded?" (historical fact - WHEN)
- "Who was the first mayor of Brisbane?" (biographical fact - WHO)
- "What is defined as a monopoly?" (definition - WHAT IS DEFINED AS)

Generate ONE question that:
- Tests understanding of WHY or HOW a principle/mechanism works
- Can be expert-level but must test CONCEPTUAL understanding (not memorization)
- Is completely self-contained (no references to source material)
- Has a clear, unambiguous correct answer
- Includes 4 plausible answer options (A, B, C, D)
- Focuses on principles, mechanisms, relationships, or cause-and-effect"""

    # Define JSON schema for structured output
    response_schema = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The self-contained question text testing conceptual understanding"
            },
            "options": {
                "type": "object",
                "properties": {
                    "A": {"type": "string"},
                    "B": {"type": "string"},
                    "C": {"type": "string"},
                    "D": {"type": "string"}
                },
                "required": ["A", "B", "C", "D"]
            },
            "correct_answer": {
                "type": "string",
                "description": "The letter of the correct answer (A, B, C, or D)"
            }
        },
        "required": ["question", "options", "correct_answer"]
    }

    # Call LM Studio API with structured output
    try:
        response = requests.post(
            lm_studio_url,
            json={
                "model": "qwen/qwen3-14b",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert educator who creates conceptual questions testing understanding of WHY and HOW, not WHAT or WHEN. Your questions test principles and mechanisms, never definitions or facts. Your questions are completely self-contained and never reference source material."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "conceptual_question",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0]['message']

            # Parse JSON response
            content = message.get('content', '{}')
            parsed = json.loads(content)

            # Add cell coordinates, source article, and concepts
            if parsed.get('question'):
                parsed['cell_x'] = cell['center_x']
                parsed['cell_y'] = cell['center_y']
                parsed['cell_gx'] = cell['gx']
                parsed['cell_gy'] = cell['gy']
                parsed['source_article'] = title
                parsed['concepts_tested'] = concepts

            finish_reason = data['choices'][0].get('finish_reason', 'unknown')
            tokens_used = data.get('usage', {}).get('total_tokens', 0)

            return {
                'question': parsed if parsed.get('question') else None,
                'finish_reason': finish_reason,
                'tokens_used': tokens_used
            }
        else:
            print(f"  Error from LM Studio: {response.status_code}")
            return {
                'question': None,
                'error': f'HTTP {response.status_code}',
                'finish_reason': 'error'
            }

    except requests.exceptions.RequestException as e:
        print(f"  Request failed: {e}")
        return {
            'question': None,
            'error': str(e),
            'finish_reason': 'error'
        }
    except json.JSONDecodeError as e:
        print(f"  JSON parsing failed: {e}")
        return {
            'question': None,
            'error': f'JSON parse error: {e}',
            'finish_reason': 'error'
        }


def generate_questions_for_cells(cells, full_articles, num_cells=None, questions_per_cell=4, random_seed=42, checkpoint_file='cell_questions_checkpoint.json', checkpoint_interval=250, resume_from_checkpoint=True):
    """
    Generate questions for cells (with checkpointing support).
    For each cell, generates one question per article (selecting 4 articles).

    Args:
        cells: List of all cell data
        full_articles: Dict mapping title to full article data
        num_cells: Number of cells to generate questions for (None = all cells)
        questions_per_cell: Number of questions to generate per cell (default: 4)
        random_seed: Random seed for reproducibility
        checkpoint_file: File to save checkpoints to
        checkpoint_interval: Save checkpoint every N cells
        resume_from_checkpoint: Whether to resume from checkpoint if it exists

    Returns:
        List of cell question data
    """
    print("="*80)
    print("CELL QUESTION GENERATION")
    print("="*80)
    print()

    # Set random seed for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)

    # Determine cells to process
    if num_cells is None:
        num_to_generate = len(cells)
        selected_cells = cells  # Use all cells in order
        print(f"Generating {questions_per_cell} questions for ALL {num_to_generate} cells...")
    else:
        num_to_generate = min(num_cells, len(cells))
        selected_cells = random.sample(cells, num_to_generate)
        print(f"Generating {questions_per_cell} questions for {num_to_generate} randomly selected cells...")

    print(f"  Random seed: {random_seed}")
    print(f"  Articles available: {len(full_articles):,}")
    print(f"  Strategy: One question per article ({questions_per_cell} articles per cell)")
    print(f"  Checkpoint interval: Every {checkpoint_interval} cells")
    print()

    # Check for existing checkpoint
    results = []
    start_index = 0

    if resume_from_checkpoint and os.path.exists(checkpoint_file):
        print(f"Found checkpoint file: {checkpoint_file}")
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)

            results = checkpoint_data.get('cells', [])
            start_index = len(results)

            print(f"  Resuming from cell {start_index + 1}/{num_to_generate}")
            print(f"  Already completed: {start_index} cells, {sum(len(r['questions']) for r in results)} questions")
            print()
        except Exception as e:
            print(f"  ⚠ Failed to load checkpoint: {e}")
            print(f"  Starting from beginning...")
            results = []
            start_index = 0
            print()

    for i, cell in enumerate(selected_cells[start_index:], start=start_index):
        print(f"Cell {i+1}/{num_to_generate}: ({cell['gx']}, {cell['gy']}) - \"{cell['label']}\"")

        cell_questions = []
        total_tokens = 0
        source_articles = []

        # Generate questions_per_cell questions (one per article)
        # Using two-step process: concept extraction → question generation
        for q_num in range(questions_per_cell):
            # Select one random article for this question
            article = select_random_article(cell, full_articles)

            if not article:
                print(f"  Question {q_num+1}/{questions_per_cell}: No article available")
                continue

            article_title = article.get('title', 'Untitled')
            article_text = article.get('text', '')
            print(f"  Question {q_num+1}/{questions_per_cell}: Using \"{article_title[:60]}...\"")

            # STEP 1: Extract concepts from article
            print(f"    Step 1: Extracting concepts...")
            concepts_data = extract_concepts_from_article(article)

            if not concepts_data:
                print(f"    ✗ No conceptual content found, skipping article")
                continue

            concepts = concepts_data.get('concepts', [])
            reasoning = concepts_data.get('reasoning', '')
            print(f"    ✓ Found {len(concepts)} concept(s): {', '.join(concepts[:2])}")
            if reasoning:
                print(f"      Reasoning: {reasoning[:80]}...")

            # STEP 2: Generate conceptual question
            print(f"    Step 2: Generating conceptual question...")

            # Try up to 3 times to generate a valid question
            max_retries = 3
            question_generated = False

            for attempt in range(max_retries):
                # Generate one question based on extracted concepts
                result = generate_question_for_article(article, cell, concepts_data)

                if not result['question']:
                    if attempt < max_retries - 1:
                        print(f"    ⚠ Attempt {attempt+1} failed: {result.get('error', 'Unknown error')}, retrying...")
                    else:
                        print(f"    ✗ Failed after {max_retries} attempts: {result.get('error', 'Unknown error')}")
                    continue

                question_data = result['question']
                question_text = question_data.get('question', '')

                # Quality check 1: Is question self-contained?
                if not is_question_self_contained(question_text):
                    if attempt < max_retries - 1:
                        print(f"    ⚠ Attempt {attempt+1}: Question references source material, retrying...")
                    else:
                        print(f"    ✗ Failed quality check after {max_retries} attempts: Not self-contained")
                    continue

                # Quality check 2: Is this a mitochondria placeholder?
                if is_mitochondria_placeholder(question_text, article_text):
                    if attempt < max_retries - 1:
                        print(f"    ⚠ Attempt {attempt+1}: Generic placeholder detected, retrying...")
                    else:
                        print(f"    ✗ Failed quality check after {max_retries} attempts: Placeholder question")
                    continue

                # Quality check 3: Is this a conceptual question (not factual)?
                if not is_concept_question(question_text):
                    if attempt < max_retries - 1:
                        print(f"    ⚠ Attempt {attempt+1}: Factual question detected (not conceptual), retrying...")
                    else:
                        print(f"    ✗ Failed quality check after {max_retries} attempts: Not conceptual")
                    continue

                # Question passed all quality checks!
                cell_questions.append(question_data)
                total_tokens += result.get('tokens_used', 0)
                source_articles.append(article_title)
                print(f"    ✓ Generated: {question_text[:60]}...")
                question_generated = True
                break

            if not question_generated:
                print(f"    → Skipping this question slot after {max_retries} failed attempts")

        print(f"  Total: {len(cell_questions)}/{questions_per_cell} questions, {total_tokens} tokens")
        print()

        # Store result
        results.append({
            'cell': {
                'gx': cell['gx'],
                'gy': cell['gy'],
                'center_x': cell['center_x'],
                'center_y': cell['center_y'],
                'label': cell['label']
            },
            'questions': cell_questions,
            'metadata': {
                'source_articles': source_articles,
                'total_tokens': total_tokens,
                'questions_generated': len(cell_questions),
                'questions_requested': questions_per_cell
            }
        })

        # Save checkpoint every checkpoint_interval cells
        if (i + 1) % checkpoint_interval == 0:
            print()
            print(f"💾 Checkpoint: Saving progress ({len(results)} cells completed)...")
            save_checkpoint(results, checkpoint_file, questions_per_cell)
            print(f"   Saved to {checkpoint_file}")
            print()

    return results


def save_checkpoint(results, checkpoint_file, questions_per_cell=4):
    """Save checkpoint file with current results"""
    checkpoint_data = {
        'metadata': {
            'checkpoint_at': datetime.now().isoformat(),
            'num_cells': len(results),
            'questions_per_cell': questions_per_cell,
            'total_questions': sum(len(r['questions']) for r in results),
            'model': 'qwen3-14b',
            'method': 'wikipedia-article-based-conceptual',
            'status': 'in_progress'
        },
        'cells': results
    }

    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)


def save_questions(results, output_file='cell_questions.json'):
    """Save generated questions to JSON file"""
    print(f"Saving questions to {output_file}...")

    output_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'num_cells': len(results),
            'questions_per_cell': 4,
            'total_questions': sum(len(r['questions']) for r in results),
            'model': 'qwen3-14b',
            'method': 'wikipedia-article-based-conceptual',
            'status': 'completed'
        },
        'cells': results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"  Saved {len(results)} cells")
    print(f"  Total questions: {output_data['metadata']['total_questions']}")

    # Show quality summary
    print()
    print("Quality Summary:")
    print(f"  Cells processed: {len(results)}")
    print(f"  Cells with 4 questions: {sum(1 for r in results if len(r['questions']) == 4)}")
    print(f"  Cells with <4 questions: {sum(1 for r in results if len(r['questions']) < 4)}")

    return output_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate conceptual questions for heatmap cells')
    parser.add_argument('--num-cells', type=int, default=None,
                        help='Number of cells to generate questions for (default: None = all 1,521 cells)')
    parser.add_argument('--random-seed', type=int, default=42,
                        help='Random seed for cell selection (default: 42)')
    parser.add_argument('--output', type=str, default='cell_questions.json',
                        help='Output file (default: cell_questions.json)')
    parser.add_argument('--checkpoint-file', type=str, default='cell_questions_checkpoint.json',
                        help='Checkpoint file (default: cell_questions_checkpoint.json)')
    parser.add_argument('--checkpoint-interval', type=int, default=250,
                        help='Save checkpoint every N cells (default: 250)')
    parser.add_argument('--no-resume', action='store_true',
                        help='Do not resume from checkpoint (start from beginning)')

    args = parser.parse_args()

    # Load data
    cells = load_cell_labels()
    full_articles = load_full_wikipedia_data()

    # Generate questions
    results = generate_questions_for_cells(
        cells,
        full_articles,
        num_cells=args.num_cells,
        random_seed=args.random_seed,
        checkpoint_file=args.checkpoint_file,
        checkpoint_interval=args.checkpoint_interval,
        resume_from_checkpoint=(not args.no_resume)
    )

    # Save results
    output_file = save_questions(results, args.output)

    # Clean up checkpoint file on successful completion
    if os.path.exists(args.checkpoint_file):
        print(f"Removing checkpoint file: {args.checkpoint_file}")
        os.remove(args.checkpoint_file)

    print()
    print("="*80)
    print("✓ Question generation complete")
    print("="*80)
    print(f"Output: {output_file}")
    print()


if __name__ == '__main__':
    main()
