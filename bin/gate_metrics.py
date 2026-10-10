"""Spike 2 gate: out-of-fold precision and weighted recall per cutoff, with extrapolated false alarms.

Usage: python -I bin/gate_metrics.py freeze/finetune.json data OOF.tsv GATE.tsv OUT.json
OOF.tsv: id<TAB>line<TAB>p for every training row, each scored by the fold model that did not train on it.
GATE.tsv: id<TAB>line<TAB>p for the gate sample, scored by the all-data model.
precision(t) = TP_w(t) / (flags_w(t) + r(t) * U), recall(t) = TP_w(t) / P_w, where labeled pool rows weigh 1,
net-sample rows weigh N, presumed-NO rows are left out (their stratum is covered by r), r(t) = gate flags / gate
size and U = the unlabeled stratum size. Cutoff = argmax F1 on the frozen grid (ties go to the higher cutoff).
"""
import json
import sys

ft_path, d, oof_path, gate_path, out_path = sys.argv[1:6]
ft = json.load(open(ft_path))
g = ft["gate"]
weight = {row.split()[0]: float(row.split()[3]) for row in list(open(f"{d}/labelset/key.tsv"))[1:]}
rows = {json.loads(l)["id"]: json.loads(l) for l in open(f"{d}/finetune/rows.jsonl")}
oof = {l.split("\t")[0]: float(l.split("\t")[2]) for l in open(oof_path)}
gate = [float(l.split("\t")[2]) for l in open(gate_path)]
labeled = [(weight[i], rows[i]["expected"]["aurora"], oof[i]) for i in weight]
neg_oof = [oof[i] for i, r in rows.items() if r["kind"] == "presumed_no"]
assert len(oof) == len(rows), f"OOF covers {len(oof)} of {len(rows)} rows"
assert len(gate) == g["gate_size"], f"gate has {len(gate)} rows, expected {g['gate_size']}"

pos_w = sum(w for w, y, _ in labeled if y)
table = []
for t in g["cutoff_grid"]:
    tp = sum(w for w, y, p in labeled if y and p >= t)
    flags = sum(w for w, _, p in labeled if p >= t)
    r = sum(p >= t for p in gate) / len(gate)
    fa = r * g["unlabeled_stratum"]
    prec = tp / (flags + fa) if flags + fa else 0.0
    rec = tp / pos_w
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    table.append({"cutoff": t, "tp_w": tp, "flags_w": flags, "gate_flags": round(r * len(gate)),
                  "extrapolated_false_alarms": round(fa), "precision": prec, "recall": rec, "f1": f1,
                  "presumed_no_oof_flag_rate": sum(p >= t for p in neg_oof) / len(neg_oof)})
best = max(table, key=lambda x: (x["f1"], x["cutoff"]))
result = {"positives_w": pos_w, "chosen": best,
          "gate_pass": best["precision"] >= g["min_precision"] and best["recall"] >= g["min_recall"],
          "table": table}
json.dump(result, open(out_path, "w"), indent=1)
print(f"cutoff {best['cutoff']}: precision {best['precision']:.1%}, recall {best['recall']:.1%}, F1 {best['f1']:.3f}, "
      f"extrapolated false alarms {best['extrapolated_false_alarms']} -> gate {'PASS' if result['gate_pass'] else 'FAIL'}")
