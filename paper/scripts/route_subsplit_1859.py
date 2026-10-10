"""Split base Laya's 1859 long-route flags (articles over 300 tokens, sent to predict_long) into those laya 0.4.1 read
whole (the state fits the room the question leaves, so predict_long hands it to system_one in one pass) and those it
scored in overlapping windows. 1859 data only; written and run on 2026-10-10, after the 1872 download, when an AI
review (Claude Opus) pointed out the one-pass path.

Usage (from the repo root):
  HF_HUB_OFFLINE=1 LAYA_REVISION=7b928d828b7b0e022f929d9bd2e44165aa270148 \
  .venv/bin/python -I paper/scripts/route_subsplit_1859.py
(needs data/window.txt from bin/extract_window.py on the 1859 archive)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bin"))
import holdout_data   # noqa: E402
import laya   # noqa: E402
from laya.common import encode_text, serialize_state, window_budget   # noqa: E402

assert laya.__version__ == "0.4.1", laya.__version__
cfg = json.load(open("freeze/config.json"))
agent = laya.load(cfg["laya_checkpoint"], device="cpu")
questions = cfg["laya_questions"]
internal = [agent._to_internal(questions[q]) for q in questions]
budget, step, room = window_budget(agent.tok, internal, agent.cfg.get("max_len", 512), agent.cfg.get("head_max_len", 192))

final = {line: yes for _, line, _, _, yes, _ in holdout_data.load("data", "results/1859-adjudication-opus.tsv", [], [])["rows"]}
texts = open("data/window.txt").read().splitlines()
groups = {"read whole": [0, 0], "windowed": [0, 0]}
for row in open("data/laya_scores.tsv"):
    line, p, route = row.rstrip("\n").split("\t")
    line = int(line)
    if route != "long" or float(p) < 0.5 or line not in final:
        continue
    state = serialize_state({"body": texts[line - 1]}).replace(agent.tok.mask_token, " ")
    n = len(encode_text(agent.tok, state, add_special_tokens=False)["input_ids"])
    g = groups["read whole" if n <= room else "windowed"]
    g[0] += 1
    g[1] += final[line]
print(f"room {room} tokens, window {budget}, stride {step}")
for name, (flags, true) in groups.items():
    print(f"long route, {name}: flags {flags}, sightings {true}, precision {100 * true / flags:.1f}%")
