"""Shared loader for the post-download analyses (prereg section 7): the final labels, systems and rows exactly as
bin/score_1872.py builds them. score_1872.py is frozen and runs on import, so its logic is copied here, not imported;
bin/test_analyses_1872.sh checks this copy reproduces that scorer's printed output.

rows: (id, line, stratum, weight, final_yes, {system: flagged}) in key.tsv order.
"""
import glob
import importlib.util
import math
import os
import sys

_spec = importlib.util.spec_from_file_location("agent_outputs", os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_outputs.py"))
ao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ao)


def add_args(ap):
    """The scorer's data arguments, same syntax as bin/score_1872.py."""
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--system", action="append", default=[])
    ap.add_argument("--checker", action="append", default=[])
    ap.add_argument("--h1")
    ap.add_argument("--strict")
    ap.add_argument("--fuzzy")


def load(d, adjudication, system_specs, checker_specs):
    key = {}
    for row in list(open(f"{d}/labelset/key.tsv"))[1:]:
        item_id, line, stratum, weight = row.split()
        key[item_id] = (int(line), stratum, float(weight))
    claude = {k: v for p in sorted(glob.glob(f"{d}/labels/claude/b*.tsv")) for k, v in ao.read_labels(p, ("YES", "NO", "MISSING"), 2).items()}
    gemma = ao.read_labels(f"{d}/labels/gemma.tsv", ("YES", "NO", "UNPARSED"))
    adj = ao.read_labels(adjudication, ("YES", "NO"), 3)
    kinds = dict(l.split() for l in list(open(f"{d}/adjudication/manifest.tsv"))[1:])
    if any(claude[i] != gemma[i] and i not in adj and i not in kinds for i in key):
        sys.exit("a Claude/Gemma disagreement that is not in the adjudication manifest")
    for i in [i for i in key if claude[i] == "MISSING" and i not in adj]:   # no label: excluded, as the scorer does
        del key[i]
    by_line = {line: i for i, (line, _, _) in key.items()}
    final = {i: adj.get(i, claude[i]) == "YES" for i in key}

    systems = {}
    for s in system_specs:
        name, spec = s.split("=", 1)
        systems[name] = load_system(spec)
    for c in checker_specs:
        name, rest = c.split("=", 1)
        base, path = rest.split(":", 1)
        verdict = {}
        for i, v in ao.read_labels(path, ("YES", "NO", "UNPARSED")).items():
            if i.startswith("L") and i[1:].isdigit():
                verdict[int(i[1:])] = v
            elif i in key:
                verdict[key[i][0]] = v
        systems[name] = {line for line in systems[base] if verdict.get(line) != "NO"}   # missing/UNPARSED: kept
    rows = [(i, line, st, w, final[i], {n: (line in f) for n, f in systems.items()})
            for i, (line, st, w) in key.items()]
    return {"rows": rows, "names": list(systems), "kinds": kinds, "by_line": by_line, "key": key}


def load_system(spec):
    kind, *rest = spec.split(":")
    if kind == "lines":
        return {int(x) for x in open(rest[0]) if x.strip()}
    cut = float(rest[1])
    if kind == "scores":
        return {int(l.split("\t")[0]) for l in open(rest[0]) if float(l.split("\t")[1]) >= cut}
    if kind == "scores3":
        return {int(l.split("\t")[1]) for l in open(rest[0]) if float(l.split("\t")[2]) >= cut}
    sys.exit(f"unknown system kind {kind}")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (m - c, m + c)


def ci(v):
    """Percentile interval, the scorer's rule."""
    v = sorted(v)
    return (v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1])


def union(*ns):
    return lambda f: any(f[n] for n in ns)
