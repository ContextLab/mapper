import json
import hashlib
import random

# Load questions
with open("/Users/jmanning/mapper/data/domains/.working/logic-questions.json") as f:
    questions = json.load(f)

# Load existing domain file
with open("/Users/jmanning/mapper/data/domains/logic.json") as f:
    domain_data = json.load(f)

print(f"Total questions loaded: {len(questions)}")

# Set random seed for reproducible slot assignment
random.seed(42)

assembled = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    qid = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()[:16]

    # Randomly assign correct answer to A/B/C/D
    slots = ["A", "B", "C", "D"]
    random.shuffle(slots)
    correct_slot = slots[0]

    # Build options dict
    options = {}
    options[correct_slot] = q["correct_answer"]
    distractor_slots = [s for s in ["A", "B", "C", "D"] if s != correct_slot]
    for i, ds in enumerate(distractor_slots):
        options[ds] = q["distractors"][i]

    # Sort options by key for consistent display
    options = dict(sorted(options.items()))

    assembled.append({
        "id": qid,
        "question_text": q["question_text"],
        "options": options,
        "correct_answer": correct_slot,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    })

# Verify counts
diff_counts = {}
for q in assembled:
    d = q["difficulty"]
    diff_counts[d] = diff_counts.get(d, 0) + 1
print(f"Difficulty distribution: {diff_counts}")
print(f"Total assembled: {len(assembled)}")

# Check for duplicate IDs
ids = [q["id"] for q in assembled]
if len(ids) != len(set(ids)):
    dupes = [i for i in ids if ids.count(i) > 1]
    print(f"WARNING: Duplicate IDs found: {set(dupes)}")
else:
    print("All IDs unique.")

# Verify answer slot distribution
slot_counts = {}
for q in assembled:
    s = q["correct_answer"]
    slot_counts[s] = slot_counts.get(s, 0) + 1
print(f"Answer slot distribution: {slot_counts}")

# Write to domain file
domain_data["questions"] = assembled
with open("/Users/jmanning/mapper/data/domains/logic.json", "w") as f:
    json.dump(domain_data, f, indent=2, ensure_ascii=False)

print("Successfully wrote logic.json")
