"""
Tests for embedding pipeline correctness.

Verifies article and question embedding integrity, correctness of
embedding text construction, cross-embedding consistency, and semantic
clustering. Uses real pipeline output files (pickle is required for
numpy array deserialization of our own trusted pipeline data).

Run with: .venv/bin/python -m pytest tests/test_embedding_pipeline.py -v
"""

import json
import hashlib
import pickle
import numpy as np
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"

# ─── Fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def question_embeddings():
    """Load the question embeddings pkl file."""
    path = EMBEDDINGS_DIR / "question_embeddings_2500.pkl"
    if not path.exists():
        pytest.skip(f"Question embeddings not found at {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def article_embeddings():
    """Load the article embeddings pkl file."""
    path = EMBEDDINGS_DIR / "wikipedia_embeddings.pkl"
    if not path.exists():
        pytest.skip(f"Article embeddings not found at {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def all_domain_questions():
    """Load all questions from all domain JSON files, deduplicated."""
    index_path = DOMAINS_DIR / "index.json"
    with open(index_path) as f:
        index = json.load(f)

    seen = set()
    questions = []
    for d in index["domains"]:
        domain_path = DOMAINS_DIR / f"{d['id']}.json"
        if not domain_path.exists():
            continue
        with open(domain_path) as f:
            bundle = json.load(f)
        for q in bundle.get("questions", []):
            if q["id"] not in seen:
                seen.add(q["id"])
                questions.append(q)
    return questions


# ─── Article embedding tests ─────────────────────────────────────

class TestArticleEmbeddings:
    def test_shape_250k_by_768(self, article_embeddings):
        emb = article_embeddings["embeddings"]
        assert emb.shape == (250000, 768), f"Expected (250000, 768), got {emb.shape}"

    def test_dtype_float32(self, article_embeddings):
        assert article_embeddings["embeddings"].dtype == np.float32

    def test_model_is_embeddinggemma(self, article_embeddings):
        assert article_embeddings["model"] == "google/embeddinggemma-300m"

    def test_no_nan(self, article_embeddings):
        assert not np.any(np.isnan(article_embeddings["embeddings"]))

    def test_no_inf(self, article_embeddings):
        assert not np.any(np.isinf(article_embeddings["embeddings"]))

    def test_titles_count_matches(self, article_embeddings):
        n_emb = article_embeddings["embeddings"].shape[0]
        n_titles = len(article_embeddings["titles"])
        assert n_emb == n_titles, f"Embedding count {n_emb} != title count {n_titles}"

    def test_unit_normalized(self, article_embeddings):
        norms = np.linalg.norm(article_embeddings["embeddings"][:100], axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-4)


# ─── Question embedding tests ────────────────────────────────────

class TestQuestionEmbeddings:
    def test_count_is_2500(self, question_embeddings):
        assert question_embeddings["num_questions"] == 2500

    def test_shape_2500_by_768(self, question_embeddings):
        emb = question_embeddings["embeddings"]
        assert emb.shape == (2500, 768), f"Expected (2500, 768), got {emb.shape}"

    def test_dtype_float32(self, question_embeddings):
        assert question_embeddings["embeddings"].dtype == np.float32

    def test_model_is_embeddinggemma(self, question_embeddings):
        assert question_embeddings["model"] == "google/embeddinggemma-300m"

    def test_dim_is_768(self, question_embeddings):
        assert question_embeddings["dim"] == 768

    def test_no_nan(self, question_embeddings):
        assert not np.any(np.isnan(question_embeddings["embeddings"]))

    def test_no_inf(self, question_embeddings):
        assert not np.any(np.isinf(question_embeddings["embeddings"]))

    def test_unit_normalized(self, question_embeddings):
        norms = np.linalg.norm(question_embeddings["embeddings"], axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-4)

    def test_embedding_method_recorded(self, question_embeddings):
        assert question_embeddings["embedding_method"] == "question_text + correct_answer_text"

    def test_checksum_matches_data(self, question_embeddings):
        """Verify the stored checksum matches recomputed checksum."""
        recomputed = hashlib.sha256(
            question_embeddings["embeddings"].tobytes()
        ).hexdigest()
        assert question_embeddings["checksum"] == recomputed

    def test_all_question_ids_unique(self, question_embeddings):
        ids = question_embeddings["question_ids"]
        assert len(ids) == len(set(ids)), "Duplicate question IDs in embeddings"

    def test_question_ids_match_domain_files(self, question_embeddings, all_domain_questions):
        """Every question ID in the embeddings must exist in domain files."""
        domain_ids = {q["id"] for q in all_domain_questions}
        embed_ids = set(question_embeddings["question_ids"])
        missing = embed_ids - domain_ids
        assert not missing, f"Embedding IDs not found in domain files: {missing}"

    def test_all_domain_questions_embedded(self, question_embeddings, all_domain_questions):
        """Every question from domain files must be in the embeddings."""
        domain_ids = {q["id"] for q in all_domain_questions}
        embed_ids = set(question_embeddings["question_ids"])
        missing = domain_ids - embed_ids
        assert not missing, f"Domain questions missing from embeddings: {missing}"

    def test_embedding_text_includes_correct_answer(
        self, question_embeddings, all_domain_questions
    ):
        """Verify embedding text = question_text + ' ' + correct_answer_text."""
        qid_to_q = {q["id"]: q for q in all_domain_questions}

        for i, qid in enumerate(question_embeddings["question_ids"]):
            q = qid_to_q[qid]
            expected_text = f"{q['question_text']} {q['options'][q['correct_answer']]}"
            actual_text = question_embeddings["question_texts"][i]
            assert actual_text == expected_text, (
                f"Question {qid}: expected text to include correct answer.\n"
                f"  Expected: {expected_text[:80]}...\n"
                f"  Actual:   {actual_text[:80]}..."
            )

    def test_domain_ids_present_for_each_question(self, question_embeddings):
        """Every question must have at least one domain_id."""
        for i, domains in enumerate(question_embeddings["domain_ids"]):
            qid = question_embeddings["question_ids"][i]
            assert len(domains) >= 1, f"Question {qid} has no domain_ids"

    def test_embeddings_have_variance(self, question_embeddings):
        """Embeddings should not all be identical (sanity check)."""
        emb = question_embeddings["embeddings"]
        diffs = np.linalg.norm(emb[1:] - emb[0], axis=1)
        assert np.any(diffs > 0.01), "All embeddings appear identical"

    def test_same_domain_questions_cluster(self, question_embeddings):
        """Questions from the same domain should be more similar than random pairs."""
        emb = question_embeddings["embeddings"]
        domains = question_embeddings["domain_ids"]

        # Find physics questions
        physics_indices = [i for i, d in enumerate(domains) if "physics" in d]
        # Find art-history questions
        art_indices = [i for i, d in enumerate(domains) if "art-history" in d]

        if len(physics_indices) < 5 or len(art_indices) < 5:
            pytest.skip("Not enough questions in physics or art-history")

        # Within-domain similarity (physics)
        physics_emb = emb[physics_indices[:20]]
        within_sim = np.mean(physics_emb @ physics_emb.T)

        # Between-domain similarity (physics vs art-history)
        art_emb = emb[art_indices[:20]]
        between_sim = np.mean(physics_emb @ art_emb.T)

        assert within_sim > between_sim, (
            f"Within-domain similarity ({within_sim:.4f}) should exceed "
            f"between-domain similarity ({between_sim:.4f})"
        )


# ─── Transcript embedding tests ──────────────────────────────────

class TestTranscriptEmbeddings:
    @pytest.fixture(scope="class")
    def transcript_embeddings(self):
        path = EMBEDDINGS_DIR / "transcript_embeddings.pkl"
        if not path.exists():
            pytest.skip(f"Transcript embeddings not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    def test_shape_n_by_768(self, transcript_embeddings):
        emb = transcript_embeddings["embeddings"]
        assert emb.ndim == 2, f"Expected 2D, got {emb.ndim}D"
        assert emb.shape[1] == 768, f"Expected dim 768, got {emb.shape[1]}"
        assert emb.shape[0] > 0, "No transcripts embedded"

    def test_dtype_float32(self, transcript_embeddings):
        assert transcript_embeddings["embeddings"].dtype == np.float32

    def test_model_is_embeddinggemma(self, transcript_embeddings):
        assert transcript_embeddings["model"] == "google/embeddinggemma-300m"

    def test_dim_is_768(self, transcript_embeddings):
        assert transcript_embeddings["dim"] == 768

    def test_no_nan(self, transcript_embeddings):
        assert not np.any(np.isnan(transcript_embeddings["embeddings"]))

    def test_no_inf(self, transcript_embeddings):
        assert not np.any(np.isinf(transcript_embeddings["embeddings"]))

    def test_checksum_matches_data(self, transcript_embeddings):
        recomputed = hashlib.sha256(
            transcript_embeddings["embeddings"].tobytes()
        ).hexdigest()
        assert transcript_embeddings["checksum"] == recomputed

    def test_video_ids_unique(self, transcript_embeddings):
        ids = transcript_embeddings["video_ids"]
        assert len(ids) == len(set(ids)), "Duplicate video IDs in embeddings"

    def test_video_ids_count_matches_embeddings(self, transcript_embeddings):
        n_emb = transcript_embeddings["embeddings"].shape[0]
        n_ids = len(transcript_embeddings["video_ids"])
        assert n_emb == n_ids, f"Embedding count {n_emb} != video ID count {n_ids}"

    def test_num_transcripts_matches(self, transcript_embeddings):
        assert transcript_embeddings["num_transcripts"] == transcript_embeddings["embeddings"].shape[0]

    def test_transcript_lengths_all_above_min(self, transcript_embeddings):
        min_words = transcript_embeddings.get("min_words", 100)
        for i, length in enumerate(transcript_embeddings["transcript_lengths"]):
            assert length >= min_words, (
                f"Transcript {i} has {length} words, below minimum {min_words}"
            )

    def test_embeddings_have_variance(self, transcript_embeddings):
        emb = transcript_embeddings["embeddings"]
        if emb.shape[0] < 2:
            pytest.skip("Need at least 2 transcripts for variance check")
        diffs = np.linalg.norm(emb[1:] - emb[0], axis=1)
        assert np.any(diffs > 0.01), "All transcript embeddings appear identical"


# ─── Cross-embedding consistency tests ───────────────────────────

class TestCrossEmbeddingConsistency:
    @pytest.fixture(scope="class")
    def transcript_embeddings(self):
        path = EMBEDDINGS_DIR / "transcript_embeddings.pkl"
        if not path.exists():
            pytest.skip(f"Transcript embeddings not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    def test_same_model_for_articles_and_questions(
        self, article_embeddings, question_embeddings
    ):
        assert article_embeddings["model"] == question_embeddings["model"]

    def test_same_model_for_all_three(
        self, article_embeddings, question_embeddings, transcript_embeddings
    ):
        assert article_embeddings["model"] == transcript_embeddings["model"]
        assert question_embeddings["model"] == transcript_embeddings["model"]

    def test_same_dimensions(self, article_embeddings, question_embeddings):
        assert (
            article_embeddings["embeddings"].shape[1]
            == question_embeddings["embeddings"].shape[1]
            == 768
        )

    def test_all_three_same_dimensions(
        self, article_embeddings, question_embeddings, transcript_embeddings
    ):
        assert (
            article_embeddings["embeddings"].shape[1]
            == question_embeddings["embeddings"].shape[1]
            == transcript_embeddings["embeddings"].shape[1]
            == 768
        )

    def test_cosine_similarity_in_valid_range(
        self, article_embeddings, question_embeddings
    ):
        """Spot-check that article and question embeddings produce valid cosine sims."""
        a_sample = article_embeddings["embeddings"][:10]
        q_sample = question_embeddings["embeddings"][:10]
        sims = a_sample @ q_sample.T
        assert np.all(sims >= -1.01) and np.all(sims <= 1.01), (
            f"Cosine similarities out of range: min={sims.min()}, max={sims.max()}"
        )

    def test_transcript_cosine_similarity_in_valid_range(
        self, article_embeddings, transcript_embeddings
    ):
        """Spot-check that article and transcript embeddings produce valid cosine sims."""
        a_sample = article_embeddings["embeddings"][:10]
        t_sample = transcript_embeddings["embeddings"][:10]
        sims = a_sample @ t_sample.T
        assert np.all(sims >= -1.01) and np.all(sims <= 1.01), (
            f"Cosine similarities out of range: min={sims.min()}, max={sims.max()}"
        )


# ─── UMAP output tests ──────────────────────────────────────────

class TestUMAPOutputs:
    @pytest.fixture(scope="class")
    def umap_reducer_data(self):
        path = EMBEDDINGS_DIR / "umap_reducer.pkl"
        if not path.exists():
            pytest.skip(f"UMAP reducer not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    @pytest.fixture(scope="class")
    def umap_bounds(self):
        path = EMBEDDINGS_DIR / "umap_bounds.pkl"
        if not path.exists():
            pytest.skip(f"UMAP bounds not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    @pytest.fixture(scope="class")
    def article_coords(self):
        path = EMBEDDINGS_DIR / "article_coords.pkl"
        if not path.exists():
            pytest.skip(f"Article coords not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    @pytest.fixture(scope="class")
    def question_coords(self):
        path = EMBEDDINGS_DIR / "question_coords.pkl"
        if not path.exists():
            pytest.skip(f"Question coords not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    @pytest.fixture(scope="class")
    def transcript_coords(self):
        path = EMBEDDINGS_DIR / "transcript_coords.pkl"
        if not path.exists():
            pytest.skip(f"Transcript coords not found at {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    def test_reducer_has_required_keys(self, umap_reducer_data):
        required = {"reducer", "n_neighbors", "min_dist", "random_state",
                     "metric", "n_components", "n_training_samples", "timestamp"}
        assert required.issubset(umap_reducer_data.keys())

    def test_reducer_metric_is_cosine(self, umap_reducer_data):
        assert umap_reducer_data["metric"] == "cosine"

    def test_reducer_n_components_is_2(self, umap_reducer_data):
        assert umap_reducer_data["n_components"] == 2

    def test_reducer_random_state_is_42(self, umap_reducer_data):
        assert umap_reducer_data["random_state"] == 42

    def test_bounds_has_required_keys(self, umap_bounds):
        required = {"x_min", "x_max", "y_min", "y_max", "x_range", "y_range"}
        assert required.issubset(umap_bounds.keys())

    def test_bounds_ranges_positive(self, umap_bounds):
        assert umap_bounds["x_range"] > 0
        assert umap_bounds["y_range"] > 0

    def test_article_coords_shape(self, article_coords):
        coords = article_coords["coords"]
        assert coords.ndim == 2
        assert coords.shape[1] == 2
        assert coords.shape[0] == 250000, f"Expected 250000 articles, got {coords.shape[0]}"

    def test_question_coords_shape(self, question_coords):
        coords = question_coords["coords"]
        assert coords.ndim == 2
        assert coords.shape[1] == 2
        assert coords.shape[0] == 2500, f"Expected 2500 questions, got {coords.shape[0]}"

    def test_transcript_coords_shape(self, transcript_coords):
        coords = transcript_coords["coords"]
        assert coords.ndim == 2
        assert coords.shape[1] == 2
        assert coords.shape[0] > 0

    def test_all_coords_in_0_1_range(self, article_coords, question_coords):
        for name, data in [("article", article_coords), ("question", question_coords)]:
            coords = data["coords"]
            assert coords.min() >= -0.001, f"{name} coords below 0: {coords.min()}"
            assert coords.max() <= 1.001, f"{name} coords above 1: {coords.max()}"

    def test_no_nan_in_coords(self, article_coords, question_coords):
        for name, data in [("article", article_coords), ("question", question_coords)]:
            assert not np.any(np.isnan(data["coords"])), f"NaN in {name} coords"

    def test_coords_checksum_matches(self, question_coords):
        recomputed = hashlib.sha256(question_coords["coords"].tobytes()).hexdigest()
        assert question_coords["checksum"] == recomputed

    def test_coords_have_variance(self, question_coords):
        """Coords should not all be at the same point."""
        coords = question_coords["coords"]
        x_std = np.std(coords[:, 0])
        y_std = np.std(coords[:, 1])
        assert x_std > 0.01, f"X coordinates have no variance (std={x_std})"
        assert y_std > 0.01, f"Y coordinates have no variance (std={y_std})"

    def test_training_sample_count_matches(self, umap_reducer_data):
        """Training count should be articles + questions + transcripts."""
        n = umap_reducer_data["n_training_samples"]
        assert n > 252000, f"Expected >252K training samples, got {n}"
