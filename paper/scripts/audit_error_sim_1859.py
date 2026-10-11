"""Simulated annotator error passed through the registered audit correction, on the 1859 data. Not pre-registered;
written before any human audit answer was received, to replace with a committed number the single unrecorded run in
which an AI review (Claude Opus) flipped 8% of answers and saw fine-tuned Laya's recall fall from 87.0% to 53.7%.

The answer key is taken as correct. A simulated annotator copies it, except that each card's answer is flipped with
probability r_yes on items the key calls YES and r_no on items it calls NO (one random draw per card, in page order,
random.Random(seed) for seeds 1-200, so every setting reuses the same draws). Each answers file is scored by the
unmodified bin/audit_1872.py in storm mode; only its point estimates, H1 verdict and test-retest count are read. The 1859 audit itself is balanced and
gets no corrected H1/H2, so a storm-style 1859 sample (250 items, seed 1872) and its page (10 hidden repeats, seed
1872) are drawn once for this simulation only, with the AI review's flags: fine-tuned Laya = out-of-fold score >= 0.80,
base Laya = score >= 0.5, keywords strict and fuzzy. The run with no flips must reproduce the LLM-key numbers.

Usage (from the repo root):
  python3 -I paper/scripts/audit_error_sim_1859.py WORKDIR > paper/scripts/audit_error_sim_1859.txt
WORKDIR must be missing or empty; it receives the sample, the page and every answers file.
"""
import glob
import hashlib
import os
import random
import re
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bin"))
import holdout_data as hd   # noqa: E402

ADJ = "results/1859-adjudication-opus.tsv"
SPECS = ["base_laya=scores:data/laya_scores.tsv:0.5", "strict=lines:data/rg_strict.lines",
         "fuzzy=lines:data/rg_fuzzy.lines", "ft_laya=scores3:results/finetune/oof.tsv:0.80"]
RATES = (0.01, 0.02, 0.04, 0.08)
DIRECTIONS = (("both ways", 1, 1), ("false YES only (on key-NO items)", 0, 1), ("false NO only (on key-YES items)", 1, 0))
SEEDS = range(1, 201)
PY = sys.executable

work = sys.argv[1]
os.makedirs(work, exist_ok=True)
if os.listdir(work):
    sys.exit(f"{work} is not empty")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"{' '.join(cmd)} failed:\n{p.stderr}")
    return p.stdout


ft, base = f"{work}/ft.lines", f"{work}/base.lines"
for path, spec in ((ft, SPECS[3]), (base, SPECS[0])):
    with open(path, "w") as out:
        out.writelines(f"{x}\n" for x in sorted(hd.load_system(spec.split("=", 1)[1])))
FLAGS = ["--ft", ft, "--keyword", "data/rg_strict.lines", "--keyword", "data/rg_fuzzy.lines", "--base", base]
SYS = ["--adjudication", ADJ, *(x for s in SPECS for x in ("--system", s)), "--h1", "ft_laya", "--strict", "strict",
       "--fuzzy", "fuzzy"]
run([PY, "-I", "bin/draw_audit.py", "storm", "data", f"{work}/items.jsonl", f"{work}/sample.tsv",
     "--size", "250", "--seed", "1872", *FLAGS])
strata = {s: (d, n) for _, s, n, d in (l.rstrip("\n").split("\t") for l in list(open(f"{work}/sample.tsv"))[1:])}
run([PY, "-I", "bin/make_audit_page.py", "freeze/labeler_prompt.md", f"{work}/items.jsonl", f"{work}/page",
     "--set", "sim1859", "--repeats", "10", "--seed", "1872"])

data = hd.load("data", ADJ, SPECS, [])
rows = data["rows"]
final = {r[0]: r[4] for r in rows}
cards = [l.rstrip("\n").split("\t") for l in list(open(f"{work}/page/audit_key.tsv"))[1:] if l.strip()]


def key_metrics():   # LLM-key precision and recall, computed here, independently of the scorer
    pos = sum(w for _, _, _, w, y, _ in rows if y)
    rec = lambda pred: sum(w for _, _, _, w, y, f in rows if y and pred(f)) / pos
    flagged = [(w, y) for _, _, _, w, y, f in rows if f["ft_laya"]]
    m = {"ft_p": sum(w for w, y in flagged if y) / sum(w for w, _ in flagged), "ft_r": rec(lambda f: f["ft_laya"]),
         "strict_r": rec(lambda f: f["strict"]), "h2": rec(lambda f: f["strict"] or f["ft_laya"]) - rec(lambda f: f["strict"])}
    missed = sum(1 for _, _, _, _, y, f in rows if y and f["ft_laya"] and not f["strict"])
    return m, m["ft_p"] >= 0.80 and m["ft_r"] >= 0.80 and missed >= 1


ROW = re.compile(r"^\| (\S+) \| ([\d.]+)% \(.*?\) \| ([\d.]+)% \(", re.M)


