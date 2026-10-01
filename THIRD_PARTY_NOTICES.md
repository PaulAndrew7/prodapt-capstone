# Third-party notices

## Fonts

| Asset | Source | License | Used in |
|---|---|---|---|
| Clash Display (Semibold 600, Bold 700), by Indian Type Foundry | https://www.fontshare.com/fonts/clash-display | ITF Free Font License (free for personal and commercial use) | `apps/web/src/assets/fonts/` |
| Switzer Variable (100-900), by Indian Type Foundry | https://www.fontshare.com/fonts/switzer | ITF Free Font License (free for personal and commercial use) | `apps/web/src/assets/fonts/` |

Downloaded from the Fontshare CDN on 2026-09-25 and self-hosted as woff2.

## Icons

| Asset | Source | License |
|---|---|---|
| Phosphor Icons (`@phosphor-icons/react`) | https://phosphoricons.com | MIT |

## Database

| Asset | Source | License | Used in |
|---|---|---|---|
| PostgreSQL 16 and pgvector 0.8.1, as prebuilt binaries in the `pixeltable-pgserver` 0.5.1 wheel | https://github.com/pixeltable/pixeltable-pgserver | pixeltable-pgserver: Apache-2.0; PostgreSQL: PostgreSQL License; pgvector: PostgreSQL License | Installed by `uv sync` into `services/api/.venv`; started by `services/api/app/localdb.py` |

## Models

| Asset | Source | License | Used in |
|---|---|---|---|
| BAAI/bge-small-en-v1.5 (384-d English embeddings), ONNX build `Qdrant/bge-small-en-v1.5-onnx-Q` loaded through fastembed | https://huggingface.co/BAAI/bge-small-en-v1.5 | MIT | `services/api/app/retrieval/embeddings.py`; downloaded at first use into `MODEL_CACHE_DIR`, not committed |

| Claude Sonnet 5.5 (Anthropic), the runtime language model | Anthropic API with the user's own key | Used under Anthropic's terms; not bundled, trained or fine-tuned here | `services/api/app/workflow/claude_model.py` through the Anthropic Python SDK (MIT) |
| GPT-4o mini (OpenAI), supported alternative | Through the project organizers' gateway with a lab key | Used under OpenAI's and the organizers' terms; not bundled, trained or fine-tuned here | `services/api/app/workflow/llm.py` through the OpenAI Python SDK (Apache-2.0) |
| Claude Haiku 4.5 (Anthropic), cheaper option for test runs | Anthropic API with the user's own key | Used under Anthropic's terms; not bundled, trained or fine-tuned here | `services/api/app/workflow/claude_model.py` through the Anthropic Python SDK (MIT) |

Python and JavaScript dependencies are pinned in `services/api/uv.lock` and `pnpm-lock.yaml` under their own licenses.

## Data

All policies, organizations, people and cases in `apps/web/src/fixtures/` are fictional demo material authored for this project. They are not real policies, law or regulatory guidance.

The demo policy corpus in `data/demo/` (Kestrel Mutual) and the evaluation scenarios in `data/evaluation/` are likewise fictional, authored for this project; see `docs/data/corpus-decision.md`.
