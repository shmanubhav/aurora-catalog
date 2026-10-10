#!/usr/bin/env bash
# Offline checks for the post-download analyses, on 1859 development data and toy cases only (never 1872 outputs).
# Exits non-zero on any mismatch.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"
t=$(mktemp -d)
SYS=(--adjudication results/1859-adjudication-opus.tsv --system base_laya=scores:data/laya_scores.tsv:0.5
     --system strict=lines:data/rg_strict.lines --system fuzzy=lines:data/rg_fuzzy.lines
     --system ft_laya=scores3:results/finetune/oof.tsv:0.80
     --checker ft+qwen=ft_laya:results/finetune/checkers/1859_qwen_think.tsv
     --checker ft+opus=ft_laya:results/finetune/checkers/1859_opus.tsv --h1 ft_laya --strict strict --fuzzy fuzzy)
ref=results/score_1872_repro_1859.md
fail() { echo "MISMATCH: $1"; exit 1; }

# Each system's weighted precision and recall in an output table must equal the frozen scorer's 1859 table.
same_table() {   # same_table OUT PRECISION_COLUMN RECALL_COLUMN
  python3 -I - "$ref" "$1" "$2" "$3" <<'EOF'
import sys
ref, out, pc, rc = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
def table(path, p, r):
    rows = [l.split("|") for l in open(path) if l.startswith("| ") and "%" in l and not l.startswith("| System")]
    return {c[1].strip(): (c[p].strip().split()[0], c[r].strip().split()[0]) for c in rows}
want, got = table(ref, 4, 6), table(out, pc, rc)
bad = [n for n in want if want[n] != got.get(n)]
sys.exit(f"{bad}: want {[want[n] for n in bad]} got {[got.get(n) for n in bad]}" if bad else 0)
EOF
}

# 1. Reprints with every article its own group reproduce the scorer's 1859 output to the printed digit.
python3 -I bin/reprints_1872.py data data/window.txt "$t/rep.md" --seed 1859 --drop-zero-positive --containment 1.01 "${SYS[@]}" > /dev/null
for c in "H2 gain" "H2' gain"; do
  grep -qxF -- "$(grep -F -- "- $c" "$ref")" "$t/rep.md" || fail "reprints $c"
done
grep -qF "precision 91.9%, weighted recall 87.0% (bar: both >= 80%); the 15 final-YES articles it flags that strict missed fall in 15 distinct reprint groups; final-YES groups it flags with no strict-matched member: 15" "$t/rep.md" || fail "reprints H1"
same_table "$t/rep.md" 4 5 || fail "reprints system rows"
echo "reprints, singleton groups: 1859 scorer output reproduced"

# 2. Audit, storm mode, on a 1859 storm-style sample with the human agreeing everywhere: the corrected numbers are
#    the LLM-key numbers.
awk -F'\t' '$3 >= 0.80 {print $2}' results/finetune/oof.tsv > "$t/ft.lines"
awk -F'\t' '$2 >= 0.5 {print $1}' data/laya_scores.tsv > "$t/base.lines"
python3 -I bin/draw_audit.py storm data "$t/items.jsonl" "$t/sample.tsv" --size 250 --seed 1872 --ft "$t/ft.lines" \
  --keyword data/rg_strict.lines --keyword data/rg_fuzzy.lines --base "$t/base.lines" 2> /dev/null
python3 -I bin/make_audit_page.py freeze/labeler_prompt.md "$t/items.jsonl" "$t/page" --set test --repeats 10 --seed 1872 2> /dev/null
python3 -I - "$t/page/audit_key.tsv" "$t/answers.tsv" "${SYS[@]:0:2}" <<'EOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("hd", "bin/holdout_data.py"); hd = importlib.util.module_from_spec(spec); spec.loader.exec_module(hd)
final = {r[0]: r[4] for r in hd.load("data", sys.argv[4], [], [])["rows"]}
with open(sys.argv[2], "w") as out:
    for l in list(open(sys.argv[1]))[1:]:
        c, src, _ = l.split("\t")
        out.write(f"{c}\t{'YES' if final[src] else 'NO'}\n")
EOF
python3 -I bin/audit_1872.py storm data "$t/sample.tsv" "$t/page/audit_key.tsv" "$t/answers.tsv" "$t/aud.md" "${SYS[@]}" \
  --ft "$t/ft.lines" --keyword data/rg_strict.lines --keyword data/rg_fuzzy.lines --base "$t/base.lines" --resamples 200 > /dev/null
