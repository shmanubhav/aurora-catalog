"""Human-audit agreement and the audit-corrected H1/H2 (prereg section 5).

Usage, 1872: python -I bin/audit_1872.py storm DATA SAMPLE.tsv AUDIT_KEY.tsv ANSWERS.tsv OUT.md --adjudication ADJ.tsv
               --system ... [--checker ...] --h1 SYSTEM --strict SYSTEM --ft FLAGS.lines --keyword FLAGS.lines
               [--keyword FLAGS.lines] --base FLAGS.lines [--seed 1872] [--resamples 2000]
Usage, 1859: python -I bin/audit_1872.py balanced DATA SAMPLE.tsv AUDIT_KEY.tsv ANSWERS.tsv OUT.md --adjudication ADJ.tsv
SAMPLE.tsv: id, stratum, stratum_size, drawn (bin/draw_audit.py). AUDIT_KEY.tsv: card_id, source_id, is_repeat
(bin/make_audit_page.py). ANSWERS.tsv: card_id<TAB>YES|NO, the file the audit page downloads.
The LLM label is the final label of bin/score_1872.py (bin/holdout_data.py). The human label of an item is its
non-repeat card's answer, or its repeat card's answer when only that one was answered; items with both answered give
test-retest agreement. Every answered item is used; a stratum with under 80% of its drawn items answered is marked
incomplete.
Per stratum: raw agreement (Wilson 95%), Cohen's kappa with a 95% bootstrap of the stratum's audited items, positive
agreement 2a/(2a+b+c), negative agreement 2d/(2d+b+c), p1 = share of audited LLM-YES items the human calls YES, p0 =
the same for LLM-NO items. A quantity with no audited items is not estimable, and the LLM label stands. Kappa is not
estimable when either rater gave a single label (it would read 0 by construction); resamples where it is not
estimable are left out of its interval, and their number is shown.
balanced (1859): strata are final-YES and final-NO, so kappa within a stratum is never estimable; kappa is also given
pooled over the sample, unweighted (the sample is balanced, not population-weighted). No corrected H1/H2.
storm (1872): the strata of every key.tsv item are recomputed as bin/draw_audit.py does and must match SAMPLE.tsv.
Every labeled item gets y = p1 or p0 of its stratum by its LLM label (net items weigh H/n); precision of a system =
sum over its flags of w*y / sum over its flags of w; recall = sum over its flags of w*y / sum over all items of w*y.
H1 is recomputed on these (its unmatched-sighting condition stays on the LLM key) and H2 = recall(strict OR h1) -
recall(strict). Intervals: 2,000 bootstrap resamples of the audited items within each stratum (strata in sample-file
order, items sorted by id; random.Random(seed), a separate generator from the kappa intervals), percentile rule of
bin/score_1872.py. They cover audit sampling only (the labeled set is not resampled). A resample with no audited
LLM-YES (or LLM-NO) item in a stratum leaves that cell's LLM label standing; how often that happened is shown.
"""
import argparse
import importlib.util
import os
import random
import sys
from collections import defaultdict

_spec = importlib.util.spec_from_file_location("holdout_data", os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdout_data.py"))
hd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hd)

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["storm", "balanced"])
ap.add_argument("data")
ap.add_argument("sample")
ap.add_argument("audit_key")
ap.add_argument("answers")
ap.add_argument("out")
ap.add_argument("--ft")
ap.add_argument("--keyword", action="append", default=[])
ap.add_argument("--base")
ap.add_argument("--seed", type=int, default=1872)
ap.add_argument("--resamples", type=int, default=2000)
hd.add_args(ap)
a = ap.parse_args()
if a.mode == "storm" and not (a.h1 and a.strict and a.ft and a.keyword and a.base):
    sys.exit("storm mode needs --h1, --strict, --ft, --keyword and --base")

data = hd.load(a.data, a.adjudication, a.system, a.checker)
rows, names = data["rows"], data["names"]
llm = {r[0]: r[4] for r in rows}

sample = [l.rstrip("\n").split("\t") for l in list(open(a.sample))[1:] if l.strip()]
stratum_of_sampled = {i: s for i, s, _, _ in sample}
drawn = {s: int(d) for _, s, _, d in sample}
size = {s: int(n) for _, s, n, _ in sample}
order = list(dict.fromkeys(s for _, s, _, _ in sample))   # strata in sample-file order

cards = {}
for l in list(open(a.audit_key))[1:]:
    if l.strip():
        c, src, rep = l.rstrip("\n").split("\t")
        if src not in stratum_of_sampled:
            sys.exit(f"card {c} points at {src}, which is not in {a.sample}")
        cards[c] = (src, rep == "1")
