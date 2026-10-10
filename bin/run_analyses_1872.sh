#!/usr/bin/env bash
# Run one post-download analysis of the 1872 holdout (prereg sections 5-7) with literal settings.
# Usage: bin/run_analyses_1872.sh reprints | ocr | truncation | audit1872 ANSWERS.tsv | audit1859 ANSWERS.tsv
# Refuses unless the analysis code is exactly the committed, pushed version in results/1872/analysis_scripts.sha256 and
# every 1872 input still has the hash results/1872_stage_log.tsv last logged for it (the analyses are pure functions of
# committed stage outputs). Each run first commits and pushes a start row to results/1872/analysis_log.tsv, then the
# SHA-256 of its scripts, inputs and output, or a failed row; so every attempt, failed ones included, is on the public
# record. An analysis whose output exists runs again only with REASON="...", and the earlier output is kept beside it.
set -euo pipefail
cd "$(dirname "$0")/.."
D=data/1872
OUT=results/1872/analyses
LOG=results/1872/analysis_log.tsv
STAGES=results/1872_stage_log.tsv
PUBLIC_ROOT_SHA=cfe81037c2410d57402ab150ef2e4f983a6aeba7   # as bin/run_1872.sh
FT=data/ft_checkpoint_copy   # copied from llm02 /srv/laya-batch/work/ft on 2026-10-10 (results/1872/ft_checkpoint_copy.sha256)
FT_SHA="e3238ee4b9d5e0378b0ab533cb3660c69af80ffa35f00d4155b519605c83a57e  ft_config.json
afd200541042bfdd51a6da4821e554b71fb58999a4ece9ef7bb1adf435eb0079  rl_agent_config.json
dbba919c6e5e492bc22beb80abb64e6fcc7e8744dc696e8388b8c977767afa4b  tokenizer/tokenizer.json
e8e6a37c189f9dd23976b86b3e1ddb6928472e9f87c94103a1aaff311f45f090  tokenizer/tokenizer_config.json"
SYS=(--adjudication "$D"/adjudication/adjudication_opus.tsv
     --system base_laya=lines:"$D"/flags_base_laya.lines --system strict=lines:"$D"/flags_strict.lines
     --system fuzzy=lines:"$D"/flags_fuzzy.lines --system ft_laya=lines:"$D"/flags_ft_laya.lines
     --checker ft+qwen=ft_laya:"$D"/checker/qwen.tsv --checker ft+opus=ft_laya:"$D"/checker/opus.tsv
     --h1 ft_laya --strict strict --fuzzy fuzzy)
INPUTS=("$D"/labelset/key.tsv "$D"/labels/claude/b*.tsv "$D"/labels/gemma.tsv "$D"/adjudication/manifest.tsv
        "$D"/adjudication/adjudication_opus.tsv "$D"/flags_base_laya.lines "$D"/flags_strict.lines "$D"/flags_fuzzy.lines
        "$D"/flags_ft_laya.lines "$D"/checker/qwen.tsv "$D"/checker/opus.tsv)
SCRIPTS=(bin/holdout_data.py bin/agent_outputs.py bin/run_analyses_1872.sh)
USAGE="usage: $0 reprints | ocr | truncation | audit1872 ANSWERS.tsv | audit1859 ANSWERS.tsv"

sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
logged() {   # each FILE must match the last hash the stage log recorded for it
  for f in "$@"; do
    want=$(awk -F'\t' -v p="$f" '$3 == p {h = $4} END {print h}' "$STAGES")
    [ -n "$want" ] && [ "$(sha "$f")" = "$want" ] || { echo "$f does not match the stage log"; exit 1; }
  done
}
frozen() {   # each FILE must match its prereg/MANIFEST.tsv hash
  for f in "$@"; do
    [ "$(awk -F'\t' -v p="$f" '$1 == p {print $2}' prereg/MANIFEST.tsv)" = "$(sha "$f")" ] || { echo "$f differs from prereg/MANIFEST.tsv"; exit 1; }
  done
}
answers() {   # answers SET FILE: the page's own download, committed (and so pushed, by the HEAD check) before scoring
  [ "$(basename "$2")" = "audit_answers_$1.tsv" ] || { echo "$2: expected the $1 page's download, audit_answers_$1.tsv"; exit 1; }
  git ls-files --error-unmatch "$2" > /dev/null 2>&1 && git diff --quiet HEAD -- "$2" || { echo "commit $2 first"; exit 1; }
}
row() {   # row ANALYSIS FILE SHA: one log line
  printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$(date -u +%FT%TZ)" "$2" "$3" "$(printf '%s' "${REASON:-}" | tr '\t\n' '  ')" >> "$LOG"
}
publish() {   # publish MESSAGE: commit the analysis log and outputs, push the branch
  git add "$LOG" "$OUT"
  git commit -q -m "$1"
  git push -q origin "HEAD:refs/heads/$(git branch --show-current)"
}
run() {   # run ANALYSIS OUTPUT COMMAND...: pushed start row, then the command; a failure is logged and pushed too
  local a=$1 out=$2; shift 2
  if [ -e "$out" ]; then
    [ -n "${REASON:-}" ] || { echo "$out exists; set REASON=... to run again"; exit 1; }
    mv "$out" "$out.before-$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  row "$a" start "$(git rev-parse HEAD)"
  publish "1872 analysis $a start"
  if ! "$@"; then
    row "$a" failed "$(git rev-parse HEAD)"
    publish "1872 analysis $a failed"
    exit 1
  fi
}
record() {   # record ANALYSIS FILE...: the hashes of everything a finished run used and wrote, then publish
  local a=$1; shift
  for f in "$@"; do row "$a" "$f" "$(sha "$f")"; done
  publish "1872 analysis $a"
}

