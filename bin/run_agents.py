"""Run one isolated headless Claude Code agent per sandbox directory made by bin/render_agent_prompts.py.

Usage: python -I bin/run_agents.py SANDBOX MODEL BATCH_DIR --columns N [--parallel 6] [--attempts 3]
                                   [--stage-run 1 --max-stage-runs 3]
Each agent runs `claude -p` (bin/agent_outputs.agent_cmd: --restricted, only the Read and Write tools, the full MODEL ID,
no MCP servers, no session persistence) in its own directory with the trimmed environment of agent_outputs.agent_env.
An agent is done when every bNNN.tsv it owes passes the shared validator. Before every attempt its directory is moved to
SANDBOX/_attempts/NAME.runR.beforeK and rebuilt from canonical inputs only; logs go to SANDBOX/_logs/NAME.runR.attemptK.*;
a timeout or crash is a failed attempt. Only outputs from a run whose log shows exactly MODEL are kept; the first
complete answers stand. Accepted answers are attested with their SHA-256 in SANDBOX/_verified.tsv. A later run of the
same sandbox (a stage re-run) reloads attested answers after checking their hashes and asks only for what is missing.
Appends to SANDBOX/agents.tsv: run, agent, attempts, done, models, cost_usd, permission_denials.
Exit 1: a run used another model, or an attested answer changed. Exit 3: some agent is not done and this is not the
final stage run (--stage-run < --max-stage-runs): re-run the stage. On the final stage run, agents still not done go
to the frozen failure rules. Exit 0 otherwise.
"""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("sandbox")
ap.add_argument("model")
ap.add_argument("batch_dir")
ap.add_argument("--parallel", type=int, default=6)
ap.add_argument("--attempts", type=int, default=3)
ap.add_argument("--timeout", type=int, default=3600, help="seconds per attempt")
ap.add_argument("--columns", type=int, required=True, help="fields per answer line: 2 for labelers and checkers, 3 for adjudicators")
ap.add_argument("--stage-run", type=int, default=1, help="which run of the pipeline stage this is (from the stage log)")
ap.add_argument("--max-stage-runs", type=int, default=3, help="on this run, agents not done go to the failure rules")
a = ap.parse_args()

spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ao)

CMD = ao.agent_cmd(a.model)
ENV = ao.agent_env(os.environ)   # exits before any agent starts if a proxy or model override is set
owners = dict(l.rstrip("\n").split("\t") for l in open(f"{a.sandbox}/_owners.tsv") if l.strip())
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(f"{a.sandbox}/_logs", exist_ok=True)
os.makedirs(f"{a.sandbox}/_attempts", exist_ok=True)   # a run killed before its first log still used its number
RUN = 1 + max([int(m) for p in os.listdir(f"{a.sandbox}/_logs") + os.listdir(f"{a.sandbox}/_attempts") for m in re.findall(r"\.run(\d+)\.", p)], default=0)


def owed(d):
    """The batch names this agent must answer, from the ownership file written at render time."""
    return owners[os.path.basename(d)].split(",")


def valid(d, b):   # the shared validator (bin/agent_outputs.py), also used by bin/collect_agents.py
    return ao.valid(f"{d}/{b}.tsv", f"{a.batch_dir}/{b}.ids", a.columns)


# Answers attested by an earlier run of this sandbox: reloaded only if the file still has the attested hash.
attested = {}
if os.path.exists(f"{a.sandbox}/_verified.tsv"):
    for line in open(f"{a.sandbox}/_verified.tsv"):
        if line.strip():
            name, b, sha = line.rstrip("\n").split("\t")
            path = f"{a.sandbox}/{name}/{b}.tsv"
            # a killed run may have moved the attested file aside: any copy with the attested hash is the same answer
            copies = [p for p in [path] + sorted(glob.glob(f"{a.sandbox}/_attempts/{name}.run*.before*/{b}.tsv")) if os.path.isfile(p)]
            found = next((p for p in copies if hashlib.sha256(open(p, encoding="utf-8").read().encode("utf-8")).hexdigest() == sha), None)
            text = open(found, encoding="utf-8").read() if found else None
            if found and found != path:
                if os.path.isfile(path):   # the folder copy differs from the attested answer: keep it aside, never overwrite it
                    shutil.move(path, f"{path}.changed-run{RUN}")
                print(f"{name}/{b}: attested answer taken from {os.path.relpath(found, a.sandbox)}"
                      + (f"; the differing folder copy was kept as {b}.tsv.changed-run{RUN}" if os.path.isfile(f"{path}.changed-run{RUN}") else ""), file=sys.stderr)
            if name not in owners or b not in owed(f"{a.sandbox}/{name}") or text is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != sha:
                sys.exit(f"attested answer {name}/{b} is missing or changed since it was verified: stop and investigate")
            attested.setdefault(name, {})[b] = text


