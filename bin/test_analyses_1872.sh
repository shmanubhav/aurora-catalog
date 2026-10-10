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
# Kappa and its interval on an estimable stratum: LLM YES YES NO NO, human YES NO NO NO -> kappa 0.50.
d2="$t/toy2"; mkdir -p "$d2/labelset" "$d2/labels/claude" "$d2/adjudication"
printf 'id\tline\tstratum\tweight\nb1\t1\tnet\t2\nb2\t2\tnet\t2\nb3\t3\tnet\t2\nb4\t4\tnet\t2\n' > "$d2/labelset/key.tsv"
printf 'b1\tYES\nb2\tYES\nb3\tNO\nb4\tNO\n' | tee "$d2/labels/claude/b001.tsv" > "$d2/labels/gemma.tsv"
printf 'id\tkind\n' > "$d2/adjudication/manifest.tsv"; : > "$d2/adj.tsv"; : > "$d2/none.lines"
printf 'id\tstratum\tstratum_size\tdrawn\nb1\tS5\t4\t4\nb2\tS5\t4\t4\nb3\tS5\t4\t4\nb4\tS5\t4\t4\n' > "$d2/sample.tsv"
printf 'card_id\tsource_id\tis_repeat\nc1\tb1\t0\nc2\tb2\t0\nc3\tb3\t0\nc4\tb4\t0\n' > "$d2/key.tsv"
printf 'c1\tYES\nc2\tNO\nc3\tNO\nc4\tNO\n' > "$d2/answers.tsv"
python3 -I bin/audit_1872.py storm "$d2" "$d2/sample.tsv" "$d2/key.tsv" "$d2/answers.tsv" "$d2/out.md" --adjudication "$d2/adj.tsv" \
  --system ft=lines:"$d2/none.lines" --system strict=lines:"$d2/none.lines" --h1 ft --strict strict \
  --ft "$d2/none.lines" --keyword "$d2/none.lines" --base "$d2/none.lines" --resamples 300 > /dev/null
python3 -I - "$d2/out.md" <<'PY' || fail "toy: kappa interval"
import random, sys
pairs = [(1, 1), (0, 1), (0, 0), (0, 0)]   # (human, LLM) by id
def kappa(p):
    n = len(p); yh = sum(h for h, _ in p) / n; ym = sum(m for _, m in p) / n
    if yh in (0, 1) or ym in (0, 1):
        return None
    po = sum(h == m for h, m in p) / n; pe = yh * ym + (1 - yh) * (1 - ym)
    return (po - pe) / (1 - pe)
rng = random.Random(1872)
ks = sorted(k for k in (kappa([pairs[rng.randrange(4)] for _ in pairs]) for _ in range(300)) if k is not None)
want = f"| 0.50 ({ks[int(0.025 * len(ks))]:.2f} to {ks[int(0.975 * len(ks)) - 1]:.2f}; {len(ks)} of 300 resamples estimable) |"
sys.exit(0 if want in open(sys.argv[1]).read() else f"want {want}")
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

# OCR quality on known strings, and a reprint pair, in the toy: pool qualities 1, 0.75, 0.5, 0.25; net "aa, bb" (0.5,
# a token with punctuation is not letters) and "" (0). Cut points 0.4167 and 0.8333. Lines 10 and 20 are one reprint.
python3 -I - "$d" <<'PY'
import sys
lines = ["x"] * 60
for n, txt in {10: "aa bb cc dd", 20: "aa bb cc 1d", 30: "aa bb 1c 1d", 40: "aa 1b 1c 1d", 50: "aa, bb", 60: ""}.items():
    lines[n - 1] = txt
open(f"{sys.argv[1]}/window_ocr.txt", "w").write("\n".join(lines) + "\n")
same = "the aurora borealis was seen here last night by many people in town"
for n, txt in {10: same, 20: same, 30: "cotton prices fell sharply in the new orleans market this week",
               40: "the steamer arrived late from memphis with a heavy cargo today",
               50: "a brilliant light appeared in the northern sky after dark on monday",
               60: "the council met to discuss the new bridge over the river"}.items():
    lines[n - 1] = txt
open(f"{sys.argv[1]}/window_rep.txt", "w").write("\n".join(lines) + "\n")
PY
python3 -I bin/ocr_terciles_1872.py "$d" "$d/window_ocr.txt" "$d/ocr.md" --adjudication "$d/adj.tsv" --system ft=lines:"$d/ft.lines" > /dev/null
for want in 'pool articles: 0.4167 and 0.8333.' '| low | 1 + 1 |' '| mid | 2 + 1 |' '| high | 1 + 0 |'; do
  grep -qF -- "$want" "$d/ocr.md" || { cat "$d/ocr.md"; fail "ocr toy: $want"; }
done
python3 -I bin/reprints_1872.py "$d" "$d/window_rep.txt" "$d/rep.md" --seed 1 --resamples 50 --adjudication "$d/adj.tsv" \
  --system ft=lines:"$d/ft.lines" --system strict=lines:"$d/strict.lines" --system fuzzy=lines:"$d/strict.lines" \
  --h1 ft --strict strict --fuzzy fuzzy > /dev/null
for want in 'Labeled items: 6 in 5 groups (pool 3, net 2); groups with more than one article: 1, largest 2.' \
            '| ft | 1 | 1 | 100.0% | 16.7% |' \
            'the 1 final-YES articles it flags that strict missed fall in 1 distinct reprint groups; final-YES groups it flags with no strict-matched member: 0'; do
  grep -qF -- "$want" "$d/rep.md" || { cat "$d/rep.md"; fail "reprint toy: $want"; }
done
echo "ocr and reprint toys: known qualities, cut points and one merged reprint pair"

# 6. Truncation counter (needs the laya venv and a copy of the fine-tuned tokenizer and config in data/ft_checkpoint_copy).
if [ -x .venv/bin/python ] && [ -d data/ft_checkpoint_copy ]; then
  python3 -I -c 'import json
rows = [" ".join(["aurora"] * 3000), "the sky was red", "", "northern lights seen", "cotton prices"]
for n, s in enumerate(rows, 1):
    print(json.dumps({"id": f"L{n}", "line": n, "state": s}))' > "$t/trunc.jsonl"
  .venv/bin/python -I bin/truncation_1872.py data/ft_checkpoint_copy data/ft_checkpoint_copy/ft_config.json "$t/trunc.jsonl" "$t/trunc.md" --max-len 512 > /dev/null
  grep -qF "Articles scored: 5. Truncated (any state token dropped): 1." "$t/trunc.md" || { cat "$t/trunc.md"; fail "truncation"; }
  grep -qF -- "- line 1:" "$t/trunc.md" || fail "truncation line"
  echo "truncation counter: the one over-long article is counted"
else
  echo "truncation counter: skipped (no laya venv or tokenizer copy)"
fi
rm -rf "$t"
