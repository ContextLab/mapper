#!/usr/bin/env python3
"""
Simple LaTeX Disambiguation Test with Hand-Crafted Examples

Tests specifically on the problematic cases identified by the user.
"""

import json
from openai import OpenAI

client = OpenAI()


def disambiguate_single(text: str) -> str:
    """Test disambiguation on a single string."""
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
            "output": "GDP per capita of \\$10{,}000. Government has \\$100 million per year",
            "explanation": "Currency in LaTeX: escape BOTH delimiters AND remove \\text{} (it only works inside math mode)"
        },
        {
            "input": "Budget of $60M$ for the $30\\text{M}$ facility",
            "output": "Budget of \\$60M for the \\$30M facility",
            "explanation": "M/B/K suffixes indicate currency; escape delimiters AND remove \\text{} command"
        },
        {
            "input": "A company must make 10,000 toy cars. Each costs $50 to produce.",
            "output": "A company must make 10,000 toy cars. Each costs \\$50 to produce.",
            "explanation": "10,000 toy cars is a count (physical units), $50 is currency"
        }
    ]

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

Now process this string:
"{text}"

Return ONLY the disambiguated string, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a LaTeX and currency disambiguation expert. Return only the disambiguated string."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            max_tokens=1000
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error: {e}")
        return text


def main():
    print("=" * 80)
    print("SIMPLE LATEX DISAMBIGUATION TEST")
    print("=" * 80)
    print()

    # Test cases specifically identified by the user
    test_cases = [
        # Should escape unpaired currency
        "A vaccine costs $200 per person.",

        # Should escape all currency references
        "Cost per QALY = $200/0.01 = $20,000",

        # Should keep counts but escape the currency amount at the end
        "Reserve $20$ of the $100$ seats and pay $50 deposit",

        # The problematic Example 17 case - GDP and budget in LaTeX delimiters
        "Country has GDP per capita of $10{,}000$. Government has $100\\text{ million}$ per year",

        # Mixed: percentages should stay, GDP should be escaped
        "North has $60\\%$ enrollment. GDP is $10{,}000$",

        # Count vs currency with M suffix
        "Admits $90$ students with a budget of $60M$",

        # NEW: The toy car case - physical units should NOT be treated as currency
        "A toy company must make 10,000 toy cars. Each costs $50 to produce.",

        # NEW: Test mismatched delimiter fix - both delimiters should be escaped together
        "Country has GDP per capita of $10{,}000$. Government has $100\\text{ million}$ per year",
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}:")
        print(f"ORIGINAL: {test}")
        result = disambiguate_single(test)
        print(f"RESULT:   {result}")
        print(f"CHANGED:  {'YES' if result != test else 'NO'}")
        print()
        print("-" * 80)
        print()

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
