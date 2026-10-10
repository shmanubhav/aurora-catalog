"""Build spike 2's training rows, presumed-NO samples, reprint groups and grouped folds.

Usage: python -I bin/prep_finetune.py freeze/config.json freeze/finetune.json data OUTDIR
Writes OUTDIR/rows.jsonl ({id, line, state, questions, expected, fold, group}; labeled + presumed-NO train),
OUTDIR/gate.jsonl (presumed-NO gate sample, minus reprints of any training article) and OUTDIR/prep_stats.json.
"""
import glob
import json
import random
import re
import sys
from collections import defaultdict

cfg_path, ft_path, d, outdir = sys.argv[1:5]
cfg, ft = json.load(open(cfg_path)), json.load(open(ft_path))
rng = random.Random(ft["seed"])
question = cfg["laya_questions"]
qid = next(iter(question))

lines = open(f"{d}/window.txt").read().splitlines()
key = {row.split()[0]: int(row.split()[1]) for row in list(open(f"{d}/labelset/key.tsv"))[1:]}
claude = dict(l.split() for p in glob.glob(f"{d}/labels/claude/b*.tsv") for l in open(p))
adj = {l.split("\t")[0]: l.split("\t")[1] for l in open(ft["adjudication"])}
final = {i: adj.get(i, claude[i]) for i in key}

# Presumed NO: never in the pool, never a loose-net hit, never labeled.
excluded = {int(x) for f in ("pool.lines", "rg_loose.lines") for x in open(f"{d}/{f}")} | set(key.values())
candidates = [n for n in range(1, len(lines) + 1) if n not in excluded and lines[n - 1].strip()]
sampled = rng.sample(candidates, ft["presumed_no_train"] + ft["presumed_no_gate"])
train_neg, gate_neg = sampled[:ft["presumed_no_train"]], sampled[ft["presumed_no_train"]:]

docs = {n: ("labeled", final[i] == "YES") for i, n in key.items()}
docs.update({n: ("presumed_no", False) for n in train_neg})
docs.update({n: ("gate", False) for n in gate_neg})


def shingles(text, k=ft["shingle_words"]):
    words = re.findall(r"[a-z]+", text.lower())
    return {hash(" ".join(words[j:j + k])) for j in range(max(0, len(words) - k + 1))}


sh = {n: shingles(lines[n - 1]) for n in docs}
index = defaultdict(list)
for n, s in sh.items():
    for h in s:
        index[h].append(n)
parent = {n: n for n in docs}


def find(n):
    while parent[n] != n:
        parent[n] = parent[parent[n]]
        n = parent[n]
    return n


# Candidate pairs share a shingle that is rare enough to mean something; then test containment.
shared = defaultdict(int)
for h, ns in index.items():
    if 1 < len(ns) <= ft["max_shingle_df"]:
        for a in range(len(ns)):
            for b in range(a + 1, len(ns)):
                shared[(ns[a], ns[b])] += 1
dup_pairs = 0
for (a, b), c in shared.items():
    if sh[a] and sh[b] and c / min(len(sh[a]), len(sh[b])) >= ft["reprint_containment"]:
        parent[find(a)] = find(b)
        dup_pairs += 1

groups = defaultdict(list)
for n in docs:
    groups[find(n)].append(n)
gid = {n: min(g) for g in groups.values() for n in g}   # stable id: string hashes vary per process

# Gate articles that reprint any training article would flatter the false-alarm count: drop them.
train_groups = {gid[n] for n, (kind, _) in docs.items() if kind != "gate"}
gate = [n for n in gate_neg if gid[n] not in train_groups]

# Grouped folds: whole groups only, positives spread first, then fill by size.
train_group_list = sorted((sorted(g) for g in groups.values() if any(docs[n][0] != "gate" for n in g)), key=min)
rng.shuffle(train_group_list)
train_group_list.sort(key=lambda g: -sum(docs[n][1] for n in g))
folds, pos, size = {}, [0] * ft["folds"], [0] * ft["folds"]
for g in train_group_list:
    p = sum(docs[n][1] for n in g if docs[n][0] != "gate")
    f = min(range(ft["folds"]), key=lambda k: (pos[k], size[k])) if p else min(range(ft["folds"]), key=lambda k: size[k])
    for n in g:
        folds[n] = f
    pos[f] += p
    size[f] += len(g)

line_to_id = {n: i for i, n in key.items()}
with open(f"{outdir}/rows.jsonl", "w") as out:
    for n, (kind, yes) in sorted(docs.items()):
        if kind == "gate":
            continue
        out.write(json.dumps({"id": line_to_id.get(n, f"neg{n}"), "line": n, "kind": kind, "state": lines[n - 1],
                              "questions": question, "expected": {qid: yes}, "fold": folds[n],
                              "group": gid[n]}) + "\n")
with open(f"{outdir}/gate.jsonl", "w") as out:
    for n in gate:
        out.write(json.dumps({"line": n, "state": lines[n - 1]}) + "\n")
stats = {"labeled": len(key), "labeled_yes": sum(v == "YES" for v in final.values()),
         "presumed_no_train": len(train_neg), "gate_sampled": len(gate_neg), "gate_kept": len(gate),
         "unlabeled_pool_size": len(candidates), "reprint_pairs": dup_pairs,
         "groups_in_training": len(train_group_list),
         "multi_doc_groups": sum(1 for g in train_group_list if len(g) > 1),
         "fold_sizes": size, "fold_positives": pos}
json.dump(stats, open(f"{outdir}/prep_stats.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
