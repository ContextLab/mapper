"""
Tests for video sliding-window embedding pipeline.

Tests are split into two groups:
1. Window creation logic (pure Python, no model/data dependencies)
2. Embedding output validation (requires actual .npy files from pipeline run)

Run with: .venv/bin/python -m pytest tests/test_sliding_window_pipeline.py -v
"""

import json
import numpy as np
import pytest
from pathlib import Path

# Import the windowing function directly
import sys
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from embed_video_windows import create_windows, WINDOW_SIZE, STRIDE, MIN_WORDS

TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "transcripts"
EMBEDDING_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "embeddings"
COORD_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "coordinates"


# ─── Window creation logic tests ──────────────────────────────────

class TestCreateWindows:
    def test_constants_match_spec(self):
        """FR-V003: 512-word windows, CL-002: 50-word stride."""
        assert WINDOW_SIZE == 512
        assert STRIDE == 50
        assert MIN_WORDS == 50

    def test_short_text_returns_empty(self):
        """Text below MIN_WORDS should produce no windows."""
        short = " ".join(["word"] * (MIN_WORDS - 1))
        assert create_windows(short) == []

    def test_exactly_min_words_returns_single(self):
        """Text with exactly MIN_WORDS should produce one window."""
        text = " ".join(["word"] * MIN_WORDS)
        windows = create_windows(text)
        assert len(windows) == 1
        assert windows[0] == text

    def test_below_window_size_returns_single(self):
        """Text shorter than WINDOW_SIZE but >= MIN_WORDS → single window."""
        text = " ".join(["word"] * 200)
        windows = create_windows(text)
        assert len(windows) == 1
        assert windows[0] == text

    def test_exactly_window_size_returns_single(self):
        """Text with exactly WINDOW_SIZE words → one window."""
        text = " ".join([f"w{i}" for i in range(WINDOW_SIZE)])
        windows = create_windows(text)
        assert len(windows) == 1
        assert len(windows[0].split()) == WINDOW_SIZE

    def test_window_size_plus_stride_returns_two(self):
        """Text with WINDOW_SIZE + STRIDE words should produce 2 windows."""
        n = WINDOW_SIZE + STRIDE
        text = " ".join([f"w{i}" for i in range(n)])
        windows = create_windows(text)
        assert len(windows) == 2

    def test_each_window_has_correct_size(self):
        """All windows should have exactly WINDOW_SIZE words."""
        text = " ".join([f"w{i}" for i in range(WINDOW_SIZE * 3)])
        windows = create_windows(text)
        for i, w in enumerate(windows):
            assert len(w.split()) == WINDOW_SIZE, (
                f"Window {i} has {len(w.split())} words, expected {WINDOW_SIZE}"
            )

    def test_stride_offset_is_correct(self):
        """Consecutive windows should be offset by exactly STRIDE words."""
        text = " ".join([f"w{i}" for i in range(WINDOW_SIZE * 3)])
        windows = create_windows(text)
        for i in range(len(windows) - 1):
            words_a = windows[i].split()
            words_b = windows[i + 1].split()
            # First word of window b should be word at offset STRIDE from window a
            assert words_b[0] == f"w{(i + 1) * STRIDE}"

    def test_window_count_formula(self):
        """Number of windows should follow: (n_words - WINDOW_SIZE) // STRIDE + 1."""
        for n_words in [600, 1000, 2000, 5000]:
            text = " ".join(["x"] * n_words)
            windows = create_windows(text)
            expected = (n_words - WINDOW_SIZE) // STRIDE + 1
            assert len(windows) == expected, (
                f"n_words={n_words}: expected {expected} windows, got {len(windows)}"
            )

    def test_empty_text_returns_empty(self):
        assert create_windows("") == []
        assert create_windows("   ") == []

    def test_real_transcript_produces_windows(self):
        """Test with a real transcript file from disk."""
        transcripts = sorted(TRANSCRIPT_DIR.glob("*.txt"))
        if not transcripts:
            pytest.skip("No transcript files found")
        text = transcripts[0].read_text(encoding="utf-8").strip()
        words = text.split()
        if len(words) < MIN_WORDS:
            pytest.skip(f"First transcript too short ({len(words)} words)")
        windows = create_windows(text)
        assert len(windows) >= 1
        # Each window should be proper size
        for w in windows:
            wc = len(w.split())
            assert wc == WINDOW_SIZE or (len(words) < WINDOW_SIZE and wc == len(words))

    def test_overlapping_content(self):
        """Windows should share overlapping content (512 - 50 = 462 shared words)."""
        text = " ".join([f"w{i}" for i in range(WINDOW_SIZE + STRIDE)])
        windows = create_windows(text)
        assert len(windows) == 2
        set_a = set(windows[0].split())
        set_b = set(windows[1].split())
        overlap = set_a & set_b
        # Overlap should be WINDOW_SIZE - STRIDE = 462 words
        assert len(overlap) == WINDOW_SIZE - STRIDE


