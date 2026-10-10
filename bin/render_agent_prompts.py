"""Fill a frozen agent prompt and give each agent its own sandbox directory holding only its own files.

Usage: python -I bin/render_agent_prompts.py ROLE BATCH_DIR SANDBOX [--agents 4]
ROLE labeler | adjudicator: one agent per batch, SANDBOX/bNNN/ with bNNN.txt; prompt filled from
  freeze/labeler_agent_prompt.md / freeze/adjudicator_prompt.md; the agent writes SANDBOX/bNNN/bNNN.tsv.
ROLE checker: batches split into --agents contiguous groups (sizes differ by at most one, larger groups first),
  SANDBOX/agentK/ with the group's bNNN.txt and bNNN.ids and freeze/labeler_prompt_1872.md; prompt filled from
  freeze/checker_agent_prompt.md; the agent writes SANDBOX/agentK/bNNN.tsv.
Prompts go to SANDBOX/_prompts/NAME.md and ownership to SANDBOX/_owners.tsv (agent, batches), outside every
agent's directory, so no agent can edit its own prompt or claim another agent's batch.
SANDBOX must be outside the repository and must not exist yet. bin/run_agents.py runs the agents.
"""
import argparse
import glob
import os
import shutil
import sys

ap = argparse.ArgumentParser()
ap.add_argument("role", choices=["labeler", "adjudicator", "checker"])
ap.add_argument("batch_dir")
ap.add_argument("sandbox")
ap.add_argument("--agents", type=int, default=4)
a = ap.parse_args()

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sandbox = os.path.abspath(os.path.expanduser(a.sandbox))
if sandbox == repo or sandbox.startswith(repo + os.sep):
    sys.exit("the sandbox must be outside the repository")
if os.path.exists(sandbox):
    sys.exit(f"{sandbox} already exists: use a fresh directory")

batches = sorted(os.path.basename(p)[:-4] for p in glob.glob(f"{a.batch_dir}/b*.txt"))
os.makedirs(f"{sandbox}/_prompts")
owners = open(f"{sandbox}/_owners.tsv", "w")


def template(name):
    lines = open(f"{repo}/freeze/{name}").read().splitlines(keepends=True)
    return "".join(lines[1:]) if lines and lines[0].startswith("<!--") else "".join(lines)


if a.role in ("labeler", "adjudicator"):
    t = template("labeler_agent_prompt.md" if a.role == "labeler" else "adjudicator_prompt.md")
    for b in batches:
        d = f"{sandbox}/{b}"
        os.makedirs(d)
        shutil.copy(f"{a.batch_dir}/{b}.txt", d)
        n = sum(1 for _ in open(f"{a.batch_dir}/{b}.ids"))
        p = t.replace("{BATCH_FILE}", f"{d}/{b}.txt").replace("{N}", str(n)).replace("{OUT_FILE}", f"{d}/{b}.tsv")
        open(f"{sandbox}/_prompts/{b}.md", "w").write(p)
        owners.write(f"{b}\t{b}\n")
else:
    t = template("checker_agent_prompt.md")
    k, extra = divmod(len(batches), a.agents)
    start = 0
    for g in range(a.agents):
        group = batches[start:start + k + (1 if g < extra else 0)]
        start += len(group)
        if not group:
            continue
        d = f"{sandbox}/agent{g + 1}"
        os.makedirs(d)
        shutil.copy(f"{repo}/freeze/labeler_prompt_1872.md", d)
        for b in group:
            shutil.copy(f"{a.batch_dir}/{b}.txt", d)
            shutil.copy(f"{a.batch_dir}/{b}.ids", d)
        p = (t.replace("{YEAR}", "1872").replace("{PROMPT_FILE}", f"{d}/labeler_prompt_1872.md")
              .replace("{BATCH_DIR}", d).replace("{BATCHES}", ", ".join(f"{b}.txt" for b in group)))
        open(f"{sandbox}/_prompts/agent{g + 1}.md", "w").write(p)
        owners.write(f"agent{g + 1}\t{','.join(group)}\n")
owners.close()
print(f"{a.role}: {len(batches)} batches -> {sandbox}", file=sys.stderr)
