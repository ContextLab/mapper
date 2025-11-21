#!/usr/bin/env python3
"""
Add Readability Scores to Questions

This script adds Flesch Reading Ease and Flesch-Kincaid Grade Level scores
to all questions in cell_questions.json. These metrics will be used for
adaptive question sequencing based on user performance.

Usage:
    python3 scripts/add_readability_scores.py

Outputs:
    - Updates cell_questions.json in place (creates backup first)
    - Prints summary statistics
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import textstat
    HAS_TEXTSTAT = True
except ImportError:
    print("ERROR: textstat not installed")
    print("Install with: pip install textstat")
    sys.exit(1)


def strip_latex(text: str) -> str:
    """
    Remove LaTeX notation from text for readability analysis.

    LaTeX like $x^2$ or $$formula$$ should not be counted in readability,
    as they represent mathematical notation, not readable text.

    Args:
        text: Text potentially containing LaTeX

    Returns:
        Text with LaTeX removed
    """
    # Remove display math $$...$$
    text = re.sub(r'\$\$.*?\$\$', ' ', text)
    # Remove inline math $...$
    text = re.sub(r'\$[^$]+\$', ' ', text)
    # Remove LaTeX commands \command{...}
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', ' ', text)
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def calculate_readability_scores(text: str) -> Dict[str, float]:
    """
    Calculate readability scores for text.

    Args:
        text: Question text (may contain LaTeX)

    Returns:
        Dict with 'flesch_reading_ease' and 'flesch_kincaid_grade'
    """
    # Strip LaTeX for readability analysis
    clean_text = strip_latex(text)

    # Handle empty text
    if not clean_text or len(clean_text.strip()) == 0:
        return {
            'flesch_reading_ease': 100.0,  # Default: very easy
            'flesch_kincaid_grade': 0.0     # Default: kindergarten
        }

    try:
        # Calculate Flesch Reading Ease (0-100, higher = easier)
        reading_ease = textstat.flesch_reading_ease(clean_text)

        # Calculate Flesch-Kincaid Grade Level (0-18+)
        grade_level = textstat.flesch_kincaid_grade(clean_text)

        # Ensure values are in reasonable ranges
        reading_ease = max(0.0, min(100.0, reading_ease))
        grade_level = max(0.0, grade_level)

        return {
            'flesch_reading_ease': round(reading_ease, 2),
            'flesch_kincaid_grade': round(grade_level, 2)
        }
    except Exception as e:
        print(f"Warning: Failed to calculate readability for text: {clean_text[:50]}...")
        print(f"  Error: {e}")
        # Return default values
        return {
            'flesch_reading_ease': 50.0,
            'flesch_kincaid_grade': 12.0
        }


def add_readability_to_questions(data: Dict) -> Dict:
    """
    Add readability scores to all questions in the data structure.

    Args:
        data: Loaded cell_questions.json data

    Returns:
        Updated data with readability scores added
    """
    total_questions = 0
    questions_updated = 0
    questions_skipped = 0

    # Track stats by level
    level_stats = {0: [], 1: [], 2: [], 3: [], 4: []}

    print("Processing questions...")
    print()

    for cell in data.get('cells', []):
        for question in cell.get('questions', []):
            total_questions += 1

            # Check if scores already exist
            if 'flesch_reading_ease' in question and 'flesch_kincaid_grade' in question:
                questions_skipped += 1
                # Still track stats for summary
                level = question.get('level', 0)
                level_stats[level].append({
                    'ease': question['flesch_reading_ease'],
                    'grade': question['flesch_kincaid_grade']
                })
                continue

            # Calculate scores
            question_text = question.get('question', '')
            scores = calculate_readability_scores(question_text)

            # Add scores to question
            question['flesch_reading_ease'] = scores['flesch_reading_ease']
            question['flesch_kincaid_grade'] = scores['flesch_kincaid_grade']

            questions_updated += 1

            # Track stats
            level = question.get('level', 0)
            level_stats[level].append({
                'ease': scores['flesch_reading_ease'],
                'grade': scores['flesch_kincaid_grade']
            })

            # Progress indicator
            if questions_updated % 100 == 0:
                print(f"  Processed {questions_updated} questions...")

    print()
    print(f"✓ Completed processing {total_questions} questions")
    print(f"  Updated: {questions_updated}")
    print(f"  Skipped (already had scores): {questions_skipped}")
    print()

    # Print summary statistics by level
    print("="*60)
    print("READABILITY SUMMARY BY LEVEL")
    print("="*60)
    print()

    for level in range(5):
        if not level_stats[level]:
            print(f"Level {level}: No questions")
            continue

        stats = level_stats[level]
        avg_ease = sum(s['ease'] for s in stats) / len(stats)
        avg_grade = sum(s['grade'] for s in stats) / len(stats)
        min_ease = min(s['ease'] for s in stats)
        max_ease = max(s['ease'] for s in stats)
        min_grade = min(s['grade'] for s in stats)
        max_grade = max(s['grade'] for s in stats)

        level_names = {
            0: "Most Specific (Expert)",
            1: "Specific",
            2: "Undergraduate",
            3: "High School",
            4: "Middle School (Broadest)"
        }

        print(f"Level {level} - {level_names[level]}:")
        print(f"  Questions: {len(stats)}")
        print(f"  Reading Ease: {avg_ease:.1f} (range: {min_ease:.1f}-{max_ease:.1f})")
        print(f"  Grade Level:  {avg_grade:.1f} (range: {min_grade:.1f}-{max_grade:.1f})")
        print()

    return data


def main():
    # File paths
    input_file = Path('cell_questions.json')
    backup_file = Path('cell_questions.json.backup')

    # Check if input file exists
    if not input_file.exists():
        print(f"ERROR: {input_file} not found")
        print("Make sure you're running this from the repository root")
        return 1

    print("="*60)
    print("ADD READABILITY SCORES TO QUESTIONS")
    print("="*60)
    print()
    print(f"Input:  {input_file}")
    print(f"Backup: {backup_file}")
    print()

    # Load existing data
    print("Loading questions...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_cells = len(data.get('cells', []))
    total_questions = sum(len(cell.get('questions', [])) for cell in data.get('cells', []))
    print(f"  Loaded {total_questions} questions across {total_cells} cells")
    print()

    # Create backup
    print("Creating backup...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Backup saved to {backup_file}")
    print()

    # Add readability scores
    updated_data = add_readability_to_questions(data)

    # Save updated data
    print("Saving updated questions...")
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2)
    print(f"  ✓ Saved to {input_file}")
    print()

    print("="*60)
    print("✓ SUCCESS")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Spot-check questions to verify readability scores make sense")
    print("2. Commit the updated cell_questions.json")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
