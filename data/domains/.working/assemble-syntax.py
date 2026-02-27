#!/usr/bin/env python3
"""Assemble syntax-questions.json into the final syntax.json domain file."""

import json
import hashlib
import random

# Load questions
with open("/Users/jmanning/mapper/data/domains/.working/syntax-questions.json") as f:
    questions = json.load(f)

# Load existing domain file
with open("/Users/jmanning/mapper/data/domains/syntax.json") as f:
    domain_data = json.load(f)

print(f"Loaded {len(questions)} questions")

# Verify counts
difficulties = {}
for q in questions:
    d = q["difficulty"]
    difficulties[d] = difficulties.get(d, 0) + 1
print(f"Difficulty distribution: {difficulties}")

# Set seed for reproducible randomization
random.seed(42)

slots = ["A", "B", "C", "D"]

assembled = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    sha = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()
    qid = sha[:16]

    # Randomly assign correct answer and distractors to A/B/C/D
    all_answers = [q["correct_answer"]] + q["distractors"]

    # Shuffle the slot assignment
    slot_order = list(slots)
    random.shuffle(slot_order)

    options = {}
    correct_slot = slot_order[0]  # First shuffled slot gets correct answer
    options[correct_slot] = q["correct_answer"]
    for i, distractor in enumerate(q["distractors"]):
        options[slot_order[i + 1]] = distractor

    # Sort options by key for consistent display
    sorted_options = {k: options[k] for k in sorted(options.keys())}

    assembled.append({
        "id": qid,
        "question_text": q["question_text"],
        "options": sorted_options,
        "correct_answer": correct_slot,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    })

# Check for duplicate IDs
ids = [q["id"] for q in assembled]
if len(ids) != len(set(ids)):
    dupes = [i for i in ids if ids.count(i) > 1]
    print(f"WARNING: Duplicate IDs found: {dupes}")
else:
    print(f"All {len(ids)} IDs are unique")

# Check answer distribution
answer_dist = {}
for q in assembled:
    a = q["correct_answer"]
    answer_dist[a] = answer_dist.get(a, 0) + 1
print(f"Answer slot distribution: {answer_dist}")

# Update domain data
domain_data["questions"] = assembled

# Write final file
with open("/Users/jmanning/mapper/data/domains/syntax.json", "w") as f:
    json.dump(domain_data, f, indent=2)

print(f"\nWrote {len(assembled)} questions to syntax.json")

# Print first 3 questions as samples
for i, q in enumerate(assembled[:3]):
    print(f"\nSample {i+1}: {q['id']}")
    print(f"  Q: {q['question_text']}")
    print(f"  Correct: {q['correct_answer']}")
    print(f"  Options: {list(q['options'].keys())}")
