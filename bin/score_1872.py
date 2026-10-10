"""Score a storm holdout: every system's precision and weighted recall, the pre-registered hypotheses, checker arms.

Usage: python -I bin/score_1872.py DATA OUT.md --seed N --adjudication ADJ.tsv
         --system NAME=lines:FILE | NAME=scores:FILE:CUTOFF | NAME=scores3:FILE:CUTOFF   (repeat)
         [--checker NAME=SYSTEM:VERDICTS.tsv]   (repeat)
         [--h1 SYSTEM] [--strict SYSTEM] [--fuzzy SYSTEM]
DATA holds labelset/key.tsv (id line stratum weight), labels/claude/b*.tsv, labels/gemma.tsv, adjudication/manifest.tsv.
Final label = the adjudicated label where one exists, else the Claude/Gemma consensus (an unadjudicated
disagreement is an error). lines files list flagged line numbers; scores files are line<TAB>p; scores3 files are
id<TAB>line<TAB>p. Checker verdicts are id<TAB>YES|NO|UNPARSED keyed by label-set id or by "L<line>"; a flag is
kept unless its verdict is NO, and a flag with no verdict is an error.
Precision is weighted (unweighted counts and a Wilson interval are printed alongside); weighted recall uses a
bootstrap that resamples pool and net separately, every system read from the same resamples; percentile intervals.
Recall is relative to positives inside pool plus loose-net sample: positives outside both are unobserved.
"""
import argparse
import glob
import json
import math
import random
import sys
import importlib.util
import os
_spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ao)

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("out")
ap.add_argument("--seed", type=int, required=True)
ap.add_argument("--adjudication", required=True)
ap.add_argument("--system", action="append", default=[])
ap.add_argument("--checker", action="append", default=[])
ap.add_argument("--h1")
ap.add_argument("--strict")
ap.add_argument("--fuzzy")
ap.add_argument("--resamples", type=int, default=2000)
ap.add_argument("--drop-zero-positive", action="store_true", help="1859 behaviour (score.py); the 1872 freeze counts them")
a = ap.parse_args()
d = a.data

key = {}
for row in list(open(f"{d}/labelset/key.tsv"))[1:]:
    item_id, line, stratum, weight = row.split()
    key[item_id] = (int(line), stratum, float(weight))
by_line = {line: i for i, (line, _, _) in key.items()}
# Every label file goes through the one strict reader (bin/agent_outputs.py) the validator also uses.
claude = {k: v for p in sorted(glob.glob(f"{d}/labels/claude/b*.tsv")) for k, v in ao.read_labels(p, ("YES", "NO", "MISSING"), 2).items()}
gemma = ao.read_labels(f"{d}/labels/gemma.tsv", ("YES", "NO", "UNPARSED"))
adj = ao.read_labels(a.adjudication, ("YES", "NO"), 3)
kinds = dict(l.split() for l in list(open(f"{d}/adjudication/manifest.tsv"))[1:])
# Frozen failure rule: an adjudication item still unanswered after three attempts keeps the Sonnet label and is listed.
unanswered = sorted(i for i in kinds if i not in adj and claude[i] != "MISSING")   # MISSING ones are excluded, listed below
if any(claude[i] != gemma[i] and i not in adj and i not in kinds for i in key):
    sys.exit("a Claude/Gemma disagreement that is not in the adjudication manifest")
# An item with no Sonnet label (failed batch) whose adjudication is also unanswered has no label: it is excluded
# from every system and listed.
unlabeled = sorted(i for i in key if claude[i] == "MISSING" and i not in adj)
for i in unlabeled:
    del key[i]
by_line = {line: i for i, (line, _, _) in key.items()}
final = {i: adj.get(i, claude[i]) == "YES" for i in key}


def load_system(spec):
    kind, *rest = spec.split(":")
    if kind == "lines":
        return {int(x) for x in open(rest[0]) if x.strip()}
    cut = float(rest[1])
    if kind == "scores":
        return {int(l.split("\t")[0]) for l in open(rest[0]) if float(l.split("\t")[1]) >= cut}
    if kind == "scores3":
        return {int(l.split("\t")[1]) for l in open(rest[0]) if float(l.split("\t")[2]) >= cut}
    sys.exit(f"unknown system kind {kind}")


systems = {}
for s in a.system:
    name, spec = s.split("=", 1)
    systems[name] = load_system(spec)


def verdict_line(v_id):
    if v_id.startswith("L") and v_id[1:].isdigit():
        return int(v_id[1:])
    return key[v_id][0]


no_verdict = {}
for c in a.checker:
    name, rest = c.split("=", 1)
    base, path = rest.split(":", 1)
    verdict = {verdict_line(i): v for i, v in ao.read_labels(path, ("YES", "NO", "UNPARSED")).items()
               if i in key or (i.startswith("L") and i[1:].isdigit())}
    # Frozen failure rule: a missing or UNPARSED verdict counts as kept (counted and listed below).
    no_verdict[name] = sorted(line for line in systems[base] if line in by_line and line not in verdict)
    systems[name] = {line for line in systems[base] if verdict.get(line) != "NO"}

# rows in key.tsv order: (id, line, stratum, weight, y, {system: flagged})
rows = [(i, line, st, w, final[i], {n: (line in f) for n, f in systems.items()})
        for i, (line, st, w) in key.items()]
pool = [r for r in rows if r[2] == "pool"]
net = [r for r in rows if r[2] != "pool"]
names = list(systems)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (m - c, m + c)


def recall(sample, pred):
    pos = sum(r[3] for r in sample if r[4])
    return (sum(r[3] for r in sample if r[4] and pred(r[5])) / pos) if pos else 0.0


