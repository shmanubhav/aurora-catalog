#!/usr/bin/env bash
# Hand-computed toy case for bin/score_1872.py; exits non-zero on any mismatch.
# Positives: a1 a3 a4 (weight 1) + a5 (weight 5) = 8. strict flags 10,20 -> 1/2, recall 1/8; ft (>= 0.8) flags 10,20,30
# -> 2/3, recall 2/8; checker drops 20 -> 2/2, recall 2/8; H2 gain = 2/8 - 1/8 = +12.5%; a3 is adjudicated.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp -d)
mkdir -p "$t/labelset" "$t/labels/claude" "$t/adjudication"
printf 'id\tline\tstratum\tweight\na1\t10\tpool\t1\na2\t20\tpool\t1\na3\t30\tpool\t1\na4\t40\tpool\t1\na5\t50\tnet\t5\na6\t60\tnet\t5\n' > "$t/labelset/key.tsv"
printf 'a1\tYES\na2\tNO\na3\tYES\na4\tYES\na5\tYES\na6\tNO\n' > "$t/labels/claude/b001.tsv"
printf 'a1\tYES\na2\tNO\na3\tNO\na4\tYES\na5\tYES\na6\tNO\n' > "$t/labels/gemma.tsv"
printf 'a3\tYES\treason\n' > "$t/adj.tsv"
printf 'id\tkind\na3\tdisagree\n' > "$t/adjudication/manifest.tsv"
printf '10\n20\n' > "$t/s.lines"
printf '10\t0.9\n30\t0.85\n40\t0.2\n20\t0.81\n' > "$t/ft.tsv"
printf 'L10\tYES\nL20\tNO\nL30\tYES\n' > "$t/chk.tsv"
python3 -I "$here/score_1872.py" "$t" "$t/out.md" --seed 1 --resamples 200 --adjudication "$t/adj.tsv" \
  --system strict=lines:"$t/s.lines" --system ft=scores:"$t/ft.tsv":0.8 --checker ft+chk=ft:"$t/chk.tsv" --h1 ft --strict strict > /dev/null
for want in '| strict | 2 | 1 | 50.0% |' '| ft | 3 | 2 | 66.7% |' '| ft+chk | 2 | 2 | 100.0% |' \
            '12.5% (' '25.0% (' 'H2 gain: (strict OR h1) - strict: +12.5%' 'final-YES flags strict missed 1 -> FAIL' \
            'excluding Opus-adjudicated items (1): precision 1/1'; do
  grep -qF -- "$want" "$t/out.md" || { echo "MISSING: $want"; cat "$t/out.md"; exit 1; }
done
echo "toy case: all expected values present"

# Failure rules: a missing checker verdict is kept; an unanswered agreed check is reported, not a crash;
# a MISSING Sonnet label with an unanswered adjudication is excluded and listed.
printf 'id\tline\tstratum\tweight\na1\t10\tpool\t1\na2\t20\tpool\t1\na3\t30\tpool\t1\na4\t40\tpool\t1\na5\t50\tnet\t5\na6\t60\tnet\t5\na7\t70\tpool\t1\n' > "$t/labelset/key.tsv"
printf 'a1\tYES\na2\tNO\na3\tYES\na4\tYES\na5\tYES\na6\tNO\na7\tMISSING\n' > "$t/labels/claude/b001.tsv"
printf 'a1\tYES\na2\tNO\na3\tNO\na4\tYES\na5\tYES\na6\tNO\na7\tYES\n' > "$t/labels/gemma.tsv"
printf 'id\tkind\na3\tdisagree\na4\tagreed-check\na7\tsonnet-missing\n' > "$t/adjudication/manifest.tsv"
printf 'L10\tYES\nL20\tNO\n' > "$t/chk.tsv"
python3 -I "$here/score_1872.py" "$t" "$t/out2.md" --seed 1 --resamples 200 --adjudication "$t/adj.tsv" \
  --system strict=lines:"$t/s.lines" --system ft=scores:"$t/ft.tsv":0.8 --checker ft+chk=ft:"$t/chk.tsv" --h1 ft --strict strict > /dev/null
for want in 'flags with no checker verdict, kept by rule: 1 (lines 30)' 'adjudication items unanswered, Sonnet label kept by rule: 1 (a4)' \
            'items with no label (Sonnet batch failed, adjudication unanswered), excluded: 1 (a7)' '0 of 0 answered agreed checks (1 drawn)' \
            '| ft+chk | 2 | 2 | 100.0% |'; do
  grep -qF -- "$want" "$t/out2.md" || { echo "MISSING: $want"; cat "$t/out2.md"; exit 1; }
done
echo "failure rules: all expected values present"