answers = {}
for n, l in enumerate(open(a.answers), 1):
    if not l.strip():
        continue
    f = l.rstrip("\n").split("\t")
    if len(f) != 2 or f[0] not in cards or f[1] not in ("YES", "NO") or f[0] in answers:
        sys.exit(f"{a.answers}:{n}: malformed or repeated answer row")
    answers[f[0]] = f[1] == "YES"
given = defaultdict(dict)
for c, (src, rep) in cards.items():
    if c in answers:
        given[src]["rep" if rep else "orig"] = answers[c]
human = {}
for src, g in given.items():
    if src not in llm:
        sys.exit(f"{src} was answered but has no LLM label (excluded by the scorer's failure rule)")
    human[src] = g.get("orig", g.get("rep"))

if a.mode == "storm":
    lines_of = lambda p: {int(x) for x in open(p) if x.strip()}
    ft, base = lines_of(a.ft), lines_of(a.base)
    kw = set().union(*(lines_of(p) for p in a.keyword))
    stratum = {}
    for row in list(open(f"{a.data}/labelset/key.tsv"))[1:]:   # every item, as bin/draw_audit.py partitions them
        i, line, st, _ = row.split()
        line = int(line)
        stratum[i] = ("S5" if st != "pool" else "S1" if line in ft and line in kw else "S2" if line in ft
                      else "S3" if line in kw else "S4" if line in base else None)
        if stratum[i] is None:
            sys.exit(f"{i} is in the pool but flagged by no system")
    counts = defaultdict(int)
    for s in stratum.values():
        counts[s] += 1
    if dict(counts) != size or any(stratum[i] != s for i, s in stratum_of_sampled.items()):
        sys.exit(f"recomputed strata {dict(counts)} do not match {a.sample} {size}")
else:
    stratum = {i: ("YES" if y else "NO") for i, y in llm.items()}
    if any(stratum.get(i) != s for i, s in stratum_of_sampled.items()):
        sys.exit(f"a sampled item's final label does not match its stratum in {a.sample}")

audited = {s: sorted((i, human[i], llm[i]) for i in human if stratum_of_sampled[i] == s) for s in order}


def kappa(pairs):   # pairs of (human, llm) booleans; nan when either rater gave a single label
    n = len(pairs)
    yh, ym = sum(h for h, _ in pairs) / n, sum(m for _, m in pairs) / n
    if yh in (0, 1) or ym in (0, 1):
        return float("nan")
    po = sum(h == m for h, m in pairs) / n
    pe = yh * ym + (1 - yh) * (1 - ym)
    return (po - pe) / (1 - pe)


def kappa_cell(pairs, rng):
    k = kappa(pairs)
    if k != k:
        return "not estimable (a rater gave one label)"
    ks = [kk for kk in (kappa([pairs[rng.randrange(len(pairs))] for _ in pairs]) for _ in range(a.resamples)) if kk == kk]
    if not ks:
        return f"{k:.2f} (no resample estimable)"
    return f"{k:.2f} ({{:.2f}} to {{:.2f}}; {len(ks)} of {a.resamples} resamples estimable)".format(*hd.ci(ks))


def share(x, n):
    return f"{x / n:.1%} ({x}/{n})" if n else "not estimable"


def p_of(items):   # (p1, p0); None where not estimable
    yes = [h for _, h, m in items if m]
    no = [h for _, h, m in items if not m]
    return (sum(yes) / len(yes) if yes else None, sum(no) / len(no) if no else None)


out = []
w = out.append
w(f"# Human audit ({a.mode}, {os.path.basename(a.sample)})\n")
w(f"Cards answered: {len(answers)} of {len(cards)}; items with a human label: {len(human)} of {len(sample)}.\n")
w("| Stratum | Answered / drawn | Raw agreement (Wilson 95%) | Kappa (95% bootstrap) | Positive agreement | Negative agreement | p1 | p0 |")
w("|---|---|---|---|---|---|---|---|")
krng = random.Random(a.seed)
for s in order:
    pairs = [(h, m) for _, h, m in audited[s]]
    n = len(pairs)
    flag = "" if n >= 0.8 * drawn[s] else " (incomplete)"
    if not n:
        w(f"| {s} | 0 / {drawn[s]}{flag} | not estimable | not estimable | not estimable | not estimable | not estimable | not estimable |")
        continue
    agree = sum(h == m for h, m in pairs)
    lo, hi = hd.wilson(agree, n)
    a_, d_ = sum(h and m for h, m in pairs), sum(not h and not m for h, m in pairs)
    bc = n - agree
    p1n = [h for h, m in pairs if m]
    p0n = [h for h, m in pairs if not m]
    w(f"| {s} | {n} / {drawn[s]}{flag} | {agree / n:.1%} ({lo:.1%}-{hi:.1%}) | {kappa_cell(pairs, krng)} | "
      f"{share(2 * a_, 2 * a_ + bc)} | {share(2 * d_, 2 * d_ + bc)} | {share(sum(p1n), len(p1n))} | {share(sum(p0n), len(p0n))} |")
