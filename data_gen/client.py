"""Shared teacher-model (DeepSeek-V3.2) client + helpers for data distillation.

Reuses the same OpenAI-compatible endpoint configured in the project .env
(BASE_URL / API_KEY), identical to models/llm1_online.py.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, Optional

import openai
from dotenv import load_dotenv

# Load the project-root .env (this file lives in data_gen/)
load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"))

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
TEACHER_MODEL = os.getenv("TEACHER_MODEL", "deepseek/deepseek-v3.2-exp")

_client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)


def chat(system: str, user: str, temperature: float = 0.7, max_retries: int = 4) -> Optional[str]:
    """Single teacher call. Returns content string, or None on repeated failure."""
    for attempt in range(max_retries):
        try:
            resp = _client.chat.completions.create(
                model=TEACHER_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                stream=False,
            )
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001 - broad by design for API robustness
            wait = 2 ** attempt
            print(f"[teacher] error ({e}); retry in {wait}s ({attempt + 1}/{max_retries})")
            time.sleep(wait)
    return None


def parallel_map(fn: Callable, items: Iterable, workers: int = 8, desc: str = "") -> list:
    """Run fn over items concurrently, preserving nothing (order-agnostic).

    fn should return either a record (dict) or None to skip. Failures/None are
    silently dropped so the pipeline is resumable and partial-tolerant.
    """
    items = list(items)
    results = []
    done = 0
    total = len(items)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, it): it for it in items}
        for fut in as_completed(futures):
            done += 1
            try:
                rec = fut.result()
            except Exception as e:  # noqa: BLE001
                rec = None
                print(f"[{desc}] worker exception: {e}")
            if rec is not None:
                results.append(rec)
            if done % 10 == 0 or done == total:
                print(f"[{desc}] {done}/{total} processed, {len(results)} kept")
    return results


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------
def write_jsonl(path: str, records: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[write] {len(records)} records -> {path}")


def read_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def alpaca(instruction: str, input_text: str, output: str) -> dict:
    """LLaMA-Factory 'alpaca' format record."""
    return {"instruction": instruction, "input": input_text, "output": output}
