# Session Notes — 2026-02-21 Art History Question Generation

## Status: SUSPENDED — resume from here

---

## Task: Art History Question Generation (IN PROGRESS)

### Pipeline Progress Summary

| Questions | Pipeline Step | Status |
|-----------|--------------|--------|
| **Q1-Q5** | Step 3 complete (distractors generated) | **Need Step 4 (review distractors) → Step 5 (compile)** |
| **Q6** | Step 2 complete (Q+A reviewed) | **Need Step 3 (distractors) → Step 4 → Step 5** |
| **Q7-Q13** | Step 1 complete (Q+A generated) | **Need Step 2 (review) → Step 3 → Step 4 → Step 5** |
| **Q14-Q50** | Not started | **Need full 5-step pipeline** |

**All progress saved in**: `data/domains/.working/art-history-step1-progress.json`

### Resume Instructions

1. Read `data/domains/.working/art-history-step1-progress.json` — contains all Q+A text, distractors, and step status
2. Read `data/domains/.working/art-history-concepts.json` — full 50-concept list with Wikipedia articles
3. Dispatch in parallel:
   - **Step 4** (review distractors) for Q1-Q5
   - **Step 3** (generate distractors) for Q6
   - **Step 2** (review Q+A) for Q7-Q13
   - **Step 1** (generate Q+A) for Q14-Q20 (Level 2 batch 1)
4. Continue cascading through pipeline until all 50 done
5. After all 50 complete, run Final Assembly (hash IDs, randomize option slots, write to `data/domains/art-history.json`)

### Concept List (50 total)

**Level 1 (Q1-Q13)**: chiaroscuro, Surrealism, Mona Lisa, Art Nouveau, Terracotta Army, Sistine Chapel ceiling, Art Deco, mosaic, Dada, the Louvre, Venus de Milo, Neoclassicism, The Great Wave off Kanagawa

**Level 2 (Q14-Q26)**: sfumato, contrapposto, Benin Bronzes, Mughal painting, vanitas, en plein air, tempera, lost-wax casting, impasto, arabesque, Romanesque art, Pictorialism, installation art

**Level 3 (Q27-Q38)**: Japonisme, provenance, Salon des Refusés, readymades of Marcel Duchamp, Ajanta Caves, Silk Road transmission of art, Olmec colossal heads, cabinet of curiosities, art forgery, Degenerate Art exhibition, kintsugi, Salon (Paris)

**Level 4 (Q39-Q50)**: paragone, Erwin Panofsky, ut pictura poesis, institutional critique, appropriation art, Orientalism (book), polychromy, ekphrasis, repatriation of cultural property, The Work of Art in the Age of Mechanical Reproduction, connoisseurship, wabi-sabi

### Key Review Catches So Far
- **Q2 Surrealism**: Removed "super-reality" hint — etymology made answer guessable
- **Q3 Mona Lisa**: Completely replaced — original tested sfumato (overlaps with Q14 sfumato concept). Now tests "La Gioconda" Italian title
- **Q4 Art Nouveau**: Jugendstil caught as synonym (would be correct) — replaced with Aestheticism
- **Q5 Terracotta Army**: Changed "clay soldiers" → "figures" to avoid giving away "terracotta" + "army"

### Q1-Q5 Distractors (Step 3 complete, need Step 4 review)

**Q1 chiaroscuro** — Correct: "strong contrasts between light and dark to model three-dimensional form"
- D1: "complementary color contrasts to create visual depth"
- D2: "gradual blending of tones to eliminate visible edges" (this is actually sfumato — good distractor)
- D3: "strong contrasts between warm and cool pigments to suggest atmospheric perspective"

**Q2 Surrealism** — Correct: "Surrealism"
- D1: "Dadaism" — D2: "Expressionism" — D3: "Futurism"

**Q3 Mona Lisa** — Correct: "La Gioconda"
- D1: "La Primavera" — D2: "La Pietà" — D3: "La Velata"

**Q4 Art Nouveau** — Correct: "Art Nouveau"
- D1: "Arts and Crafts" — D2: "Art Deco" — D3: "Aestheticism"

**Q5 Terracotta Army** — Correct: "The Terracotta Army, from the mausoleum of Qin Shi Huang"
- D1: "The Terracotta Army, from the burial complex of Emperor Wu of Han"
- D2: "The jade burial suits, from the imperial tombs of the Ming Dynasty"
- D3: "The bronze ritual vessels, from the royal tombs at Anyang during the Shang Dynasty"

### Q6-Q13 Step 1 Results (need Step 2 review)

| Q# | Concept | Question (truncated) | Answer |
|----|---------|---------------------|--------|
| Q6 | Sistine Chapel ceiling | "nine central panels...which book of the Bible?" | "The Book of Genesis" |
| Q7 | Art Deco | "...named after a 1925 Paris exposition...bold geometric forms" | "Art Deco" |
| Q8 | mosaic | "...assembling small pieces...tesserae...into images or patterns" | "A mosaic" |
| Q9 | Dada | "Which best describes Dada...emerged in Zurich during WWI?" | "An anti-art movement that rejected logic..." |
| Q10 | the Louvre | "...originally served what purpose...late 12th century?" | "fortress to defend Paris" |
| Q11 | Venus de Milo | "...ancient Greek marble sculpture...Aphrodite...which museum?" | "The Louvre Museum in Paris" |
| Q12 | Neoclassicism | "...reaction against Rococo excess...revived Greek and Roman..." | "Neoclassicism" |
| Q13 | Great Wave | "...first print in which famous series by Hokusai...?" | "Thirty-six Views of Mount Fuji" |

**NOTE**: Q6 already passed Step 2 review (no changes needed). Q7-Q13 still need Step 2.

---

## Other Context
- Branch: `generate-astrophysics-questions`
- Last commit: `9b12f16` — quantum-physics 50 questions + UI/estimator improvements
- Working questions file: `data/domains/.working/art-history-questions.json` (empty — no questions fully through pipeline yet)
- Domain file to update: `data/domains/art-history.json` (currently 150 questions with 5 difficulty levels — will be replaced with 50 questions, 4 levels)
