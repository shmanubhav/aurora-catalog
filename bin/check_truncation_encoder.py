"""Check that bin/truncation_1872.py's stand-in encoder reports the same state_tokens_dropped as a real laya
Agent.predict_batch, on base Laya (M6), the 30 longest 1859 articles, at small max_len so truncation happens.

Usage: HF_HUB_OFFLINE=1 .venv/bin/python -I bin/check_truncation_encoder.py BASE_LAYA_SNAPSHOT data/window.txt freeze/config.json
Output of the run on 2026-10-10: results/1872/truncation_encoder_check.txt."""
import json
import sys

import laya
from laya import agent as la
from laya.common import uses_parallel_layout

snap, window, cfg_path = sys.argv[1:4]
questions = json.load(open(cfg_path))["laya_questions"]
texts = open(window).read().splitlines()
longest = sorted(range(len(texts)), key=lambda i: -len(texts[i]))[:30]
states = [{"body": texts[i]} for i in longest]

agent = laya.load(snap, device="mps")
for max_len in (256, 1024):
    real = [r["usage"]["state_tokens_dropped"] for r in agent.predict_batch(states, questions, batch_size=8, max_len=max_len)]

    class Encoder:
        pass
    enc = Encoder()
    enc.cfg = json.load(open(f"{snap}/rl_agent_config.json"))
    enc.tok = la._load_tokenizer(f"{snap}/tokenizer", enc.cfg)
    enc.parallel_options = uses_parallel_layout(enc.cfg)
    ids = list(questions)
    internal = {q: la.Agent._to_internal(questions[q]) for q in ids}
    mine = [max(it["state_stats"]["state_tokens_dropped"] for it in la.Agent._encode_state(enc, s, ids, internal, max_len=max_len))
            for s in states]
    print(f"max_len {max_len}: real {real[:6]}... stand-in {mine[:6]}... identical: {real == mine}, truncated {sum(x > 0 for x in real)}/30")
