# scripts/utils/ — Shared Pipeline Utilities

## OVERVIEW

Shared modules for OpenAI API access, Batch API operations, Wikipedia article download, and distributed GPU embedding sync. All pipeline scripts import from here.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| OpenAI API key / client | `api_utils.py` | Loads from `.credentials/openai.key`, validates `sk-` prefix |
| Batch API calls | `openai_batch.py` | `batch_with_cache()` is the main entry point for all LLM calls |
| Download Wikipedia articles | `wikipedia_utils.py` | `download_articles_batch()`, `extract_article_text()` |
| Sync GPU cluster results | `sync_and_merge_embeddings.py` | SSH/SFTP via paramiko, reads `.credentials/tensor*.txt` |
| Local embedding generation | `generate_embeddings_local.py` | Metal (MPS) acceleration, CPU fallback |
| Merge embedding checkpoints | `merge_embeddings.py` | Combines `cluster*_gpu*.pkl` into single file |
| Question bounding box | `calculate_question_bounds.py` | Computes coordinate bounds for question overlay |
| Generate question embeddings | `../embeddings/generate_question_embeddings.py` | Separate subdir, not in utils |

## CONVENTIONS

- **`__init__.py` exports**: `load_openai_key`, `create_openai_client`, batch helpers, Wikipedia helpers. Import as `from scripts.utils import ...`.
- **Credential paths**: Hardcoded relative to project root (e.g., `Path('.credentials/openai.key')`). Scripts must run from project root.
- **`batch_with_cache()`**: Handles JSONL creation, file upload, batch submission, polling, result download, and local file caching. Preferred over raw API calls.
- **Cluster credentials**: Plain text files at `.credentials/tensor01.txt`, `.credentials/tensor02.txt` with `server:`, `username:`, `password:` lines.

## ANTI-PATTERNS

- **Never import directly from script files** — always go through `__init__.py` exports or import the module.
- **Never call OpenAI API without `api_utils.py`** — key validation and client creation are centralized there.
- **Never run scripts from subdirectories** — relative `.credentials/` paths require CWD = project root.
