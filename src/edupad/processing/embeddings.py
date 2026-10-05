"""Embedding teks lewat Cloudflare Workers AI (bge-m3, multilingual, 1024 dimensi).

DeepSeek tidak menyediakan API embedding. Mengganti model = ubah EMBEDDING_MODEL
lalu `edupad index --force` (model ikut di-hash, jadi semua vektor dibuat ulang).
"""

from __future__ import annotations

import time

import requests

from edupad.config import get_settings

EMBEDDING_MODEL = "@cf/baai/bge-m3"
RERANK_MODEL = "@cf/baai/bge-reranker-base"
EMBEDDING_DIM = 1024
BATCH_SIZE = 32
MAX_RETRIES = 3
TIMEOUT = 120


class EmbeddingError(RuntimeError):
    pass


def _run_model(model: str, payload: dict, retries: int = MAX_RETRIES) -> dict:
    settings = get_settings()
    if not (settings.cloudflare_account_id and settings.cloudflare_api_token):
        raise EmbeddingError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN belum diisi di .env")
    url = f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/run/{model}"
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=TIMEOUT,
                                     headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"})
        except requests.RequestException as e:
            error = str(e)
        else:
            if response.ok:
                return response.json()["result"]
            error = f"HTTP {response.status_code}: {response.text[:200]}"
            if response.status_code < 500 and response.status_code != 429:
                break  # token salah / kuota habis: mengulang tidak akan membantu
        if attempt < retries:
            time.sleep(2 ** attempt)
    raise EmbeddingError(f"Cloudflare Workers AI: {error}")


def _embed(texts: list[str]) -> list[list[float]]:
    return _run_model(EMBEDDING_MODEL, {"text": texts})["data"]


def rerank(query: str, texts: list[str]) -> list[float]:
    """Skor relevansi per teks (urutan sama dengan input). Satu kali coba: dipakai saat menjawab."""
    result = _run_model(RERANK_MODEL, {"query": query, "contexts": [{"text": t} for t in texts]}, retries=1)
    scores = [0.0] * len(texts)
    for item in result["response"]:
        scores[item["id"]] = item["score"]
    return scores


def embed_passages(texts: list[str]) -> list[list[float]]:
    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors += _embed(texts[start:start + BATCH_SIZE])
    return vectors


def embed_query(text: str) -> list[float]:
    return _embed([text])[0]
