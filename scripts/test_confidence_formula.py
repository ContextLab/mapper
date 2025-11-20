#!/usr/bin/env python3
"""
Test different confidence formula approaches to find one that:
1. Starts at 0% when 0 questions asked
2. Approaches 100% as coverage improves
3. Never goes negative
"""

import numpy as np
import random

def generate_grid_centers(grid_size=39):
    """Generate all grid cell centers"""
    centers = []
    for gx in range(grid_size):
        for (gy) in range(grid_size):
            x = (gx + 0.5) / grid_size
            y = (gy + 0.5) / grid_size
            centers.append((x, y))
    return centers

def generate_questions(n_questions=1000):
    """Generate random question coordinates"""
    questions = []
    for _ in range(n_questions):
        x = random.random()
        y = random.random()
        questions.append((x, y))
    return questions

def distance(p1, p2):
    """Euclidean distance between two points"""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def compute_X(centers, asked_questions):
    """X = max distance from any cell center to nearest asked question"""
    if len(asked_questions) == 0:
        return float('inf')

    X = 0
    for center in centers:
        min_dist = min(distance(center, q) for q in asked_questions)
        X = max(X, min_dist)
    return X

def compute_Y_all_questions(centers, all_questions):
    """Y = max distance from any cell center to ANY question (CURRENT BROKEN APPROACH)"""
    Y = 0
    for center in centers:
        min_dist = min(distance(center, q) for q in all_questions)
        Y = max(Y, min_dist)
    return Y

def compute_Y_theoretical_max():
    """Y = theoretical maximum distance in [0,1] x [0,1] space"""
    # Maximum distance is from one corner to opposite corner
    return np.sqrt(2)

def compute_Y_grid_diagonal(grid_size=39):
    """Y = diagonal of a single grid cell (reasonable worst case)"""
    cell_size = 1.0 / grid_size
    return np.sqrt(2) * cell_size

# Test different formulas
print("Testing Confidence Formulas")
print("=" * 80)

centers = generate_grid_centers(39)
all_questions = generate_questions(1000)

print(f"\nGrid: 39x39 = {len(centers)} cells")
print(f"Total questions available: {len(all_questions)}")
print()

# Simulate asking questions one by one
test_points = [1, 10, 50, 100, 500, 1000]

print("\n" + "=" * 80)
print("FORMULA 1 (CURRENT - BROKEN): confidence = 1 - (X / Y_all_questions)")
print("=" * 80)
for n in test_points:
    asked = all_questions[:n]
    X = compute_X(centers, asked)
    Y = compute_Y_all_questions(centers, all_questions)
    confidence = 1 - (X / Y) if Y > 0 else 0
    print(f"After {n:4d} questions: X={X:.4f}, Y={Y:.4f}, Confidence={confidence*100:7.1f}%")

print("\n" + "=" * 80)
print("FORMULA 2: confidence = 1 - (X / Y_theoretical_max)")
print("  where Y_theoretical_max = sqrt(2) (corner to corner)")
print("=" * 80)
Y_max = compute_Y_theoretical_max()
print(f"Y (theoretical max) = {Y_max:.4f}")
print()
for n in test_points:
    asked = all_questions[:n]
    X = compute_X(centers, asked)
    confidence = 1 - (X / Y_max)
    confidence = max(0, min(1, confidence))  # Clamp to [0, 1]
    print(f"After {n:4d} questions: X={X:.4f}, Confidence={confidence*100:7.1f}%")

print("\n" + "=" * 80)
print("FORMULA 3: confidence = 1 - (X / Y_half_space)")
print("  where Y_half_space = 0.5 * sqrt(2) (half the maximum distance)")
print("=" * 80)
Y_half = compute_Y_theoretical_max() / 2
print(f"Y (half space) = {Y_half:.4f}")
print()
for n in test_points:
    asked = all_questions[:n]
    X = compute_X(centers, asked)
    confidence = 1 - (X / Y_half)
    confidence = max(0, min(1, confidence))  # Clamp to [0, 1]
    print(f"After {n:4d} questions: X={X:.4f}, Confidence={confidence*100:7.1f}%")

print("\n" + "=" * 80)
print("FORMULA 4: confidence = exp(-X / lambda)")
print("  where lambda = 0.1 (characteristic length scale)")
print("=" * 80)
lambda_param = 0.1
print(f"Lambda (decay length) = {lambda_param:.4f}")
print()
for n in test_points:
    asked = all_questions[:n]
    X = compute_X(centers, asked)
    confidence = np.exp(-X / lambda_param)
    print(f"After {n:4d} questions: X={X:.4f}, Confidence={confidence*100:7.1f}%")

print("\n" + "=" * 80)
print("FORMULA 5 (USER'S NEW SPEC): confidence = (Y - Z) / (Y - X)")
print("  X = best case (max dist with ALL questions answered)")
print("  Y = worst case (max dist with 1 corner question)")
print("  Z = current observed max dist to nearest asked question")
print("=" * 80)

# X: Best case - compute with ALL questions
X = compute_X(centers, all_questions)
print(f"X (best case - all questions): {X:.4f}")

# Y: Worst case - one question at a corner (furthest from opposite corner)
# Place question at (0, 0), furthest cell is at (1, 1)
worst_case_question = [(0.0, 0.0)]
Y = compute_X(centers, worst_case_question)
print(f"Y (worst case - 1 corner question): {Y:.4f}")
print()

for n in test_points:
    asked = all_questions[:n]
    Z = compute_X(centers, asked)

    # Confidence: (Y - Z) / (Y - X)
    # When Z = Y (worst case), confidence = 0
    # When Z = X (best case), confidence = 1
    if Y > X:
        confidence = (Y - Z) / (Y - X)
        confidence = max(0, min(1, confidence))  # Clamp to [0, 1]
    else:
        confidence = 1.0 if Z <= X else 0.0

    print(f"After {n:4d} questions: Z={Z:.4f}, Confidence={confidence*100:7.1f}%")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)
print()
print("Formula 5 is the most intuitive:")
print("  - X = max distance when ALL questions answered (best coverage)")
print("  - Y = max distance when 1 corner question answered (worst coverage)")
print("  - Z = current max distance")
print("  - Confidence scales linearly from Y (0%) to X (100%)")
print()
print("This directly answers: 'What percentage of the way are we from worst to best?'")
print()
print("RECOMMENDED: Formula 5 - confidence = (Y - Z) / (Y - X)")
