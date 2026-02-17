#!/usr/bin/env python3
"""
Generate domain-specific quiz questions using GPT-5-nano Batch API.

Two-pass pipeline:
  Pass 1 (CURATE): For each domain, send article titles from the UMAP region
    to GPT-5-nano to select topically relevant, conceptually rich articles.
  Pass 2 (GENERATE): For each curated article, generate a deep conceptual MCQ
    that tests understanding — not rote memorization or trivia.

Usage:
    python scripts/generate_domain_questions.py
    python scripts/generate_domain_questions.py --domain physics
    python scripts/generate_domain_questions.py --force
"""

import hashlib
import json
import os
import random
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# macOS threading fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Import utils directly — bypassing __init__.py which pulls in wikipediaapi
import importlib.util

_utils_dir = Path(__file__).parent / "utils"


def _import_from(module_name, file_name):
    spec = importlib.util.spec_from_file_location(module_name, _utils_dir / file_name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_api_utils = _import_from("api_utils", "api_utils.py")
_batch_utils = _import_from("openai_batch", "openai_batch.py")

load_openai_key = _api_utils.load_openai_key
batch_with_cache = _batch_utils.batch_with_cache

from openai import OpenAI

# ── Constants ──────────────────────────────────────────────────────────────────

QUESTIONS_PER_DOMAIN = 50
ARTICLES_TO_CURATE = 120
DIFFICULTY_LEVELS = [1, 2, 3, 4, 5]
QUESTIONS_PER_LEVEL = QUESTIONS_PER_DOMAIN // len(DIFFICULTY_LEVELS)  # 10

# ── Prompts ────────────────────────────────────────────────────────────────────

CURATION_SYSTEM_PROMPT = """You are selecting Wikipedia articles for a quiz about a specific academic domain.

Given a numbered list of article titles with short excerpts, select ALL articles that are relevant to the stated domain. Be INCLUSIVE — if an article could plausibly generate a question about the domain, include it.

Return ONLY a JSON array of the selected article numbers. No explanation, no text outside the array.
Example: [1, 3, 5, 7, 8, 12, 15, 18, 22, 25, 28, 31, 34, 38, 42, 45]

INCLUDE articles about:
- Core concepts, theories, laws, processes in the domain
- Important people who made contributions to the domain
- Applications, experiments, discoveries in the domain
- Historical events that shaped the domain
- Interdisciplinary connections to the domain

EXCLUDE only:
- Articles with NO connection to the domain whatsoever
- Stubs with insufficient content for a quiz question
- Disambiguation pages"""


QUESTION_SYSTEM_PROMPT = """You are an expert educator creating quiz questions for a university-level knowledge assessment.

Given a Wikipedia article title and excerpt, generate ONE multiple-choice question (A, B, C, D) that tests DEEP CONCEPTUAL UNDERSTANDING.

QUESTION QUALITY REQUIREMENTS:
1. Test UNDERSTANDING, not memorization. Bad: "In what year was X born?" Good: "What mechanism explains X's effect on Y?"
2. Require the reader to UNDERSTAND a concept, relationship, cause-effect, or process.
3. All four options must be plausible to someone with partial knowledge. Distractors should represent common misconceptions or related-but-incorrect concepts.
4. The correct answer MUST be directly supported by the article excerpt.
5. The question must be self-contained — no references to "the article" or "the passage."
6. Use LaTeX for math: $x^2$, $\\frac{1}{2}$, $\\int_0^\\infty$

DIFFICULTY LEVELS:
- 1: Identify a key concept or definition
- 2: Understand a relationship or distinguish between related concepts
- 3: Apply knowledge — why does X happen? What would change if Y?
- 4: Analyze — compare mechanisms, evaluate claims, identify assumptions
- 5: Synthesize — connect ideas, evaluate implications

BAD PATTERNS (NEVER USE):
- "In which year/country/city...?"
- "What is the name of...?"
- "Who was the first to...?"

GOOD PATTERNS:
- "What mechanism/process explains...?"
- "How does X relate to Y?"
- "Why does X occur rather than Y?"
- "What distinguishes X from Y?"
- "If X were changed, what would happen to Y?"

OUTPUT (strict JSON, no markdown):
{"question_text": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "correct_answer": "B", "concepts_tested": ["concept1", "concept2"]}"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate domain quiz questions (two-pass)"
    )
    parser.add_argument(
        "--domain", type=str, default=None, help="Process specific domain only"
    )
    parser.add_argument(
        "--force", action="store_true", help="Regenerate even if output exists"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show plan without API calls"
    )
    parser.add_argument(
        "--skip-curation",
        action="store_true",
        help="Skip pass 1, use random articles (for testing)",
    )
    return parser.parse_args()


def load_domains(path: Path) -> List[Dict]:
    print(f"Loading domains from {path}...")
    with open(path, "r") as f:
        domains = json.load(f)["domains"]
    print(f"  ✓ {len(domains)} domains")
    return domains


def load_articles(path: Path) -> List[Dict]:
    print(f"Loading articles from {path}...")
    with open(path, "r") as f:
        articles = json.load(f)
    valid = [a for a in articles if a.get("excerpt") and len(a["excerpt"].strip()) > 80]
    print(f"  ✓ {len(valid)} articles with excerpts (of {len(articles)} total)")
    return valid


def get_articles_in_region(articles: List[Dict], region: Dict) -> List[Dict]:
    return [
        a
        for a in articles
        if region["x_min"] <= a["x"] <= region["x_max"]
        and region["y_min"] <= a["y"] <= region["y_max"]
    ]


def compute_question_id(question_text: str, domain_id: str) -> str:
    raw = f"{domain_id}:{question_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _extract_json_object(text: str) -> Optional[Dict]:
    """Brace-matching JSON extraction for responses with reasoning tokens."""
    start = text.find("{")
    if start < 0:
        return None
    depth, in_string, escape_next = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\" and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _extract_json_array(text: str) -> Optional[List]:
    """Bracket-matching JSON array extraction."""
    start = text.find("[")
    if start < 0:
        return None
    depth, in_string, escape_next = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\" and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def get_domain_hierarchy(domain: Dict, all_domains: List[Dict]) -> List[str]:
    ids = [domain["id"]]
    if domain.get("parent_id"):
        ids.append(domain["parent_id"])
    if "all" not in ids:
        ids.append("all")
    return ids


def assign_difficulty_levels(count: int) -> List[int]:
    levels = []
    for level in DIFFICULTY_LEVELS:
        levels.extend([level] * QUESTIONS_PER_LEVEL)
    while len(levels) < count:
        levels.append(3)
    random.shuffle(levels)
    return levels[:count]


# ── Domain Keywords (for pre-filtering) ───────────────────────────────────────

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "all": [],  # No filtering for "all" domain
    "physics": [
        "physics",
        "quantum",
        "relativity",
        "thermodynamics",
        "mechanics",
        "electromagnetism",
        "photon",
        "electron",
        "neutron",
        "proton",
        "momentum",
        "magnetic",
        "electric",
        "gravity",
        "entropy",
        "atom",
        "plasma",
        "optics",
        "laser",
        "superconductor",
        "semiconductor",
        "oscillation",
        "frequency",
        "wavelength",
        "spectrum",
        "acceleration",
        "velocity",
        "diffraction",
        "interference",
        "refraction",
        "tensor",
        "boson",
        "fermion",
        "quark",
        "lepton",
        "hadron",
        "meson",
        "baryon",
        "neutrino",
        "higgs",
        "isotope",
        "fusion",
        "fission",
        "half-life",
    ],
    "neuroscience": [
        "neuroscience",
        "brain",
        "neuron",
        "neural",
        "cortex",
        "synapse",
        "neurotransmitter",
        "dopamine",
        "serotonin",
        "cognitive",
        "hippocampus",
        "amygdala",
        "cerebral",
        "cerebellum",
        "thalamus",
        "axon",
        "dendrite",
        "glia",
        "myelin",
        "prefrontal",
        "temporal",
        "parietal",
        "occipital",
        "limbic",
        "basal ganglia",
        "brainstem",
        "spinal cord",
        "perception",
        "consciousness",
        "memory",
        "attention",
        "learning",
        "plasticity",
        "neuroplasticity",
        "electroencephalography",
        "eeg",
        "fmri",
        "neuroimaging",
        "neuropathology",
        "neurological",
        "epilepsy",
        "alzheimer",
        "parkinson",
        "dementia",
        "psychiatric",
        "psychopharmacology",
    ],
    "mathematics": [
        "mathematics",
        "mathematical",
        "theorem",
        "proof",
        "equation",
        "algebra",
        "geometry",
        "topology",
        "calculus",
        "integral",
        "derivative",
        "differential",
        "matrix",
        "vector",
        "tensor",
        "polynomial",
        "function",
        "convergence",
        "series",
        "sequence",
        "limit",
        "infinity",
        "prime",
        "modular",
        "group theory",
        "ring",
        "field theory",
        "manifold",
        "dimension",
        "space",
        "metric",
        "norm",
        "eigenvalue",
        "eigenvector",
        "determinant",
        "combinatorics",
        "graph theory",
        "probability",
        "statistics",
        "stochastic",
        "algorithm",
        "computation",
        "conjecture",
        "lemma",
        "corollary",
        "axiom",
        "set theory",
        "logic",
        "number theory",
        "arithmetic",
        "isomorphism",
        "homomorphism",
    ],
    "art-history": [
        "art",
        "painting",
        "sculpture",
        "architecture",
        "museum",
        "gallery",
        "renaissance",
        "baroque",
        "gothic",
        "medieval",
        "impressionism",
        "expressionism",
        "cubism",
        "surrealism",
        "modernism",
        "postmodern",
        "contemporary art",
        "fresco",
        "mosaic",
        "ceramic",
        "pottery",
        "tapestry",
        "engraving",
        "etching",
        "lithograph",
        "woodcut",
        "portrait",
        "landscape",
        "still life",
        "cathedral",
        "church",
        "temple",
        "palace",
        "castle",
        "monument",
        "heritage",
        "aesthetic",
        "artistic",
        "painter",
        "sculptor",
        "architect",
        "exhibition",
        "collection",
        "artifact",
        "antiquity",
        "classical",
        "romantic",
        "neoclassical",
    ],
    "biology": [
        "biology",
        "biological",
        "cell",
        "organism",
        "species",
        "evolution",
        "genetic",
        "gene",
        "dna",
        "rna",
        "protein",
        "enzyme",
        "metabolism",
        "mitosis",
        "meiosis",
        "chromosome",
        "mutation",
        "natural selection",
        "ecology",
        "ecosystem",
        "biodiversity",
        "taxonomy",
        "phylogenetic",
        "microbiology",
        "bacteria",
        "virus",
        "fungus",
        "plant",
        "animal",
        "mammal",
        "vertebrate",
        "invertebrate",
        "marine biology",
        "botany",
        "zoology",
        "anatomy",
        "physiology",
        "biochemistry",
        "molecular biology",
        "immunology",
        "pathogen",
        "antibiotic",
        "photosynthesis",
        "respiration",
        "fermentation",
        "symbiosis",
    ],
}

# Sub-domain keywords inherit from parent + add specific ones
DOMAIN_KEYWORDS["astrophysics"] = DOMAIN_KEYWORDS["physics"] + [
    "astrophysics",
    "astronomy",
    "star",
    "galaxy",
    "nebula",
    "cosmos",
    "cosmic",
    "supernova",
    "black hole",
    "pulsar",
    "quasar",
    "redshift",
    "hubble",
    "telescope",
    "orbit",
    "planet",
    "solar",
    "lunar",
    "comet",
    "asteroid",
    "meteor",
    "exoplanet",
    "dark matter",
    "dark energy",
    "big bang",
    "expansion",
    "constellation",
    "celestial",
    "stellar",
    "interstellar",
    "intergalactic",
    "magnetar",
    "white dwarf",
]
DOMAIN_KEYWORDS["quantum-physics"] = DOMAIN_KEYWORDS["physics"] + [
    "quantum",
    "superposition",
    "entanglement",
    "decoherence",
    "wavefunction",
    "wave function",
    "schrodinger",
    "heisenberg",
    "uncertainty",
    "planck",
    "quantization",
    "quantum field",
    "quantum mechanics",
    "quantum electrodynamics",
    "qed",
    "qcd",
    "quantum chromodynamics",
    "quantum computing",
    "qubit",
    "tunneling",
    "tunnelling",
    "dirac",
    "pauli",
    "bell inequality",
]
DOMAIN_KEYWORDS["european-art-history"] = DOMAIN_KEYWORDS["art-history"] + [
    "european",
    "italy",
    "italian",
    "france",
    "french",
    "spain",
    "spanish",
    "dutch",
    "flemish",
    "german",
    "british",
    "english",
    "greek",
    "roman",
    "byzantine",
    "romanesque",
    "art nouveau",
    "pre-raphaelite",
    "mannerism",
    "rococo",
    "fauvism",
    "dada",
]
DOMAIN_KEYWORDS["chinese-art-history"] = DOMAIN_KEYWORDS["art-history"] + [
    "chinese",
    "china",
    "dynasty",
    "tang",
    "song",
    "ming",
    "qing",
    "han",
    "zhou",
    "calligraphy",
    "jade",
    "silk",
    "porcelain",
    "lacquer",
    "scroll",
    "ink",
    "brush painting",
    "imperial",
    "confucian",
    "buddhist",
    "taoist",
    "pagoda",
    "forbidden city",
]
DOMAIN_KEYWORDS["molecular-cell-biology"] = DOMAIN_KEYWORDS["biology"] + [
    "molecular",
    "cell",
    "organelle",
    "membrane",
    "cytoplasm",
    "nucleus",
    "ribosome",
    "mitochondria",
    "endoplasmic reticulum",
    "golgi",
    "lysosome",
    "vesicle",
    "signal transduction",
    "receptor",
    "kinase",
    "transcription",
    "translation",
    "replication",
    "apoptosis",
    "autophagy",
    "stem cell",
    "differentiation",
]
DOMAIN_KEYWORDS["genetics"] = DOMAIN_KEYWORDS["biology"] + [
    "genetics",
    "genome",
    "genotype",
    "phenotype",
    "allele",
    "heredity",
    "inheritance",
    "mendel",
    "recombination",
    "crossing over",
    "epigenetics",
    "methylation",
    "crispr",
    "gene expression",
    "transcription factor",
    "promoter",
    "enhancer",
    "intron",
    "exon",
    "splicing",
    "polymerase",
    "sequencing",
    "genomics",
    "proteomics",
]
DOMAIN_KEYWORDS["cognitive-neuroscience"] = DOMAIN_KEYWORDS["neuroscience"] + [
    "cognitive",
    "cognition",
    "perception",
    "attention",
    "memory",
    "language",
    "decision",
    "executive function",
    "working memory",
    "long-term memory",
    "short-term memory",
    "visual",
    "auditory",
    "emotion",
    "social cognition",
    "theory of mind",
    "metacognition",
]
DOMAIN_KEYWORDS["computational-neuroscience"] = DOMAIN_KEYWORDS["neuroscience"] + [
    "computational",
    "model",
    "simulation",
    "neural network",
    "artificial neural",
    "algorithm",
    "information processing",
    "coding",
    "decoding",
    "bayesian",
    "spiking",
    "connectome",
    "network",
    "dynamics",
    "oscillation",
    "synchronization",
]
DOMAIN_KEYWORDS["neurobiology"] = DOMAIN_KEYWORDS["neuroscience"] + [
    "neurobiology",
    "cell biology",
    "molecular",
    "ion channel",
    "receptor",
    "signaling",
    "pathway",
    "development",
    "regeneration",
    "degeneration",
    "neuropeptide",
    "neuroendocrine",
    "autonomic",
    "peripheral",
    "central nervous system",
    "blood-brain barrier",
]
DOMAIN_KEYWORDS["calculus"] = DOMAIN_KEYWORDS["mathematics"] + [
    "calculus",
    "integral",
    "derivative",
    "differentiation",
    "integration",
    "limit",
    "continuity",
    "series",
    "convergence",
    "taylor",
    "fourier",
    "laplace",
    "differential equation",
    "partial differential",
    "ordinary differential",
    "gradient",
    "divergence",
    "curl",
    "stokes",
    "green",
    "gauss",
]
DOMAIN_KEYWORDS["linear-algebra"] = DOMAIN_KEYWORDS["mathematics"] + [
    "linear algebra",
    "matrix",
    "vector",
    "eigenvalue",
    "eigenvector",
    "determinant",
    "rank",
    "null space",
    "column space",
    "row space",
    "linear transformation",
    "orthogonal",
    "unitary",
    "hermitian",
    "diagonal",
    "triangular",
    "decomposition",
    "factorization",
    "svd",
    "singular value",
    "least squares",
    "inner product",
]
DOMAIN_KEYWORDS["number-theory"] = DOMAIN_KEYWORDS["mathematics"] + [
    "number theory",
    "prime",
    "integer",
    "divisibility",
    "modular",
    "congruence",
    "diophantine",
    "fermat",
    "euler",
    "gauss",
    "riemann",
    "zeta function",
    "algebraic number",
    "transcendental",
    "quadratic",
    "reciprocity",
    "sieve",
    "factorization",
    "cryptography",
]
DOMAIN_KEYWORDS["probability-statistics"] = DOMAIN_KEYWORDS["mathematics"] + [
    "probability",
    "statistics",
    "statistical",
    "random",
    "distribution",
    "expected value",
    "variance",
    "standard deviation",
    "regression",
    "hypothesis",
    "confidence interval",
    "bayesian",
    "frequentist",
    "correlation",
    "covariance",
    "sampling",
    "estimation",
    "inference",
    "likelihood",
    "markov",
    "poisson",
    "gaussian",
    "normal distribution",
    "central limit",
    "law of large numbers",
    "chi-squared",
    "p-value",
]


def keyword_score(article: Dict, keywords: List[str]) -> int:
    """Score an article by keyword matches in title + excerpt."""
    if not keywords:
        return 1  # "all" domain — everything passes
    text = (article.get("title", "") + " " + article.get("excerpt", "")).lower()
    return sum(1 for kw in keywords if kw.lower() in text)


# ── Pass 1: Article Curation ──────────────────────────────────────────────────


def curate_articles(
    client: OpenAI, domain: Dict, region_articles: List[Dict]
) -> List[Dict]:
    """Two-stage curation: keyword pre-filter → batched LLM selection."""
    domain_name = domain["name"]
    domain_id = domain["id"]

    if len(region_articles) <= ARTICLES_TO_CURATE:
        return region_articles

    keywords = DOMAIN_KEYWORDS.get(domain_id, [])

    if domain_id == "all":
        all_kw = set()
        for kw_list in DOMAIN_KEYWORDS.values():
            all_kw.update(kw_list)
        all_kw_list = list(all_kw)
        scored = [(keyword_score(a, all_kw_list), a) for a in region_articles]
        matched = [(s, a) for s, a in scored if s > 0]
        matched.sort(key=lambda x: -x[0])
        candidates = [a for _, a in matched]
        print(f"    'all' domain — {len(candidates)} keyword-matched from any domain")
    elif keywords:
        scored = [(keyword_score(a, keywords), a) for a in region_articles]
        matched = [(s, a) for s, a in scored if s > 0]
        matched.sort(key=lambda x: -x[0])
        candidates = [a for _, a in matched]
        print(
            f"    Keyword pre-filter: {len(candidates)}/{len(region_articles)} matched"
        )
    else:
        candidates = list(region_articles)
        random.shuffle(candidates)
        print(f"    No keyword filter: {len(candidates)} candidates")

    if len(candidates) < 20:
        print(
            f"    ⚠ Only {len(candidates)} keyword matches — using all without LLM curation"
        )
        return candidates

    max_to_send = min(len(candidates), 500)
    candidates = candidates[:max_to_send]
    random.shuffle(candidates)

    BATCH_SIZE = 50
    batches = [
        candidates[i : i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)
    ]

    requests = []
    batch_map = {}
    for batch_idx, batch in enumerate(batches):
        lines = []
        for idx, a in enumerate(batch):
            excerpt = a.get("excerpt", "")[:200]
            lines.append(f"{idx + 1}. {a['title']} — {excerpt}")

        cid = f"curate-{domain_id}-b{batch_idx}"
        requests.append(
            {
                "custom_id": cid,
                "user_prompt": f"Domain: {domain_name}\n\nSelect ALL articles relevant to {domain_name}.\n\n{chr(10).join(lines)}",
            }
        )
        batch_map[cid] = batch

    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=CURATION_SYSTEM_PROMPT,
        description=f"Curate: {domain_name} ({len(batches)} batches)",
        model="gpt-5-nano",
        max_tokens=8000,
        response_format=None,
        poll_interval=30,
        timeout=None,
    )

    curated = []
    for cid, response in results.items():
        batch = batch_map.get(cid, [])
        if not batch:
            continue

        try:
            indices = json.loads(response.strip())
        except json.JSONDecodeError:
            indices = _extract_json_array(response)

        if not indices or not isinstance(indices, list):
            print(f"    ⚠ Batch {cid} parse failed — skipping batch")
            continue

        for idx in indices:
            if isinstance(idx, int) and 1 <= idx <= len(batch):
                curated.append(batch[idx - 1])

    seen_titles = set()
    unique_curated = []
    for a in curated:
        if a["title"] not in seen_titles:
            seen_titles.add(a["title"])
            unique_curated.append(a)
    curated = unique_curated

    print(
        f"    LLM selected {len(curated)} relevant articles from {max_to_send} candidates"
    )

    if len(curated) < 20:
        print(
            f"    ⚠ Too few curated ({len(curated)}) — using top keyword-scored instead"
        )
        curated = candidates[:ARTICLES_TO_CURATE]

    return curated[:ARTICLES_TO_CURATE]


# ── Pass 2: Question Generation ───────────────────────────────────────────────


def parse_question_response(
    response_text: str,
    article: Dict,
    difficulty: int,
    domain: Dict,
    domain_ids: List[str],
) -> Optional[Dict]:
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _extract_json_object(text)
        if data is None:
            return None

    for field in ["question_text", "options", "correct_answer"]:
        if field not in data:
            return None
    options = data["options"]
    if not isinstance(options, dict):
        return None
    for letter in ["A", "B", "C", "D"]:
        if letter not in options:
            return None
    correct = data["correct_answer"].strip().upper()
    if correct not in ["A", "B", "C", "D"]:
        return None

    return {
        "id": compute_question_id(data["question_text"].strip(), domain["id"]),
        "question_text": data["question_text"].strip(),
        "options": {k: v.strip() for k, v in options.items()},
        "correct_answer": correct,
        "difficulty": difficulty,
        "x": article["x"],
        "y": article["y"],
        "z": 0.0,
        "source_article": article["title"],
        "domain_ids": domain_ids,
        "concepts_tested": data.get("concepts_tested", []),
    }


def generate_questions_batch(
    client: OpenAI,
    articles: List[Dict],
    difficulties: List[int],
    domain: Dict,
    domain_ids: List[str],
    label: str,
) -> List[Dict]:
    requests = []
    article_map = {}
    for i, (article, diff) in enumerate(zip(articles, difficulties)):
        cid = f"{domain['id']}--{label}-q{i:03d}"
        excerpt = article.get("excerpt", "")[:1500]
        requests.append(
            {
                "custom_id": cid,
                "user_prompt": f"Difficulty: {diff}/5\nArticle: {article['title']}\nExcerpt: {excerpt}\n\nGenerate ONE deep conceptual question at difficulty {diff}.",
            }
        )
        article_map[cid] = (article, diff)

    results = batch_with_cache(
        client=client,
        requests=requests,
        system_prompt=QUESTION_SYSTEM_PROMPT,
        description=f"{label}: {domain['name']}",
        model="gpt-5-nano",
        max_tokens=8000,
        response_format=None,
        poll_interval=60,
        timeout=None,
    )

    questions = []
    for cid, resp in results.items():
        article, diff = article_map[cid]
        q = parse_question_response(resp, article, diff, domain, domain_ids)
        if q:
            questions.append(q)
    return questions


# ── Domain Orchestrator ───────────────────────────────────────────────────────


def generate_for_domain(
    client: OpenAI,
    domain: Dict,
    all_articles: List[Dict],
    all_domains: List[Dict],
    output_dir: Path,
    force: bool = False,
    dry_run: bool = False,
    skip_curation: bool = False,
) -> Optional[List[Dict]]:
    domain_id = domain["id"]
    output_path = output_dir / f"{domain_id}_questions.json"

    if output_path.exists() and not force:
        print(f"\n  ⏭ {domain_id} — exists (use --force)")
        with open(output_path, "r") as f:
            return json.load(f)

    region = domain["region"]
    print(f"\n{'=' * 60}")
    print(f"Domain: {domain['name']} ({domain_id})")
    print(
        f"Region: x=[{region['x_min']:.2f}, {region['x_max']:.2f}] "
        f"y=[{region['y_min']:.2f}, {region['y_max']:.2f}]"
    )
    print(f"{'=' * 60}")

    region_articles = get_articles_in_region(all_articles, region)
    print(f"  Articles in region: {len(region_articles)}")

    if dry_run:
        print(
            f"  [DRY RUN] Would curate then generate {QUESTIONS_PER_DOMAIN} questions"
        )
        return None

    # Pass 1: Curate
    print(f"\n  [Pass 1] Curating articles for {domain['name']}...")
    if skip_curation:
        curated = random.sample(
            region_articles, min(ARTICLES_TO_CURATE, len(region_articles))
        )
        print(f"    Skipped — random {len(curated)} articles")
    else:
        curated = curate_articles(client, domain, region_articles)

    domain_ids = get_domain_hierarchy(domain, all_domains)
    batch_size = min(len(curated), QUESTIONS_PER_DOMAIN)
    difficulties = assign_difficulty_levels(batch_size)

    # Pass 2: Generate
    print(f"\n  [Pass 2] Generating {batch_size} questions from curated articles...")
    questions = generate_questions_batch(
        client, curated[:batch_size], difficulties, domain, domain_ids, "pass1"
    )
    print(f"  Result: {len(questions)}/{QUESTIONS_PER_DOMAIN}")

    used_titles = {q["source_article"] for q in questions}

    retry = 0
    while len(questions) < batch_size and retry < 2:
        retry += 1
        shortfall = batch_size - len(questions)
        remaining = [a for a in curated if a["title"] not in used_titles]
        if not remaining:
            break

        extra = remaining[:shortfall]
        print(f"  Retry {retry}: {len(extra)} more curated articles...")
        new_qs = generate_questions_batch(
            client,
            extra,
            assign_difficulty_levels(len(extra)),
            domain,
            domain_ids,
            f"retry{retry}",
        )
        questions.extend(new_qs)
        used_titles.update(q["source_article"] for q in new_qs)
        print(f"  After retry {retry}: {len(questions)} total")

    # Deduplicate
    seen = set()
    unique = []
    for q in questions:
        if q["id"] not in seen:
            seen.add(q["id"])
            unique.append(q)
    questions = unique[:QUESTIONS_PER_DOMAIN]

    with open(output_path, "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved {len(questions)} questions to {output_path}")
    return questions


def main():
    args = parse_args()
    project_root = Path(__file__).parent.parent

    print("=" * 60)
    print("DOMAIN QUESTIONS — DEEP CONCEPTUAL (two-pass)")
    print("=" * 60)
    print(f"Started: {datetime.now()}\n")

    domains = load_domains(project_root / "data" / "domains" / "index.json")
    articles = load_articles(project_root / "wikipedia_articles.json")
    output_dir = project_root / "data" / "domains"

    if args.domain:
        domains = [d for d in domains if d["id"] == args.domain]
        if not domains:
            print(f"Error: Domain '{args.domain}' not found")
            sys.exit(1)

    if not args.dry_run:
        client = OpenAI(api_key=load_openai_key())
        print("  ✓ OpenAI client initialized")
    else:
        client = None

    print(f"\n  Domains: {len(domains)}, Questions/domain: {QUESTIONS_PER_DOMAIN}")
    print("  Pipeline: curate → generate → retry\n")

    all_questions = {}
    for domain in domains:
        all_questions[domain["id"]] = generate_for_domain(
            client=client,
            domain=domain,
            all_articles=articles,
            all_domains=domains,
            output_dir=output_dir,
            force=args.force,
            dry_run=args.dry_run,
            skip_curation=args.skip_curation,
        )

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        total = 0
        for did, qs in sorted(all_questions.items()):
            n = len(qs) if qs else 0
            total += n
            print(f"  {'✓' if n >= QUESTIONS_PER_DOMAIN else '⚠'} {did}: {n}")
        print(f"\n  Total: {total} questions")

    print(f"\nCompleted: {datetime.now()}")


if __name__ == "__main__":
    main()
