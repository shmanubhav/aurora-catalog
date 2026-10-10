"""Score the spike: final labels, Laya and rg precision and weighted recall, Laya-only finds, cutoff sweep.

Usage: python -I bin/score.py freeze/config.json data ADJUDICATION.tsv OUT.md
Final label = the adjudicated label where one exists (every disagreement, Gemma UNPARSED, agreed checks),
else the Claude/Gemma consensus. Net-sample items carry weight N (1-in-N sample of the loose net), pool items 1.
Recall is relative to positives inside pool + loose net; positives outside both are unobserved.
"""
import glob
import json
import math
import random
import sys

cfg_path, d, adj_path, out_path = sys.argv[1:5]
cfg = json.load(open(cfg_path))
cutoff = cfg["cutoff"]

key = {}
for row in list(open(f"{d}/labelset/key.tsv"))[1:]:
    item_id, line, stratum, weight = row.split()
    key[item_id] = (int(line), stratum, float(weight))
claude = dict(l.split() for p in glob.glob(f"{d}/labels/claude/b*.tsv") for l in open(p))
gemma = {l.split("\t")[0]: l.split("\t")[1] for l in open(f"{d}/labels/gemma.tsv")}
adj = {l.split("\t")[0]: l.split("\t")[1].strip() for l in open(adj_path) if l.strip()}
kinds = dict(l.split() for l in list(open(f"{d}/adjudication/manifest.tsv"))[1:])
missing = [i for i, k in kinds.items() if i not in adj]
if missing:
    sys.exit(f"{len(missing)} adjudication items have no label, e.g. {missing[:3]}")

final = {i: adj.get(i, claude[i]) for i in key}
assert all(claude[i] == gemma[i] or i in adj for i in key), "an unadjudicated disagreement"
p_laya = {int(l.split("\t")[0]): float(l.split("\t")[1]) for l in open(f"{d}/laya_scores.tsv")}
rg = {int(l) for l in open(f"{d}/rg_strict.lines")}
meta = {}
wanted = {line for line, _, _ in key.values()}
for n, l in enumerate(open(f"{d}/window.jsonl"), 1):
    if n in wanted:
        a = json.loads(l)
        meta[n] = (a["date"], a["newspaper_name"] or "?", (a["headline"] or a["article"])[:70].replace("\n", " "))

rows = [(i, line, stratum, w, final[i] == "YES", p_laya[line], line in rg) for i, (line, stratum, w) in key.items()]


def metrics(rows, t=cutoff):
    pos = sum(w for *_, w, y, _, _ in [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows] if y)
    lf = [r for r in rows if r[5] >= t]
    rf = [r for r in rows if r[6]]
    tp_l = sum(r[3] for r in lf if r[4])
    tp_r = sum(r[3] for r in rf if r[4])
    tp_u = sum(r[3] for r in rows if r[4] and (r[5] >= t or r[6]))
    return {"pos": pos, "laya_flags": sum(r[3] for r in lf), "laya_tp": tp_l, "rg_flags": sum(r[3] for r in rf),
            "rg_tp": tp_r, "union_tp": tp_u}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (m - c, m + c)


m = metrics(rows)
prec_l, prec_r = m["laya_tp"] / m["laya_flags"], m["rg_tp"] / m["rg_flags"]
rec_l, rec_r, rec_u = m["laya_tp"] / m["pos"], m["rg_tp"] / m["pos"], m["union_tp"] / m["pos"]

rng = random.Random(cfg["seed"])
pool = [r for r in rows if r[2] == "pool"]
net = [r for r in rows if r[2] == "net"]
boot = []
for _ in range(2000):
    s = [rng.choice(pool) for _ in pool] + [rng.choice(net) for _ in net]
    b = metrics(s)
    if b["pos"]:
        boot.append((b["laya_tp"] / b["pos"], b["rg_tp"] / b["pos"]))
boot_l = sorted(x for x, _ in boot)
boot_r = sorted(y for _, y in boot)
ci = lambda v: (v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1])

