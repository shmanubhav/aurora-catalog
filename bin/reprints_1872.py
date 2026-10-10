"""Reprint-group sensitivity (prereg section 6): H1 point estimates and the H2/H2' intervals with reprint groups as the unit.

Usage: python -I bin/reprints_1872.py DATA WINDOW.txt OUT.md --seed N --adjudication ADJ.tsv --system ... [--checker ...]
         --h1 SYSTEM --strict SYSTEM --fuzzy SYSTEM [--resamples 2000] [--drop-zero-positive] [--containment 0.5]
Groups follow the Freeze 1 method of bin/prep_finetune.py with the freeze/finetune.json settings: 5-word shingles of
the lowercased a-z words of each labeled article (its WINDOW.txt line); a shingle's frequency is counted over all
labeled items; two articles sharing a shingle of frequency 2 to 20 are a candidate pair, joined when their shared
such shingles / the smaller article's shingle count >= 0.5; union-find, never joining pool with net. Shingles are kept
as strings (prep_finetune.py used Python's per-process string hash: the same sets barring a hash collision).
A group is flagged by a system if any member is, and final-YES if any member is. Pool groups weigh 1, net groups the
net weight H/n. The bootstrap resamples groups with replacement within pool and within net, groups in key.tsv order
of their first member. --containment above 1 makes every article its own group, and the output then repeats
bin/score_1872.py's H1 point estimates and H2/H2' lines (bin/test_analyses_1872.sh).
"""
import argparse
import importlib.util
import os
import random
import re
import sys
from collections import defaultdict

_spec = importlib.util.spec_from_file_location("holdout_data", os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdout_data.py"))
hd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hd)

SHINGLE_WORDS, MAX_SHINGLE_DF = 5, 20   # freeze/finetune.json shingle_words, max_shingle_df

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("window")
ap.add_argument("out")
ap.add_argument("--seed", type=int, required=True)
ap.add_argument("--resamples", type=int, default=2000)
ap.add_argument("--drop-zero-positive", action="store_true", help="1859 behaviour, for the reproduction test only")
ap.add_argument("--containment", type=float, default=0.5, help="freeze/finetune.json reprint_containment")
hd.add_args(ap)
a = ap.parse_args()
if not (a.h1 and a.strict and a.fuzzy):
    sys.exit("--h1, --strict and --fuzzy are required")

data = hd.load(a.data, a.adjudication, a.system, a.checker)
rows, names = data["rows"], data["names"]
text = open(a.window).read().splitlines()


def shingles(t):
    words = re.findall(r"[a-z]+", t.lower())
    return {" ".join(words[j:j + SHINGLE_WORDS]) for j in range(max(0, len(words) - SHINGLE_WORDS + 1))}


part = {r[0]: ("pool" if r[2] == "pool" else "net") for r in rows}
sh = {r[0]: shingles(text[r[1] - 1]) for r in rows}
index = defaultdict(list)
for i, s in sh.items():
    for h in s:
        index[h].append(i)
parent = {i: i for i in sh}


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


shared = defaultdict(int)
for h, ids in index.items():
    if 1 < len(ids) <= MAX_SHINGLE_DF:
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                if part[ids[x]] == part[ids[y]]:
                    shared[(ids[x], ids[y])] += 1
for (x, y), c in shared.items():
    if c / min(len(sh[x]), len(sh[y])) >= a.containment:
        parent[find(x)] = find(y)

members = defaultdict(list)
for r in rows:   # key.tsv order, so each group's first member fixes its place
    members[find(r[0])].append(r)
groups = []
for ms in members.values():
    if len({m[3] for m in ms}) != 1:
        sys.exit("a reprint group mixes weights")
    groups.append((ms[0][0], ms[0][2], ms[0][3], any(m[4] for m in ms),
                   {n: any(m[5][n] for m in ms) for n in names}, [m[0] for m in ms]))
gid = {m: g[0] for g in groups for m in g[5]}
pool = [g for g in groups if g[1] == "pool"]
net = [g for g in groups if g[1] != "pool"]


def recall(sample, pred):   # group tuples: (first id, stratum, weight, final-YES, {system: flagged}, member ids)
    pos = sum(g[2] for g in sample if g[3])
    return (sum(g[2] for g in sample if g[3] and pred(g[4])) / pos) if pos else 0.0


contrasts = {
    "H2 gain: (strict OR h1) - strict": (hd.union(a.strict, a.h1), hd.union(a.strict)),
    "H2' gain: (strict OR fuzzy OR h1) - (strict OR fuzzy)": (hd.union(a.strict, a.fuzzy, a.h1), hd.union(a.strict, a.fuzzy)),
}
rng = random.Random(a.seed)
boot = {c: [] for c in contrasts}
for _ in range(a.resamples):
    s = [rng.choice(pool) for _ in pool] + [rng.choice(net) for _ in net]
    if a.drop_zero_positive and not any(g[3] for g in s):
        continue
    for c, (p1, p2) in contrasts.items():
        boot[c].append(recall(s, p1) - recall(s, p2))

out = []
w = out.append
sizes = sorted((len(g[5]) for g in groups), reverse=True)
w(f"# Reprint-group sensitivity (seed {a.seed}, {len(boot[next(iter(boot))])} bootstrap resamples, containment {a.containment})\n")
w(f"Labeled items: {len(rows)} in {len(groups)} groups (pool {len(pool)}, net {len(net)}); groups with more than one "
  f"article: {sum(1 for n in sizes if n > 1)}, largest {sizes[0] if sizes else 0}. Weighted final-YES groups: "
  f"{sum(g[2] for g in groups if g[3]):.0f}.\n")
w("| System | Flagged groups | Final-YES | Precision, weighted | Weighted recall |")
w("|---|---|---|---|---|")
point = {}
for n in names:
    fl = [g for g in groups if g[4][n]]
    tp = [g for g in fl if g[3]]
    prec = sum(g[2] for g in tp) / sum(g[2] for g in fl) if fl else float("nan")
    point[n] = (prec, recall(groups, hd.union(n)))
    w(f"| {n} | {len(fl)} | {len(tp)} | {prec:.1%} | {point[n][1]:.1%} |")
w("")
for c, (p1, p2) in contrasts.items():
    est = recall(groups, p1) - recall(groups, p2)
    lo, hi = hd.ci(boot[c])
    w(f"- {c}: {est:+.1%} (95% bootstrap {lo:+.1%} to {hi:+.1%}){'; lower bound > 0' if lo > 0 else ''}")
p, r = point[a.h1]
missed = [row for row in rows if row[4] and row[5][a.h1] and not row[5][a.strict]]   # articles, on the LLM key
k = len({gid[row[0]] for row in missed})
w(f"- H1 ({a.h1}) at group level: precision {p:.1%}, weighted recall {r:.1%}; the {len(missed)} final-YES articles it "
  f"flags that strict missed fall in {k} distinct reprint groups -> {'PASS' if p >= 0.80 and r >= 0.80 and k >= 1 else 'FAIL'} "
  f"(point estimates; sensitivity only, the article-level H1 decides)")
open(a.out, "w").write("\n".join(out) + "\n")
print("\n".join(out))
