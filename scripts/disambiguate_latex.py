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
            "explanation": "Both are numbers in LaTeX delimiters (counts, not currency)"
        },
        {
            "input": "Admits $90$ students from Group A and $10$ from Group B",
            "output": "Admits $90$ students from Group A and $10$ from Group B",
            "explanation": "Numbers of students in LaTeX delimiters, not currency"
        },
        {
            "input": "GDP per capita of $10{{,}}000$. Government has $100\\text{{ million}}$ per year",
            "output": "GDP per capita of \\$10{{,}}000. Government has \\$100 million per year",
            "explanation": "Currency in LaTeX: escape BOTH delimiters AND remove \\text{{}} (it only works inside math mode)"
        },
        {
            "input": "Budget of $60M$ for the $30\\text{{M}}$ facility",
            "output": "Budget of \\$60M for the \\$30M facility",
            "explanation": "M/B/K suffixes indicate currency; escape delimiters AND remove \\text{{}} command"
        },
        {
            "input": "A company must make 10,000 toy cars. Each costs $50 to produce.",
            "output": "A company must make 10,000 toy cars. Each costs \\$50 to produce.",
            "explanation": "10,000 toy cars is a count (physical units), $50 is currency"
        }
    ]

    # Use a unique delimiter that won't appear in the text
    delimiter = "###ENDSTRING###"

    prompt = f"""You are a LaTeX disambiguation expert. Your task is to distinguish between LaTeX math notation and currency symbols.

CRITICAL RULES:
1. Numbers used as COUNTS in LaTeX delimiters (like $20$ students, $100$ seats) → KEEP AS IS
2. Numbers representing MONEY, even in LaTeX delimiters, must be escaped:
   - Currency amounts: $10{{,}}000$, $100\\text{{ million}}$, $60M$, $30B$ → ESCAPE as \\$
   - Look for context: "GDP", "budget", "costs", "million", "billion", "M", "B", "K"
   - BUT if followed by physical units (cars, people, items, units, etc.), it's a COUNT not money
   - IMPORTANT: When escaping currency in LaTeX delimiters, escape BOTH delimiters → \\$10{{,}}000 (NOT \\$10{{,}}000$)
   - If removing delimiters, also remove \\text{{}} commands (they only work in math mode) → \\$100 million
3. Mathematical expressions always keep delimiters: $x^2$, $\\frac{{1}}{{2}}$, $a > b$, $Q_{{d}}=Q_{{s}}$
4. Percentages and pure numbers in LaTeX are NOT currency: $60\\%$, $0.90$, $10\\%$ → KEEP AS IS
5. Unpaired $ before numbers is always currency: $5 billion, $50 → ESCAPE as \\$
6. Plain numbers with commas followed by physical units are COUNTS: 10,000 cars, 5,000 people → LEAVE UNCHANGED
7. NEVER create mismatched delimiters: If you escape one $, escape the matching $ too
8. NEVER leave \\text{{}} outside math delimiters: it only renders inside $...$ → convert to plain text

Decision tree:
- Is it math (variables, operators, fractions)? → KEEP delimiters
- Is it a percentage ($60\\%$) or decimal ($0.90$)? → KEEP delimiters
- Is it a count ($20$ students, $100$ seats, 10,000 cars)? → KEEP delimiters (or leave plain)
- Is it money (has million/billion/M/B/K or GDP/budget/cost context)? → ESCAPE as \\$ (escape BOTH delimiters!)
- Does it have physical unit words (cars, people, items, units)? → NOT currency, leave alone
- Is it unpaired $ before a number? → ESCAPE as \\$

Examples:
{json.dumps(examples, indent=2)}

Now process these {len(strings)} strings. Return ONLY the disambiguated strings, separated by the delimiter "{delimiter}", in the same order as input.

IMPORTANT: Each string can contain multiple lines. Use ONLY "{delimiter}" to separate strings, not newlines.

INPUT STRINGS:
{delimiter.join(strings)}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a LaTeX and currency disambiguation expert. Return only the disambiguated strings, separated by {delimiter}."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            max_tokens=8000
        )

        # Parse delimiter-separated response
        result_text = response.choices[0].message.content.strip()
        result_strings = result_text.split(delimiter)

        # Clean up strings
        result_strings = [s.strip() for s in result_strings if s.strip()]

        # Verify we got the right number of results
        if len(result_strings) != len(strings):
            print(f"Warning: Expected {len(strings)} results, got {len(result_strings)}. Using original strings.")
            return strings

        return result_strings

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
