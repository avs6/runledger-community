"""
Example 35 — Prompt Compression (LLMLingua-2)

The final, lossy stage of the Context Compiler: a small token-classifier drops low-information
tokens to hit a target keep-rate while preserving task performance. Runs on CPU (no GPU).

This example calls the compression service directly so you can see the token reduction. In
production it's an opt-in Context Compiler stage (`stages.compress`), configured per route on the
dashboard Gateway page with an engage policy (always / over-budget / over-% of budget), a keep
rate, and a model.

Prerequisites
─────────────
  • The compression service is up:  docker compose up -d
    (first call downloads the LLMLingua-2 model — allow a minute)

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 35_prompt_compression.py

Key .env variables:
    COMPRESSION_URL  — http://localhost:8209  (default)
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

COMPRESSION_URL = os.getenv("COMPRESSION_URL", "http://localhost:8209")

TEXT = (
    "The parental leave policy grants sixteen weeks of fully paid leave to all full-time "
    "employees, and this leave may be taken either continuously or split into two separate "
    "blocks within the first twelve months following the birth or adoption of a child. "
    "Throughout the entire duration of the parental leave period, employees continue to "
    "retain their full health insurance benefits with no reduction whatsoever, and the "
    "company also continues to make its standard retirement contributions during that time."
)


def sep(t: str) -> None:
    print(f"\n{'─' * 60}\n  {t}\n{'─' * 60}")


sep("POST /compress  (keep rate 0.5)")
with httpx.Client(timeout=180.0) as client:
    resp = client.post(f"{COMPRESSION_URL}/compress", json={"text": TEXT, "rate": 0.5})

if resp.status_code != 200:
    print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
    raise SystemExit(1)

d = resp.json()
print(f"  Model:      {d['model']}")
print(f"  Original:   {d['original_tokens']} tokens")
print(f"  Compressed: {d['compressed_tokens']} tokens  (ratio {d['ratio']})")
print(f"\n  Compressed prompt:\n    {d['compressed_text']}")

sep("Enable it in the Context Compiler")
print("  Per route context_compiler_config:")
print('    "stages": { "compress": true },')
print('    "compression_model": "bert-base-multilingual",')
print('    "compression_rate": 0.5,')
print('    "compress_when": "over_budget"   // always | over_budget | over_pct')
print("  (all configurable on the dashboard Gateway page → Context Compiler config)")

print("\n✓ Example 35 complete.\n")
