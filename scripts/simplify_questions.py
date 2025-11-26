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
# NOTE: Reading levels calibrated DOWN by ~2 grades to account for generation overshoot
LEVEL_CONFIG = {
    4: {
        'target_audience': 'elementary school students (ages 8-10, 3rd grade)',
        'max_grade_level': 5,  # Lowered from 8 to account for overshoot
        'simplification_level': 'major',
        'example_concepts': 'basic scientific concepts, simple cause and effect'
    },
    3: {
        'target_audience': 'middle school students (ages 11-13, 6th grade)',
        'max_grade_level': 9,  # Lowered from 12 to account for overshoot
        'simplification_level': 'moderate',
        'example_concepts': 'intermediate scientific principles, multi-step reasoning'
    },
    2: {
        'target_audience': 'high school students (ages 14-17, 9th grade)',
        'max_grade_level': 12,  # Lowered from 16 to account for overshoot
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

    # Add readability examples for levels that need simplification
    readability_guidance = ""
    if level == 4:  # Middle school
        readability_guidance = """

READABILITY TARGET: Flesch-Kincaid grade level 3-5 (elementary school reading level)

CRITICAL BREVITY RULES - STRICTLY ENFORCE THESE:
1. Each sentence MUST be under 15 words - count carefully!
2. Questions: 1 sentence only (max 2 if absolutely necessary)
3. Answer options: 1 short sentence each (under 15 words)
4. NO compound sentences with "and," "but," "so" connecting clauses
5. NO parenthetical additions like "(both known and unknown)"
6. NO multi-clause structures like "which explains why..."
7. Use ONLY simple subject-verb-object sentences

Writing Rules for Elementary School (ages 8-10, 3rd grade):
- Use simple, everyday words - NO academic vocabulary
- Use active voice: "The brain sends signals" not "Signals are sent"
- One idea per sentence - no exceptions
- Use concrete examples: "brain cells" not "neurons"
- Avoid ALL technical terms: "systematic," "hierarchical," "faceted," "contingent"

EXAMPLES SHOWING COMMON MISTAKES TO AVOID:

Example 1 - Too many clauses:
❌ BAD (18 words, Grade 12): "Long-term structures set up opportunities and weak spots, and sudden events trigger changes past tipping points."
✅ GOOD (13 words, Grade 4): "Big events can cause change when conditions are right for it."

Example 2 - Academic vocabulary:
❌ BAD (23 words, Grade 18): "Why does using faceted classification with modern information technology help many different users and search tasks more than using one fixed hierarchical taxonomy?"
✅ GOOD (14 words, Grade 5): "Why does sorting things many ways help more than sorting just one way?"

Example 3 - Original good examples:
❌ BAD (Grade 14): "Why do emergent properties of the brain, such as patterns of learning, arise from interactions among neurons rather than being localized in a single neuron?"
✅ GOOD (Grade 4): "Why does learning need many brain cells working together instead of just one brain cell?"

Example 4:
❌ BAD (Grade 15): "How does multilevel integration and communication across cells and tissues enable a coherent physiological response to a perturbation?"
✅ GOOD (Grade 5): "When something bothers your body, how do different parts work together to fix it?"

Example 5:
❌ BAD (Grade 13): "The implementation of recursive algorithms necessitates consideration of computational complexity."
✅ GOOD (Grade 5): "When a computer repeats the same steps over and over, you need to think about how long it will take."""
    elif level == 3:  # High school → Middle school
        readability_guidance = """

READABILITY TARGET: Flesch-Kincaid grade level 6-9 (middle school reading level)

Writing Rules for Middle School (ages 11-13, 6th grade level):
- BREVITY: Questions must be 1-2 sentences maximum
- BREVITY: Answer choices must be short phrases or single sentences, max 2 sentences
- Keep sentences clear and under 20 words when possible
- Use intermediate-level vocabulary - avoid overly technical terms
- Break complex sentences into two shorter sentences
- Explain technical terms when necessary"""
    elif level == 2:  # Undergraduate → High school
        readability_guidance = """

READABILITY TARGET: Flesch-Kincaid grade level 9-12 (high school reading level)

Writing Rules for High School (ages 14-17, 9th grade level):
- BREVITY: Questions should be 1-2 sentences when possible
- BREVITY: Answer choices should be concise, max 2 sentences
- Use clear, direct language
- Technical terms are acceptable but should be explained in context
- Maintain precision while being concise"""

    return f"""You are an expert educator simplifying questions for {config['target_audience']}.
{readability_guidance}

Given a Wikipedia article and a complex question:
1. Simplify the question content to be age-appropriate for {config['target_audience']}
   - Simplification level: {config['simplification_level']}
   - Target concepts: {config['example_concepts']}
2. Simplify wording to be clear and concise - FOLLOW THE WRITING RULES ABOVE
3. Convert any math notation to inline LaTeX using $...$ delimiters
   - The ENTIRE math expression must be enclosed: $x^2$, $\\frac{{1}}{{2}}$, $\\sqrt{{x}}$, $\\alpha$
   - Do NOT partially enclose: "$x$^2" is WRONG, "$x^2$" is CORRECT
   - Examples: x^2 → $x^2$, 1/2 → $\\frac{{1}}{{2}}$, sqrt(x) → $\\sqrt{{x}}$
4. CRITICAL - LaTeX Dollar Sign Escaping:
   - When writing currency amounts, ALWAYS escape the dollar sign as \\$ to prevent LaTeX rendering conflicts
   - Examples: "$200 million" → "\\$200 million", "GDP of $10,000" → "GDP of \\$10,000"
   - Only use unescaped $ for actual math expressions like $x^2$ or $\\frac{{1}}{{2}}$
   - Physical unit counts are NOT currency: "10,000 cars" stays as plain text
5. Maintain factual accuracy based on the article
6. Keep the correct answer the same (same letter: A, B, C, or D)
7. Ensure all 4 options are plausible
8. IMPORTANT: Do not lose essential content or change the core concept being tested

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

    # Add readability examples for levels that need simplification
    readability_guidance = ""
    if level == 4:  # Elementary school
        readability_guidance = """

READABILITY TARGET: Flesch-Kincaid grade level 3-5 (elementary school reading level)

CRITICAL BREVITY RULES - STRICTLY ENFORCE THESE:
1. Each sentence MUST be under 15 words - count carefully!
2. Questions: 1-2 sentences maximum
3. Answer options: 1 short sentence each (under 15 words)
4. NO compound sentences with "and," "but," "so" connecting clauses
5. NO parenthetical additions like "(both known and unknown)"
6. NO multi-clause structures like "which explains why..."
7. Use ONLY simple subject-verb-object sentences

Writing Rules for Elementary School (ages 8-10, 3rd grade):
- Use simple, everyday words - NO academic vocabulary
- Use active voice: "The mouse runs" not "Running is done by the mouse"
- One simple idea per sentence - no exceptions
- Ask about specific examples or experiments, not general principles
- Use concrete, relatable scenarios from daily life
- Avoid ALL technical terms: "systematic," "hierarchical," "faceted," "contingent"

EXAMPLES OF GOOD ELEMENTARY SCHOOL QUESTIONS:

Example 1 (Biology) - Concrete scenario, simple cause-effect:
"A scientist removes part of a mouse's brain. The mouse can still see and hear. But it cannot remember where it stored food yesterday. What does this tell us about the brain?"
(Grade 5 - 4 short sentences, each under 15 words)

Example 2 (Physics) - Everyday scenario, simple question:
"You drop a ball from a ladder. It bounces back up. But it does not go as high as before. Where did some of the energy go?"
(Grade 5 - 4 short sentences, clear and simple)

Example 3 (Systems thinking) - Relatable analogy:
"A school club has three people. One makes rules. Another checks if rules are followed. The third manages money. Why does splitting jobs help the club work better?"
(Grade 5 - short simple sentences)

Example 4 (Decision theory) - Simple numbers, relatable choice, LaTeX escaping:
"Sam can pick two choices. Choice A: Get \\$10 for sure. Choice B: Flip a coin. Heads gets \\$25. Tails gets \\$0. Most people pick A even though B has a higher average. Why?"
(Grade 5 - broken into very short sentences, dollar signs properly escaped as \\$)"""
    elif level == 3:  # High school → Middle school
        readability_guidance = """

READABILITY TARGET: Flesch-Kincaid grade level 6-9 (middle school reading level)

Writing Rules for Middle School (ages 11-13, 6th grade level):
- BREVITY: Questions must be 1-2 sentences maximum
- BREVITY: Answer choices must be short phrases or single sentences, max 2 sentences
- Use clear scenarios or examples
- Keep sentences under 20 words when possible
- Use intermediate-level vocabulary
- Avoid overly technical terms - explain when necessary"""
    elif level == 2:  # Undergraduate → High school
        readability_guidance = """

READABILITY TARGET: Flesch-Kincaid grade level 9-12 (high school reading level)

Writing Rules for High School (ages 14-17, 9th grade level):
- BREVITY: Questions should be 1-2 sentences when possible
- BREVITY: Answer choices should be concise, max 2 sentences
- Use clear academic language
- Technical terms are acceptable but should be explained in context
- Can use multi-step reasoning but keep it clear"""

    return f"""You are an expert educator creating NEW questions for {config['target_audience']}.
{readability_guidance}

Given a Wikipedia article and concepts that should be tested:
1. Generate a NEW question (not a simplification) at the appropriate level
   - Target audience: {config['target_audience']}
   - Target concepts: {config['example_concepts']}
   - FOLLOW THE WRITING RULES AND EXAMPLES ABOVE
2. Test the same core concepts as the original
3. Use concrete scenarios and examples (not abstract explanations)
4. Use inline LaTeX for any math
   - The ENTIRE math expression must be enclosed: $x^2$, $\\frac{{1}}{{2}}$, $\\sqrt{{x}}$, $\\alpha$
   - Do NOT partially enclose: "$x$^2" is WRONG, "$x^2$" is CORRECT
5. CRITICAL - LaTeX Dollar Sign Escaping:
   - When writing currency amounts, ALWAYS escape the dollar sign as \\$ to prevent LaTeX rendering conflicts
   - Examples: "$200 million" → "\\$200 million", "GDP of $10,000" → "GDP of \\$10,000"
   - Only use unescaped $ for actual math expressions like $x^2$ or $\\frac{{1}}{{2}}$
   - Physical unit counts are NOT currency: "10,000 cars" stays as plain text
6. Maintain factual accuracy based on the article
7. Create 4 plausible options with one clearly correct answer

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
        model="gpt-5-mini",
        temperature=1.0,
        max_tokens=10000,
        response_format=response_format,
        poll_interval=60
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
            model="gpt-5-mini",
            temperature=1.0,
            max_tokens=10000,
            response_format=response_format_pass2,
            poll_interval=60
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
                if grade_level > max_grade + 4:
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