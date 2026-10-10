"""Score every article in the text view with Laya's frozen noul question.

Usage: python -I bin/laya_score.py freeze/config.json data/window.txt OUT.tsv [--limit N]
Writes `line<TAB>p_true<TAB>route` per article in line order (1-based lines, matching rg -n).
Resumes from the last complete block if OUT.tsv already exists. LAYA_DEVICE picks the device (default mps; cuda on ROCm). LAYA_MATCH_MPS_PRECISION=1 reproduces M6 numerics elsewhere.
"""
import json
import os
import sys
import time

import laya

BLOCK = 256

cfg_path, text_path, out_path = sys.argv[1:4]
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
cfg = json.load(open(cfg_path))
questions = cfg["laya_questions"]
qid = next(iter(questions))

lines = open(text_path).read().splitlines()
if limit:
    lines = lines[:limit]
done = sum(1 for _ in open(out_path)) if os.path.exists(out_path) else 0

agent = laya.load(cfg["laya_checkpoint"], device=os.environ.get("LAYA_DEVICE", "mps"))
if os.environ.get("LAYA_MATCH_MPS_PRECISION") == "1" and agent.device.type != "mps":
    # Laya's MPS rule on any device: fp32 below mps_amp_min_rows rows, autocast at or above. Matches M6 scores.
    agent._amp_enabled_for = lambda rows: agent.amp_enabled and rows >= agent.mps_amp_min_rows
t0, scored = time.time(), 0

with open(out_path, "a") as out:
    for start in range(done, len(lines), BLOCK):
        block = lines[start:start + BLOCK]
        ntok = [len(ids) for ids in agent.tok(block, add_special_tokens=False)["input_ids"]]
        short = [i for i, n in enumerate(ntok) if n <= cfg["short_max_tokens"]]
        probs, routes = [None] * len(block), [None] * len(block)
        if short:
            results = agent.predict_batch([{"body": block[i]} for i in short], questions, batch_size=64)
            for i, r in zip(short, results):
                probs[i], routes[i] = r["answers"][qid]["noul"], "batch"
        for i in (i for i in range(len(block)) if probs[i] is None):
            r = agent.predict_long({"body": block[i]}, questions)
            probs[i], routes[i] = r["answers"][qid]["noul"], "long"
        out.writelines(f"{start + i + 1}\t{p:.4f}\t{routes[i]}\n" for i, p in enumerate(probs))
        out.flush()
        scored += len(block)
        rate = scored / (time.time() - t0)
        left = (len(lines) - start - len(block)) / rate
        print(f"{start + len(block)}/{len(lines)}  {rate:.0f}/s  eta {left / 60:.0f} min", file=sys.stderr, flush=True)
