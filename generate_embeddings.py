#!/usr/bin/env python3
"""
Extract questions from experiment.js and generate embeddings for knowledge map.

This script helps convert your experiment data into the format needed for the
web-based knowledge map demo.

Requirements:
    pip install sentence-transformers scikit-learn numpy
"""

import os
import json
import re
import numpy as np
import argparse

# Fix for macOS mutex/threading issues with PyTorch
# Set BEFORE importing sentence_transformers
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Import heavy ML libraries only when needed (lazy imports)
# This avoids loading PyTorch when just validating/preserving coordinates


def normalize_question_format(question):
    """
    Normalize question format to use consistent keys.
    Handles both 'choices'/'correct' and 'options'/'correctIndex' formats.
    """
    normalized = {
        'question': question['question']
    }

    # Normalize options/choices
    if 'options' in question:
        normalized['options'] = question['options']
    elif 'choices' in question:
        normalized['options'] = question['choices']
    else:
        raise ValueError(f"Question missing 'options' or 'choices': {question}")

    # Normalize correctIndex/correct
    if 'correctIndex' in question:
        normalized['correctIndex'] = question['correctIndex']
    elif 'correct' in question:
        normalized['correctIndex'] = question['correct']
    else:
        raise ValueError(f"Question missing 'correctIndex' or 'correct': {question}")

    # Copy over other fields if present
    for key in ['topic', 'x', 'y', 'embedding_full']:
        if key in question:
            normalized[key] = question[key]

    return normalized


def extract_questions_from_js(js_file_path):
    """
    Extract questions from experiment.js file.

    Adjust the parsing logic based on your actual file structure.
    """
    with open(js_file_path, 'r') as f:
        content = f.read()

    # Example parsing - adjust based on your actual structure
    # This is a placeholder that you'll need to customize
    questions = []

    # Pattern to find question objects
    # You'll need to adjust this regex based on your actual format
    pattern = r'{\s*question:\s*["\']([^"\']+)["\']\s*,\s*choices:\s*\[([^\]]+)\]\s*,\s*correct:\s*(\d+)'

    matches = re.finditer(pattern, content)

    for match in matches:
        question_text = match.group(1)
        choices_str = match.group(2)
        correct_idx = int(match.group(3))

        # Parse choices
        choices = re.findall(r'["\']([^"\']+)["\']', choices_str)

        questions.append({
            'question': question_text,
            'choices': choices,
            'correct': correct_idx
        })

    return [normalize_question_format(q) for q in questions]


