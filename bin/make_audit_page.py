"""Build the blind human-audit page: one article per screen, YES/NO, answers kept in the browser.

Usage: python -I bin/make_audit_page.py PROMPT.md ITEMS.jsonl OUTDIR --set NAME --repeats 10 --seed 1872
ITEMS.jsonl rows: {"id","text"}. Writes OUTDIR/audit.html (article text, opaque card ids and the prompt only,
no network requests) and OUTDIR/audit_key.tsv (card_id, source_id, is_repeat), kept by the researcher.
"""
import argparse
import html
import json
import os
import random
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("prompt")
ap.add_argument("items")
ap.add_argument("outdir")
ap.add_argument("--set", required=True, dest="setname")
ap.add_argument("--repeats", type=int, default=10)
ap.add_argument("--seed", type=int, default=1872)
ap.add_argument("--min-gap", type=int, default=20)
args = ap.parse_args()
if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.setname):
    sys.exit("--set must be letters, digits, . _ -")

items = [json.loads(line) for line in open(args.items) if line.strip()]
texts = {r["id"]: r["text"] for r in items}
if len(texts) != len(items):
    sys.exit("duplicate ids in items file")
if args.repeats > len(items):
    sys.exit("more repeats than items")
rng = random.Random(args.seed)

# Order: shuffle the items, then insert hidden duplicates; retry until each pair is at least `gap` cards apart.
ids = sorted(texts)
rng.shuffle(ids)
gap = min(args.min_gap, max(1, len(ids) // 2))
if gap < args.min_gap:
    print(f"warning: only {len(ids)} items, repeat gap relaxed to {gap}", file=sys.stderr)
dups = rng.sample(ids, args.repeats)
for _attempt in range(10000):
    seq = [(i, False) for i in ids]
    for src in dups:
        seq.insert(rng.randint(0, len(seq)), (src, True))
    where = {}
    for k, (i, rep) in enumerate(seq):
        where.setdefault(i, []).append(k)
    if all(len(ps) == 1 or abs(ps[1] - ps[0]) >= gap for ps in where.values()):
        break
else:
    sys.exit("could not place repeats far enough apart")

# No highlighting: annotators see the text exactly as the LLM labelers did.


prompt = open(args.prompt).read()
prompt = re.sub(r"Reply with exactly one word: YES or NO\.?", "Press YES or NO.", prompt)
prompt_html = html.escape(prompt.strip())

os.makedirs(args.outdir, exist_ok=True)
n = len(seq)
width = max(3, len(str(n)))
card_ids = [f"c{k:0{width}d}" for k in range(1, n + 1)]
with open(os.path.join(args.outdir, "audit_key.tsv"), "w") as out:
    out.write("card_id\tsource_id\tis_repeat\n")
    for cid, (src, rep) in zip(card_ids, seq):
        out.write(f"{cid}\t{src}\t{int(rep)}\n")

cards = "\n".join(
    f'<section class="card" data-id="{cid}" hidden><p class="text">{html.escape(texts[src])}</p></section>'
    for cid, (src, _rep) in zip(card_ids, seq))

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Article Audit</title>
<style>
:root {{ --bg:#f7f5f0; --fg:#1d1d1f; --muted:#6b6b70; --card:#ffffff; --line:#e3e0d8; --yes:#1f7a4d; --no:#a33a2b; --pick:#fff3c4; --mark:#ffe58a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141416; --fg:#ececef; --muted:#9a9aa2; --card:#1e1e22; --line:#2e2e34; --yes:#4cc38a; --no:#f07a68; --pick:#3a3320; --mark:#6b5a14; }} }}
* {{ box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--fg); font:18px/1.6 Georgia, serif; margin:0; padding:0 16px 40px; }}
header {{ position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line); padding:10px 0; z-index:1; }}
.bar {{ max-width:760px; margin:0 auto; display:flex; gap:10px; align-items:center; flex-wrap:wrap; font-family:system-ui, sans-serif; }}
#progress {{ flex:1; color:var(--muted); font-size:16px; }}
details {{ max-width:760px; margin:14px auto; font-family:system-ui, sans-serif; font-size:15px; color:var(--muted); white-space:pre-wrap; }}
summary {{ cursor:pointer; color:var(--fg); }}
.card {{ max-width:760px; margin:14px auto; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }}
.text {{ margin:0; overflow-wrap:anywhere; }}
mark {{ background:var(--mark); color:inherit; border-radius:3px; padding:0 2px; }}
button {{ font:600 16px system-ui, sans-serif; padding:10px 14px; border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }}
.answer {{ max-width:760px; margin:0 auto; display:flex; gap:12px; }}
.answer button {{ flex:1; min-height:64px; font-size:22px; }}
.answer button[data-v=YES] {{ color:var(--yes); }} .answer button[data-v=NO] {{ color:var(--no); }}
.answer button.on {{ background:var(--pick); border-color:currentColor; }}
#done {{ max-width:760px; margin:20px auto; font-family:system-ui, sans-serif; }}
footer {{ max-width:760px; margin:24px auto 0; font:13px/1.4 system-ui, sans-serif; color:var(--muted); }}
</style></head><body>
<header><div class="bar"><span id="progress"></span><button id="back">Back</button><button id="dl">Download answers</button></div></header>
<details open><summary>Instructions (tap to hide)</summary>{prompt_html}</details>
{cards}
<div class="answer" id="answer"><button data-v="YES">YES</button><button data-v="NO">NO</button></div>
<div id="done" hidden><p>All cards answered. Tap "Download answers" and send the file back. You can still use Back to change an answer.</p></div>
<footer>Judge each article on its own text. Your answers stay in this browser until you download them.</footer>
<script>
const KEY = "aurora-audit-{args.setname}";
let answers = {{}};
try {{ answers = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
const cards = [...document.querySelectorAll(".card")];
let cur = Math.max(0, cards.findIndex(c => !answers[c.dataset.id]));
if (cards.every(c => answers[c.dataset.id])) cur = cards.length;
function render() {{
  const n = cards.filter(c => answers[c.dataset.id]).length;
  cards.forEach((c, k) => c.hidden = k !== cur);
  const finished = cur >= cards.length;
  document.getElementById("answer").hidden = finished;
  document.getElementById("done").hidden = !finished;
  document.getElementById("progress").textContent = (finished ? cards.length : cur + 1) + " of " + cards.length + " (" + n + " answered)";
  if (!finished) {{
    const v = answers[cards[cur].dataset.id];
    for (const b of document.querySelectorAll("#answer button")) b.classList.toggle("on", b.dataset.v === v);
  }}
  window.scrollTo(0, 0);
}}
for (const b of document.querySelectorAll("#answer button")) b.addEventListener("click", () => {{
  answers[cards[cur].dataset.id] = b.dataset.v;
  try {{ localStorage.setItem(KEY, JSON.stringify(answers)); }} catch (e) {{}}
  cur++; render();
}});
document.getElementById("back").addEventListener("click", () => {{ if (cur > 0) {{ cur--; render(); }} }});
document.getElementById("dl").addEventListener("click", () => {{
  const rows = cards.filter(c => answers[c.dataset.id]).map(c => c.dataset.id + "\\t" + answers[c.dataset.id]);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([rows.join("\\n") + "\\n"], {{type:"text/tab-separated-values"}}));
  a.download = "audit_answers_{args.setname}.tsv"; document.body.appendChild(a); a.click(); a.remove();
}});
render();
</script></body></html>
"""
open(os.path.join(args.outdir, "audit.html"), "w").write(page)
print(f"{n} cards ({len(ids)} items + {args.repeats} repeats) -> {args.outdir}", file=sys.stderr)
