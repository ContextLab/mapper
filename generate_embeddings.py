#!/usr/bin/env python3
"""
Extract questions from experiment.js and generate embeddings for knowledge map.

This script helps convert your experiment data into the format needed for the
web-based knowledge map demo.

Requirements:
    pip install sentence-transformers scikit-learn numpy
"""

import json
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import argparse


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
    
    return questions


def generate_embeddings(questions, model_name='all-MiniLM-L6-v2'):
    """
    Generate embeddings for questions using sentence-transformers.
    
    Args:
        questions: List of question dictionaries
        model_name: Name of sentence-transformer model to use
        
    Popular models:
        - 'all-MiniLM-L6-v2': Fast, good quality (384 dim)
        - 'all-mpnet-base-v2': Better quality, slower (768 dim)
        - 'paraphrase-multilingual-MiniLM-L12-v2': Multilingual
    """
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print("Generating embeddings...")
    question_texts = [q['question'] for q in questions]
    embeddings = model.encode(question_texts, show_progress_bar=True)
    
    return embeddings


def reduce_dimensions(embeddings, method='pca', n_components=2):
    """
    Reduce embedding dimensions for visualization.
    
    Args:
        embeddings: High-dimensional embeddings
        method: 'pca' or 'tsne'
        n_components: Number of dimensions (typically 2 for visualization)
    """
    print(f"Reducing dimensions using {method.upper()}...")
    
    if method == 'pca':
        reducer = PCA(n_components=n_components)
        reduced = reducer.fit_transform(embeddings)
        print(f"Explained variance: {sum(reducer.explained_variance_ratio_):.2%}")
    elif method == 'tsne':
        reducer = TSNE(n_components=n_components, random_state=42)
        reduced = reducer.fit_transform(embeddings)
    else:
        raise ValueError(f"Unknown method: {method}")
    
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
            'options': q['choices'],
            'correctIndex': q['correct'],
            'x': float(x_normalized[i]),  # Normalized x coordinate [0, 1]
            'y': float(y_normalized[i]),  # Normalized y coordinate [0, 1]
            'topic': extract_topic(q['question'])  # Optional: extract topic
        }
        
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
    parser.add_argument('--method', default='pca', choices=['pca', 'tsne'], help='Dimensionality reduction method')
    parser.add_argument('--output', default='questions_with_embeddings.json', help='Output file path')
    parser.add_argument('--html-snippet', action='store_true', help='Generate HTML snippet')
    
    args = parser.parse_args()
    
    # Load questions
    if args.input:
        print(f"Parsing questions from {args.input}...")
        questions = extract_questions_from_js(args.input)
    elif args.questions_json:
        print(f"Loading questions from {args.questions_json}...")
        with open(args.questions_json, 'r') as f:
            questions = json.load(f)
    else:
        print("Error: Must provide either --input or --questions-json")
        return
    
    print(f"Loaded {len(questions)} questions")
    
    # Generate embeddings
    embeddings = generate_embeddings(questions, args.model)
    
    # Reduce dimensions
    embeddings_2d = reduce_dimensions(embeddings, method=args.method)
    
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