def generate_embeddings_openai(questions, model_name='text-embedding-3-small'):
    """
    Generate embeddings using OpenAI API (no PyTorch, no mutex issues).

    Args:
        questions: List of question dictionaries
        model_name: OpenAI embedding model name
            - 'text-embedding-3-small': Fast, cheap, 1536 dim
            - 'text-embedding-3-large': Better quality, 3072 dim
            - 'text-embedding-ada-002': Legacy, 1536 dim

    Requires: pip install openai
    Set OPENAI_API_KEY environment variable
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("OpenAI not installed. Install with: pip install openai")

    import os
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)
    question_texts = [q['question'] for q in questions]

    print(f"Generating embeddings via OpenAI API using model: {model_name}")
    print(f"Processing {len(question_texts)} questions...")

    response = client.embeddings.create(
        model=model_name,
        input=question_texts
    )

    embeddings = np.array([item.embedding for item in response.data])
    print(f"Generated embeddings with shape: {embeddings.shape}")
    return embeddings


def generate_embeddings(questions, model_name='all-mpnet-base-v2', use_openai=False):
    """
    Generate embeddings for questions.

    Args:
        questions: List of question dictionaries
        model_name: Model name (OpenAI or sentence-transformer)
        use_openai: If True, use OpenAI API (avoids PyTorch mutex issues)

    OpenAI models (use_openai=True):
        - 'text-embedding-3-small': Fast, cheap, 1536 dim
        - 'text-embedding-3-large': Better quality, 3072 dim

    Local models (use_openai=False, may have mutex issues on macOS):
        - 'all-MiniLM-L6-v2': Fast, good quality (384 dim)
        - 'all-mpnet-base-v2': Better quality, slower (768 dim)
    """
    if use_openai:
        return generate_embeddings_openai(questions, model_name)

    # Use datawrangler (note: still uses PyTorch underneath)
    import datawrangler as dw

    print(f"Generating embeddings with datawrangler using model: {model_name}")
    question_texts = [q['question'] for q in questions]
    print(f"Processing {len(question_texts)} questions...")

    embeddings = dw.wrangle(question_texts, text_kwargs={'model': model_name})

    print(f"Generated embeddings with shape: {embeddings.shape}")
    return embeddings


def reduce_dimensions(embeddings, method='umap', n_components=2, save_reducer=False):
    """
    Reduce embedding dimensions for visualization.

    Args:
        embeddings: High-dimensional embeddings
        method: 'pca', 'tsne', or 'umap' (recommended)
        n_components: Number of dimensions (typically 2 for visualization)
        save_reducer: If True, save fitted reducer for inverse transforms (UMAP only)
    """
    print(f"Reducing dimensions using {method.upper()}...")

    if method == 'pca':
        from sklearn.decomposition import PCA
        reducer = PCA(n_components=n_components, random_state=42)
        reduced = reducer.fit_transform(embeddings)
        print(f"Explained variance: {sum(reducer.explained_variance_ratio_):.2%}")
    elif method == 'tsne':
        from sklearn.manifold import TSNE
        perplexity = min(30, len(embeddings) - 1)
        reducer = TSNE(n_components=n_components, random_state=42, perplexity=perplexity)
        reduced = reducer.fit_transform(embeddings)
    elif method == 'umap':
        try:
            import umap
            import pickle
        except ImportError:
            print("UMAP not installed. Install with: pip install umap-learn")
            print("Falling back to PCA...")
            from sklearn.decomposition import PCA
            reducer = PCA(n_components=n_components, random_state=42)
            reduced = reducer.fit_transform(embeddings)
            return reduced

        n_neighbors = min(15, len(embeddings) - 1)

        # Use .fit() instead of .fit_transform() to retain model for inverse_transform
        reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            metric='cosine',
            random_state=42
        )

        # Fit the model (don't use fit_transform!)
        reducer.fit(embeddings)
        reduced = reducer.transform(embeddings)

        print(f"UMAP reduction complete")

        # Save the reducer if requested
        if save_reducer:
            with open('umap_reducer.pkl', 'wb') as f:
                pickle.dump(reducer, f)
            print("Saved UMAP reducer to umap_reducer.pkl")

            # Also save the bounds for inverse transform
            bounds = {
                'x_min': float(reduced[:, 0].min()),
                'x_max': float(reduced[:, 0].max()),
                'y_min': float(reduced[:, 1].min()),
                'y_max': float(reduced[:, 1].max()),
            }
            with open('umap_bounds.pkl', 'wb') as f:
                pickle.dump(bounds, f)
            print("Saved UMAP bounds to umap_bounds.pkl")
    else:
        raise ValueError(f"Unknown method: {method}. Use 'pca', 'tsne', or 'umap'")

    return reduced


def create_web_data(questions, embeddings_2d, embeddings_full=None):
    """
    Create data structure for web demo with normalized 2D coordinates.
    
    Args:
        questions: Original question data
        embeddings_2d: 2D reduced embeddings
        embeddings_full: Optional full embeddings (for future use)
    """
    # Normalize 2D coordinates to [0, 1] range
    x_coords = embeddings_2d[:, 0]
    y_coords = embeddings_2d[:, 1]
    
    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()
    
    x_normalized = (x_coords - x_min) / (x_max - x_min)
    y_normalized = (y_coords - y_min) / (y_max - y_min)
    
    web_questions = []
    
    for i, q in enumerate(questions):
        question_data = {
            'question': q['question'],
            'options': q['options'],
            'correctIndex': q['correctIndex'],
            'x': float(x_normalized[i]),  # Normalized x coordinate [0, 1]
            'y': float(y_normalized[i]),  # Normalized y coordinate [0, 1]
        }

        # Add topic if it exists, otherwise extract it
        if 'topic' in q:
            question_data['topic'] = q['topic']
        else:
            question_data['topic'] = extract_topic(q['question'])

        if embeddings_full is not None:
            question_data['embedding_full'] = embeddings_full[i].tolist()

        web_questions.append(question_data)
    
    return web_questions


def extract_topic(question_text):
    """
    Simple topic extraction based on keywords.
    Customize this based on your domain.
    """
    text_lower = question_text.lower()
    
    # Biology example topics
    if any(word in text_lower for word in ['mitochondria', 'chloroplast', 'organelle']):
        return 'cell_organelles'
    elif any(word in text_lower for word in ['photosynthesis', 'chloroplast', 'sunlight']):
        return 'photosynthesis'
    elif any(word in text_lower for word in ['gene', 'dna', 'heredity', 'chromosome']):
        return 'genetics'
    elif any(word in text_lower for word in ['protein', 'ribosome', 'synthesis']):
        return 'protein_synthesis'
    elif any(word in text_lower for word in ['respiration', 'atp', 'energy']):
        return 'cellular_respiration'
    else:
        return 'general'


def save_for_web(web_data, output_path='questions_with_embeddings.json'):
    """Save data in format ready for web demo."""
    with open(output_path, 'w') as f:
        json.dump(web_data, f, indent=2)
    print(f"\nSaved {len(web_data)} questions to {output_path}")


def generate_html_snippet(web_data):
    """Generate JavaScript code to paste into HTML."""
    js_code = "const questionsData = " + json.dumps(web_data, indent=4) + ";"
    return js_code


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for knowledge map')
    parser.add_argument('--input', help='Path to experiment.js file')
    parser.add_argument('--questions-json', help='Path to questions JSON file (alternative to parsing JS)')
    parser.add_argument('--model', default='all-MiniLM-L6-v2', help='Sentence transformer model')
    parser.add_argument('--method', default='umap', choices=['pca', 'tsne', 'umap'], help='Dimensionality reduction method (umap recommended)')
    parser.add_argument('--output', default='questions_with_embeddings.json', help='Output file path')
    parser.add_argument('--html-snippet', action='store_true', help='Generate HTML snippet')
    parser.add_argument('--preserve-coordinates', action='store_true',
                       help='Preserve existing x,y coordinates if present in input')
    parser.add_argument('--update-in-place', action='store_true',
                       help='Update the input questions.json file in place (sets --preserve-coordinates)')
    parser.add_argument('--save-reducer', action='store_true',
                       help='Save UMAP reducer and bounds for inverse transforms (UMAP only)')

    args = parser.parse_args()

    # If update-in-place is set, enable preserve-coordinates and set output to input file
    if args.update_in_place:
        if not args.questions_json:
            print("Error: --update-in-place requires --questions-json")
            return
        args.preserve_coordinates = True
        args.output = args.questions_json
        print(f"Updating {args.questions_json} in place, preserving coordinates...")

    # Load questions
    if args.input:
        print(f"Parsing questions from {args.input}...")
        questions = extract_questions_from_js(args.input)
    elif args.questions_json:
        print(f"Loading questions from {args.questions_json}...")
        with open(args.questions_json, 'r') as f:
            raw_questions = json.load(f)
        questions = [normalize_question_format(q) for q in raw_questions]
    else:
        print("Error: Must provide either --input or --questions-json")
        return

    print(f"Loaded {len(questions)} questions")

    # Check if questions already have coordinates
    has_coordinates = all('x' in q and 'y' in q for q in questions)
    if has_coordinates and args.preserve_coordinates:
        print("Questions already have coordinates - preserving them")
        # Just validate and save as-is
        web_data = questions
        save_for_web(web_data, args.output)
        print("\n✅ Done! Questions validated and saved.")
        return
    
    # Generate embeddings
    embeddings = generate_embeddings(questions, args.model)

    # Reduce dimensions
    embeddings_2d = reduce_dimensions(embeddings, method=args.method, save_reducer=args.save_reducer)

    # Create web data
    web_data = create_web_data(questions, embeddings_2d, embeddings)
    
    # Save
    save_for_web(web_data, args.output)
    
    if args.html_snippet:
        snippet_path = args.output.replace('.json', '_snippet.js')
        with open(snippet_path, 'w') as f:
            f.write(generate_html_snippet(web_data))
        print(f"HTML snippet saved to {snippet_path}")
    
    print("\n✅ Done! You can now:")
    print(f"1. Copy the content of {args.output}")
    print("2. Replace the questionsData array in the HTML file")
    print("3. Deploy to GitHub Pages")


def demo_with_sample_data():
    """
    Generate sample data for testing (if no experiment.js available).
    """
    sample_questions = [
        {
            'question': 'What is the primary function of mitochondria?',
            'choices': ['Protein synthesis', 'Energy production', 'DNA storage', 'Cell division'],
            'correct': 1
        },
        {
            'question': 'Which process converts sunlight into chemical energy?',
            'choices': ['Respiration', 'Photosynthesis', 'Fermentation', 'Glycolysis'],
            'correct': 1
        },
        # Add more sample questions...
    ]
    
    print("Running with sample data...")
    embeddings = generate_embeddings(sample_questions)
    embeddings_2d = reduce_dimensions(embeddings)
    web_data = create_web_data(sample_questions, embeddings_2d)
    save_for_web(web_data, 'sample_questions.json')


if __name__ == '__main__':
    # If no arguments provided, show help and run demo
    import sys
    if len(sys.argv) == 1:
        print("=" * 60)
        print("Knowledge Map - Embedding Generator")
        print("=" * 60)
        print("\nNo arguments provided. Running demo with sample data...\n")
        demo_with_sample_data()
        print("\n" + "=" * 60)
        print("For your actual data, run:")
        print("  python generate_embeddings.py --input experiment.js")
        print("  python generate_embeddings.py --questions-json questions.json")
        print("\nFor more options: python generate_embeddings.py --help")
        print("=" * 60)
    else:
        main()
