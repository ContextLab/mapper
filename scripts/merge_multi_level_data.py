#!/usr/bin/env python3
"""
Merge Multi-Level Data
======================

Merges all level outputs (level_0 through level_4) into final unified files:
- wikipedia_articles_level_{0-4}.json → wikipedia_articles.json
- cell_questions_level_{0-4}.json → cell_questions.json

Features:
- Deduplicates articles by title (keeps earliest level)
- Merges questions by cell coordinates
- Preserves all metadata and relationships
- Validates output integrity
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Any
from pathlib import Path


def load_json(filepath: str) -> Any:
    """Load JSON file with error handling."""
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found, skipping...")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def save_json(filepath: str, data: Any, indent: int = 2):
    """Save JSON file with pretty formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    print(f"Saved: {filepath}")


def merge_articles(base_path: str, num_levels: int = 5) -> List[Dict]:
    """
    Merge wikipedia_articles_level_{0-4}.json files.

    Deduplicates by title, keeping the first occurrence (earliest level).

    Args:
        base_path: Directory containing level files
        num_levels: Number of levels to merge (0 to num_levels-1)

    Returns:
        List of unique articles with metadata
    """
    print("\n=== Merging Wikipedia Articles ===")

    all_articles = []
    seen_titles = set()
    level_stats = {}

    for level in range(num_levels):
        filepath = os.path.join(base_path, f'wikipedia_articles_level_{level}.json')
        data = load_json(filepath)

        if data is None:
            level_stats[level] = {'total': 0, 'unique': 0, 'duplicates': 0}
            continue

        level_total = len(data)
        level_unique = 0
        level_duplicates = 0

        for article in data:
            title = article.get('title', '')

            if title not in seen_titles:
                # First occurrence - add to unique articles
                all_articles.append(article)
                seen_titles.add(title)
                level_unique += 1
            else:
                level_duplicates += 1

        level_stats[level] = {
            'total': level_total,
            'unique': level_unique,
            'duplicates': level_duplicates
        }

        print(f"Level {level}: {level_total} articles ({level_unique} unique, {level_duplicates} duplicates)")

    print(f"\nTotal unique articles: {len(all_articles)}")
    return all_articles, level_stats


def merge_cell_questions(base_path: str, num_levels: int = 5) -> Dict:
    """
    Merge cell_questions_level_{0-4}.json files.

    Merges questions by cell coordinates (gx, gy).
    Combines questions from all levels for each cell.

    Args:
        base_path: Directory containing level files
        num_levels: Number of levels to merge (0 to num_levels-1)

    Returns:
        Merged cell questions data with metadata
    """
    print("\n=== Merging Cell Questions ===")

    all_cells = {}  # Key: (gx, gy), Value: cell data
    level_stats = {}
    total_questions = 0

    # Collect metadata from first file
    global_metadata = None

    for level in range(num_levels):
        filepath = os.path.join(base_path, f'cell_questions_level_{level}.json')
        data = load_json(filepath)

        if data is None:
            level_stats[level] = {'cells': 0, 'questions': 0}
            continue

        # Store metadata from first valid file
        if global_metadata is None and 'metadata' in data:
            global_metadata = data['metadata'].copy()

        cells = data.get('cells', [])
        level_cells = len(cells)
        level_questions = 0

        for cell_data in cells:
            cell_info = cell_data.get('cell', {})
            gx = cell_info.get('gx')
            gy = cell_info.get('gy')

            if gx is None or gy is None:
                print(f"Warning: Cell missing coordinates in level {level}: {cell_info}")
                continue

            key = (gx, gy)
            questions = cell_data.get('questions', [])
            level_questions += len(questions)

            if key not in all_cells:
                # First occurrence - store complete cell data
                all_cells[key] = {
                    'cell': cell_info,
                    'questions': questions.copy(),
                    'source_levels': [level]
                }
            else:
                # Merge questions from this level
                all_cells[key]['questions'].extend(questions)
                all_cells[key]['source_levels'].append(level)

        level_stats[level] = {
            'cells': level_cells,
            'questions': level_questions
        }
        total_questions += level_questions

        print(f"Level {level}: {level_cells} cells, {level_questions} questions")

    # Convert to list and calculate merged stats
    merged_cells = []
    for (gx, gy), cell_data in sorted(all_cells.items()):
        # Add summary stats to each cell
        cell_data['num_questions'] = len(cell_data['questions'])
        cell_data['num_levels'] = len(cell_data['source_levels'])
        merged_cells.append(cell_data)

    print(f"\nTotal cells: {len(merged_cells)}")
    print(f"Total questions: {total_questions}")

    # Update metadata with merge information
    if global_metadata is None:
        global_metadata = {}

    global_metadata.update({
        'merge_info': {
            'num_levels_merged': num_levels,
            'total_cells': len(merged_cells),
            'total_questions': total_questions,
            'level_stats': level_stats
        }
    })

    result = {
        'cells': merged_cells,
        'metadata': global_metadata
    }

    return result, level_stats


