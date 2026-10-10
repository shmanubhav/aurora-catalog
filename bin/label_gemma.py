"""Label the blind items with Gemma on LM Studio, using the frozen labeler prompt.

Usage: python -I bin/label_gemma.py freeze/labeler_prompt.md data/labelset/items.jsonl OUT.tsv [--limit N]
Writes `id<TAB>label<TAB>finish_reason<TAB>prompt_tokens<TAB>reasoning_tokens<TAB>raw` per item; label is YES, NO or UNPARSED.
Gemma 4 reasons before answering, so max_tokens must cover that (GEMMA_MAX_TOKENS, default 4096).
Resumes from ids already in OUT.tsv; rows land in completion order. Stops if a prompt comes near the loaded context (truncation risk).
"""
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.environ.get("GEMMA_BASE", "http://localhost:1234")   # LM Studio, or the LiteLLM gateway with LLM_KEY set
KEY = os.environ.get("LLM_KEY")
CONTEXT = int(os.environ.get("GEMMA_CONTEXT", "0"))   # known server context; 0 = ask LM Studio
MODEL = os.environ.get("GEMMA_MODEL", "google/gemma-4-26b-a4b-qat")
MAX_TOKENS = int(os.environ.get("GEMMA_MAX_TOKENS", "4096"))
WORKERS = int(os.environ.get("GEMMA_WORKERS", "1"))   # parallel requests; match the loaded PARALLEL slots

prompt_path, items_path, out_path = sys.argv[1:4]
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
prompt = open(prompt_path).read().strip()
items = [json.loads(line) for line in open(items_path)][:limit]
done = {line.split("\t")[0] for line in open(out_path)} if os.path.exists(out_path) else set()


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {KEY}"} if KEY else {})})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def loaded_context():
    if CONTEXT:
        return CONTEXT
    model = call(f"/api/v0/models/{MODEL}")
    if model.get("state") != "loaded":
        sys.exit(f"{MODEL} is not loaded; load it with an explicit --context-length first")
    return model["loaded_context_length"]


def label_one(item):
    label, used, finish, thought, raw = "UNPARSED", 0, None, 0, ""
    for _attempt in range(2):
        r = call("/v1/chat/completions", {
            "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": f"{prompt}\n\nArticle:\n\n{item['text']}"}]})
        used = r["usage"]["prompt_tokens"]
        if used + MAX_TOKENS > ctx:
            raise SystemExit(f"{item['id']}: prompt {used} tokens against a {ctx} context; refusing to risk truncation")
        raw = r["choices"][0]["message"].get("content") or ""
        finish = r["choices"][0].get("finish_reason")
        thought = (r["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens") or r["usage"].get("completion_tokens", 0)
        found = re.search(r"\b(YES|NO)\b", raw.upper())
        if found:
            label = found.group(1)
            break
        if finish == "length":
            break   # a reasoning loop: at temperature 0 a retry repeats it, so leave it UNPARSED for adjudication
    return f"{item['id']}\t{label}\t{finish}\t{used}\t{thought}\t{json.dumps(raw)}\n"


todo = [item for item in items if item["id"] not in done]
ctx, t0, scored = loaded_context(), time.time(), 0
with open(out_path, "a") as out, ThreadPoolExecutor(max_workers=WORKERS) as pool:
    for line in map(lambda f: f.result(), as_completed(pool.submit(label_one, item) for item in todo)):
        out.write(line)
        out.flush()
        scored += 1
        if scored % 25 == 0:
            ctx = loaded_context()   # catches an unload and a JIT reload at another size
            rate = scored / (time.time() - t0)
            print(f"{len(done) + scored}/{len(items)}  {rate:.2f}/s", file=sys.stderr, flush=True)
print(f"done: {len(done) + scored}/{len(items)}", file=sys.stderr)
