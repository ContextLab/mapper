#!/usr/bin/env python3
"""
Manual Test of LaTeX Disambiguation with Both LaTeX and Currency

Tests the prompt on hand-crafted examples that mix LaTeX and currency.
"""

import json
from openai import OpenAI

client = OpenAI()


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
        elif 'output' in result:
            return result['output']
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
    print("MANUAL LaTeX DISAMBIGUATION TEST")
    print("=" * 80)
    print()

    # Test cases that mix LaTeX and currency
    test_cases = [
        # Should remain unchanged (properly delimited LaTeX)
        "Reserve $20$ of the $100$ seats for Group B",
        "Admits $90$ students from Group A and $10$ from Group B",
        "Calculate $\\frac{1}{2}$ of total enrollment",
        "When $Q_{d}=Q_{s}$ the market clears",
        "Growth follows $x^2$ where $x$ is years",

        # Should be escaped (currency)
        "The vaccine costs $200 per person",
        "GDP is $5.2 trillion",
        "Budget of $100 million per year",
        "Enrollment fee is $50",
        "The town has $10,000 residents",

        # Mixed: LaTeX should stay, currency should be escaped
        "Calculate $\\frac{1}{2}$ of $100 billion",
        "If $a > b$ and costs $50, find $c$",
        "Reserve $20$ seats at $50 each",
        "When $x=10$ the cost is $1,000",
    ]

    print(f"Testing {len(test_cases)} cases...")
    print()

    results = disambiguate_batch(test_cases)

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    for i, (original, result) in enumerate(zip(test_cases, results), 1):
        changed = original != result
        print(f"--- Test Case {i} ---")
        print(f"ORIGINAL:     {original}")
        print(f"RESULT:       {result}")
        print(f"CHANGED:      {'YES' if changed else 'NO'}")
        if changed:
            print(f"STATUS:       {'✓ CORRECT' if check_correctness(i, original, result) else '✗ INCORRECT'}")
        else:
            print(f"STATUS:       {'✓ CORRECT' if check_correctness(i, original, result) else '✗ INCORRECT'}")
        print()

    print("=" * 80)


def check_correctness(case_num, original, result):
    """Check if the result is correct based on expected behavior."""
    # Cases 1-5: Should remain unchanged
    if case_num <= 5:
        return original == result

    # Cases 6-10: Should have currency escaped
    elif case_num <= 10:
        return result != original and '\\$' in result

    # Cases 11-14: Mixed, should have some changes
    else:
        return result != original and '\\$' in result


if __name__ == '__main__':
    main()
