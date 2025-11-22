#!/usr/bin/env python3
"""
Disambiguate LaTeX from Currency Symbols

This script processes all questions in cell_questions.json to distinguish between
LaTeX math notation ($x^2$) and currency symbols ($5 billion).

Two-pass approach:
1. Pass 1 (automated): Identify all strings with >= 2 dollar signs as candidates
2. Pass 2 (LLM): Use GPT-5-nano to escape non-LaTeX dollar signs

Usage:
    python3 scripts/disambiguate_latex.py

Outputs:
    - cell_questions_parsed.json (disambiguated questions)
    - notes/latex_disambiguation_report.json (processing stats)
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()


def count_dollar_signs(text: str) -> int:
    """Count number of dollar signs in text."""
    return text.count('$')


def extract_all_strings(data: Dict) -> Dict[int, Tuple[str, List[str]]]:
    """
    Extract all question and option strings from cell_questions.json.

    Args:
        data: Loaded cell_questions.json data

    Returns:
        Dict mapping unique index -> (question_text, cell_coords, question_id)
        where strings have >= 2 dollar signs (candidate LaTeX)
    """
    candidates = {}
    idx = 0

    for cell in data.get('cells', []):
        cell_x = cell.get('x', 0)
        cell_y = cell.get('y', 0)

        for question in cell.get('questions', []):
            question_id = question.get('questionId', '')

            # Check question text
            question_text = question.get('question', '')
            if count_dollar_signs(question_text) >= 2:
                candidates[idx] = {
                    'type': 'question',
                    'text': question_text,
                    'cell_x': cell_x,
                    'cell_y': cell_y,
                    'question_id': question_id,
                    'option_key': None
                }
                idx += 1

            # Check option texts
            options = question.get('options', {})
            for option_key, option_text in options.items():
                if count_dollar_signs(option_text) >= 2:
                    candidates[idx] = {
                        'type': 'option',
                        'text': option_text,
                        'cell_x': cell_x,
                        'cell_y': cell_y,
                        'question_id': question_id,
                        'option_key': option_key
                    }
                    idx += 1

    return candidates


def disambiguate_string_batch(strings: List[str]) -> List[str]:
    """
    Use GPT-5-nano to disambiguate LaTeX from currency in a batch of strings.

    Args:
        strings: List of text strings with potential LaTeX/currency ambiguity

    Returns:
        List of disambiguated strings with non-LaTeX $ escaped as \\$
    """
    # Build prompt for batch processing
    examples = [
        {
            "input": "The GDP is $5.2 trillion but growth follows $x^2$ where $x$ is years.",
            "output": "The GDP is \\$5.2 trillion but growth follows $x^2$ where $x$ is years.",
            "explanation": "Currency phrase vs LaTeX math expression"
        },
        {
            "input": "Calculate $\\frac{1}{2}$ of $100 billion",
            "output": "Calculate $\\frac{1}{2}$ of \\$100 billion",
            "explanation": "LaTeX fraction vs currency amount with word 'billion'"
        },
        {
            "input": "If $a > b$ and costs $50, find $c = a + b$",
            "output": "If $a > b$ and costs \\$50, find $c = a + b$",
            "explanation": "LaTeX inequalities/equations vs standalone currency with 'costs'"
        },
        {
            "input": "Reserve $20$ of the $100$ seats for students",
            "output": "Reserve $20$ of the $100$ seats for students",
            "explanation": "Both are numbers in LaTeX delimiters for consistency, not currency"
        },
        {
            "input": "Admits $90$ students from Group A and $10$ from Group B",
            "output": "Admits $90$ students from Group A and $10$ from Group B",
            "explanation": "Numbers of students in LaTeX delimiters, not currency"
        }
    ]

    prompt = f"""You are a LaTeX disambiguation expert. Your task is to distinguish between LaTeX math notation and currency symbols.

CRITICAL RULES:
1. If a number is ALREADY wrapped in LaTeX delimiters (like $20$ or $100$), keep it unchanged - it's intentional LaTeX formatting
2. Only escape $ when it appears BEFORE a number WITHOUT closing delimiter (like $5 billion, $100 million, $1.2 trillion)
3. LaTeX delimiters come in pairs: $...$ or $$...$$
4. Currency $ is typically followed by space or number and currency words (billion, million, trillion, thousand)
5. When text has "costs $50" or "$50 fee" (unpaired $), that's currency - escape it as \\$50
6. Mathematical expressions ($x^2$, $\\frac{{1}}{{2}}$, $a > b$, $Q_{{d}}=Q_{{s}}$) always keep delimiters
7. Preserve all other text exactly as-is

Key distinction:
- "$20$ students" = LaTeX formatting (both $ are delimiters) → KEEP AS IS
- "$20 million" = Currency (single $ before amount) → ESCAPE as \\$20 million
- "costs $50" = Currency (unpaired $) → ESCAPE as costs \\$50
- "$x^2$ growth" = LaTeX math → KEEP AS IS

Examples:
{json.dumps(examples, indent=2)}

Now process these strings:
{json.dumps(strings, indent=2)}

