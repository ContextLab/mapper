#!/usr/bin/env python3
"""Assemble macroeconomics domain file from questions JSON."""

import json
import hashlib
import random

# Load questions
with open("/Users/jmanning/mapper/data/domains/.working/macroeconomics-questions.json") as f:
    questions = json.load(f)

# Load existing domain file
with open("/Users/jmanning/mapper/data/domains/macroeconomics.json") as f:
    domain = json.load(f)

# Set random seed for reproducible A/B/C/D assignment
random.seed(42)

assembled = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    q_id = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()[:16]

    # Create list of all answers: correct + 3 distractors
    correct = q["correct_answer"]
    distractors = q["distractors"]

    # Assign to random A/B/C/D slots
    slots = ["A", "B", "C", "D"]
    random.shuffle(slots)

    options = {}
    correct_letter = slots[0]  # First slot gets correct answer
    options[correct_letter] = correct
    for i, d in enumerate(distractors):
        options[slots[i + 1]] = d

    # Sort options by letter for clean output
    options = dict(sorted(options.items()))

    entry = {
        "id": q_id,
        "question_text": q["question_text"],
        "options": options,
        "correct_answer": correct_letter,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    }
    assembled.append(entry)

# Update domain file
domain["questions"] = assembled

# Write output
with open("/Users/jmanning/mapper/data/domains/macroeconomics.json", "w") as f:
    json.dump(domain, f, indent=2)

print(f"Assembled {len(assembled)} questions")
print(f"Question IDs: {[q['id'] for q in assembled]}")

# Verify no duplicate IDs
ids = [q["id"] for q in assembled]
if len(ids) != len(set(ids)):
    print("WARNING: Duplicate IDs found!")
    from collections import Counter
    dupes = [item for item, count in Counter(ids).items() if count > 1]
    print(f"Duplicates: {dupes}")
else:
    print("All IDs unique.")

# Verify correct answer distribution
from collections import Counter
dist = Counter(q["correct_answer"] for q in assembled)
print(f"Answer distribution: {dict(sorted(dist.items()))}")

# Verify difficulty distribution
diff_dist = Counter(q["difficulty"] for q in assembled)
print(f"Difficulty distribution: {dict(sorted(diff_dist.items()))}")