same_table "$t/aud.md" 2 3 || fail "audit-corrected system rows"
grep -qF "(strict OR h1) - strict: +5.4% (95% audit-sampling interval +5.4% to +5.4%;" "$t/aud.md" || fail "audit-corrected H2"
grep -qF "Test-retest on hidden repeats: 10 of 10" "$t/aud.md" || fail "test-retest"
echo "audit, storm mode, perfect agreement: LLM-key numbers reproduced"

# 3. Audit, storm mode, hand-computed toy. LLM: a1 YES a2 YES a3 NO a4 NO (pool, weight 1), a5 YES a6 NO (net, weight 5).
#    Human: a1 YES a2 YES a3 YES a4 NO a5 YES a6 YES; the repeat of a5 says NO. Strata S1..S4 = a1..a4, S5 = a5 a6.
#    y = 1 1 1 0 1 1; sum w*y = 13. ft {a1,a2}: precision 2/2, recall 2/13 = 15.4%; strict {a1,a3}: recall 2/13;
#    strict OR ft: 3/13; H2 = +7.7%. S5: agreement 1/2, kappa not estimable (the human said YES twice), positive 2/3,
#    negative 0/1, p1 1/1, p0 1/1.
d="$t/toy"; mkdir -p "$d/labelset" "$d/labels/claude" "$d/adjudication"
printf 'id\tline\tstratum\tweight\na1\t10\tpool\t1\na2\t20\tpool\t1\na3\t30\tpool\t1\na4\t40\tpool\t1\na5\t50\tnet\t5\na6\t60\tnet\t5\n' > "$d/labelset/key.tsv"
printf 'a1\tYES\na2\tYES\na3\tNO\na4\tNO\na5\tYES\na6\tNO\n' | tee "$d/labels/claude/b001.tsv" > "$d/labels/gemma.tsv"
printf 'id\tkind\n' > "$d/adjudication/manifest.tsv"; : > "$d/adj.tsv"
printf '10\n20\n' > "$d/ft.lines"; printf '10\n30\n' > "$d/strict.lines"; printf '40\n' > "$d/base.lines"
printf 'id\tstratum\tstratum_size\tdrawn\na1\tS1\t1\t1\na2\tS2\t1\t1\na3\tS3\t1\t1\na4\tS4\t1\t1\na5\tS5\t2\t2\na6\tS5\t2\t2\n' > "$d/sample.tsv"
printf 'card_id\tsource_id\tis_repeat\nc1\ta1\t0\nc2\ta2\t0\nc3\ta3\t0\nc4\ta4\t0\nc5\ta5\t0\nc6\ta6\t0\nc7\ta5\t1\n' > "$d/key.tsv"
printf 'c1\tYES\nc2\tYES\nc3\tYES\nc4\tNO\nc5\tYES\nc6\tYES\nc7\tNO\n' > "$d/answers.tsv"
python3 -I bin/audit_1872.py storm "$d" "$d/sample.tsv" "$d/key.tsv" "$d/answers.tsv" "$d/out.md" --adjudication "$d/adj.tsv" \
  --system ft=lines:"$d/ft.lines" --system strict=lines:"$d/strict.lines" --h1 ft --strict strict \
  --ft "$d/ft.lines" --keyword "$d/strict.lines" --base "$d/base.lines" --resamples 200 > /dev/null
for want in '| ft | 100.0% (' '| 15.4% (' '| strict | 100.0% (' '(strict OR h1) - strict: +7.7%' \
            '| S5 | 2 / 2 | 50.0% (' '| not estimable (a rater gave one label) | 66.7% (2/3) | 0.0% (0/1) | 100.0% (1/1) | 100.0% (1/1) |' \
            '| S3 | 1 / 1 | 0.0% (' 'Test-retest on hidden repeats: 0 of 1' \
            'precision 100.0%, weighted recall 15.4%, final-YES flags strict missed (LLM key) 1 -> FAIL'; do
  grep -qF -- "$want" "$d/out.md" || { cat "$d/out.md"; fail "toy: $want"; }
