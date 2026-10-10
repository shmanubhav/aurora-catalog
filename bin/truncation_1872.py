"""Truncation count (prereg sections 3 and 7): fine-tuned Laya keeps the first MAX_LEN tokens of a longer article,
and the articles it cut are counted.

Usage: .venv/bin/python -I bin/truncation_1872.py FT_DIR CONFIG.json IN.jsonl OUT.md [--max-len 4096]
FT_DIR holds a copy of the fine-tuned checkpoint's rl_agent_config.json and tokenizer/ (no weights needed); CONFIG.json
is the ft config.json with laya_questions; IN.jsonl is what bin/ft_score.py scored ({"line", "state"} rows).
Each article is encoded exactly as laya 0.4.1 Agent.predict_batch encodes it for ft_score.py (state {"body": text},
the checkpoint's head_max_len, max_len=MAX_LEN): the library's own Agent._to_internal and Agent._encode_state run on a
stand-in that holds only the tokenizer and config, so state_tokens_dropped is the model's own count, not an estimate.
"""
import argparse
import json
import os

import laya
from laya import agent as la
from laya.common import uses_parallel_layout

ap = argparse.ArgumentParser()
ap.add_argument("ft_dir")
ap.add_argument("config")
ap.add_argument("inp")
ap.add_argument("out")
ap.add_argument("--max-len", type=int, default=4096)
a = ap.parse_args()
assert laya.__version__ == "0.4.1", laya.__version__


class Encoder:   # what Agent._encode_state reads from self
    pass


la._fix_tokenizer_config(a.ft_dir)   # the same patch laya.load applies before reading the tokenizer
enc = Encoder()
enc.cfg = json.load(open(os.path.join(a.ft_dir, "rl_agent_config.json")))
enc.tok = la._load_tokenizer(os.path.join(a.ft_dir, "tokenizer"), enc.cfg)
enc.parallel_options = uses_parallel_layout(enc.cfg)
questions = json.load(open(a.config))["laya_questions"]
ids = list(questions)
internal = {q: la.Agent._to_internal(questions[q]) for q in ids}

total, cut, longest = 0, [], 0
for row in map(json.loads, open(a.inp)):
    items = la.Agent._encode_state(enc, {"body": row["state"]}, ids, internal, max_len=a.max_len)
    stats = [it["state_stats"] for it in items]
    total += 1
    longest = max(longest, stats[0]["state_tokens"])
    dropped = max(s["state_tokens_dropped"] for s in stats)
    if dropped:
        cut.append((row["line"], stats[0]["state_tokens"], dropped))

out = [f"# Fine-tuned Laya truncation count (max_len {a.max_len}, head_max_len {enc.cfg.get('head_max_len', 192)})\n",
       f"Articles scored: {total}. Truncated (any state token dropped): {len(cut)}. Longest article: {longest} tokens.\n"]
out += [f"- line {n}: {t} tokens, {d} dropped" for n, t, d in cut]
open(a.out, "w").write("\n".join(out) + "\n")
print("\n".join(out[:2]))
