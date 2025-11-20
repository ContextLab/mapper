#!/usr/bin/env python3
"""
Test level 0 generation on a small sample (10 articles) using excerpts instead of full text.
"""

import json
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from api_utils import create_openai_client
from openai_batch import batch_with_cache

# System prompts (plain text, no structured outputs)
CONCEPT_EXTRACTION_SYSTEM_PROMPT = """You are an expert at identifying key concepts in encyclopedia articles.

Given a Wikipedia article title and excerpt, identify 1-3 specific concepts that someone might want to learn about.

Guidelines:
- Focus on concrete, learnable topics (not overly broad or abstract)
- Each concept should be distinct and specific
- Concepts should be suitable for quiz questions
- Skip articles that are too specific/narrow or lists

Format your response as:
SUITABLE: yes/no
REASONING: Brief explanation
CONCEPTS:
- Concept 1
- Concept 2
"""

QUESTION_GENERATION_SYSTEM_PROMPT = """You are an expert at creating conceptual quiz questions.

Given a Wikipedia article title, excerpt, and a concept, generate ONE high-quality multiple-choice question.

Guidelines:
- Test understanding of the concept, not trivial facts
- Create 4 plausible options
- Make distractors challenging but clearly wrong
- Question should be standalone (understandable without the article)

Format your response as:
QUESTION: [question text]
A: [option A]
B: [option B]
C: [option C]
D: [option D]
CORRECT: [A/B/C/D]
"""

def load_sample_articles(n=10):
    """Load first n articles from wikipedia_articles.json"""
    with open('wikipedia_articles.json', 'r') as f:
        articles = json.load(f)

    # Use excerpt as text for this test
    sample = []
    for article in articles[:n]:
        sample.append({
            'title': article['title'],
            'text': article['excerpt'],  # Use excerpt instead of full text
            'x': article['x'],
            'y': article['y'],
            # Parent fields (empty for level 0)
            'parent_articles': [],
            'parent_concepts': [],
            'level': 0
        })

    return sample

def extract_concepts_sample(articles, client):
    """Extract concepts from sample articles"""
    print(f"\nStep 1: Extract concepts from {len(articles)} articles")
    print("=" * 80)

    # Create batch requests
    requests = []
    for article in articles:
        user_prompt = f"""Article: {article['title']}

Excerpt:
{article['text']}

Identify 1-3 key concepts suitable for quiz questions."""

        requests.append({
            'custom_id': f"concepts-{article['title']}",
            'user_prompt': user_prompt
        })

    # Submit batch
    print(f"Submitting {len(requests)} concept extraction requests...")
    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=CONCEPT_EXTRACTION_SYSTEM_PROMPT,
        description="Level 0 concept extraction (sample)",
        model="gpt-5-nano",
        temperature=1.0,
        max_tokens=1500,
        response_format=None,  # No structured outputs
        poll_interval=30
    )

    # Parse results
    concept_results = {}
    for custom_id, response_text in results.items():
        title = custom_id.replace('concepts-', '')

        # Parse plain text response
        lines = response_text.strip().split('\n')
        suitable = False
        reasoning = ""
        concepts = []
        in_concepts = False

        for line in lines:
            line = line.strip()
            if line.startswith('SUITABLE:'):
                suitable = line.split(':', 1)[1].strip().lower() in ['yes', 'true', 'y']
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
            elif line.startswith('CONCEPTS:'):
                in_concepts = True
            elif in_concepts and line.startswith('-'):
                concepts.append(line[1:].strip())

        concept_results[title] = {
            'suitable': suitable,
            'reasoning': reasoning,
            'concepts': concepts
        }

        print(f"  {title}: {len(concepts)} concepts (suitable: {suitable})")

    return concept_results

def generate_questions_sample(articles, concept_results, client):
    """Generate questions from concepts"""
    print(f"\nStep 2: Generate questions from concepts")
    print("=" * 80)

    # Create batch requests (one per concept)
    requests = []
    concept_map = {}  # Map custom_id to (title, concept)

    for article in articles:
        title = article['title']
        result = concept_results.get(title)

        if not result or not result['suitable']:
            continue

        for concept in result['concepts']:
            custom_id = f"question-{title}-{len(requests)}"

            user_prompt = f"""Article: {title}

Excerpt:
{article['text']}

Concept: {concept}

Generate ONE multiple-choice question testing understanding of this concept."""

            requests.append({
                'custom_id': custom_id,
                'user_prompt': user_prompt
            })

            concept_map[custom_id] = (title, concept)

    print(f"Submitting {len(requests)} question generation requests...")

    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
        description="Level 0 question generation (sample)",
        model="gpt-5-nano",
        temperature=1.0,
        max_tokens=1500,
        response_format=None,  # No structured outputs
        poll_interval=30
    )

    # Parse results
    questions = []
    for custom_id, response_text in results.items():
        title, concept = concept_map[custom_id]

        # Parse plain text response
        lines = response_text.strip().split('\n')
        question_text = ""
        options = {}
        correct = ""

        for line in lines:
            line = line.strip()
            if line.startswith('QUESTION:'):
                question_text = line.split(':', 1)[1].strip()
            elif line.startswith('A:'):
                options['A'] = line.split(':', 1)[1].strip()
            elif line.startswith('B:'):
                options['B'] = line.split(':', 1)[1].strip()
            elif line.startswith('C:'):
                options['C'] = line.split(':', 1)[1].strip()
            elif line.startswith('D:'):
                options['D'] = line.split(':', 1)[1].strip()
            elif line.startswith('CORRECT:'):
                correct = line.split(':', 1)[1].strip().upper()

        if question_text and len(options) == 4 and correct:
            questions.append({
                'article': title,
                'concept': concept,
                'question': question_text,
                'options': options,
                'correct': correct
            })
            print(f"  Generated question for: {title} / {concept}")

    return questions

def main():
    print("=" * 80)
    print("LEVEL 0 SAMPLE TEST (10 articles)")
    print("=" * 80)

    # Load sample
    articles = load_sample_articles(n=10)
    print(f"\nLoaded {len(articles)} sample articles")
    for article in articles:
        print(f"  - {article['title']}")

    # Create client
    client = create_openai_client()

    # Extract concepts
    concept_results = extract_concepts_sample(articles, client)

    # Generate questions
    questions = generate_questions_sample(articles, concept_results, client)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Articles processed: {len(articles)}")
    print(f"Suitable articles: {sum(1 for r in concept_results.values() if r['suitable'])}")
    print(f"Total concepts: {sum(len(r['concepts']) for r in concept_results.values())}")
    print(f"Questions generated: {len(questions)}")
    print()

    # Save sample output
    output = {
        'metadata': {
            'level': 0,
            'sample_size': len(articles),
            'total_questions': len(questions)
        },
        'questions': questions
    }

    with open('level_0_sample_test.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("Saved to: level_0_sample_test.json")

if __name__ == '__main__':
    main()