done
head -n 6 "$d/answers.tsv" > "$d/partial.tsv"   # a5's repeat card c7 unanswered: still complete
sed '$d' "$d/partial.tsv" > "$d/partial2.tsv"    # a6 unanswered: S5 1 of 2 is under 80%
python3 -I bin/audit_1872.py storm "$d" "$d/sample.tsv" "$d/key.tsv" "$d/partial2.tsv" "$d/out2.md" --adjudication "$d/adj.tsv" \
  --system ft=lines:"$d/ft.lines" --system strict=lines:"$d/strict.lines" --h1 ft --strict strict \
  --ft "$d/ft.lines" --keyword "$d/strict.lines" --base "$d/base.lines" --resamples 50 > /dev/null
grep -qF '| S5 | 1 / 2 (incomplete) |' "$d/out2.md" || fail "toy: incomplete stratum"
printf 'c1\tYES\nc2\tYES\nc3\tYES\nc4\tNO\nc6\tYES\nc7\tNO\n' > "$d/reponly.tsv"   # a5 answered only on its repeat card
python3 -I bin/audit_1872.py storm "$d" "$d/sample.tsv" "$d/key.tsv" "$d/reponly.tsv" "$d/out3.md" --adjudication "$d/adj.tsv" \
  --system ft=lines:"$d/ft.lines" --system strict=lines:"$d/strict.lines" --h1 ft --strict strict \
  --ft "$d/ft.lines" --keyword "$d/strict.lines" --base "$d/base.lines" --resamples 50 > /dev/null
for want in 'items with a human label: 6 of 6' 'Test-retest on hidden repeats: 0 of 0' '| S5 | 2 / 2 | 0.0% ('; do
  grep -qF -- "$want" "$d/out3.md" || { cat "$d/out3.md"; fail "toy, repeat-only answer: $want"; }
done
# The H2 audit-sampling interval, recomputed independently from the documented procedure: random.Random(1872), strata
# in sample order, each stratum's items sorted by id and drawn as many times as it has, an empty cell keeping its LLM label.
python3 -I - "$d/out.md" <<'PY' || fail "toy: H2 interval"
import random, sys
items = {"S1": [(1, 1)], "S2": [(1, 1)], "S3": [(1, 0)], "S4": [(0, 0)], "S5": [(1, 1), (1, 0)]}   # (human, LLM)
labeled = [("S1", 1, 1), ("S2", 1, 1), ("S3", 0, 1), ("S4", 0, 1), ("S5", 1, 5), ("S5", 0, 5)]     # (stratum, LLM, weight)
rng, vals = random.Random(1872), []
for _ in range(200):
    p = {}
    for s, its in items.items():
        r = [its[rng.randrange(len(its))] for _ in its]
        yes, no = [h for h, m in r if m], [h for h, m in r if not m]
        p[(s, 1)], p[(s, 0)] = (sum(yes) / len(yes) if yes else 1.0), (sum(no) / len(no) if no else 0.0)
    vals.append(p[("S2", 1)] / sum(w * p[(s, m)] for s, m, w in labeled))   # only a2 (S2, LLM YES) is ft but not strict
vals.sort()
want = f"(95% audit-sampling interval {vals[5]:+.1%} to {vals[194]:+.1%};"
sys.exit(0 if want in open(sys.argv[1]).read() else f"want {want}")
PY
# Kappa and the interval generators, on two strata with many distinct resample values and only 7 resamples, so the
# endpoints depend on the exact random stream. S4 (pool, base-only, weight 1): LLM q1 YES, q2-q4 NO; human q1 YES,
# q2 YES, q3 NO, q4 NO (kappa 0.50). S5 (net, weight 2): LLM b01-b05 YES, b06-b10 NO; human YES on b01-b03 and b06
# (kappa 0.40). ft flags b01 b02 b06; strict flags nothing, so H2 = recall(ft) = 2(2 p1_S5 + p0_S5) / den with
# den = p1_S4 + 3 p0_S4 + 10 p1_S5 + 10 p0_S5; point 2.8 / 10 = 28.0%. The audit key lists cards out of id order, so
# a version that skips the sort by id would draw in a different order.
d2="$t/toy2"; mkdir -p "$d2/labelset" "$d2/labels/claude" "$d2/adjudication"
python3 -I - "$d2" <<'PY'
import sys
d = sys.argv[1]
q = [("q1", 101, "YES", "YES"), ("q2", 102, "NO", "YES"), ("q3", 103, "NO", "NO"), ("q4", 104, "NO", "NO")]
b = [(f"b{k:02d}", k, "YES" if k <= 5 else "NO", "YES" if k in (1, 2, 3, 6) else "NO") for k in range(1, 11)]
with open(f"{d}/labelset/key.tsv", "w") as f:
    f.write("id\tline\tstratum\tweight\n" + "".join(f"{i}\t{n}\tpool\t1\n" for i, n, _, _ in q) + "".join(f"{i}\t{n}\tnet\t2\n" for i, n, _, _ in b))