laya_only = sorted((r for r in rows if r[4] and r[5] >= cutoff and not r[6]), key=lambda r: -r[5])
rg_only = sorted((r for r in rows if r[4] and r[6] and r[5] < cutoff), key=lambda r: r[5])
net_yes = [r for r in net if r[4]]

agree = [(claude[i], gemma[i]) for i in key if gemma[i] != "UNPARSED"]
po = sum(a == b for a, b in agree) / len(agree)
pc = sum((sum(a == v for a, _ in agree) / len(agree)) * (sum(b == v for _, b in agree) / len(agree)) for v in ("YES", "NO"))
kappa = (po - pc) / (1 - pc)
checks = [i for i, k in kinds.items() if k == "agreed-check"]
overturned = [i for i in checks if adj[i] != claude[i]]

out = []
w = out.append
w(f"# Aurora spike results (cutoff {cutoff})\n")
w(f"Labeled items: {len(rows)} (pool {len(pool)}, net sample {len(net)} at weight {net[0][3]:.0f}). "
  f"Estimated positives in pool + loose net: {m['pos']:.0f} (pool {sum(r[4] for r in pool)}, net sample {len(net_yes)} -> {len(net_yes) * net[0][3]:.0f}).\n")
w("| | Flags | True | Precision (95% CI) | Weighted recall (95% bootstrap) |\n|---|---|---|---|---|")
lo, hi = wilson(m["laya_tp"], m["laya_flags"])
w(f"| Laya >= {cutoff} | {m['laya_flags']:.0f} | {m['laya_tp']:.0f} | {prec_l:.1%} ({lo:.1%}-{hi:.1%}) | {rec_l:.1%} ({ci(boot_l)[0]:.1%}-{ci(boot_l)[1]:.1%}) |")
lo, hi = wilson(m["rg_tp"], m["rg_flags"])
w(f"| rg strict | {m['rg_flags']:.0f} | {m['rg_tp']:.0f} | {prec_r:.1%} ({lo:.1%}-{hi:.1%}) | {rec_r:.1%} ({ci(boot_r)[0]:.1%}-{ci(boot_r)[1]:.1%}) |")
w(f"| Either | | {m['union_tp']:.0f} | | {rec_u:.1%} |\n")
w(f"Laya-only sightings (rg strict missed): {len(laya_only)}. rg-only sightings (Laya < {cutoff}): {len(rg_only)}. "
  f"Sightings missed by both (net sample): {len(net_yes)} sampled, about {len(net_yes) * net[0][3]:.0f} estimated.\n")
w("## Laya cutoff sweep (cutoffs below 0.5 are not measurable: lower-scored articles were only labeled when rg or the loose net flagged them)\n")
w("| Cutoff | Flags | True | Precision | Weighted recall |\n|---|---|---|---|---|")
for t in (0.5, 0.6, 0.7, 0.8, 0.9):
    mt = metrics(rows, t)
    w(f"| {t:.1f} | {mt['laya_flags']:.0f} | {mt['laya_tp']:.0f} | {mt['laya_tp'] / mt['laya_flags']:.1%} | {mt['laya_tp'] / mt['pos']:.1%} |")
w(f"\n## Labelers\nClaude vs Gemma: raw agreement {po:.1%}, Cohen's kappa {kappa:.2f} ({len(agree)} items; "
  f"{sum(g == 'UNPARSED' for g in gemma.values())} Gemma loops excluded). "
  f"Adjudicator overturned {len(overturned)} of {len(checks)} agreed checks.\n")
w("## Laya-only sightings\n")
for r in laya_only:
    date, paper, head = meta[r[1]]
    w(f"- line {r[1]} p={r[5]:.2f} {date} {paper}: {head}")
w("\n## rg-only sightings Laya missed\n")
for r in rg_only:
    date, paper, head = meta[r[1]]
    w(f"- line {r[1]} p={r[5]:.2f} {date} {paper}: {head}")
w("\n## Sightings in the net sample (missed by both)\n")
for r in net_yes:
    date, paper, head = meta[r[1]]
    w(f"- line {r[1]} p={r[5]:.2f} {date} {paper}: {head}")
open(out_path, "w").write("\n".join(out) + "\n")
print("\n".join(out[:12]))