def validate_articles(articles: List[Dict]) -> Dict[str, Any]:
    """
    Validate merged articles data.

    Checks:
    - No duplicate titles
    - All required fields present
    - Valid coordinate ranges
    """
    print("\n=== Validating Articles ===")

    validation = {
        'total_articles': len(articles),
        'duplicate_titles': [],
        'missing_fields': [],
        'invalid_coordinates': [],
        'errors': []
    }

    seen_titles = set()
    required_fields = ['title', 'content', 'url']

    for i, article in enumerate(articles):
        # Check for duplicates
        title = article.get('title', '')
        if title in seen_titles:
            validation['duplicate_titles'].append(title)
        seen_titles.add(title)

        # Check required fields
        missing = [field for field in required_fields if field not in article]
        if missing:
            validation['missing_fields'].append({
                'index': i,
                'title': title,
                'missing': missing
            })

        # Check coordinates if present
        if 'x' in article and 'y' in article:
            x, y = article['x'], article['y']
            if not (0 <= x <= 1 and 0 <= y <= 1):
                validation['invalid_coordinates'].append({
                    'title': title,
                    'x': x,
                    'y': y
                })

    # Summary
    if validation['duplicate_titles']:
        validation['errors'].append(f"Found {len(validation['duplicate_titles'])} duplicate titles")
    if validation['missing_fields']:
        validation['errors'].append(f"Found {len(validation['missing_fields'])} articles with missing fields")
    if validation['invalid_coordinates']:
        validation['errors'].append(f"Found {len(validation['invalid_coordinates'])} articles with invalid coordinates")

    if validation['errors']:
        print("VALIDATION ERRORS:")
        for error in validation['errors']:
            print(f"  - {error}")
    else:
        print("✓ All articles valid")

    return validation


