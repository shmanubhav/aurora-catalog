"""Base Laya precision on 1859 by scoring route: short articles (<= 300 tokens, one pass) vs long (max over windows).
Reads 1859 data only. Written and run on 2026-10-10, after the 1872 download, as a diagnostic for the paper.

Usage: python3 -I paper/scripts/route_split_1859.py   (from the repo root; needs the local data/ folder)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bin"))
import holdout_data   # noqa: E402

final = {line: yes for _, line, _, _, yes, _ in holdout_data.load("data", "results/1859-adjudication-opus.tsv", [], [])["rows"]}
scores = {}
for row in open("data/laya_scores.tsv"):
    line, p, route = row.rstrip("\n").split("\t")
    scores[int(line)] = (float(p), route)
for route in ("batch", "long"):
    flags = [n for n, (p, r) in scores.items() if r == route and p >= 0.5]
    labeled = [n for n in flags if n in final]
    true = sum(final[n] for n in labeled)
    print(f"{route}: flags {len(flags)}, labeled {len(labeled)}, sightings {true}, precision {100 * true / len(labeled):.1f}%")