for name in ("labels/claude/b001.tsv", "labels/gemma.tsv"):
    open(f"{d}/{name}", "w").write("".join(f"{i}\t{m}\n" for i, _, m, _ in q + b))
open(f"{d}/adjudication/manifest.tsv", "w").write("id\tkind\n"); open(f"{d}/adj.tsv", "w").write("")
open(f"{d}/none.lines", "w").write(""); open(f"{d}/base.lines", "w").write("101\n102\n103\n104\n")
open(f"{d}/ft.lines", "w").write("1\n2\n6\n")
with open(f"{d}/sample.tsv", "w") as f:
    f.write("id\tstratum\tstratum_size\tdrawn\n" + "".join(f"{i}\tS4\t4\t4\n" for i, *_ in q) + "".join(f"{i}\tS5\t10\t10\n" for i, *_ in b))
items = q + b
order = [7, 2, 12, 0, 9, 4, 13, 1, 6, 11, 3, 8, 10, 5]   # cards c01.. point at items in this scrambled order
with open(f"{d}/key.tsv", "w") as k, open(f"{d}/answers.tsv", "w") as a:
    k.write("card_id\tsource_id\tis_repeat\n")
    for c, j in enumerate(order, 1):
        k.write(f"c{c:02d}\t{items[j][0]}\t0\n"); a.write(f"c{c:02d}\t{items[j][3]}\n")
PY
python3 -I bin/audit_1872.py storm "$d2" "$d2/sample.tsv" "$d2/key.tsv" "$d2/answers.tsv" "$d2/out.md" --adjudication "$d2/adj.tsv" \
  --system ft=lines:"$d2/ft.lines" --system strict=lines:"$d2/none.lines" --h1 ft --strict strict \
  --ft "$d2/none.lines" --keyword "$d2/none.lines" --base "$d2/base.lines" --resamples 7 > /dev/null
python3 -I - "$d2/out.md" <<'PY' || { cat "$d2/out.md"; fail "toy: kappa and interval generators"; }
import random, sys
S4 = [(1, 1), (1, 0), (0, 0), (0, 0)]                                   # (human, LLM), items sorted by id
S5 = [(1, 1), (1, 1), (1, 1), (0, 1), (0, 1), (1, 0), (0, 0), (0, 0), (0, 0), (0, 0)]
R = 7
def kappa(p):
    n = len(p); yh = sum(h for h, _ in p) / n; ym = sum(m for _, m in p) / n
    if yh in (0, 1) or ym in (0, 1):
        return None
    po = sum(h == m for h, m in p) / n; pe = yh * ym + (1 - yh) * (1 - ym)
    return (po - pe) / (1 - pe)
def ci(v):
    v = sorted(v); return v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1]
krng, want = random.Random(1872), []
for name, pairs in (("S4", S4), ("S5", S5)):   # one generator for the kappa intervals, strata in sample order
    ks = [k for k in (kappa([pairs[krng.randrange(len(pairs))] for _ in pairs]) for _ in range(R)) if k is not None]
    lo, hi = ci(ks)
    want.append(f"| {kappa(pairs):.2f} ({lo:.2f} to {hi:.2f}; {len(ks)} of {R} resamples estimable) |")
def p(r):
    yes, no = [h for h, m in r if m], [h for h, m in r if not m]
    return (sum(yes) / len(yes) if yes else 1.0), (sum(no) / len(no) if no else 0.0)
rng, h2 = random.Random(1872), []   # its own generator for the corrected bootstrap
for _ in range(R):
    p14, p04 = p([S4[rng.randrange(4)] for _ in S4])
    p15, p05 = p([S5[rng.randrange(10)] for _ in S5])
    den = p14 + 3 * p04 + 10 * p15 + 10 * p05
    h2.append(2 * (2 * p15 + p05) / den if den else 0.0)
