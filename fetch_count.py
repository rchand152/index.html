#!/usr/bin/env python3
"""Reads the current 'letters released' count without incrementing it.
Prints just the integer, so it's easy to use in a shell script:
    COUNT=$(python3 fetch_count.py)
"""
import sys
import urllib.request
import json

URL = "https://countapi.mileshilliard.com/api/v1/get/letter-to-the-universe_released"

try:
    with urllib.request.urlopen(URL, timeout=10) as r:
        data = json.loads(r.read().decode())
        print(int(data["value"]))
except Exception as e:
    # if the key doesn't exist yet (no one has released a letter), default to 0
    print(0, file=sys.stdout)
    print(f"warning: {e}", file=sys.stderr)
