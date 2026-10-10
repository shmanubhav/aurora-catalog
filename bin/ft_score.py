"""Score articles with a fine-tuned Laya checkpoint, whole article per call (no windowing).

Usage (in the laya-batch container): python -I ft_score.py CHECKPOINT_DIR config.json IN.jsonl OUT.tsv MAX_LEN
IN.jsonl rows need "line" and "state" (an "id" is passed through when present). Writes id<TAB>line<TAB>p_true.
"""
import json
import sys

import laya

ckpt, cfg_path, in_path, out_path, max_len = sys.argv[1:6]
questions = json.load(open(cfg_path))["laya_questions"]
qid = next(iter(questions))
rows = [json.loads(line) for line in open(in_path)]
rows.sort(key=lambda r: len(r["state"]))   # similar lengths per batch: less padding
agent = laya.load(ckpt, device="cuda")
with open(out_path, "w") as out:
    for start in range(0, len(rows), 16):
        chunk = rows[start:start + 16]
        results = agent.predict_batch([{"body": r["state"]} for r in chunk], questions, batch_size=16,
                                      max_len=int(max_len))
        for r, res in zip(chunk, results):
            out.write(f"{r.get('id', '')}\t{r['line']}\t{res['answers'][qid]['noul']:.4f}\n")
        out.flush()
print(f"scored {len(rows)}", file=sys.stderr)