lo, hi = ci(h2)
want.append(f"+28.0% (95% audit-sampling interval {lo:+.1%} to {hi:+.1%};")
text = open(sys.argv[1]).read()
missing = [x for x in want if x not in text]
sys.exit(f"want {missing}" if missing else 0)
PY
echo "audit, hand-computed toy: all expected values present"

# 4. Audit, balanced mode, on the committed 1859 sample with the human agreeing everywhere.
python3 -I bin/make_audit_page.py freeze/labeler_prompt.md results/audit/items_1859.jsonl "$t/p59" --set t59 --repeats 10 --seed 1872 2> /dev/null
python3 -I - "$t/p59/audit_key.tsv" "$t/a59.tsv" results/1859-adjudication-opus.tsv <<'EOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("hd", "bin/holdout_data.py"); hd = importlib.util.module_from_spec(spec); spec.loader.exec_module(hd)
final = {r[0]: r[4] for r in hd.load("data", sys.argv[3], [], [])["rows"]}
with open(sys.argv[2], "w") as out:
    for l in list(open(sys.argv[1]))[1:]:
        c, src, _ = l.split("\t")
        out.write(f"{c}\t{'YES' if final[src] else 'NO'}\n")
EOF
python3 -I bin/audit_1872.py balanced data results/audit/sample_1859.tsv "$t/p59/audit_key.tsv" "$t/a59.tsv" "$t/a59.md" \
  --adjudication results/1859-adjudication-opus.tsv --resamples 200 > /dev/null
for want in '| YES | 50 / 50 | 100.0% (' '| NO | 50 / 50 | 100.0% (' 'raw agreement 100.0%' 'kappa 1.00'; do
  grep -qF -- "$want" "$t/a59.md" || { cat "$t/a59.md"; fail "balanced: $want"; }
done
echo "audit, balanced mode, perfect agreement: as expected"

# 5. OCR terciles on 1859: the terciles split the pool in thirds and their positives add up to the total.
python3 -I bin/ocr_terciles_1872.py data data/window.txt "$t/ocr.md" "${SYS[@]}" > /dev/null
python3 -I - "$t/ocr.md" <<'EOF' || fail "ocr terciles"
import sys
rows = [l.split("|") for l in open(sys.argv[1]) if l.startswith("| low") or l.startswith("| mid") or l.startswith("| high")]
pool = [int(r[2].split("+")[0]) for r in rows]
pos = sum(float(r[3]) for r in rows)
sys.exit(0 if len(rows) == 3 and sum(pool) == 1229 and max(pool) - min(pool) <= 3 and round(pos) == 354 else f"{pool} {pos}")
EOF
echo "ocr terciles: pool split in thirds, positives add up"

# OCR and reprint toys on their own data: pool p1..p5 (weight 1), net n1..n3 (weight 3); final-YES p1 p2 p3 n1.
# Flags: ft {p1,p2,p3}, strict {p1,p4,p5}. OCR qualities: p1 0.75, p2 0, p3 0.25, p4 0.5, p5 1; n1 "aa," 0 (punctuation
# is not a letter), n2 "" 0, n3 1. Cut points exactly 0.25 and 0.75, so p3 and p1 check that ties go to the lower tercile.
# Reprints: p2 and p3 share a text (one group); n3 has p1's text but is net, so it must stay apart. Groups: YES p1,
# {p2,p3} (weight 1 each) and n1 (3) = 5; strict finds p1 (1/5), strict OR ft finds p1 and {p2,p3} (2/5): H2 +20.0%.
d3="$t/toy3"; mkdir -p "$d3/labelset" "$d3/labels/claude" "$d3/adjudication"
printf 'id\tline\tstratum\tweight\np1\t1\tpool\t1\np2\t2\tpool\t1\np3\t3\tpool\t1\np4\t4\tpool\t1\np5\t8\tpool\t1\nn1\t5\tnet\t3\nn2\t6\tnet\t3\nn3\t7\tnet\t3\n' > "$d3/labelset/key.tsv"
printf 'p1\tYES\np2\tYES\np3\tYES\np4\tNO\np5\tNO\nn1\tYES\nn2\tNO\nn3\tNO\n' | tee "$d3/labels/claude/b001.tsv" > "$d3/labels/gemma.tsv"
printf 'id\tkind\n' > "$d3/adjudication/manifest.tsv"; : > "$d3/adj.tsv"
printf '1\n2\n3\n' > "$d3/ft.lines"; printf '1\n4\n8\n' > "$d3/strict.lines"
python3 -I - "$d3" <<'PY'
import sys
a = "the aurora borealis was seen here last night by many people in town"
b = "a brilliant light appeared in the northern sky after dark on monday evening"
rep = [a, b, b, "cotton prices fell sharply in the new orleans market this week", "the steamer arrived late from memphis with cargo",
       "the council met to discuss the new bridge over the river", a, "letters from the west report heavy snow on the plains"]
