#!/usr/bin/env python3
"""Emit the release performance metric for the ADAMANT site artifact."""
import json
from pathlib import Path

zip_path = Path(__file__).resolve().parents[1] / "site" / "downloads" / "eng-kit.zip"
print(json.dumps({
    "schema": "eng-perf/v1",
    "name": "ADAMANT site kit artifact size",
    "metrics": {"site_kit_bytes": {"value": zip_path.stat().st_size, "direction": "lower", "unit": "bytes"}},
}, indent=2))