def fresh_dir(d, attempt):
    """Before every attempt, including the first, move the agent's directory aside whole (nothing is deleted) and
    rebuild it from canonical inputs only, so nothing written before this attempt can reach it."""
    name = os.path.basename(d)
    os.makedirs(f"{a.sandbox}/_attempts", exist_ok=True)
    if os.path.exists(d):
        dest = f"{a.sandbox}/_attempts/{name}.run{RUN}.before{attempt}"
        if os.path.exists(dest):
            sys.exit(f"{dest} exists: refusing to nest attempts")
        shutil.move(d, dest)
    os.makedirs(d)
    for b in owed(d):
        shutil.copy(f"{a.batch_dir}/{b}.txt", d)
        if name.startswith("agent"):   # checker agents also get their ids and the frozen labeler prompt
            shutil.copy(f"{a.batch_dir}/{b}.ids", d)
    if name.startswith("agent"):
        shutil.copy(f"{REPO}/freeze/labeler_prompt_1872.md", d)


def run(d):
    name = os.path.basename(d)
    models, cost, denials, attempt = set(), 0.0, 0, 0
    kept = dict(attested.get(name, {}))
    while attempt < a.attempts and not all(b in kept for b in owed(d)):
        attempt += 1
        fresh_dir(d, attempt)
        prompt = open(f"{a.sandbox}/_prompts/{name}.md").read()
        log = f"{a.sandbox}/_logs/{name}.run{RUN}.attempt{attempt}"
        try:
            res = subprocess.run(CMD, input=prompt, cwd=d, env=ENV, capture_output=True, text=True, timeout=a.timeout)
            stdout, stderr = res.stdout, res.stderr
        except Exception as exc:   # a timeout or launch failure is a failed attempt, never an abort
            stdout, stderr = "", f"attempt failed: {exc!r}"
        finally:
            open(f"{log}.json", "w").write(stdout)
            open(f"{log}.err", "w").write(stderr)
        try:
            out = json.loads(stdout)
            used = set((out.get("modelUsage") or {}).keys())
            models |= used
            cost += out.get("total_cost_usd") or 0.0
            denials += len(out.get("permission_denials") or [])
        except json.JSONDecodeError:
            used = set()   # unverifiable run: a failed attempt, and its outputs are not kept
        if used == {a.model}:
            kept.update({b: open(f"{d}/{b}.tsv", encoding="utf-8").read() for b in owed(d) if b not in kept and valid(d, b)})   # first complete answers stand
    for b in owed(d):   # the final directory holds only model-verified answers: anything else is renamed out of reach
        if b in kept:
            open(f"{d}/{b}.tsv", "w", encoding="utf-8").write(kept[b])
        elif os.path.exists(f"{d}/{b}.tsv"):
            shutil.move(f"{d}/{b}.tsv", f"{d}/{b}.unverified.tsv")
    done = all(b in kept for b in owed(d))
    hashes = {b: hashlib.sha256(text.encode("utf-8")).hexdigest() for b, text in kept.items()}   # attest only what was accepted
    return name, attempt, done, sorted(models), round(cost, 4), denials, hashes


dirs = [f"{a.sandbox}/{name}" for name in sorted(owners)]
with ThreadPoolExecutor(max_workers=a.parallel) as pool:
    results = list(pool.map(run, dirs))   # run() never raises on an agent failure
with open(f"{a.sandbox}/_verified.tsv.new", "w") as out:   # earlier attested answers are carried in `kept`, so this merges
    for name, *_, hashes in results:
        for b, h in sorted(hashes.items()):
            out.write(f"{name}\t{b}\t{h}\n")
os.replace(f"{a.sandbox}/_verified.tsv.new", f"{a.sandbox}/_verified.tsv")
with open(f"{a.sandbox}/agents.tsv", "a") as out:
    for name, att, done, models, cost, den, _ in results:
        out.write(f"{RUN}\t{name}\t{att}\t{done}\t{','.join(models)}\t{cost}\t{den}\n")
wrong = [r for r in results if set(r[3]) - {a.model}]   # a run that used any other model aborts the stage
undone = [r[0] for r in results if not r[2]]
final = a.stage_run >= a.max_stage_runs
print(f"run {RUN} (stage run {a.stage_run} of at most {a.max_stage_runs}): {len(results) - len(undone)}/{len(results)} agents done; "
      f"cost ${sum(r[4] for r in results):.2f}; permission denials {sum(r[5] for r in results)}; model mismatches {len(wrong)}", file=sys.stderr)
if undone and not wrong:
    print(f"not done: {', '.join(undone)} -> " + ("final stage run: these go to the frozen failure rules" if final else
          "re-run the stage (ATTEMPT=n REASON=...); only these are asked again"), file=sys.stderr)
sys.exit(1 if wrong else 3 if undone and not final else 0)