ocr = ["aa bb cc 1d", "1a 1b 1c 1d", "aa 1b 1c 1d", "aa bb 1c 1d", "aa,", "", "aa bb", "aa bb cc dd"]
open(f"{sys.argv[1]}/window_rep.txt", "w").write("\n".join(rep) + "\n")
open(f"{sys.argv[1]}/window_ocr.txt", "w").write("\n".join(ocr) + "\n")
PY
python3 -I bin/ocr_terciles_1872.py "$d3" "$d3/window_ocr.txt" "$d3/ocr.md" --adjudication "$d3/adj.tsv" --system ft=lines:"$d3/ft.lines" > /dev/null
for want in 'pool articles: 0.2500 and 0.7500.' '| low | 2 + 2 |' '| mid | 2 + 0 |' '| high | 1 + 1 |'; do
  grep -qF -- "$want" "$d3/ocr.md" || { cat "$d3/ocr.md"; fail "ocr toy: $want"; }
done
# Reprint toy, its own data. Pool (weight 1): p1 YES ft+strict, text A; p2 YES ft only and p3 YES strict only, one
# shared text B (a strict-matched reprint beside an ft-only miss); p4 and p5 NO strict; p6 YES ft only, text E;
# p7 and p8 NO, unflagged, with containment exactly 0.5 (1 shared shingle of p7's 2), so they must join. Net (weight 3):
# n1 YES; n2 NO; n3 NO with p1's text, which must stay apart. Groups: YES p1, {p2,p3}, p6 (1 each) and n1 (3) = 6;
# strict finds p1 and {p2,p3} (2/6); with ft also p6 (3/6): H2 +16.7%. Articles ft flags that strict missed: p2 and
# p6, in 2 distinct groups; groups with no strict-matched member: only p6.
d4="$t/toy4"; mkdir -p "$d4/labelset" "$d4/labels/claude" "$d4/adjudication"
python3 -I - "$d4" <<'PY'
import sys
d = sys.argv[1]
A = "the aurora borealis was seen here last night by many people in town"
B = "a brilliant light appeared in the northern sky after dark on monday evening"
items = [("p1", "pool", "YES", A), ("p2", "pool", "YES", B), ("p3", "pool", "YES", B),
         ("p4", "pool", "NO", "cotton prices fell sharply in the new orleans market this week"),
         ("p5", "pool", "NO", "the steamer arrived late from memphis with cargo and passengers"),
         ("p6", "pool", "YES", "letters from the west report a red glow on the plains at midnight"),
         ("p7", "pool", "NO", "alpha bravo charlie delta echo foxtrot"), ("p8", "pool", "NO", "alpha bravo charlie delta echo golf hotel"),
         ("n1", "net", "YES", "the council met to discuss the new bridge over the river"),
         ("n2", "net", "NO", "a schooner was lost off the cape with all hands aboard"), ("n3", "net", "NO", A)]
with open(f"{d}/labelset/key.tsv", "w") as f:
    f.write("id\tline\tstratum\tweight\n" + "".join(f"{i}\t{n}\t{st}\t{1 if st == 'pool' else 3}\n" for n, (i, st, _, _) in enumerate(items, 1)))
for name in ("labels/claude/b001.tsv", "labels/gemma.tsv"):
    open(f"{d}/{name}", "w").write("".join(f"{i}\t{y}\n" for i, _, y, _ in items))
