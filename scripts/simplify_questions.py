#!/usr/bin/env python3
"""
Simplify Questions Script
=========================

Simplifies questions from cell_questions_level_{n}.json files using GPT-5-mini.
Produces cell_questions_level_{n}_simplified.json with age-appropriate wording
and inline LaTeX formatting.

Features:
- Two-pass system: simplification first, then new generation if needed
- Level-specific simplification targets (L4=middle school → L0=experts)
- Converts math notation to inline LaTeX ($...$)
- Validates content preservation using Flesch-Kincaid readability
- Logs excluded questions with reasons

Usage:
    # Pilot run (20 questions)
    python scripts/simplify_questions.py --level 4 --pilot 20

    # Full run
    python scripts/simplify_questions.py --level 4

    # All levels
    python scripts/simplify_questions.py --all
"""

import json
import argparse
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.utils.api_utils import create_openai_client
from scripts.utils.openai_batch import batch_with_cache

# Try to import textstat for readability scoring
try:
    import textstat
    HAS_TEXTSTAT = True
except ImportError:
    print("Warning: textstat not installed. Install with: pip install textstat")
    print("Readability validation will be disabled.")
    HAS_TEXTSTAT = False


# Level-specific configuration
LEVEL_CONFIG = {
    4: {
        'target_audience': 'middle school students (ages 11-14)',
        'max_grade_level': 8,
        'simplification_level': 'major',
        'example_concepts': 'basic scientific concepts, simple cause and effect'
    },
    3: {
        'target_audience': 'high school students (ages 14-18)',
        'max_grade_level': 12,
        'simplification_level': 'moderate',
        'example_concepts': 'intermediate scientific principles, multi-step reasoning'
    },
    2: {
        'target_audience': 'undergraduate students',
        'max_grade_level': 16,
        'simplification_level': 'some',
        'example_concepts': 'advanced concepts, domain-specific terminology'
    },
    1: {
        'target_audience': 'PhD-level researchers',
        'max_grade_level': 100,  # No limit
        'simplification_level': 'wording only',
        'example_concepts': 'cutting-edge research, specialized knowledge'
    },
    0: {
        'target_audience': 'domain experts',
        'max_grade_level': 100,  # No limit
        'simplification_level': 'wording only',
        'example_concepts': 'expert-level insights, professional practice'
    }
}


def load_json(filepath: Path) -> Any:
    """Load JSON file with error handling."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: Path, data: Any, indent: int = 2):
    """Save JSON file with pretty formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    print(f"Saved: {filepath}")


def calculate_flesch_kincaid(text: str) -> float:
    """
    Calculate Flesch-Kincaid grade level for text.

    Args:
        text: Text to analyze

    Returns:
        Grade level (e.g., 8.5 = 8th grade level)
    """
    if not HAS_TEXTSTAT:
        return 0.0  # Return 0 if library not available

    try:
        return textstat.flesch_kincaid_grade(text)
    except:
        return 0.0


def hash_question(question: str) -> str:
    """Create hash of question for tracking."""
    return hashlib.md5(question.encode()).hexdigest()[:8]


def get_simplification_prompt(level: int) -> str:
    """
    Get system prompt for simplification (Pass 1).

    Args:
        level: Question level (0-4)

    Returns:
        System prompt string
    """
    config = LEVEL_CONFIG[level]

    return f"""You are an expert educator simplifying questions for {config['target_audience']}.

Given a Wikipedia article and a complex question:
1. Simplify the question content to be age-appropriate for {config['target_audience']}
   - Simplification level: {config['simplification_level']}
   - Target concepts: {config['example_concepts']}
2. Simplify wording to be clear and concise
3. Convert any math notation to inline LaTeX using $...$ delimiters
   Examples:
   - x^2 → $x^2$ or $x^{{2}}$
   - 1/2 → $\\frac{{1}}{{2}}$
   - sqrt(x) → $\\sqrt{{x}}$
   - alpha → $\\alpha$
4. Maintain factual accuracy based on the article
5. Keep the correct answer the same (same letter: A, B, C, or D)
6. Ensure all 4 options are plausible
7. IMPORTANT: Do not lose essential content or change the core concept being tested

Return ONLY valid JSON (no markdown, no explanation):
{{
  "question": "simplified question text with LaTeX",
  "options": {{
    "A": "option text with LaTeX if needed",
    "B": "option text",
    "C": "option text",
    "D": "option text"
  }},
  "correct_answer": "A" or "B" or "C" or "D",
  "simplification_notes": "brief description of what changed",
  "content_preserved": true or false
}}"""