# ─── Transcript coverage tests ────────────────────────────────────

class TestTranscriptCoverage:
    """Verify expected window counts from actual transcript data."""

    @pytest.fixture(scope="class")
    def transcript_stats(self):
        """Compute window stats for all transcripts."""
        transcripts = sorted(TRANSCRIPT_DIR.glob("*.txt"))
        if not transcripts:
            pytest.skip("No transcript files found")
        stats = []
        for tf in transcripts:
            text = tf.read_text(encoding="utf-8").strip()
            words = text.split()
            windows = create_windows(text)
            stats.append({
                "video_id": tf.stem,
                "word_count": len(words),
                "window_count": len(windows),
            })
        return stats

    def test_all_transcripts_processed(self, transcript_stats):
        """Every transcript should produce stats."""
        assert len(transcript_stats) >= 1800, (
            f"Expected ~1864 transcripts, got {len(transcript_stats)}"
        )

    def test_most_transcripts_have_windows(self, transcript_stats):
        """Most transcripts should have at least one window."""
        with_windows = [s for s in transcript_stats if s["window_count"] > 0]
        pct = len(with_windows) / len(transcript_stats) * 100
        assert pct > 90, f"Only {pct:.1f}% of transcripts have windows"

    def test_total_windows_reasonable(self, transcript_stats):
        """Total window count should match dry-run expectation (~27K)."""
        total = sum(s["window_count"] for s in transcript_stats)
        assert 20000 < total < 50000, f"Unexpected total windows: {total}"

    def test_no_extremely_large_window_count(self, transcript_stats):
        """No single transcript should have an unreasonable number of windows."""
        max_windows = max(s["window_count"] for s in transcript_stats)
        # A very long transcript (~30K words) would have ~590 windows
        assert max_windows < 1000, f"Unreasonably large window count: {max_windows}"


# ─── Embedding output validation tests ───────────────────────────

class TestSlidingWindowEmbeddings:
    """Tests that validate the .npy output files after pipeline run."""

    @pytest.fixture(scope="class")
    def embedding_files(self):
        files = sorted(EMBEDDING_DIR.glob("*.npy"))
        if not files:
            pytest.skip("No embedding .npy files found (run embed_video_windows.py first)")
        return files

    @pytest.fixture(scope="class")
    def sample_embeddings(self, embedding_files):
        """Load a sample of embedding files for validation."""
        sample = embedding_files[:20]
        results = {}
        for f in sample:
            results[f.stem] = np.load(f)
        return results

    def test_embedding_count_matches_transcripts(self, embedding_files):
        """Number of .npy files should roughly match transcript count."""
        transcript_count = len(list(TRANSCRIPT_DIR.glob("*.txt")))
        emb_count = len(embedding_files)
        # Allow some to be skipped (too short)
        assert emb_count >= transcript_count * 0.9, (
            f"Only {emb_count} embeddings for {transcript_count} transcripts"
        )

    def test_each_embedding_is_2d_768(self, sample_embeddings):
        """Each .npy file should be (N_windows, 768)."""
        for vid, emb in sample_embeddings.items():
            assert emb.ndim == 2, f"{vid}: expected 2D, got {emb.ndim}D"
            assert emb.shape[1] == 768, f"{vid}: expected dim 768, got {emb.shape[1]}"

    def test_embedding_dtype_float32(self, sample_embeddings):
        for vid, emb in sample_embeddings.items():
            assert emb.dtype == np.float32, f"{vid}: dtype is {emb.dtype}"

    def test_no_nan_values(self, sample_embeddings):
        for vid, emb in sample_embeddings.items():
            assert not np.any(np.isnan(emb)), f"{vid} contains NaN values"

    def test_no_inf_values(self, sample_embeddings):
        for vid, emb in sample_embeddings.items():
            assert not np.any(np.isinf(emb)), f"{vid} contains Inf values"

    def test_window_count_matches_transcript(self, sample_embeddings):
        """Number of embedding rows should match expected window count."""
        for vid, emb in sample_embeddings.items():
            transcript_path = TRANSCRIPT_DIR / f"{vid}.txt"
            if not transcript_path.exists():
                continue
            text = transcript_path.read_text(encoding="utf-8").strip()
            expected_windows = create_windows(text)
            assert emb.shape[0] == len(expected_windows), (
                f"{vid}: {emb.shape[0]} embedding rows != {len(expected_windows)} windows"
            )

    def test_embeddings_have_variance(self, sample_embeddings):
        """Windows from the same video should not all be identical."""
        for vid, emb in sample_embeddings.items():
            if emb.shape[0] < 2:
                continue
            diffs = np.linalg.norm(emb[1:] - emb[0], axis=1)
            assert np.any(diffs > 0.01), f"{vid}: all embeddings appear identical"

    def test_embedding_ids_match_transcripts(self, embedding_files):
        """Every .npy file should correspond to a transcript .txt file."""
        transcript_ids = {f.stem for f in TRANSCRIPT_DIR.glob("*.txt")}
        orphans = []
        for f in embedding_files:
            if f.stem not in transcript_ids:
                orphans.append(f.stem)
        assert not orphans, f"Embeddings without transcripts: {orphans[:10]}"


