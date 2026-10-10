"""Exploratory (prereg section 6): weighted recall by OCR-quality tercile.

Usage: python -I bin/ocr_terciles_1872.py DATA WINDOW.txt OUT.md --adjudication ADJ.tsv --system ... [--checker ...]
OCR quality of an article (its WINDOW.txt line) = the share of its whitespace-separated tokens made only of letters
(str.isalpha); an article with no tokens scores 0. Cut points = statistics.quantiles of the pool articles' qualities,
n=3 (its default 'exclusive' method); low: q <= c1, mid: c1 < q <= c2, high: q > c2; net articles use the pool's cut
points. Per tercile and system: weighted final-YES flagged / weighted final-YES in the tercile (net articles weigh H/n).
Point estimates only: the registration names no interval for this exploratory measure.
"""
import argparse
import importlib.util
import os
import statistics

_spec = importlib.util.spec_from_file_location("holdout_data", os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdout_data.py"))
hd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hd)

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("window")
ap.add_argument("out")
hd.add_args(ap)
a = ap.parse_args()

data = hd.load(a.data, a.adjudication, a.system, a.checker)
rows, names = data["rows"], data["names"]
text = open(a.window).read().splitlines()


def quality(t):
    tokens = t.split()
    return sum(tok.isalpha() for tok in tokens) / len(tokens) if tokens else 0.0


q = {r[0]: quality(text[r[1] - 1]) for r in rows}
c1, c2 = statistics.quantiles([q[r[0]] for r in rows if r[2] == "pool"], n=3)
tercile = {i: ("low" if v <= c1 else "mid" if v <= c2 else "high") for i, v in q.items()}

out = []
w = out.append
w("# Weighted recall by OCR-quality tercile (exploratory)\n")
w(f"OCR quality = share of whitespace tokens made only of letters. Cut points from the {sum(r[2] == 'pool' for r in rows)} "
  f"pool articles: {c1:.4f} and {c2:.4f}.\n")
w("| Tercile | Articles (pool + net) | Weighted final-YES | " + " | ".join(names) + " |")
w("|---|---|---|" + "---|" * len(names))
for t in ("low", "mid", "high"):
    sub = [r for r in rows if tercile[r[0]] == t]
    pos = sum(r[3] for r in sub if r[4])
    cells = [f"{sum(r[3] for r in sub if r[4] and r[5][n]) / pos:.1%}" if pos else "n/a" for n in names]
    w(f"| {t} | {sum(r[2] == 'pool' for r in sub)} + {sum(r[2] != 'pool' for r in sub)} | {pos:.1f} | " + " | ".join(cells) + " |")
open(a.out, "w").write("\n".join(out) + "\n")
print("\n".join(out))
