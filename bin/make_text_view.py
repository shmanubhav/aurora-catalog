"""Write one line per article (headline + text, whitespace collapsed), aligned to the jsonl line order.

Usage: python -I bin/make_text_view.py IN.jsonl OUT.txt
Both searchers (rg and Laya) read this same text, so neither gets cleaner input.
"""
import json
import re
import sys

src, dst = sys.argv[1:3]
with open(src) as f, open(dst, "w") as out:
    for line in f:
        r = json.loads(line)
        text = f"{r['headline']} {r['article']}".strip()
        out.write(re.sub(r"\s+", " ", text) + "\n")