if a.mode == "balanced":
    pairs = [(h, m) for s in order for _, h, m in audited[s]]
    if pairs:
        agree = sum(h == m for h, m in pairs)
        lo, hi = hd.wilson(agree, len(pairs))
        w(f"\nPooled over the balanced sample (unweighted): raw agreement {agree / len(pairs):.1%} ({lo:.1%}-{hi:.1%}), "
          f"kappa {kappa_cell(pairs, krng)}")
rt = [(g["orig"], g["rep"]) for g in given.values() if "orig" in g and "rep" in g]
w(f"\nTest-retest on hidden repeats: {sum(x == y for x, y in rt)} of {len(rt)} answered pairs agree.")

if a.mode == "storm":
    # Sums of weight by (stratum, LLM label), over all labeled items and over each system's flags.
    cells = [(s, m) for s in order for m in (True, False)]
    total = defaultdict(float)
    flagged = {n: defaultdict(float) for n in names}
    contr = {"strict OR h1": hd.union(a.strict, a.h1), "strict": hd.union(a.strict)}
    flagged_c = {c: defaultdict(float) for c in contr}
    for i, line, st, wt, y, f in rows:
        total[(stratum[i], y)] += wt
        for n in names:
            if f[n]:
                flagged[n][(stratum[i], y)] += wt
        for c, pred in contr.items():
            if pred(f):
                flagged_c[c][(stratum[i], y)] += wt

    def ys(p):   # y per (stratum, LLM label); a p that is not estimable leaves the LLM label standing
        return {(s, m): (1.0 if m else 0.0) if p[s][0 if m else 1] is None else p[s][0 if m else 1] for s, m in cells}

    def metrics(p):
        y = ys(p)
        den = sum(total[c] * y[c] for c in cells)
        res = {}
        for n in names:
            fw = sum(flagged[n][c] for c in cells)
            fy = sum(flagged[n][c] * y[c] for c in cells)
            res[n] = (fy / fw if fw else float("nan"), fy / den if den else 0.0)
        rec = {c: (sum(flagged_c[c][k] * y[k] for k in cells) / den if den else 0.0) for c in contr}
        res["H2"] = rec["strict OR h1"] - rec["strict"]
        return res

    point = metrics({s: p_of(audited[s]) for s in order})
    rng = random.Random(a.seed)
    boot, fallback = [], defaultdict(int)
    for _ in range(a.resamples):
        p = {s: p_of([audited[s][rng.randrange(len(audited[s]))] for _ in audited[s]]) for s in order}
        for s in order:
            for k, m in ((0, "LLM-YES"), (1, "LLM-NO")):
                if p[s][k] is None and total[(s, k == 0)]:
                    fallback[(s, m)] += 1
        boot.append(metrics(p))

    def with_ci(est, values):   # a system with no flags has no precision in any resample
        values = [v for v in values if v == v]
        return f"{est:.1%} ({{:.1%}}-{{:.1%}})".format(*hd.ci(values)) if values and est == est else "n/a"

    w("\n## Audit-corrected precision and recall (sensitivity; the LLM key decides H1)\n")
    w("| System | Precision (95% bootstrap) | Weighted recall (95% bootstrap) |")
    w("|---|---|---|")
    for n in names:
        w(f"| {n} | {with_ci(point[n][0], [b[n][0] for b in boot])} | {with_ci(point[n][1], [b[n][1] for b in boot])} |")
    lo, hi = hd.ci([b["H2"] for b in boot])
    w(f"\n- H2 gain, audit-corrected: (strict OR h1) - strict: {point['H2']:+.1%} "
      f"(95% audit-sampling interval {lo:+.1%} to {hi:+.1%}; the labeled set is not resampled)")
    p, r = point[a.h1]
    missed = sum(1 for row in rows if row[4] and row[5][a.h1] and not row[5][a.strict])
    w(f"- H1 ({a.h1}), audit-corrected: precision {p:.1%}, weighted recall {r:.1%}, final-YES flags strict missed "
      f"(LLM key) {missed} -> {'PASS' if p >= 0.80 and r >= 0.80 and missed >= 1 else 'FAIL'} (point estimates; sensitivity only)")
    falls = [f"{s} {m}: {k}" for (s, m), k in sorted(fallback.items()) if k]
    w(f"- Resamples where a cell had no audited item and its LLM label stood (of {a.resamples}): "
      + ("; ".join(falls) if falls else "none"))
open(a.out, "w").write("\n".join(out) + "\n")
print("\n".join(out))