open(f"{d}/adjudication/manifest.tsv", "w").write("id\tkind\n"); open(f"{d}/adj.tsv", "w").write("")
open(f"{d}/window.txt", "w").write("\n".join(t for *_, t in items) + "\n")
open(f"{d}/ft.lines", "w").write("1\n2\n6\n"); open(f"{d}/strict.lines", "w").write("1\n3\n4\n5\n")
PY
python3 -I bin/reprints_1872.py "$d4" "$d4/window.txt" "$d4/rep.md" --seed 3 --resamples 5 --adjudication "$d4/adj.tsv" \
  --system ft=lines:"$d4/ft.lines" --system strict=lines:"$d4/strict.lines" --system fuzzy=lines:"$d4/strict.lines" \
  --h1 ft --strict strict --fuzzy fuzzy > /dev/null
for want in 'Labeled items: 11 in 9 groups (pool 6, net 3); groups with more than one article: 2, largest 2.' \
            '| ft | 3 | 3 | 100.0% | 50.0% |' \
            'the 2 final-YES articles it flags that strict missed fall in 2 distinct reprint groups; final-YES groups it flags with no strict-matched member: 1'; do
  grep -qF -- "$want" "$d4/rep.md" || { cat "$d4/rep.md"; fail "reprint toy: $want"; }
done
# The group bootstrap, recomputed independently with 5 resamples: groups in key order of their first member,
# resampled within pool and within net.
python3 -I - "$d4/rep.md" <<'PY' || { cat "$d4/rep.md"; fail "reprint toy: group bootstrap"; }
import random, sys
pool = [(1, 1, 1, 1), (1, 1, 1, 1), (1, 0, 0, 1), (1, 0, 0, 1), (1, 1, 1, 0), (1, 0, 0, 0)]   # (w, YES, ft, strict): p1, {p2,p3}, p4, p5, p6, {p7,p8}
net = [(3, 1, 0, 0), (3, 0, 0, 0), (3, 0, 0, 0)]                                         # n1, n2, n3
def rec(s, pred):
    pos = sum(w for w, y, _, _ in s if y)
    return sum(w for w, y, f, k in s if y and pred(f, k)) / pos if pos else 0.0
rng, v = random.Random(3), []
for _ in range(5):
    s = [rng.choice(pool) for _ in pool] + [rng.choice(net) for _ in net]
    v.append(rec(s, lambda f, k: f or k) - rec(s, lambda f, k: k))
v.sort()
want = f"(strict OR h1) - strict: +16.7% (95% bootstrap {v[0]:+.1%} to {v[3]:+.1%})"
sys.exit(0 if want in open(sys.argv[1]).read() else f"want {want}")
PY
echo "ocr and reprint toys: exact cut points with ties, reprints joined at containment 0.5, pool and net kept apart, group-level misses, group bootstrap"

# 6. Truncation counter (needs the laya venv and a copy of the fine-tuned tokenizer and config in data/ft_checkpoint_copy).
if [ -x .venv/bin/python ] && [ -d data/ft_checkpoint_copy ]; then
  python3 -I -c 'import json
rows = [" ".join(["aurora"] * 3000), "the sky was red", "", " ".join(["aurora"] * 470), " ".join(["aurora"] * 455),
        " ".join(["aurora"] * 507)]
for n, s in enumerate(rows, 1):
    print(json.dumps({"id": f"L{n}", "line": n, "state": s}))' > "$t/trunc.jsonl"
  .venv/bin/python -I bin/truncation_1872.py data/ft_checkpoint_copy data/ft_checkpoint_copy/ft_config.json "$t/trunc.jsonl" "$t/trunc.md" --max-len 512 > /dev/null
  # 470 words = 475 state tokens: cut (room 465 after the question header) but not longer than 512; 455 words fit;
  # 507 words = exactly 512 tokens: cut, and not longer than 512.
  grep -qF "Articles scored: 6. Truncated (any state token dropped): 3. Longer than 512 tokens: 1." "$t/trunc.md" || { cat "$t/trunc.md"; fail "truncation"; }
  grep -qF -- "- line 6: 512 tokens, 47 dropped" "$t/trunc.md" || fail "truncation at exactly max_len"
  grep -qF "Room left for the article: 465 tokens." "$t/trunc.md" || fail "truncation room"
  grep -qF -- "- line 4: 475 tokens, 10 dropped" "$t/trunc.md" || fail "truncation line"
  echo "truncation counter: cut articles and over-long articles counted separately"
else
  echo "truncation counter: skipped (no laya venv or tokenizer copy)"
fi
rm -rf "$t"