def get_generation_prompt(level: int) -> str:
    """
    Get system prompt for new question generation (Pass 2).

    Args:
        level: Question level (0-4)

    Returns:
        System prompt string
    """
    config = LEVEL_CONFIG[level]

    return f"""You are an expert educator creating NEW questions for {config['target_audience']}.

Given a Wikipedia article and concepts that should be tested:
1. Generate a NEW question (not a simplification) at the appropriate level
   - Target audience: {config['target_audience']}
   - Target concepts: {config['example_concepts']}
2. Test the same core concepts as the original
3. Use inline LaTeX for any math: $x^2$, $\\frac{{1}}{{2}}$, $\\sqrt{{x}}$, $\\alpha$
4. Maintain factual accuracy based on the article
5. Create 4 plausible options with one clearly correct answer

Return ONLY valid JSON (no markdown, no explanation):
{{
  "question": "new question text with LaTeX",
  "options": {{
    "A": "option text",
    "B": "option text",
    "C": "option text",
    "D": "option text"
  }},
  "correct_answer": "A" or "B" or "C" or "D",
  "generation_notes": "brief description of approach",
  "concepts_tested": ["concept 1", "concept 2"]
}}"""


def create_simplification_request(
    question: Dict[str, Any],
    article_text: str,
    level: int
) -> str:
    """
    Create user prompt for simplification (Pass 1).

    Args:
        question: Question dict with question, options, correct_answer
        article_text: Full Wikipedia article text
        level: Question level

    Returns:
        User prompt string
    """
    # Format options
    options_str = "\n".join([
        f"{key}: {value}"
        for key, value in question['options'].items()
    ])

    # Get concepts tested
    concepts = question.get('concepts_tested', [])
    concepts_str = "\n".join([f"- {c}" for c in concepts]) if concepts else "Not specified"

    return f"""Wikipedia Article Text:
{article_text}

---

Original Question:
{question['question']}

Options:
{options_str}

Correct Answer: {question['correct_answer']}

Concepts Tested:
{concepts_str}

Please simplify this question for the target audience while preserving the core concepts."""


def create_generation_request(
    question: Dict[str, Any],
    article_text: str,
    level: int
) -> str:
    """
    Create user prompt for new generation (Pass 2).

    Args:
        question: Original question dict
        article_text: Full Wikipedia article text
        level: Question level

    Returns:
        User prompt string
    """
    # Get concepts tested
    concepts = question.get('concepts_tested', [])
    concepts_str = "\n".join([f"- {c}" for c in concepts]) if concepts else "Core concepts from original question"

    config = LEVEL_CONFIG[level]

    return f"""Wikipedia Article Text:
{article_text}

---

Original concepts to test:
{concepts_str}

Target audience: {config['target_audience']}

Generate a NEW question that tests these concepts at the appropriate level."""


