"""Second-stage check: ask a local Ollama model the frozen labeler question about each flagged article.

Usage: python3 -I verify_ollama.py PROMPT.md ITEMS.jsonl OUT.tsv [--limit N]
ITEMS rows need "id" and "text". Writes id<TAB>label<TAB>done_reason<TAB>prompt_tokens<TAB>eval_tokens<TAB>seconds<TAB>raw
(label YES, NO or UNPARSED). Resumes from ids already in OUT.tsv. Env: OLLAMA_URL (default http://127.0.0.1:11434),
VERIFY_MODEL (default qwen3.8:27b-q4_K_M), VERIFY_THINK (0 = answer directly, 1 = reason first), VERIFY_CTX (num_ctx).
"""
import json
import os
import re
import sys
import time
import urllib.request

URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("VERIFY_MODEL", "qwen3.8:27b-q4_K_M")
THINK = os.environ.get("VERIFY_THINK", "0") == "1"
CTX = int(os.environ.get("VERIFY_CTX", "16384"))

prompt_path, items_path, out_path = sys.argv[1:4]
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
prompt = open(prompt_path).read().strip()
items = [json.loads(line) for line in open(items_path)][:limit]
done = {line.split("\t")[0] for line in open(out_path)} if os.path.exists(out_path) else set()

n = 0
with open(out_path, "a") as out:
    for n, item in enumerate((i for i in items if i["id"] not in done), 1):
        body = {"model": MODEL, "stream": False, "think": THINK,
                "options": {"temperature": 0, "seed": 1872, "num_ctx": CTX},
                "messages": [{"role": "user", "content": f"{prompt}\n\nArticle:\n\n{item['text']}"}]}
        t0 = time.time()
        req = urllib.request.Request(URL + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as resp:
            r = json.load(resp)
        raw = r["message"].get("content") or ""   # thinking, if any, arrives in message.thinking and is not parsed
        if r.get("prompt_eval_count", 0) >= CTX:
            sys.exit(f"{item['id']}: prompt filled the {CTX}-token context; raise VERIFY_CTX")
        found = re.findall(r"\b(YES|NO)\b", raw.upper())
        label = found[-1] if found else "UNPARSED"
        out.write(f"{item['id']}\t{label}\t{r.get('done_reason')}\t{r.get('prompt_eval_count')}\t{r.get('eval_count')}\t"
                  f"{time.time() - t0:.1f}\t{json.dumps(raw)}\n")
        out.flush()
        if n % 25 == 0:
            print(f"{len(done) + n}/{len(items)}", file=sys.stderr, flush=True)
print(f"done: {len(done) + n}/{len(items)}", file=sys.stderr)