def score(r_yes, r_no, seed):
    tag = f"{r_yes}_{r_no}_{seed}"
    ans = f"{work}/answers_{tag}.tsv"
    rng = random.Random(seed)
    with open(ans, "w") as out:
        for card, src, _ in cards:
            y = final[src]
            if rng.random() <= (r_yes if y else r_no):
                y = not y
            out.write(f"{card}\t{'YES' if y else 'NO'}\n")
    rep = run([PY, "-I", "bin/audit_1872.py", "storm", "data", f"{work}/sample.tsv", f"{work}/page/audit_key.tsv", ans,
               f"{work}/report_{tag}.md", *SYS, *FLAGS, "--resamples", "20"])
    table = {m[1]: (float(m[2]) / 100, float(m[3]) / 100) for m in ROW.finditer(rep)}
    return {"ft_p": table["ft_laya"][0], "ft_r": table["ft_laya"][1], "strict_r": table["strict"][1],
            "h2": float(re.search(r"strict: ([+-][\d.]+)% \(95% audit", rep)[1]) / 100,
            "pass": re.search(r"-> (PASS|FAIL)", rep)[1] == "PASS",
            "retest": re.search(r"Test-retest on hidden repeats: (\d+) of (\d+) answered", rep).groups()}


jobs = [(0, 0, 0)] + [(r * ry, r * rn, s) for r in RATES for _, ry, rn in DIRECTIONS for s in SEEDS]
with ThreadPoolExecutor(os.cpu_count()) as pool:
    res = dict(zip(jobs, pool.map(lambda j: score(*j), jobs)))

key, key_pass = key_metrics()
control = res[(0, 0, 0)]
for k in key:   # with no flips p1 = 1 and p0 = 0 wherever estimable, so the scorer must print the LLM-key numbers
    if f"{control[k]:+.1%}" != f"{key[k]:+.1%}":
        sys.exit(f"no-flip control {k}: scorer {control[k]:+.1%}, LLM key {key[k]:+.1%}")
if control["pass"] != key_pass or control["retest"][0] != control["retest"][1]:
    sys.exit("no-flip control: H1 verdict or test-retest differs from the LLM key")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def cell(v, signed=False):
    f = "{:+.1%}" if signed else "{:.1%}"
    lo, hi = hd.ci(v)
    return f"{f.format(statistics.median(v))} ({f.format(lo)} to {f.format(hi)})"


print("# Simulated annotator error through the registered audit correction (1859, not pre-registered)\n")
print("Command: python3 -I paper/scripts/audit_error_sim_1859.py WORKDIR\n")
print("SHA-256 of the code and inputs:\n")
for p in ("paper/scripts/audit_error_sim_1859.py", "bin/audit_1872.py", "bin/draw_audit.py", "bin/make_audit_page.py",
          "bin/holdout_data.py", "bin/agent_outputs.py", "freeze/labeler_prompt.md", ADJ, "data/labelset/key.tsv",
          "data/labelset/items.jsonl", "data/labels/gemma.tsv", "data/adjudication/manifest.tsv", "data/laya_scores.tsv",
          "data/rg_strict.lines", "data/rg_fuzzy.lines", "results/finetune/oof.tsv"):
    print(f"- `{p}` {sha(p)}")
batches = sorted(glob.glob("data/labels/claude/b*.tsv"))
print(f"- `data/labels/claude/b*.tsv` ({len(batches)} files, concatenated in name order) "
      f"{hashlib.sha256(b''.join(open(p, 'rb').read() for p in batches)).hexdigest()}")
print("\nStorm-style sample, drawn / stratum size: " + ", ".join(f"{s} {d}/{n}" for s, (d, n) in strata.items()) + ".")
print(f"Cards on the page: {len(cards)} (10 hidden repeats). The scorer runs with --resamples 20; the point estimates "
      "read here do not depend on it.\n")
print(f"LLM key: ft_laya precision {key['ft_p']:.1%}, weighted recall {key['ft_r']:.1%}; strict recall "
      f"{key['strict_r']:.1%}; H2 gain {key['h2']:+.1%}. The no-flip run through bin/audit_1872.py printed the same "
      f"four numbers (checked to the printed digit), the same H1 verdict, and agreement on every repeat pair.\n")
ref = res[(0.08, 0.08, 7)]
print(f"The AI review's run (8% both ways, seed 7): ft_laya recall {ref['ft_r']:.1%} (it reported 53.7%), "
      f"precision {ref['ft_p']:.1%}, H2 gain {ref['h2']:+.1%}.\n")
print(f"Median and 2.5-97.5 percentile range over {len(SEEDS)} seeds of the audit-corrected point estimates:\n")
print("| Annotator error | Rate | ft_laya precision | ft_laya recall | strict recall | H2 gain | H1 passes | "
      "All repeat pairs agree |")
print("|---|---|---|---|---|---|---|---|")
for name, ry, rn in DIRECTIONS:
    for r in RATES:
        v = [res[(r * ry, r * rn, s)] for s in SEEDS]
        print(f"| {name} | {r:.0%} | {cell([x['ft_p'] for x in v])} | {cell([x['ft_r'] for x in v])} | "
              f"{cell([x['strict_r'] for x in v])} | {cell([x['h2'] for x in v], True)} | "
              f"{sum(x['pass'] for x in v)} of {len(v)} | {sum(x['retest'][0] == x['retest'][1] for x in v)} of {len(v)} |")
