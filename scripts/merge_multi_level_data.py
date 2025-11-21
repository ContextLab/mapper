#!/usr/bin/env python3
"""
Merge Multi-Level Data
======================

Merges all level outputs (level_0 through level_4) into final unified files:
- wikipedia_articles_level_{0-4}.json → wikipedia_articles.json
- cell_questions_level_{0-4}.json → cell_questions.json

Features:
- Deduplicates articles (prefers higher levels, merges within levels)
- Assigns coordinates hierarchically from parent articles
- Converts x,y coordinates to grid coordinates (gx, gy)
- Merges all questions by cell coordinates
- Strips large fields to keep file size manageable
- Validates output integrity
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Set
from pathlib import Path


# Grid configuration (39x39 grid covering [0,1] x [0,1])
GRID_SIZE = 39


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


def xy_to_grid(x: float, y: float, grid_size: int = GRID_SIZE) -> Tuple[int, int]:
    """
    Convert normalized x,y coordinates to grid coordinates.

    Args:
        x: Normalized x coordinate [0, 1]
        y: Normalized y coordinate [0, 1]
        grid_size: Size of the grid (default 39x39)

    Returns:
        (gx, gy) grid coordinates
    """
    gx = int(x * grid_size)
    gy = int(y * grid_size)

    # Clamp to grid bounds
    gx = max(0, min(gx, grid_size - 1))
    gy = max(0, min(gy, grid_size - 1))

    return gx, gy


def grid_to_bounds(gx: int, gy: int, grid_size: int = GRID_SIZE) -> Dict[str, float]:
    """
    Convert grid coordinates to cell bounds.

    Args:
        gx: Grid x coordinate
        gy: Grid y coordinate
        grid_size: Size of the grid

    Returns:
        Dict with x_min, x_max, y_min, y_max
    """
    cell_width = 1.0 / grid_size
    cell_height = 1.0 / grid_size

    return {
        'x_min': gx * cell_width,
        'x_max': (gx + 1) * cell_width,
        'y_min': gy * cell_height,
        'y_max': (gy + 1) * cell_height
    }


def strip_article_fields(article: Dict) -> Dict:
    """
    Strip large/unnecessary fields from article to reduce file size.

    Keeps: title, url, summary, x, y, umap_x, umap_y, level
    Removes: text, content, embedding, parent_concepts, parent_articles, parent_reasoning

    Args:
        article: Original article dict

    Returns:
        Stripped article dict
    """
    stripped = {}

    # Required fields
    stripped['title'] = article.get('title', '')
    stripped['url'] = article.get('url', '')

    # Use excerpt if available, otherwise truncate summary to ~200 chars
    excerpt = article.get('excerpt', '')
    if not excerpt:
        summary = article.get('summary', '')
        if summary:
            # Truncate to first sentence or ~200 chars, whichever is shorter
            excerpt = summary[:200].rsplit('.', 1)[0] + '.' if '.' in summary[:200] else summary[:200]
    stripped['excerpt'] = excerpt

    # Coordinates (will be reassigned for levels 1-4)
    stripped['x'] = article.get('x', 0.0)
    stripped['y'] = article.get('y', 0.0)
    stripped['umap_x'] = article.get('umap_x', 0.0)
    stripped['umap_y'] = article.get('umap_y', 0.0)

    # Level
    stripped['level'] = article.get('level', 0)

    # Keep parent_articles for coordinate calculation
    stripped['parent_articles'] = article.get('parent_articles', [])

    return stripped


def merge_and_deduplicate_articles(base_path: str, num_levels: int = 5) -> Tuple[Dict[str, Dict], Dict]:
    """
    Merge and deduplicate articles across all levels.

    Rules:
    - Prefer higher-level copies when deduplicating
    - Merge duplicates within same level (combine metadata)
    - Preserve parent_articles for coordinate assignment

    Args:
        base_path: Directory containing level files
        num_levels: Number of levels to merge (0 to num_levels-1)

    Returns:
        Tuple of (articles_by_title dict, level stats dict)
    """
    print("\n=== Merging and Deduplicating Articles ===")

    articles_by_title = {}  # title -> article data
    level_stats = {}

    for level in range(num_levels):
        filepath = os.path.join(base_path, f'wikipedia_articles_level_{level}.json')
        data = load_json(filepath)

        if data is None:
            level_stats[level] = {'total': 0, 'unique': 0, 'duplicates': 0, 'merged': 0}
            continue

        level_total = len(data)
        level_unique = 0
        level_duplicates = 0
        level_merged = 0

        for article in data:
            title = article.get('title', '')
            if not title:
                continue

            stripped = strip_article_fields(article)
            # Ensure level is set (it may be missing from article data)
            stripped['level'] = level

            if title not in articles_by_title:
                # New article
                articles_by_title[title] = stripped
                level_unique += 1
            else:
                existing = articles_by_title[title]

                if stripped['level'] > existing['level']:
                    # Higher level - replace
                    articles_by_title[title] = stripped
                    level_duplicates += 1
                elif stripped['level'] == existing['level']:
                    # Same level - merge parent_articles
                    existing_parents = set(existing.get('parent_articles', []))
                    new_parents = set(stripped.get('parent_articles', []))
                    existing['parent_articles'] = list(existing_parents | new_parents)
                    level_merged += 1
                else:
                    # Lower level - skip
                    level_duplicates += 1

        level_stats[level] = {
            'total': level_total,
            'unique': level_unique,
            'duplicates': level_duplicates,
            'merged': level_merged
        }

        print(f"Level {level}: {level_total} total, {level_unique} unique, {level_duplicates} duplicates, {level_merged} merged")

    print(f"\nTotal unique articles: {len(articles_by_title)}")
    return articles_by_title, level_stats


def assign_hierarchical_coordinates(articles_by_title: Dict[str, Dict]) -> Tuple[List[Dict], Dict]:
    """
    Assign coordinates hierarchically from parent articles.

    Process:
    - Level 0: Keep original coordinates (from baseline heatmap)
    - Level 1-4: Average coordinates from parent articles at strictly lower levels
    - Remove articles with no valid parent coordinates

    Args:
        articles_by_title: Dict of articles by title

    Returns:
        Tuple of (final articles list, assignment stats)
    """
    print("\n=== Assigning Hierarchical Coordinates ===")

    stats = {
        'level_0_kept': 0,
        'level_1_assigned': 0,
        'level_2_assigned': 0,
        'level_3_assigned': 0,
        'level_4_assigned': 0,
        'removed_no_parents': 0
    }

    # Build title -> article lookup
    final_articles = []
    articles_dict = {title: article for title, article in articles_by_title.items()}

    # Process each level
    for level in range(5):
        level_articles = [a for a in articles_dict.values() if a['level'] == level]

        if level == 0:
            # Level 0: Keep original coordinates
            stats['level_0_kept'] = len(level_articles)
            final_articles.extend(level_articles)
            print(f"Level 0: Kept {len(level_articles)} articles with original coordinates")
        else:
            # Level 1-4: Calculate from parent articles
            assigned = 0
            removed = 0

            for article in level_articles:
                parent_titles = article.get('parent_articles', [])

                # Find parent articles at strictly lower levels, within heatmap bounds
                parent_coords = []
                for parent_title in parent_titles:
                    if parent_title in articles_dict:
                        parent = articles_dict[parent_title]
                        if parent['level'] < level:
                            px, py = parent['x'], parent['y']
                            # Only use parents within heatmap [0,1] range
                            if 0 <= px <= 1 and 0 <= py <= 1:
                                parent_coords.append((px, py))

                if parent_coords:
                    # Average parent coordinates
                    avg_x = sum(x for x, y in parent_coords) / len(parent_coords)
                    avg_y = sum(y for x, y in parent_coords) / len(parent_coords)

                    article['x'] = avg_x
                    article['y'] = avg_y
                    # Keep original umap coordinates for reference

                    final_articles.append(article)
                    assigned += 1
                else:
                    # No valid parents - remove this article
                    removed += 1

            stats[f'level_{level}_assigned'] = assigned
            stats['removed_no_parents'] += removed
            print(f"Level {level}: Assigned {assigned} articles, removed {removed} (no valid parents)")

    # Remove parent_articles field (no longer needed)
    for article in final_articles:
        if 'parent_articles' in article:
            del article['parent_articles']

    print(f"\nFinal article count: {len(final_articles)}")
    print(f"Removed {stats['removed_no_parents']} articles with no valid parent coordinates")

    return final_articles, stats


def load_all_questions(base_path: str, num_levels: int = 5) -> Dict[str, List[Dict]]:
    """
    Load all questions from level files, indexed by source article.

    Prioritizes simplified questions (_simplified.json files).
    If simplified version doesn't exist, skips that level with a warning.

    Args:
        base_path: Directory containing level files
        num_levels: Number of levels to load

    Returns:
        Dict mapping article title -> list of questions
    """
    print("\n=== Loading Questions ===")

    questions_by_article = defaultdict(list)
    total_questions = 0

    for level in range(num_levels):
        # Try simplified version first
        simplified_filepath = os.path.join(base_path, f'cell_questions_level_{level}_simplified.json')
        original_filepath = os.path.join(base_path, f'cell_questions_level_{level}.json')

        filepath = None
        is_simplified = False

        if os.path.exists(simplified_filepath):
            filepath = simplified_filepath
            is_simplified = True
        elif os.path.exists(original_filepath):
            # Warn that simplified version doesn't exist
            print(f"⚠️  Level {level}: No simplified questions found ({simplified_filepath}), skipping...")
            continue
        else:
            # Neither file exists
            continue

        data = load_json(filepath)

        if data is None:
            continue

        questions = data.get('questions', [])
        level_questions = 0

        for question in questions:
            source_article = question.get('source_article', '')
            if source_article:
                questions_by_article[source_article].append(question)
                level_questions += 1

        total_questions += level_questions
        status = "simplified" if is_simplified else "original"
        print(f"Level {level}: Loaded {level_questions} questions ({status})")

    print(f"\nTotal questions loaded: {total_questions}")
    print(f"Questions distributed across {len(questions_by_article)} articles")

    return questions_by_article


def merge_cell_questions(articles: List[Dict], questions_by_article: Dict[str, List[Dict]]) -> Tuple[Dict, Dict]:
    """
    Merge questions by cell coordinates.

    Each question inherits coordinates from its source article.
    Questions are grouped by grid cell (gx, gy).

    Args:
        articles: List of articles with final coordinates
        questions_by_article: Dict mapping article title to questions

    Returns:
        Tuple of (merged cell data dict, stats dict)
    """
    print("\n=== Merging Questions by Cell ===")

    # Build article title -> (coordinates, level) lookup
    article_data = {a['title']: {'x': a['x'], 'y': a['y'], 'level': a['level']} for a in articles}

    all_cells = {}  # Key: (gx, gy), Value: cell data
    stats = {
        'total_questions': 0,
        'questions_with_coords': 0,
        'questions_no_coords': 0,
        'unique_cells': 0
    }

    for article_title, questions in questions_by_article.items():
        if article_title not in article_data:
            # Article was removed (no valid parents)
            stats['questions_no_coords'] += len(questions)
            continue

        article_info = article_data[article_title]
        x, y = article_info['x'], article_info['y']
        level = article_info['level']
        gx, gy = xy_to_grid(x, y)
        key = (gx, gy)

        # Update each question with inherited coordinates and level
        for question in questions:
            question['x'] = x
            question['y'] = y
            question['level'] = level  # Add level from source article
            stats['total_questions'] += 1
            stats['questions_with_coords'] += 1

        # Add questions to cell
        if key not in all_cells:
            bounds = grid_to_bounds(gx, gy)
            all_cells[key] = {
                'cell': {
                    'gx': gx,
                    'gy': gy,
                    **bounds
                },
                'questions': questions.copy(),
                'source_articles': [article_title]
            }
        else:
            all_cells[key]['questions'].extend(questions)
            all_cells[key]['source_articles'].append(article_title)

    # Convert to list and add stats
    merged_cells = []
    for (gx, gy), cell_data in sorted(all_cells.items()):
        cell_data['num_questions'] = len(cell_data['questions'])
        cell_data['num_articles'] = len(set(cell_data['source_articles']))
        merged_cells.append(cell_data)

    stats['unique_cells'] = len(merged_cells)

    print(f"Total questions: {stats['total_questions']}")
    print(f"Questions with coordinates: {stats['questions_with_coords']}")
    print(f"Questions removed (no coords): {stats['questions_no_coords']}")
    print(f"Unique cells: {stats['unique_cells']}")

    # Create result with metadata
    result = {
        'cells': merged_cells,
        'metadata': {
            'grid_size': GRID_SIZE,
            'total_cells': len(merged_cells),
            'total_questions': stats['questions_with_coords'],
            'stats': stats
        }
    }

    return result, stats


def validate_articles(articles: List[Dict]) -> Dict[str, Any]:
    """Validate merged articles data."""
    print("\n=== Validating Articles ===")

    validation = {
        'total_articles': len(articles),
        'duplicate_titles': [],
        'missing_fields': [],
        'invalid_coordinates': [],
        'errors': []
    }

    seen_titles = set()
    required_fields = ['title', 'url', 'excerpt', 'x', 'y', 'level']

    for i, article in enumerate(articles):
        title = article.get('title', '')

        if title in seen_titles:
            validation['duplicate_titles'].append(title)
        seen_titles.add(title)

        missing = [field for field in required_fields if field not in article]
        if missing:
            validation['missing_fields'].append({
                'index': i,
                'title': title,
                'missing': missing
            })

        if 'x' in article and 'y' in article:
            x, y = article['x'], article['y']
            # Should be within [0,1] after hierarchical assignment
            if not (0 <= x <= 1 and 0 <= y <= 1):
                validation['invalid_coordinates'].append({
                    'title': title,
                    'x': x,
                    'y': y,
                    'level': article.get('level')
                })

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
    """Validate merged cell questions data."""
    print("\n=== Validating Cell Questions ===")

    cells = data.get('cells', [])

    validation = {
        'total_cells': len(cells),
        'total_questions': 0,
        'duplicate_cells': [],
        'invalid_coordinates': [],
        'errors': []
    }

    seen_cells = set()

    for i, cell_data in enumerate(cells):
        cell_info = cell_data.get('cell', {})
        gx = cell_info.get('gx')
        gy = cell_info.get('gy')

        if gx is not None and gy is not None:
            key = (gx, gy)
            if key in seen_cells:
                validation['duplicate_cells'].append(key)
            seen_cells.add(key)

        questions = cell_data.get('questions', [])
        validation['total_questions'] += len(questions)

    if validation['duplicate_cells']:
        validation['errors'].append(f"Found {len(validation['duplicate_cells'])} duplicate cells")

    if validation['errors']:
        print("VALIDATION ERRORS:")
        for error in validation['errors']:
            print(f"  - {error}")
    else:
        print(f"✓ All {validation['total_cells']} cells and {validation['total_questions']} questions valid")

    return validation


def print_merge_summary(article_stats: Dict, coord_stats: Dict, question_stats: Dict):
    """Print comprehensive merge summary."""
    print("\n" + "="*60)
    print("MERGE SUMMARY")
    print("="*60)

    print("\nArticles by Level:")
    for level in range(5):
        stats = article_stats.get(level, {})
        print(f"  Level {level}: {stats.get('total', 0):5d} total, "
              f"{stats.get('unique', 0):5d} unique, "
              f"{stats.get('duplicates', 0):5d} duplicates, "
              f"{stats.get('merged', 0):5d} merged")

    print("\nCoordinate Assignment:")
    for key, value in coord_stats.items():
        print(f"  {key}: {value}")

    print("\nQuestions:")
    for key, value in question_stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*60)


def main():
    """Main execution function."""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    num_levels = 5

    print("Multi-Level Data Merge (Hierarchical Coordinates)")
    print("=" * 60)
    print(f"Base path: {base_path}")
    print(f"Merging levels: 0 to {num_levels - 1}")
    print(f"Grid size: {GRID_SIZE}x{GRID_SIZE}")

    # Step 1: Merge and deduplicate articles
    articles_by_title, article_stats = merge_and_deduplicate_articles(base_path, num_levels)

    # Step 2: Assign coordinates hierarchically
    articles, coord_stats = assign_hierarchical_coordinates(articles_by_title)

    # Step 3: Load all questions
    questions_by_article = load_all_questions(base_path, num_levels)

    # Step 4: Merge questions by cell
    cell_questions, question_stats = merge_cell_questions(articles, questions_by_article)

    # Step 5: Validate
    article_validation = validate_articles(articles)
    cell_validation = validate_cell_questions(cell_questions)

    # Step 6: Save
    print("\n=== Saving Merged Files ===")

    articles_output = os.path.join(base_path, 'wikipedia_articles.json')
    save_json(articles_output, articles)

    cell_questions_output = os.path.join(base_path, 'cell_questions.json')
    save_json(cell_questions_output, cell_questions)

    # Save validation report
    validation_dir = os.path.join(base_path, 'notes')
    os.makedirs(validation_dir, exist_ok=True)

    validation_report = {
        'articles': article_validation,
        'cell_questions': cell_validation,
        'merge_stats': {
            'articles': article_stats,
            'coordinates': coord_stats,
            'questions': question_stats
        }
    }

    validation_output = os.path.join(validation_dir, 'merge_validation_report.json')
    save_json(validation_output, validation_report)

    # Print summary
    print_merge_summary(article_stats, coord_stats, question_stats)

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