def union(*ns):
    return lambda f: any(f[n] for n in ns)


contrasts = {}
if a.strict and a.h1:
    contrasts["H2 gain: (strict OR h1) - strict"] = (union(a.strict, a.h1), union(a.strict))
    contrasts["H3 diff: h1 - strict"] = (union(a.h1), union(a.strict))
if a.strict and a.fuzzy and a.h1:
    contrasts["H2' gain: (strict OR fuzzy OR h1) - (strict OR fuzzy)"] = (union(a.strict, a.fuzzy, a.h1), union(a.strict, a.fuzzy))

rng = random.Random(a.seed)
boot = {n: [] for n in names}
boot_c = {c: [] for c in contrasts}
for _ in range(a.resamples):
    s = [rng.choice(pool) for _ in pool] + [rng.choice(net) for _ in net]
    if a.drop_zero_positive and not any(r[4] for r in s):
        continue
    for n in names:
        boot[n].append(recall(s, union(n)))
    for c, (p1, p2) in contrasts.items():
        boot_c[c].append(recall(s, p1) - recall(s, p2))


def ci(v):
    v = sorted(v)
    return (v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1])


out = []
w = out.append
pos_w = sum(r[3] for r in rows if r[4])
w(f"# Holdout scores (seed {a.seed}, {len(boot[names[0]]) if names else 0} bootstrap resamples)\n")
w(f"Labeled items: {len(rows)} (pool {len(pool)}, net sample {len(net)}). Weighted positives in pool + net: {pos_w:.0f}.\n")
w("| System | Flags (labeled) | True | Precision, weighted | Unweighted, Wilson 95% | Weighted recall (95% bootstrap) | F1 |")
w("|---|---|---|---|---|---|---|")
summary = {}
for n in names:
    fl = [r for r in rows if r[5][n]]
    tp = [r for r in fl if r[4]]
    prec = sum(r[3] for r in tp) / sum(r[3] for r in fl) if fl else float("nan")
    rec = recall(rows, union(n))
    lo, hi = wilson(len(tp), len(fl))
    rlo, rhi = ci(boot[n])
    f1 = 2 * prec * rec / (prec + rec) if fl and prec + rec else float("nan")
    summary[n] = (prec, rec)
    w(f"| {n} | {len(fl)} | {len(tp)} | {prec:.1%} | {len(tp)}/{len(fl)} ({lo:.1%}-{hi:.1%}) | {rec:.1%} ({rlo:.1%}-{rhi:.1%}) | {f1:.3f} |")
w("")
for c, (p1, p2) in contrasts.items():
    est = recall(rows, p1) - recall(rows, p2)
    lo, hi = ci(boot_c[c])
    w(f"- {c}: {est:+.1%} (95% bootstrap {lo:+.1%} to {hi:+.1%}){'; lower bound > 0' if lo > 0 else ''}")
if a.h1 and a.strict:
    p, r = summary[a.h1]
    unmatched = [row for row in rows if row[4] and row[5][a.h1] and not row[5][a.strict]]
    h1 = p >= 0.80 and r >= 0.80 and len(unmatched) >= 1
    w(f"- H1 ({a.h1}): precision {p:.1%}, weighted recall {r:.1%}, final-YES flags strict missed {len(unmatched)} -> {'PASS' if h1 else 'FAIL'} (point estimates)")
if a.strict and a.fuzzy:
    for n in names:
        k = sum(1 for row in rows if row[4] and row[5][n] and not row[5][a.strict] and not row[5][a.fuzzy])
        w(f"- final-YES flagged by {n} and matched by neither strict nor fuzzy: {k}")
for c in a.checker:
    name, rest = c.split("=", 1)
    adjudicated = set(kinds)
    sub = [r for r in rows if r[0] not in adjudicated]
    fl = [r for r in sub if r[5][name]]
    tp = [r for r in fl if r[4]]
    if fl:
        lo, hi = wilson(len(tp), len(fl))
        w(f"- {name} excluding Opus-adjudicated items ({len(adjudicated)}): precision {len(tp)}/{len(fl)} = {len(tp) / len(fl):.1%} (Wilson {lo:.1%}-{hi:.1%})")
for name, lines_ in no_verdict.items():
    w(f"- {name}: flags with no checker verdict, kept by rule: {len(lines_)}{' (lines ' + ', '.join(map(str, lines_)) + ')' if lines_ else ''}")
w(f"- adjudication items unanswered, Sonnet label kept by rule: {len(unanswered)}{' (' + ', '.join(unanswered) + ')' if unanswered else ''}")
w(f"- items with no label (Sonnet batch failed, adjudication unanswered), excluded: {len(unlabeled)}{' (' + ', '.join(unlabeled) + ')' if unlabeled else ''}")
agree = [(claude[i], gemma[i]) for i in key if gemma[i] != "UNPARSED" and claude[i] != "MISSING"]
po = sum(x == y for x, y in agree) / len(agree)
pc = sum((sum(x == v for x, _ in agree) / len(agree)) * (sum(y == v for _, y in agree) / len(agree)) for v in ("YES", "NO"))
checks = [i for i, k in kinds.items() if k == "agreed-check"]
answered = [i for i in checks if i in adj]
w(f"\nLabelers: Claude vs Gemma raw agreement {po:.1%}, Cohen's kappa {(po - pc) / (1 - pc):.2f} ({len(agree)} items, "
  f"{sum(g == 'UNPARSED' for g in gemma.values())} Gemma UNPARSED). Adjudicator overturned "
  f"{sum(adj[i] != claude[i] for i in answered)} of {len(answered)} answered agreed checks ({len(checks)} drawn).")
open(a.out, "w").write("\n".join(out) + "\n")
print("\n".join(out))
