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
            "explanation": "Both are numbers in LaTeX delimiters (counts, not currency)"
        },
        {
            "input": "Admits $90$ students from Group A and $10$ from Group B",
            "output": "Admits $90$ students from Group A and $10$ from Group B",
            "explanation": "Numbers of students in LaTeX delimiters, not currency"
        },
        {
            "input": "GDP per capita of $10{,}000$. Government has $100\\text{ million}$ per year",
            "output": "GDP per capita of \\$10{,}000. Government has \\$100\\text{ million} per year",
            "explanation": "Even in LaTeX delimiters, numbers with currency context should be escaped"
        },
        {
            "input": "Budget of $60M$ for the $30\\text{M}$ facility",
            "output": "Budget of \\$60M for the \\$30\\text{M} facility",
            "explanation": "M/B/K suffixes indicate currency even in LaTeX delimiters"
        }
    ]

    prompt = f"""You are a LaTeX disambiguation expert. Your task is to distinguish between LaTeX math notation and currency symbols.

CRITICAL RULES:
1. Numbers used as COUNTS in LaTeX delimiters (like $20$ students, $100$ seats) → KEEP AS IS
2. Numbers representing MONEY, even in LaTeX delimiters, must be escaped:
   - Currency amounts: $10{{,}}000$, $100\\text{{ million}}$, $60M$, $30B$ → ESCAPE as \\$
   - Look for context: "GDP", "budget", "costs", "million", "billion", "M", "B", "K"
3. Mathematical expressions always keep delimiters: $x^2$, $\\frac{{1}}{{2}}$, $a > b$, $Q_{{d}}=Q_{{s}}$
4. Percentages and pure numbers in LaTeX are NOT currency: $60\\%$, $0.90$, $10\\%$ → KEEP AS IS
5. Unpaired $ before numbers is always currency: $5 billion, $50 → ESCAPE as \\$

Decision tree:
- Is it math (variables, operators, fractions)? → KEEP delimiters
- Is it a percentage ($60\\%$) or decimal ($0.90$)? → KEEP delimiters
- Is it a count ($20$ students, $100$ seats)? → KEEP delimiters
- Is it money (has million/billion/M/B/K or GDP/budget/cost context)? → ESCAPE as \\$
- Is it unpaired $ before a number? → ESCAPE as \\$

Examples:
{json.dumps(examples, indent=2)}

Now process these strings:
{json.dumps(strings, indent=2)}

Return a JSON array of disambiguated strings in the same order. Escape $ for currency, keep $ for math/counts/percentages."""

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
