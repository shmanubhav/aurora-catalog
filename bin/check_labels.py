"""Check that each labeler has exactly one valid YES/NO for every item in the label set, and nothing else.

Usage: python -I bin/check_labels.py data/labelset data/labels
Claude: every bNNN.tsv must list its batch's ids in order; MISSING (a batch that failed every attempt, frozen
failure rule) counts as labeled and goes to adjudication. Gemma: UNPARSED (a reasoning loop) counts as labeled and goes
to adjudication. Any other value is a problem. Files are read by the strict reader in bin/agent_outputs.py.
Prints the gaps per labeler and exits 1 if any labeler is incomplete.
"""
import glob
import importlib.util
import os
import sys

_spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ao)

labelset, labels = sys.argv[1:3]
ids = [line.split("\t")[0] for line in open(f"{labelset}/key.tsv")][1:]
want = set(ids)
ok = True


def report(name, got, problems):
    global ok
    missing = sorted(want - set(got))
    extra = sorted(set(got) - want)
    complete = not missing and not extra and not problems and len(got) == len(want)
    ok &= complete
    print(f"{name}: {len(got)}/{len(want)} labeled, {len(missing)} missing, {len(extra)} extra, "
          f"{len(problems)} problems{'' if complete else '  <-- INCOMPLETE'}")
    for p in problems[:20]:
        print(f"  {p}")


claude, problems = {}, []
for batch in sorted(glob.glob(f"{labelset}/claude_batches/b*.ids")):
    name = os.path.basename(batch)[:-4]
    expected = open(batch).read().split()
    out = f"{labels}/claude/{name}.tsv"
    if not os.path.exists(out):
        problems.append(f"{name}: no output")
        continue
    try:
        got = ao.read_labels(out, ("YES", "NO", "MISSING"), 2)
    except ValueError as exc:
        problems.append(str(exc))
        continue
    if list(got) != expected:
        problems.append(f"{name}: ids differ from the batch")
    for item_id, label in got.items():
        if item_id in claude:
            problems.append(f"{name}: duplicate {item_id}")
        else:
            claude[item_id] = label
report("claude", claude, problems)
print(f"claude MISSING (Sonnet batch failed every attempt, to adjudication): {sum(v == 'MISSING' for v in claude.values())}")

gemma, problems = {}, []
path = f"{labels}/gemma.tsv"
try:
    gemma = ao.read_labels(path, ("YES", "NO", "UNPARSED")) if os.path.exists(path) else {}
except ValueError as exc:
    problems.append(str(exc))
report("gemma", gemma, problems)
print(f"gemma UNPARSED (to adjudication): {sum(v == 'UNPARSED' for v in gemma.values())}")
sys.exit(0 if ok else 1)
