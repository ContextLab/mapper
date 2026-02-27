#!/usr/bin/env python3
"""Assemble political-sociology questions into final domain file."""

import json
import hashlib
import random

# Load questions
with open("/Users/jmanning/mapper/data/domains/.working/political-sociology-questions.json") as f:
    questions = json.load(f)

# Load existing domain file
with open("/Users/jmanning/mapper/data/domains/political-sociology.json") as f:
    domain_data = json.load(f)

# Set random seed for reproducible A/B/C/D slot assignment
random.seed(42)

assembled_questions = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    q_hash = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()[:16]

    # Build options with random slot assignment
    slots = ["A", "B", "C", "D"]
    random.shuffle(slots)

    # First slot gets correct answer, remaining get distractors
    correct_slot = slots[0]
    distractor_slots = slots[1:]

    options = {}
    options[correct_slot] = q["correct_answer"]
    for i, ds in enumerate(distractor_slots):
        options[ds] = q["distractors"][i]

    # Sort options by key so they appear A, B, C, D
    options = dict(sorted(options.items()))

    assembled_questions.append({
        "id": q_hash,
        "question_text": q["question_text"],
        "options": options,
        "correct_answer": correct_slot,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    })

# Update domain data
domain_data["questions"] = assembled_questions

# Write final file
with open("/Users/jmanning/mapper/data/domains/political-sociology.json", "w") as f:
    json.dump(domain_data, f, indent=2)

# Validation
print(f"Total questions: {len(assembled_questions)}")

# Check for duplicate IDs
ids = [q["id"] for q in assembled_questions]
if len(ids) != len(set(ids)):
    print("WARNING: Duplicate IDs found!")
    from collections import Counter
    for qid, count in Counter(ids).items():
        if count > 1:
            print(f"  Duplicate: {qid} ({count} times)")
else:
    print("All IDs are unique.")

# Check difficulty distribution
from collections import Counter
diff_dist = Counter(q["difficulty"] for q in assembled_questions)
print(f"Difficulty distribution: {dict(sorted(diff_dist.items()))}")

# Check answer slot distribution
slot_dist = Counter(q["correct_answer"] for q in assembled_questions)
print(f"Answer slot distribution: {dict(sorted(slot_dist.items()))}")

# Validate word counts
issues = []
for i, q in enumerate(assembled_questions):
    qt_words = len(q["question_text"].split())
    if qt_words > 50:
        issues.append(f"Q{i+1}: question_text has {qt_words} words (max 50)")

    for slot, text in q["options"].items():
        opt_words = len(text.split())
        if opt_words > 25:
            issues.append(f"Q{i+1} option {slot}: {opt_words} words (max 25)")

if issues:
    print(f"\nWord count issues ({len(issues)}):")
    for issue in issues:
        print(f"  {issue}")
else:
    print("All word counts within limits.")

print("\nDone! Final file written to political-sociology.json")
