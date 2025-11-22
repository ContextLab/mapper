#!/usr/bin/env python3
"""
Test LaTeX Disambiguation on First 20 Candidates

This script tests the disambiguation logic on the first 20 candidate strings
from cell_questions.json and outputs the results for manual inspection.
"""

import json
import sys
from pathlib import Path
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()


def count_dollar_signs(text: str) -> int:
    """Count number of dollar signs in text."""
    return text.count('$')


def extract_first_n_candidates(data: dict, n: int = 20) -> list:
    """Extract first N candidate strings (>= 2 dollar signs)."""
    candidates = []
    count = 0

    for cell in data.get('cells', []):
        if count >= n:
            break

        for question in cell.get('questions', []):
            if count >= n:
                break

            # Check question text
            question_text = question.get('question', '')
            if count_dollar_signs(question_text) >= 2:
                candidates.append({
                    'type': 'question',
                    'text': question_text,
                    'question_id': question.get('questionId', ''),
                })
                count += 1
                if count >= n:
                    break

            # Check options
            options = question.get('options', {})
            for option_key, option_text in options.items():
                if count >= n:
                    break
                if count_dollar_signs(option_text) >= 2:
                    candidates.append({
                        'type': 'option',
                        'text': option_text,
                        'question_id': question.get('questionId', ''),
                        'option_key': option_key
                    })
                    count += 1

    return candidates


def disambiguate_batch(strings: list) -> list:
    """Use GPT-4o-mini to disambiguate a batch of strings."""
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
            model="gpt-4o-mini",
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
            print(f"Warning: Unexpected response format: {result}")
            return strings

    except Exception as e:
        print(f"Error: {e}")
        return strings


def main():
    print("=" * 80)
    print("LATEX DISAMBIGUATION TEST (First 20 Candidates)")
    print("=" * 80)
    print()

    # Load cell_questions.json
    input_file = Path('cell_questions.json')
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    print(f"Loading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print()

    # Extract first 20 candidates
    print("Extracting first 20 candidate strings...")
    candidates = extract_first_n_candidates(data, n=20)
    print(f"Found {len(candidates)} candidates")
    print()

    if len(candidates) == 0:
        print("No candidates found!")
        return 0

    # Get just the text strings
    strings = [c['text'] for c in candidates]

    # Disambiguate
    print("Disambiguating with GPT-4o-mini...")
    print()
    disambiguated = disambiguate_batch(strings)

    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    for i, (candidate, original, result) in enumerate(zip(candidates, strings, disambiguated)):
        print(f"--- Candidate {i+1} ({candidate['type']}) ---")
        print(f"Question ID: {candidate['question_id']}")
        if candidate['type'] == 'option':
            print(f"Option: {candidate['option_key']}")
        print()
        print(f"ORIGINAL:")
        print(f"  {original}")
        print()
        print(f"DISAMBIGUATED:")
        print(f"  {result}")
        print()

        # Show diff if changed
        if original != result:
            print(f"CHANGED: YES")
            # Show dollar sign positions
            orig_dollars = [i for i, c in enumerate(original) if c == '$']
            result_dollars = [i for i, c in enumerate(result) if c == '$']
            print(f"  Original $ positions: {orig_dollars}")
            print(f"  Result $ positions: {result_dollars}")
        else:
            print(f"CHANGED: NO")
        print()
        print("-" * 80)
        print()

    # Save results to file for inspection
    output = {
        'total_candidates': len(candidates),
        'candidates': [
            {
                'index': i,
                'type': c['type'],
                'question_id': c['question_id'],
                'option_key': c.get('option_key'),
                'original': orig,
                'disambiguated': result,
                'changed': orig != result
            }
            for i, (c, orig, result) in enumerate(zip(candidates, strings, disambiguated))
        ]
    }

    output_file = Path('notes/latex_test_results.json')
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {output_file}")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
