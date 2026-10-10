"""Build the blind adjudication page: every Claude/Gemma disagreement (Gemma UNPARSED counts as one) plus a
seeded sample of agreed items.

Usage: python -I bin/make_adjudication.py freeze/config.json freeze/labeler_prompt.md data/labelset data/labels OUTDIR
Writes OUTDIR/page.html (article text and YES/NO only, no labels or sources) and OUTDIR/manifest.tsv
(id, kind) kept off the page. Answers save in the browser and download as adjudication.tsv.
"""
import glob
import html
import json
import importlib.util
import os
import random
import sys

_spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ao)

cfg_path, prompt_path, labelset, labels, outdir = sys.argv[1:6]
cfg = json.load(open(cfg_path))
rng = random.Random(cfg["seed"])

# Label files go through the one strict reader (bin/agent_outputs.py) the validator and scorer use.
claude = {k: v for path in sorted(glob.glob(f"{labels}/claude/b*.tsv")) for k, v in ao.read_labels(path, ("YES", "NO", "MISSING"), 2).items()}
gemma = ao.read_labels(f"{labels}/gemma.tsv", ("YES", "NO", "UNPARSED"))
texts = {json.loads(line)["id"]: json.loads(line)["text"] for line in open(f"{labelset}/items.jsonl")}
if set(claude) != set(texts) or set(gemma) != set(texts):
    sys.exit("labels incomplete: run bin/check_labels.py first")

# A Sonnet batch that failed every attempt is MISSING (frozen failure rule) and is adjudicated like a disagreement.
disagree = sorted(i for i in texts if claude[i] != gemma[i])
agreed = sorted(i for i in texts if claude[i] == gemma[i])
spot = rng.sample(agreed, cfg["agreed_spotcheck"])
chosen = [(i, "sonnet-missing" if claude[i] == "MISSING" else "gemma-unparsed" if gemma[i] == "UNPARSED" else "disagree") for i in disagree] + [(i, "agreed-check") for i in spot]
rng.shuffle(chosen)

os.makedirs(outdir, exist_ok=True)
with open(f"{outdir}/manifest.tsv", "w") as out:
    out.write("id\tkind\n" + "".join(f"{i}\t{kind}\n" for i, kind in chosen))

question = html.escape(open(prompt_path).read().split("Reply with exactly")[0].strip())
cards = "\n".join(
    f'<section class="card" data-id="{i}"><h2>{n} of {len(chosen)} <span class="id">{i}</span></h2>'
    f'<p class="text">{html.escape(texts[i])}</p>'
    f'<div class="buttons"><button data-v="YES">YES, a sighting</button><button data-v="NO">NO</button></div></section>'
    for n, (i, _kind) in enumerate(chosen, 1))

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aurora Tie-Breaks</title>
<style>
:root {{ --bg:#f7f5f0; --fg:#1d1d1f; --muted:#6b6b70; --card:#ffffff; --line:#e3e0d8; --yes:#1f7a4d; --no:#a33a2b; --pick:#fff3c4; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141416; --fg:#ececef; --muted:#9a9aa2; --card:#1e1e22; --line:#2e2e34; --yes:#4cc38a; --no:#f07a68; --pick:#3a3320; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.55 Georgia, serif; margin:0; padding:0 16px 80px; }}
header {{ position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line); padding:12px 0; z-index:1; }}
header .bar {{ max-width:760px; margin:0 auto; display:flex; gap:12px; align-items:center; flex-wrap:wrap; font-family:system-ui, sans-serif; }}
#progress {{ flex:1; color:var(--muted); }}
details {{ max-width:760px; margin:16px auto; font-family:system-ui, sans-serif; color:var(--muted); white-space:pre-wrap; }}
.card {{ max-width:760px; margin:20px auto; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 20px; }}
.card.done {{ opacity:.55; }}
h2 {{ font:600 14px system-ui, sans-serif; color:var(--muted); margin:0 0 8px; }}
.id {{ font-weight:400; margin-left:6px; }}
.text {{ margin:0 0 14px; overflow-wrap:anywhere; }}
button {{ font:600 15px system-ui, sans-serif; padding:10px 16px; border-radius:8px; border:1px solid var(--line); background:var(--bg); color:var(--fg); cursor:pointer; }}
.buttons button[data-v=YES] {{ color:var(--yes); }} .buttons button[data-v=NO] {{ color:var(--no); }}
.buttons button.on {{ background:var(--pick); border-color:currentColor; }}
.buttons {{ display:flex; gap:10px; }}
</style></head><body>
<header><div class="bar"><span id="progress"></span><button id="next">Next unanswered</button><button id="dl">Download answers</button></div></header>
<details><summary>The question (same rules the graders used)</summary>{question}</details>
{cards}
<script>
const KEY = "aurora-adjudication-{cfg['seed']}";
let answers = {{}};
try {{ answers = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
const cards = [...document.querySelectorAll(".card")];
function render() {{
  let n = 0;
  for (const c of cards) {{
    const v = answers[c.dataset.id];
    c.classList.toggle("done", !!v); if (v) n++;
    for (const b of c.querySelectorAll("button")) b.classList.toggle("on", b.dataset.v === v);
  }}
  document.getElementById("progress").textContent = n + " of " + cards.length + " answered";
}}
for (const c of cards) for (const b of c.querySelectorAll("button")) b.addEventListener("click", () => {{
  answers[c.dataset.id] = b.dataset.v;
  try {{ localStorage.setItem(KEY, JSON.stringify(answers)); }} catch (e) {{}}
  render();
  const next = cards.find(x => !answers[x.dataset.id]); if (next) next.scrollIntoView({{behavior:"smooth", block:"start"}});
}});
document.getElementById("next").addEventListener("click", () => {{
  const next = cards.find(x => !answers[x.dataset.id]); if (next) next.scrollIntoView({{behavior:"smooth", block:"start"}});
}});
document.getElementById("dl").addEventListener("click", () => {{
  const rows = cards.filter(c => answers[c.dataset.id]).map(c => c.dataset.id + "\\t" + answers[c.dataset.id]);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([rows.join("\\n") + "\\n"], {{type:"text/tab-separated-values"}}));
  a.download = "adjudication.tsv"; a.click();
}});
render();
</script></body></html>
"""
open(f"{outdir}/page.html", "w").write(page)
print(f"{len(disagree)} disagreements + {len(spot)} agreed checks = {len(chosen)} items", file=sys.stderr)