Return a JSON array of disambiguated strings in the same order. Only escape unpaired $ symbols that represent currency."""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a LaTeX and currency disambiguation expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=1.0,
            max_tokens=2000
        )

        result = json.loads(response.choices[0].message.content)

        # Handle different possible response formats
        if 'results' in result:
            return result['results']
        elif 'disambiguated' in result:
            return result['disambiguated']
        elif 'strings' in result:
            return result['strings']
        elif isinstance(result, list):
            return result
        else:
            # Fallback: return original strings if format unexpected
            print(f"Warning: Unexpected response format: {result}")
            return strings

    except Exception as e:
        print(f"Error in batch disambiguation: {e}")
        return strings


def apply_disambiguation(data: Dict, candidates: Dict[int, Dict],
                        disambiguated: Dict[int, str]) -> Dict:
    """
    Apply disambiguated strings back to the data structure.

    Args:
        data: Original cell_questions.json data
        candidates: Candidate strings that were processed
        disambiguated: Mapping of candidate index -> disambiguated string

    Returns:
        Updated data structure with disambiguated strings
    """
    # Create lookup by (cell_x, cell_y, question_id, type, option_key)
    updates = {}
    for idx, info in candidates.items():
        if idx in disambiguated:
            key = (info['cell_x'], info['cell_y'], info['question_id'],
                   info['type'], info['option_key'])
            updates[key] = disambiguated[idx]

    # Apply updates
    for cell in data.get('cells', []):
        cell_x = cell.get('x', 0)
        cell_y = cell.get('y', 0)

        for question in cell.get('questions', []):
            question_id = question.get('questionId', '')

            # Update question text
            key = (cell_x, cell_y, question_id, 'question', None)
            if key in updates:
                question['question'] = updates[key]

            # Update option texts
            options = question.get('options', {})
            for option_key in options.keys():
                key = (cell_x, cell_y, question_id, 'option', option_key)
                if key in updates:
                    options[option_key] = updates[key]

    return data


def main():
    print("=" * 80)
    print("LATEX DISAMBIGUATION")
    print("=" * 80)
    print()

    # Load input file
    input_file = Path('cell_questions.json')
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    print(f"Loading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_cells = len(data.get('cells', []))
    total_questions = sum(len(cell.get('questions', [])) for cell in data.get('cells', []))
    print(f"  Loaded {total_questions} questions across {total_cells} cells")
    print()

    # Pass 1: Extract candidate strings (>= 2 dollar signs)
    print("Pass 1: Identifying candidate strings (>= 2 dollar signs)")
    candidates = extract_all_strings(data)
    print(f"  Found {len(candidates)} candidate strings needing disambiguation")
    print()

    if len(candidates) == 0:
        print("No candidates found - all strings are unambiguous")
        # Still create output file as copy
        output_file = Path('cell_questions_parsed.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Created {output_file} (no changes needed)")
        return 0

    # Pass 2: Disambiguate using GPT-5-nano
    print("Pass 2: Disambiguating with GPT-5-nano")
    print(f"  Processing in batches of 20...")

    batch_size = 20
    disambiguated = {}

    # Sort candidates by index for consistent batching
    sorted_indices = sorted(candidates.keys())

    for i in range(0, len(sorted_indices), batch_size):
        batch_indices = sorted_indices[i:i + batch_size]
        batch_strings = [candidates[idx]['text'] for idx in batch_indices]

        print(f"  Batch {i // batch_size + 1}/{(len(sorted_indices) + batch_size - 1) // batch_size}: " +
              f"Processing {len(batch_strings)} strings...")

        # Disambiguate batch
        result_strings = disambiguate_string_batch(batch_strings)

        # Store results
        for idx, result in zip(batch_indices, result_strings):
            disambiguated[idx] = result

        # Rate limiting
        if i + batch_size < len(sorted_indices):
            time.sleep(0.5)

    print(f"  ✓ Disambiguated {len(disambiguated)} strings")
    print()

    # Apply disambiguation to data
    print("Applying disambiguation to data structure...")
    updated_data = apply_disambiguation(data, candidates, disambiguated)

    # Save output
    output_file = Path('cell_questions_parsed.json')
    print(f"Saving: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2)
    print(f"  ✓ Saved {output_file}")
    print()

    # Save report
    report = {
        'total_questions': total_questions,
        'total_cells': total_cells,
        'candidates_found': len(candidates),
        'candidates_processed': len(disambiguated),
        'sample_candidates': [
            {
                'index': idx,
                'original': candidates[idx]['text'],
                'disambiguated': disambiguated.get(idx, candidates[idx]['text']),
                'type': candidates[idx]['type'],
                'question_id': candidates[idx]['question_id']
            }
            for idx in sorted(candidates.keys())[:10]  # First 10 samples
        ]
    }

    report_file = Path('notes/latex_disambiguation_report.json')
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"Report: {report_file}")
    print()

    # Summary
    print("=" * 80)
    print("✓ DISAMBIGUATION COMPLETE")
    print("=" * 80)
    print(f"Candidates processed: {len(disambiguated)}")
    print(f"Output: {output_file}")
    print(f"Report: {report_file}")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
