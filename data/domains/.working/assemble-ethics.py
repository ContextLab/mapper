import json
import hashlib
import random

# Load questions
with open("/Users/jmanning/mapper/data/domains/.working/ethics-questions.json", "r") as f:
    questions = json.load(f)

# Load existing domain file
with open("/Users/jmanning/mapper/data/domains/ethics.json", "r") as f:
    domain_data = json.load(f)

random.seed(42)

assembled_questions = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    q_id = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()[:16]

    # Create options with random slot assignment
    correct = q["correct_answer"]
    distractors = q["distractors"]

    # All 4 answers: correct + 3 distractors
    all_answers = [correct] + distractors
    # Shuffle to randomize placement
    random.shuffle(all_answers)

    # Find which slot (A/B/C/D) the correct answer ended up in
    slots = ["A", "B", "C", "D"]
    options = {}
    correct_slot = None
    for i, slot in enumerate(slots):
        options[slot] = all_answers[i]
        if all_answers[i] == correct:
            correct_slot = slot

    assembled_questions.append({
        "id": q_id,
        "question_text": q["question_text"],
        "options": options,
        "correct_answer": correct_slot,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    })

# Build final output
output = {
    "domain": domain_data["domain"],
    "questions": assembled_questions,
    "labels": domain_data.get("labels", []),
    "articles": domain_data.get("articles", [])
}

with open("/Users/jmanning/mapper/data/domains/ethics.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Successfully assembled {len(assembled_questions)} questions.")
print(f"Question IDs:")
for q in assembled_questions:
    print(f"  {q['id']} | D{q['difficulty']} | {q['correct_answer']} | {q['question_text'][:60]}...")
