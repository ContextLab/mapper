import json
import hashlib
import random

# Load the questions
with open("/Users/jmanning/mapper/data/domains/.working/philosophy-of-mind-questions.json", "r") as f:
    questions = json.load(f)

# Load the existing domain file
with open("/Users/jmanning/mapper/data/domains/philosophy-of-mind.json", "r") as f:
    domain_data = json.load(f)

# Set random seed
random.seed(42)

assembled_questions = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    question_id = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()[:16]

    # Build options with random slot assignment
    correct = q["correct_answer"]
    distractors = q["distractors"]

    # Create list of all answers: correct + 3 distractors
    all_answers = [correct] + distractors

    # Assign to random slots A, B, C, D
    slots = ["A", "B", "C", "D"]
    random.shuffle(slots)

    options = {}
    correct_slot = slots[0]  # First slot gets the correct answer
    options[correct_slot] = correct
    for i, distractor in enumerate(distractors):
        options[slots[i + 1]] = distractor

    # Sort options by key (A, B, C, D)
    sorted_options = dict(sorted(options.items()))

    assembled_q = {
        "id": question_id,
        "question_text": q["question_text"],
        "options": sorted_options,
        "correct_answer": correct_slot,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    }
    assembled_questions.append(assembled_q)

print(f"Total questions assembled: {len(assembled_questions)}")

# Verify all IDs are unique
ids = [q["id"] for q in assembled_questions]
print(f"Unique IDs: {len(set(ids))}")

# Verify difficulty distribution
from collections import Counter
diff_counts = Counter(q["difficulty"] for q in assembled_questions)
print(f"Difficulty distribution: {dict(sorted(diff_counts.items()))}")

# Verify correct_answer distribution
answer_counts = Counter(q["correct_answer"] for q in assembled_questions)
print(f"Answer slot distribution: {dict(sorted(answer_counts.items()))}")

# Update domain data
domain_data["questions"] = assembled_questions

# Write final file
with open("/Users/jmanning/mapper/data/domains/philosophy-of-mind.json", "w") as f:
    json.dump(domain_data, f, indent=2)

print("Successfully wrote philosophy-of-mind.json")