# ─── Coordinate output validation tests ──────────────────────────

class TestVideoCoordinates:
    """Tests for project_video_coords.py output (post-UMAP projection)."""

    @pytest.fixture(scope="class")
    def coord_files(self):
        files = sorted(COORD_DIR.glob("*.json"))
        if not files:
            pytest.skip("No coordinate .json files found (run project_video_coords.py first)")
        return files

    @pytest.fixture(scope="class")
    def sample_coords(self, coord_files):
        """Load sample coordinate files."""
        sample = coord_files[:20]
        results = {}
        for f in sample:
            with open(f) as fh:
                results[f.stem] = json.load(fh)
        return results

    def test_coord_count_matches_embeddings(self, coord_files):
        """Number of .json files should match .npy embedding files."""
        emb_count = len(list(EMBEDDING_DIR.glob("*.npy")))
        coord_count = len(coord_files)
        assert coord_count == emb_count, (
            f"{coord_count} coord files != {emb_count} embedding files"
        )

    def test_each_coord_file_is_array_of_pairs(self, sample_coords):
        """Each JSON file should be an array of [x, y] pairs."""
        for vid, coords in sample_coords.items():
            assert isinstance(coords, list), f"{vid}: expected list"
            for i, pair in enumerate(coords):
                assert isinstance(pair, list), f"{vid}[{i}]: expected list"
                assert len(pair) == 2, f"{vid}[{i}]: expected 2 values, got {len(pair)}"

    def test_coords_in_0_1_range(self, sample_coords):
        """All coordinates should be clipped to [0, 1] per CL-038."""
        for vid, coords in sample_coords.items():
            for i, (x, y) in enumerate(coords):
                assert 0.0 <= x <= 1.0, f"{vid}[{i}]: x={x} out of range"
                assert 0.0 <= y <= 1.0, f"{vid}[{i}]: y={y} out of range"

    def test_coord_count_matches_embedding_windows(self, sample_coords):
        """Number of coordinate pairs should match embedding window count."""
        for vid, coords in sample_coords.items():
            emb_path = EMBEDDING_DIR / f"{vid}.npy"
            if not emb_path.exists():
                continue
            emb = np.load(emb_path)
            assert len(coords) == emb.shape[0], (
                f"{vid}: {len(coords)} coords != {emb.shape[0]} windows"
            )

    def test_coords_have_spatial_variance(self, sample_coords):
        """Coordinates should spread across the map, not cluster at one point."""
        for vid, coords in sample_coords.items():
            if len(coords) < 3:
                continue
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            x_range = max(xs) - min(xs)
            y_range = max(ys) - min(ys)
            # Windows from same video should have SOME spread
            assert x_range > 0.001 or y_range > 0.001, (
                f"{vid}: all {len(coords)} coords at same point"
            )

    def test_precision_is_6_decimals(self, sample_coords):
        """Coordinates should have at most 6 decimal places."""
        for vid, coords in sample_coords.items():
            for i, (x, y) in enumerate(coords[:5]):
                x_str = f"{x:.10f}"
                y_str = f"{y:.10f}"
                # After 6 decimal places, should be zeros
                assert x_str[x_str.index('.') + 7:] == "0000", (
                    f"{vid}[{i}]: x has >6 decimal places: {x}"
                )
                assert y_str[y_str.index('.') + 7:] == "0000", (
                    f"{vid}[{i}]: y has >6 decimal places: {y}"
                )
