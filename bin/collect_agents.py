"""Copy agent answers into the data tree, accepting only files bin/run_agents.py verified (same validator, same bytes).

Usage: python -I bin/collect_agents.py ROLE SANDBOX BATCH_DIR DEST COLUMNS FAILED_IDS
A batch's answer is taken only from its owning agent's folder (SANDBOX/_owners.tsv), and only if SANDBOX/_verified.tsv
lists that batch with the file's SHA-256 and the shared validator passes. Otherwise the batch has failed every attempt:
its ids go to FAILED_IDS, and for the labeler role a MISSING label file is written (frozen failure rule: MISSING
labels go to adjudication); checker and adjudicator batches are left out (missing verdicts are kept; unanswered
adjudications keep the Sonnet label).
"""
import glob
import importlib.util
import os
import shutil
import sys

spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ao)

role, sandbox, batch_dir, dest, columns, failed_path = sys.argv[1:7]
columns = int(columns)
owner = {}
for line in open(f"{sandbox}/_owners.tsv"):
    if line.strip():
        name, batches = line.rstrip("\n").split("\t")
        for b in batches.split(","):
            owner[b] = name
verified = {}
for line in open(f"{sandbox}/_verified.tsv"):
    if line.strip():
        name, b, sha = line.rstrip("\n").split("\t")
        verified[b] = (name, sha)
if os.path.exists(dest):   # never mix with an earlier collection: move it aside (nothing is deleted)
    n = 1
    while os.path.exists(f"{dest}.earlier{n}"):
        n += 1
    shutil.move(dest, f"{dest}.earlier{n}")
os.makedirs(dest)
failed = []
for ids in sorted(glob.glob(f"{batch_dir}/b*.ids")):
    b = os.path.basename(ids)[:-4]
    out = f"{sandbox}/{owner.get(b, '-')}/{b}.tsv"
    ok = (b in owner and verified.get(b, (None, None))[0] == owner[b] and os.path.isfile(out)
          and ao.sha256(out) == verified[b][1] and ao.valid(out, ids, columns))
    if ok:
        shutil.copy(out, dest)
    else:
        failed += [l.strip() for l in open(ids) if l.strip()]
        if role == "labeler":
            open(f"{dest}/{b}.tsv", "w").write("".join(f"{i}\tMISSING\n" for i in open(ids).read().split()))
open(failed_path, "w").write("".join(f"{i}\n" for i in failed))
print(f"{role}: {len(glob.glob(f'{batch_dir}/b*.ids'))} batches, failed ids {len(failed)}", file=sys.stderr)
