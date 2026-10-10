"""Compare fine-tuned Laya alone with Laya plus a second-stage verifier on the out-of-fold flags.

Usage: python -I bin/verify_metrics.py CUTOFF NAME=VERIFIER.tsv [NAME=VERIFIER.tsv ...]
VERIFIER.tsv: id<TAB>YES|NO|UNPARSED per flagged article (extra columns ignored); UNPARSED counts as YES (kept).
Uses data/labelset/key.tsv (weights), data/finetune/rows.jsonl (labels), results/finetune/oof.tsv (scores) and
results/1859-adjudication-opus.tsv (ids Opus adjudicated, reported separately because Opus helped set those labels).
The gate sample had no flags, so extrapolated false alarms are 0 for every arm.
"""
import json
import math
import sys

cutoff = float(sys.argv[1])
arms = dict(a.split("=", 1) for a in sys.argv[2:])
weight = {l.split()[0]: float(l.split()[3]) for l in list(open("data/labelset/key.tsv"))[1:]}
truth = {json.loads(l)["id"]: json.loads(l)["expected"]["aurora"] for l in open("data/finetune/rows.jsonl")}
oof = {l.split("\t")[0]: float(l.split("\t")[2]) for l in open("results/finetune/oof.tsv")}
adjudicated = {l.split("\t")[0] for l in open("results/1859-adjudication-opus.tsv")}
flagged = [i for i in weight if oof[i] >= cutoff]
pos_w = sum(weight[i] for i in weight if truth[i])


def wilson(k, n, z=1.96):
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return m - c, m + c


def report(name, kept):
    tp = [i for i in kept if truth[i]]
    lo, hi = wilson(len(tp), len(kept))
    prec_w = sum(weight[i] for i in tp) / sum(weight[i] for i in kept)
    rec_w = sum(weight[i] for i in tp) / pos_w
    removed = [i for i in flagged if i not in kept]
    print(f"{name:<14} kept {len(kept):>3}  precision {prec_w:.1%} (unweighted {len(tp)}/{len(kept)}, Wilson {lo:.1%}-{hi:.1%})  "
          f"recall {rec_w:.1%}  F1 {2 * prec_w * rec_w / (prec_w + rec_w):.3f}  "
          f"removed: {sum(not truth[i] for i in removed)} false alarms, {sum(truth[i] for i in removed)} true sightings")
    return removed


print(f"cutoff {cutoff}: {len(flagged)} flagged labeled articles, {sum(not truth[i] for i in flagged)} false alarms; "
      f"{sum(i in adjudicated for i in flagged)} of them were adjudicated by Opus\n")
report("laya alone", flagged)
for name, path in arms.items():
    verdict = {l.split("\t")[0]: l.split("\t")[1].strip() for l in open(path)}
    missing = [i for i in flagged if i not in verdict]
    if missing:
        sys.exit(f"{name}: {len(missing)} flagged ids have no verdict, e.g. {missing[:3]}")
    kept = [i for i in flagged if verdict[i] != "NO"]
    removed = report(name, kept)
    sub = [i for i in flagged if i not in adjudicated]
    fa, ts = [i for i in sub if not truth[i]], [i for i in sub if truth[i]]
    print(f"    on the {len(sub)} flags Opus never adjudicated: removed {sum(i in removed for i in fa)}/{len(fa)} false alarms, "
          f"rejected {sum(i in removed for i in ts)}/{len(ts)} true sightings")
    lost = [i for i in removed if truth[i]]
    if lost:
        print(f"    true sightings it rejected: {', '.join(sorted(lost))}")
    print(f"    false alarms it kept: {', '.join(sorted(i for i in kept if not truth[i])) or 'none'}")
print(f"\nweighted positives {pos_w:.0f}; recall is over all labeled positives (Laya misses count against every arm)")