def call_gpt5_mini(
    client,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Call GPT-5-mini with retry logic.

    Args:
        client: OpenAI client
        system_prompt: System prompt
        user_prompt: User prompt
        max_retries: Maximum retry attempts

    Returns:
        Parsed JSON response or None if failed
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=1000,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            return result

        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON decode error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                print(f"  ❌ Failed to parse response after {max_retries} attempts")
                return None
        except Exception as e:
            print(f"  ⚠️  API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                print(f"  ❌ API call failed after {max_retries} attempts")
                return None

    return None


def validate_simplified_question(
    original: Dict[str, Any],
    simplified: Dict[str, Any],
    level: int
) -> Tuple[bool, str]:
    """
    Validate that simplification preserved essential content.

    Args:
        original: Original question dict
        simplified: Simplified question dict
        level: Question level

    Returns:
        (is_valid, reason) tuple
    """
    # Check required fields
    required = ['question', 'options', 'correct_answer']
    for field in required:
        if field not in simplified:
            return False, f"missing_field_{field}"

    # Check correct answer unchanged
    if original['correct_answer'] != simplified['correct_answer']:
        return False, "correct_answer_changed"

    # Check 4 options
    if len(simplified['options']) != 4:
        return False, f"wrong_option_count_{len(simplified['options'])}"

    # Check if LLM flagged content loss
    if not simplified.get('content_preserved', True):
        return False, "content_loss_flagged_by_llm"

    # Check readability appropriate for level (if textstat available)
    if HAS_TEXTSTAT and level in [4, 3, 2]:
        grade_level = calculate_flesch_kincaid(simplified['question'])
        max_grade = LEVEL_CONFIG[level]['max_grade_level']
        if grade_level > max_grade + 2:  # Allow 2 grade buffer
            return False, f"readability_too_high_{grade_level:.1f}_vs_{max_grade}"

    return True, "valid"


def simplify_question(
    question: Dict[str, Any],
    article_text: str,
    level: int,
    client
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """
    Attempt to simplify a question (Pass 1).

    Args:
        question: Original question dict
        article_text: Full Wikipedia article text
        level: Question level
        client: OpenAI client

    Returns:
        (simplified_question, status, reason) tuple
        status: 'success', 'retry', 'failed'
    """
    system_prompt = get_simplification_prompt(level)
    user_prompt = create_simplification_request(question, article_text, level)

    # Call API
    result = call_gpt5_mini(client, system_prompt, user_prompt)

    if result is None:
        return None, 'failed', 'api_error'

    # Validate result
    is_valid, reason = validate_simplified_question(question, result, level)

    if is_valid:
        # Add metadata
        result['source_article'] = question['source_article']
        result['x'] = question['x']
        result['y'] = question['y']
        result['level'] = level
        result['concepts_tested'] = question.get('concepts_tested', [])
        result['original_question_hash'] = hash_question(question['question'])

        return result, 'success', 'validated'
    else:
        return result, 'retry', reason


def generate_new_question(
    question: Dict[str, Any],
    article_text: str,
    level: int,
    client
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """
    Generate a new question at appropriate level (Pass 2).

    Args:
        question: Original question dict
        article_text: Full Wikipedia article text
        level: Question level
        client: OpenAI client

    Returns:
        (new_question, status, reason) tuple
        status: 'success', 'failed'
    """
    system_prompt = get_generation_prompt(level)
    user_prompt = create_generation_request(question, article_text, level)

    # Call API
    result = call_gpt5_mini(client, system_prompt, user_prompt)

    if result is None:
        return None, 'failed', 'api_error'

    # Validate result (use same validation but without content_preserved check)
    # Check required fields
    required = ['question', 'options', 'correct_answer']
    for field in required:
        if field not in result:
            return None, 'failed', f"missing_field_{field}"

    # Check 4 options
    if len(result['options']) != 4:
        return None, 'failed', f"wrong_option_count_{len(result['options'])}"

    # Check readability appropriate for level (if textstat available)
    if HAS_TEXTSTAT and level in [4, 3, 2]:
        grade_level = calculate_flesch_kincaid(result['question'])
        max_grade = LEVEL_CONFIG[level]['max_grade_level']
        if grade_level > max_grade + 2:  # Allow 2 grade buffer
            return None, 'failed', f"readability_too_high_{grade_level:.1f}_vs_{max_grade}"

    # Add metadata
    result['source_article'] = question['source_article']
    result['x'] = question['x']
    result['y'] = question['y']
    result['level'] = level
    result['concepts_tested'] = result.get('concepts_tested', question.get('concepts_tested', []))
    result['original_question_hash'] = hash_question(question['question'])

    return result, 'success', 'validated'


def load_articles(level: int, base_path: Path) -> Dict[str, str]:
    """
    Load Wikipedia articles for a level.

    Args:
        level: Question level
        base_path: Base directory path

    Returns:
        Dict mapping article title to full text
    """
    filepath = base_path / f'wikipedia_articles_level_{level}.json'

    if not filepath.exists():
        raise FileNotFoundError(f"Articles file not found: {filepath}")

    print(f"Loading articles from {filepath}...")
    data = load_json(filepath)

    articles = {}
    for article in data:
        title = article.get('title', '')
        text = article.get('text', '')
        if title and text:
            articles[title] = text

    print(f"  Loaded {len(articles)} articles")
    return articles


def simplify_level(
    level: int,
    pilot: Optional[int] = None,
    base_path: Path = Path('.')
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Simplify all questions for a level using OpenAI Batch API.

    Args:
        level: Question level (0-4)
        pilot: If set, only process this many questions
        base_path: Base directory path

    Returns:
        (simplified_questions, stats) tuple
    """
    print(f"\n{'='*60}")
    print(f"Simplifying Level {level} Questions")
    print(f"Target audience: {LEVEL_CONFIG[level]['target_audience']}")
    if pilot:
        print(f"PILOT MODE: Processing only {pilot} questions")
    print(f"{'='*60}\n")

    # Create OpenAI client
    client = create_openai_client()

    # Load questions
    questions_file = base_path / f'cell_questions_level_{level}.json'
    if not questions_file.exists():
        raise FileNotFoundError(f"Questions file not found: {questions_file}")

    print(f"Loading questions from {questions_file}...")
    questions_data = load_json(questions_file)
    all_questions = questions_data.get('questions', [])

    if pilot:
        all_questions = all_questions[:pilot]

    print(f"  Loaded {len(all_questions)} questions\n")

    # Load articles
    articles = load_articles(level, base_path)

    # Filter questions with missing articles and prepare batch requests
    batch_requests = []
    question_metadata = []  # Track original questions for later processing
    excluded_questions = []

    for i, question in enumerate(all_questions):
        article_title = question.get('source_article', '')
        if article_title not in articles:
            print(f"⚠️  Article '{article_title}' not found for question {i+1}, excluding...")
            excluded_questions.append({
                'original_question': question,
                'reason': 'article_not_found',
                'pass_1_attempt': None,
                'pass_2_attempt': None
            })
            continue

        # Get article text
        article_text = articles[article_title]

        # Create batch request for Pass 1 (simplification)
        user_prompt = create_simplification_request(question, article_text, level)

        batch_requests.append({
            'custom_id': f'q{i}_pass1',
            'user_prompt': user_prompt
        })

        # Store metadata for this question
        question_metadata.append({
            'index': i,
            'question': question,
            'article_text': article_text
        })

    print(f"Prepared {len(batch_requests)} batch requests for Pass 1\n")

    # Submit Pass 1 batch
    system_prompt = get_simplification_prompt(level)

    # Define JSON schema for structured output
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "simplified_question",
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
                    "correct_answer": {"type": "string"},
                    "simplification_notes": {"type": "string"},
                    "content_preserved": {"type": "boolean"}
                },
                "required": ["question", "options", "correct_answer", "simplification_notes", "content_preserved"],
                "additionalProperties": False
            }
        }
    }

    print("="*60)
    print("PASS 1: Submitting simplification batch")
    print("="*60)

    pass1_results = batch_with_cache(
        client=client,
        requests=batch_requests,
        system_prompt=system_prompt,
        description=f"Level {level} simplification (Pass 1)",
        model="gpt-5-nano",
        temperature=1.0,  # gpt-5-nano default is 1.0
        max_tokens=10000,  # Large limit for reasoning + output (gpt-5-nano uses reasoning tokens)
        response_format=response_format,
        poll_interval=60,
        timeout=3600  # 1 hour timeout
    )

    print(f"\n✓ Pass 1 batch complete: {len(pass1_results)} results\n")

    # Process Pass 1 results and identify questions needing Pass 2
    simplified_questions = []
    pass2_requests = []
    pass2_metadata = []

    stats = {
        'total_original': len(all_questions),
        'pass_1_success': 0,
        'pass_1_retry': 0,
        'pass_1_failed': 0,
        'pass_2_success': 0,
        'pass_2_failed': 0,
        'excluded': len(excluded_questions),
        'exclusion_reasons': defaultdict(int)
    }

    stats['exclusion_reasons']['article_not_found'] = len(excluded_questions)

    for i, metadata in enumerate(question_metadata):
        custom_id = f'q{metadata["index"]}_pass1'
        question = metadata['question']
        article_text = metadata['article_text']

        if custom_id not in pass1_results:
            print(f"⚠️  Question {metadata['index']+1}: No result from Pass 1, excluding...")
            excluded_questions.append({
                'original_question': question,
                'reason': 'pass_1_api_error',
                'pass_1_attempt': None,
                'pass_2_attempt': None
            })
            stats['pass_1_failed'] += 1
            stats['excluded'] += 1
            stats['exclusion_reasons']['pass_1_api_error'] += 1
            continue

        result = pass1_results[custom_id]

        # Validate result
        is_valid, reason = validate_simplified_question(question, result, level)

        if is_valid:
            # Add metadata
            result['source_article'] = question['source_article']
            result['x'] = question['x']
            result['y'] = question['y']
            result['level'] = level
            result['concepts_tested'] = question.get('concepts_tested', [])
            result['original_question_hash'] = hash_question(question['question'])

            simplified_questions.append(result)
            stats['pass_1_success'] += 1
            print(f"✅ Question {metadata['index']+1}: Pass 1 success ({reason})")
        else:
            # Needs Pass 2
            print(f"🔄 Question {metadata['index']+1}: Pass 1 needs retry ({reason}), scheduling Pass 2...")
            stats['pass_1_retry'] += 1

            # Create Pass 2 request
            user_prompt = create_generation_request(question, article_text, level)

            pass2_requests.append({
                'custom_id': f'q{metadata["index"]}_pass2',
                'user_prompt': user_prompt
            })

            pass2_metadata.append({
                'index': metadata['index'],
                'question': question,
                'pass_1_attempt': result,
                'pass_1_reason': reason
            })

    # Run Pass 2 if needed
    if pass2_requests:
        print(f"\n{'='*60}")
        print(f"PASS 2: Submitting generation batch for {len(pass2_requests)} questions")
        print(f"{'='*60}")

        system_prompt_pass2 = get_generation_prompt(level)

        # JSON schema for Pass 2
        response_format_pass2 = {
            "type": "json_schema",
            "json_schema": {
                "name": "generated_question",
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
                        "correct_answer": {"type": "string"},
                        "generation_notes": {"type": "string"},
                        "concepts_tested": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["question", "options", "correct_answer", "generation_notes", "concepts_tested"],
                    "additionalProperties": False
                }
            }
        }

        pass2_results = batch_with_cache(
            client=client,
            requests=pass2_requests,
            system_prompt=system_prompt_pass2,
            description=f"Level {level} generation (Pass 2)",
            model="gpt-5-nano",
            temperature=1.0,  # gpt-5-nano default is 1.0
            max_tokens=10000,  # Large limit for reasoning + output (gpt-5-nano uses reasoning tokens)
            response_format=response_format_pass2,
            poll_interval=60,
            timeout=3600  # 1 hour timeout
        )

        print(f"\n✓ Pass 2 batch complete: {len(pass2_results)} results\n")

        # Process Pass 2 results
        for metadata in pass2_metadata:
            custom_id = f'q{metadata["index"]}_pass2'
            question = metadata['question']

            if custom_id not in pass2_results:
                print(f"❌ Question {metadata['index']+1}: No result from Pass 2, excluding...")
                excluded_questions.append({
                    'original_question': question,
                    'reason': 'content_loss_both_passes',
                    'pass_1_attempt': metadata['pass_1_attempt'],
                    'pass_1_reason': metadata['pass_1_reason'],
                    'pass_2_attempt': None,
                    'pass_2_reason': 'api_error'
                })
                stats['pass_2_failed'] += 1
                stats['excluded'] += 1
                stats['exclusion_reasons']['content_loss_both_passes'] += 1
                continue

            result = pass2_results[custom_id]

            # Validate Pass 2 result
            # Check required fields
            required = ['question', 'options', 'correct_answer']
            is_valid = all(field in result for field in required) and len(result.get('options', {})) == 4

            # Check readability
            if is_valid and HAS_TEXTSTAT and level in [4, 3, 2]:
                grade_level = calculate_flesch_kincaid(result['question'])
                max_grade = LEVEL_CONFIG[level]['max_grade_level']
                if grade_level > max_grade + 2:
                    is_valid = False
                    reason = f"readability_too_high_{grade_level:.1f}_vs_{max_grade}"
                else:
                    reason = "validated"
            else:
                reason = "validated"

            if is_valid:
                # Add metadata
                result['source_article'] = question['source_article']
                result['x'] = question['x']
                result['y'] = question['y']
                result['level'] = level
                result['concepts_tested'] = result.get('concepts_tested', question.get('concepts_tested', []))
                result['original_question_hash'] = hash_question(question['question'])

                simplified_questions.append(result)
                stats['pass_2_success'] += 1
                print(f"✅ Question {metadata['index']+1}: Pass 2 success ({reason})")
            else:
                print(f"❌ Question {metadata['index']+1}: Pass 2 failed ({reason}), excluding...")
                excluded_questions.append({
                    'original_question': question,
                    'reason': 'content_loss_both_passes',
                    'pass_1_attempt': metadata['pass_1_attempt'],
                    'pass_1_reason': metadata['pass_1_reason'],
                    'pass_2_attempt': result,
                    'pass_2_reason': reason
                })
                stats['pass_2_failed'] += 1
                stats['excluded'] += 1
                stats['exclusion_reasons']['content_loss_both_passes'] += 1

    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary for Level {level}")
    print(f"{'='*60}")
    print(f"Total original questions: {stats['total_original']}")
    print(f"Pass 1 success: {stats['pass_1_success']}")
    print(f"Pass 1 retry needed: {stats['pass_1_retry']}")
    print(f"Pass 2 success: {stats['pass_2_success']}")
    print(f"Excluded: {stats['excluded']} ({stats['excluded']/stats['total_original']*100:.1f}%)")
    print(f"\nExclusion reasons:")
    for reason, count in sorted(stats['exclusion_reasons'].items()):
        print(f"  {reason}: {count}")
    print(f"\nTotal simplified questions: {len(simplified_questions)}")

    # Save excluded questions log
    if excluded_questions:
        notes_dir = base_path / 'notes'
        notes_dir.mkdir(exist_ok=True)
        excluded_file = notes_dir / f'excluded_questions_level_{level}.json'
        save_json(excluded_file, excluded_questions)

    return simplified_questions, stats


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Simplify questions using GPT-5-mini'
    )
    parser.add_argument(
        '--level',
        type=int,
        choices=[0, 1, 2, 3, 4],
        help='Level to simplify (0-4)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Simplify all levels'
    )
    parser.add_argument(
        '--pilot',
        type=int,
        help='Pilot mode: process only N questions'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('.'),
        help='Output directory (default: current directory)'
    )

    args = parser.parse_args()

    if not args.level and not args.all:
        parser.error("Must specify either --level or --all")

    if args.level and args.all:
        parser.error("Cannot specify both --level and --all")

    # Determine levels to process
    levels = [args.level] if args.level is not None else [4, 3, 2, 1, 0]

    # Process each level
    all_stats = {}

    for level in levels:
        try:
            simplified_questions, stats = simplify_level(
                level=level,
                pilot=args.pilot,
                base_path=args.output_dir
            )

            # Save simplified questions
            output_file = args.output_dir / f'cell_questions_level_{level}_simplified.json'

            output_data = {
                'questions': simplified_questions,
                'metadata': {
                    'level': level,
                    'target_audience': LEVEL_CONFIG[level]['target_audience'],
                    'total_original': stats['total_original'],
                    'total_simplified': len(simplified_questions),
                    'pass_1_success': stats['pass_1_success'],
                    'pass_2_success': stats['pass_2_success'],
                    'excluded': stats['excluded'],
                    'exclusion_reasons': dict(stats['exclusion_reasons']),
                    'simplification_date': datetime.now().isoformat(),
                    'api_model': 'gpt-5-mini',
                    'pilot_mode': args.pilot is not None,
                    'pilot_count': args.pilot
                }
            }

            save_json(output_file, output_data)

            all_stats[level] = stats

        except Exception as e:
            print(f"\n❌ Error processing level {level}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Print final summary
    print(f"\n{'='*60}")
    print(f"Final Summary")
    print(f"{'='*60}")
    for level, stats in all_stats.items():
        exclusion_rate = stats['excluded'] / stats['total_original'] * 100
        print(f"Level {level}: {len(simplified_questions)} questions, "
              f"{stats['excluded']} excluded ({exclusion_rate:.1f}%)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()