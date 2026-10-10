"""Draw the human-audit sample (freeze/config_1872.json, human_audit).

Usage, holdout:  python -I bin/draw_audit.py storm DATA ITEMS.jsonl OUT.tsv --size 250 --seed 1872
                   --ft FLAGS.lines --keyword FLAGS.lines [--keyword FLAGS.lines] --base FLAGS.lines
Usage, 1859:     python -I bin/draw_audit.py balanced DATA ITEMS.jsonl OUT.tsv --size 100 --seed 1872 --adjudication ADJ.tsv
storm: every labeled item falls in exactly one stratum, by priority: S1 ft AND keyword; S2 ft, no keyword;
S3 keyword, no ft; S4 base Laya only; S5 loose-net sample. Each stratum gets min(25, size), the rest is
allocated proportionally to (size - that share) by largest remainder (ties to the lower stratum number),
then drawn with random.Random(seed) within stratum. balanced: half final-YES, half final-NO.
Writes OUT.tsv (id, stratum, stratum_size, drawn) and ITEMS.jsonl ({"id", "text"}) for the audit page.
"""
import argparse
import glob
import json
import random
import sys
import importlib.util
import os
_spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ao)

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["storm", "balanced"])
ap.add_argument("data")
ap.add_argument("items_out")
ap.add_argument("out")
ap.add_argument("--size", type=int, required=True)
ap.add_argument("--seed", type=int, required=True)
ap.add_argument("--ft")
ap.add_argument("--keyword", action="append", default=[])
ap.add_argument("--base")
ap.add_argument("--adjudication")
a = ap.parse_args()

key = {}
for row in list(open(f"{a.data}/labelset/key.tsv"))[1:]:
    item_id, line, stratum, weight = row.split()
    key[item_id] = (int(line), stratum)
texts = {json.loads(l)["id"]: json.loads(l)["text"] for l in open(f"{a.data}/labelset/items.jsonl")}
lines_of = lambda p: {int(x) for x in open(p) if x.strip()}
rng = random.Random(a.seed)

if a.mode == "storm":
    ft, base = lines_of(a.ft), lines_of(a.base)
    kw = set().union(*(lines_of(p) for p in a.keyword))
    strata = {f"S{k}": [] for k in range(1, 6)}
    for i, (line, st) in key.items():   # key.tsv order, then sorted below for a stable draw
        if st != "pool":
            s = "S5"
        elif line in ft and line in kw:
            s = "S1"
        elif line in ft:
            s = "S2"
        elif line in kw:
            s = "S3"
        elif line in base:
            s = "S4"
        else:
            sys.exit(f"{i} (line {line}) is in the pool but flagged by no system")
        strata[s].append(i)
    first = {s: min(25, len(v)) for s, v in strata.items()}
    rest = a.size - sum(first.values())
    room = {s: len(v) - first[s] for s, v in strata.items()}
    total_room = sum(room.values())
    # Largest remainder in exact integers; if fewer than --size items are labeled, all are drawn.
    parts = {s: divmod(max(rest, 0) * room[s], total_room) if total_room else (0, 0) for s in strata}
    alloc = {s: first[s] + parts[s][0] for s in strata}
    left = max(rest, 0) - sum(q for q, _ in parts.values())
    for s in sorted(strata, key=lambda s: (-parts[s][1], s))[:max(0, left)]:
        alloc[s] += 1
    alloc = {s: min(alloc[s], len(strata[s])) for s in strata}
else:
    claude = {k: v for p in sorted(glob.glob(f"{a.data}/labels/claude/b*.tsv")) for k, v in ao.read_labels(p, ("YES", "NO", "MISSING"), 2).items()}
    adj = ao.read_labels(a.adjudication, ("YES", "NO"), 3)
    final = {i: adj.get(i, claude[i]) for i in key}
    strata = {"YES": [i for i in key if final[i] == "YES"], "NO": [i for i in key if final[i] == "NO"]}
    alloc = {"YES": a.size // 2, "NO": a.size - a.size // 2}

drawn = []
with open(a.out, "w") as out:
    out.write("id\tstratum\tstratum_size\tdrawn\n")
    for s in strata:
        pick = sorted(rng.sample(sorted(strata[s]), alloc[s]))
        drawn += pick
        out.writelines(f"{i}\t{s}\t{len(strata[s])}\t{alloc[s]}\n" for i in pick)
rng.shuffle(drawn)
with open(a.items_out, "w") as out:
    out.writelines(json.dumps({"id": i, "text": texts[i]}) + "\n" for i in drawn)
print(" ".join(f"{s}:{alloc[s]}/{len(v)}" for s, v in strata.items()), f"total {len(drawn)}", file=sys.stderr)