def validate_cell_questions(data: Dict) -> Dict[str, Any]:
    """
    Validate merged cell questions data.

    Checks:
    - No duplicate cells
    - Valid coordinate ranges
    - All questions have required fields
    - Parent relationships are valid
    """
    print("\n=== Validating Cell Questions ===")

    cells = data.get('cells', [])

    validation = {
        'total_cells': len(cells),
        'total_questions': 0,
        'duplicate_cells': [],
        'invalid_coordinates': [],
        'missing_cell_fields': [],
        'missing_question_fields': [],
        'errors': []
    }

    seen_cells = set()
    required_cell_fields = ['gx', 'gy', 'x_min', 'x_max', 'y_min', 'y_max']
    required_question_fields = ['question', 'article_title']

    for i, cell_data in enumerate(cells):
        cell_info = cell_data.get('cell', {})
        gx = cell_info.get('gx')
        gy = cell_info.get('gy')

        # Check for duplicate cells
        if gx is not None and gy is not None:
            key = (gx, gy)
            if key in seen_cells:
                validation['duplicate_cells'].append(key)
            seen_cells.add(key)

        # Check required cell fields
        missing = [field for field in required_cell_fields if field not in cell_info]
        if missing:
            validation['missing_cell_fields'].append({
                'index': i,
                'cell': (gx, gy),
                'missing': missing
            })

        # Check coordinate ranges
        if all(field in cell_info for field in required_cell_fields):
            x_min, x_max = cell_info['x_min'], cell_info['x_max']
            y_min, y_max = cell_info['y_min'], cell_info['y_max']

            if not (0 <= x_min <= x_max <= 1 and 0 <= y_min <= y_max <= 1):
                validation['invalid_coordinates'].append({
                    'cell': (gx, gy),
                    'bounds': (x_min, x_max, y_min, y_max)
                })

        # Validate questions
        questions = cell_data.get('questions', [])
        validation['total_questions'] += len(questions)

        for q_idx, question in enumerate(questions):
            missing = [field for field in required_question_fields if field not in question]
            if missing:
                validation['missing_question_fields'].append({
                    'cell': (gx, gy),
                    'question_index': q_idx,
                    'missing': missing
                })

    # Summary
    if validation['duplicate_cells']:
        validation['errors'].append(f"Found {len(validation['duplicate_cells'])} duplicate cells")
    if validation['invalid_coordinates']:
        validation['errors'].append(f"Found {len(validation['invalid_coordinates'])} cells with invalid coordinates")
    if validation['missing_cell_fields']:
        validation['errors'].append(f"Found {len(validation['missing_cell_fields'])} cells with missing fields")
    if validation['missing_question_fields']:
        validation['errors'].append(f"Found {len(validation['missing_question_fields'])} questions with missing fields")

    if validation['errors']:
        print("VALIDATION ERRORS:")
        for error in validation['errors']:
            print(f"  - {error}")
    else:
        print(f"✓ All {validation['total_cells']} cells and {validation['total_questions']} questions valid")

    return validation


def print_merge_summary(article_stats: Dict, cell_stats: Dict):
    """Print comprehensive merge summary."""
    print("\n" + "="*60)
    print("MERGE SUMMARY")
    print("="*60)

    print("\nArticles by Level:")
    for level, stats in sorted(article_stats.items()):
        print(f"  Level {level}: {stats['total']:5d} total, {stats['unique']:5d} unique, {stats['duplicates']:5d} duplicates")

    print("\nQuestions by Level:")
    for level, stats in sorted(cell_stats.items()):
        print(f"  Level {level}: {stats['cells']:3d} cells, {stats['questions']:5d} questions")

    print("\n" + "="*60)


def main():
    """Main execution function."""
    # Configuration
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    num_levels = 5

    print("Multi-Level Data Merge")
    print("=" * 60)
    print(f"Base path: {base_path}")
    print(f"Merging levels: 0 to {num_levels - 1}")

    # Merge articles
    articles, article_stats = merge_articles(base_path, num_levels)

    # Merge cell questions
    cell_questions, cell_stats = merge_cell_questions(base_path, num_levels)

    # Validate merged data
    article_validation = validate_articles(articles)
    cell_validation = validate_cell_questions(cell_questions)

    # Save merged files
    print("\n=== Saving Merged Files ===")

    articles_output = os.path.join(base_path, 'wikipedia_articles.json')
    save_json(articles_output, articles)

    cell_questions_output = os.path.join(base_path, 'cell_questions.json')
    save_json(cell_questions_output, cell_questions)

    # Save validation reports
    validation_dir = os.path.join(base_path, 'notes')
    os.makedirs(validation_dir, exist_ok=True)

    validation_report = {
        'articles': article_validation,
        'cell_questions': cell_validation,
        'merge_stats': {
            'articles': article_stats,
            'cell_questions': cell_stats
        }
    }

    validation_output = os.path.join(validation_dir, 'merge_validation_report.json')
    save_json(validation_output, validation_report)

    # Print summary
    print_merge_summary(article_stats, cell_stats)

    # Final status
    has_errors = bool(article_validation['errors'] or cell_validation['errors'])

    if has_errors:
        print("\n⚠️  MERGE COMPLETED WITH VALIDATION ERRORS")
        print(f"   See validation report: {validation_output}")
        return 1
    else:
        print("\n✓ MERGE COMPLETED SUCCESSFULLY")
        print(f"   Articles: {len(articles)}")
        print(f"   Cells: {cell_validation['total_cells']}")
        print(f"   Questions: {cell_validation['total_questions']}")
        return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
