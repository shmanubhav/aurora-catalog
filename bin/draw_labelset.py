"""Build the blind label set: every pool article plus a seeded 1-in-N sample of the loose-net-only articles.

Usage: python -I bin/draw_labelset.py freeze/config.json data/window.txt data/pool.lines data/net_only.lines OUTDIR
Writes OUTDIR/items.jsonl ({"id", "text"} in shuffled order, no source hints) and
OUTDIR/key.tsv (id, line, stratum, weight). Labelers only ever see items.jsonl.
"""
import json
import math
import os
import random
import sys

cfg_path, text_path, pool_path, net_path, outdir = sys.argv[1:6]
cfg = json.load(open(cfg_path))
rng = random.Random(cfg["seed"])

lines = open(text_path).read().splitlines()
pool = sorted(int(x) for x in open(pool_path))
net = sorted(int(x) for x in open(net_path))
if "loose_net" in cfg:   # 1872 rule (freeze/config_1872.json): N = max(5, ceil(H / target)), no pool cap
    n = max(5, math.ceil(len(net) / cfg["loose_net"]["target_sample"]))
    if cfg["pool"]["cap"] is not None and len(pool) > cfg["pool"]["cap"]:
        sys.exit(f"pool has {len(pool)} articles, over the cap {cfg['pool']['cap']}")
else:   # 1859 rule (freeze/config.json)
    n, cap = cfg["loose_sample_rate_n"], cfg["pool_cap"]
    if len(pool) > cap:
        sys.exit(f"pool has {len(pool)} articles, over pool_cap {cap}")

# Python round() (half to even); at least one article when H > 0, none (no net stratum) when H = 0.
sample = sorted(rng.sample(net, max(1, round(len(net) / n)))) if net else []
print(f"H {len(net)}  N {n}  n {len(sample)}  weight {len(net) / len(sample) if sample else 0:.4f}", file=sys.stderr)
items = [(line, "pool", 1.0) for line in pool] + [(line, "net", len(net) / len(sample)) for line in sample]
rng.shuffle(items)

os.makedirs(outdir, exist_ok=True)
with open(f"{outdir}/items.jsonl", "w") as out, open(f"{outdir}/key.tsv", "w") as key:
    key.write("id\tline\tstratum\tweight\n")
    for i, (line, stratum, weight) in enumerate(items, 1):
        item_id = f"a{i:04d}"
        out.write(json.dumps({"id": item_id, "text": lines[line - 1]}) + "\n")
        key.write(f"{item_id}\t{line}\t{stratum}\t{weight:.4f}\n")
print(f"pool {len(pool)}  net sample {len(sample)} of {len(net)}  items {len(items)}", file=sys.stderr)