case ${1:-} in reprints|ocr|truncation) ;; audit1872|audit1859) [ -f "${2:-}" ] || { echo "$USAGE"; exit 1; } ;; *) echo "$USAGE"; exit 1 ;; esac
# The code must be exactly the committed, pushed version, on a branch of the public history.
[ "$(git branch --show-current)" != main ] && [ "$(git rev-list --max-parents=0 HEAD)" = "$PUBLIC_ROOT_SHA" ] \
  || { echo "not on a branch of the public history (root $PUBLIC_ROOT_SHA), or on main"; exit 1; }
shasum -a 256 -c --status results/1872/analysis_scripts.sha256 || { echo "scripts differ from results/1872/analysis_scripts.sha256"; exit 1; }
[ -z "$(git status --porcelain -- bin results/1872 "$STAGES")" ] || { echo "uncommitted changes under bin/ or results/1872"; exit 1; }
frozen bin/agent_outputs.py
git merge-base --is-ancestor HEAD '@{u}' 2> /dev/null || { echo "push this commit first: the push is the public timestamp"; exit 1; }
mkdir -p "$OUT"
[ -f "$LOG" ] || printf 'analysis\tutc\tfile\tsha256\treason\n' > "$LOG"

case $1 in
reprints)
  logged "${INPUTS[@]}" "$D"/window.txt
  run reprints "$OUT"/reprints.md python3 -I bin/reprints_1872.py "$D" "$D"/window.txt "$OUT"/reprints.md --seed 1872 "${SYS[@]}"
  record reprints "${SCRIPTS[@]}" bin/reprints_1872.py "${INPUTS[@]}" "$D"/window.txt "$OUT"/reprints.md ;;
ocr)
  logged "${INPUTS[@]}" "$D"/window.txt
  run ocr "$OUT"/ocr_terciles.md python3 -I bin/ocr_terciles_1872.py "$D" "$D"/window.txt "$OUT"/ocr_terciles.md "${SYS[@]}"
  record ocr "${SCRIPTS[@]}" bin/ocr_terciles_1872.py "${INPUTS[@]}" "$D"/window.txt "$OUT"/ocr_terciles.md ;;
truncation)
  logged "$D"/ft_input.jsonl
  [ "$(cd "$FT" && shasum -a 256 ft_config.json rl_agent_config.json tokenizer/tokenizer.json tokenizer/tokenizer_config.json)" = "$FT_SHA" ] \
    || { echo "$FT differs from the fine-tuned checkpoint's files"; exit 1; }
  run truncation "$OUT"/truncation.md .venv/bin/python -I bin/truncation_1872.py "$FT" "$FT"/ft_config.json "$D"/ft_input.jsonl \
    "$OUT"/truncation.md --max-len 4096
  record truncation bin/run_analyses_1872.sh bin/truncation_1872.py "$FT"/ft_config.json "$FT"/rl_agent_config.json \
    "$FT"/tokenizer/tokenizer.json "$FT"/tokenizer/tokenizer_config.json "$D"/ft_input.jsonl "$OUT"/truncation.md ;;
audit1872)
  answers 1872 "$2"
  logged "${INPUTS[@]}" "$D"/audit/sample_1872.tsv "$D"/audit/page_1872/audit_key.tsv
  run audit1872 "$OUT"/audit_1872.md python3 -I bin/audit_1872.py storm "$D" "$D"/audit/sample_1872.tsv \
    "$D"/audit/page_1872/audit_key.tsv "$2" "$OUT"/audit_1872.md "${SYS[@]}" --ft "$D"/flags_ft_laya.lines \
    --keyword "$D"/flags_strict.lines --keyword "$D"/flags_fuzzy.lines --base "$D"/flags_base_laya.lines --seed 1872
  record audit1872 "${SCRIPTS[@]}" bin/audit_1872.py "${INPUTS[@]}" "$D"/audit/sample_1872.tsv \
    "$D"/audit/page_1872/audit_key.tsv "$2" "$OUT"/audit_1872.md ;;
audit1859)
  answers 1859 "$2"
  logged "$D"/audit/page_1859/audit_key.tsv
  frozen results/audit/sample_1859.tsv results/1859-adjudication-opus.tsv
  run audit1859 "$OUT"/audit_1859.md python3 -I bin/audit_1872.py balanced data results/audit/sample_1859.tsv \
    "$D"/audit/page_1859/audit_key.tsv "$2" "$OUT"/audit_1859.md --adjudication results/1859-adjudication-opus.tsv --seed 1872
  record audit1859 "${SCRIPTS[@]}" bin/audit_1872.py data/labelset/key.tsv data/labels/claude/b*.tsv \
    data/labels/gemma.tsv data/adjudication/manifest.tsv results/1859-adjudication-opus.tsv \
    results/audit/sample_1859.tsv "$D"/audit/page_1859/audit_key.tsv "$2" "$OUT"/audit_1859.md ;;
esac
