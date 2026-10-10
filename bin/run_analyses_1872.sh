#!/usr/bin/env bash
# Run one post-download analysis of the 1872 holdout (prereg sections 5-7) with literal settings.
# Usage: bin/run_analyses_1872.sh reprints | ocr | truncation | audit1872 ANSWERS.tsv | audit1859 ANSWERS.tsv
# Every 1872 input must still have the hash results/1872_stage_log.tsv last logged for it (these analyses are pure
# functions of committed stage outputs). Each run appends the SHA-256 of its scripts, inputs and output to
# results/1872/analysis_log.tsv; commit and push both afterwards. An analysis whose output exists runs again only with
# REASON="...", which is logged.
set -euo pipefail
cd "$(dirname "$0")/.."
D=data/1872
OUT=results/1872/analyses
LOG=results/1872/analysis_log.tsv
STAGES=results/1872_stage_log.tsv
FT=data/ft_checkpoint_copy   # copied from llm02 /srv/laya-batch/work/ft on 2026-10-10, hashes checked below
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

sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
logged() {   # each FILE must match the last hash the stage log recorded for it
  for f in "$@"; do
    want=$(awk -F'\t' -v p="$f" '$3 == p {h = $4} END {print h}' "$STAGES")
    [ -n "$want" ] && [ "$(sha "$f")" = "$want" ] || { echo "$f does not match the stage log"; exit 1; }
  done
}
record() {   # record ANALYSIS FILE...
  local a=$1; shift
  for f in "$@"; do printf '%s\t%s\t%s\t%s\t%s\n' "$a" "$(date -u +%FT%TZ)" "$f" "$(sha "$f")" "${REASON:-}" >> "$LOG"; done
}
fresh() {   # fresh OUTPUT: refuse to overwrite without a reason
  [ ! -e "$1" ] || [ -n "${REASON:-}" ] || { echo "$1 exists; set REASON=... to run again"; exit 1; }
}
[ "$(git rev-parse --abbrev-ref HEAD)" != main ] || { echo "not on main"; exit 1; }
mkdir -p "$OUT"
[ -f "$LOG" ] || printf 'analysis\tutc\tfile\tsha256\treason\n' > "$LOG"
SCRIPTS=(bin/holdout_data.py bin/agent_outputs.py bin/run_analyses_1872.sh)

case ${1:-} in
reprints)
  fresh $OUT/reprints.md
  logged "${INPUTS[@]}" $D/window.txt
  python3 -I bin/reprints_1872.py $D $D/window.txt $OUT/reprints.md --seed 1872 "${SYS[@]}"
  record reprints "${SCRIPTS[@]}" bin/reprints_1872.py "${INPUTS[@]}" $D/window.txt $OUT/reprints.md ;;
ocr)
  fresh $OUT/ocr_terciles.md
  logged "${INPUTS[@]}" $D/window.txt
  python3 -I bin/ocr_terciles_1872.py $D $D/window.txt $OUT/ocr_terciles.md "${SYS[@]}"
  record ocr "${SCRIPTS[@]}" bin/ocr_terciles_1872.py "${INPUTS[@]}" $D/window.txt $OUT/ocr_terciles.md ;;
truncation)
  fresh $OUT/truncation.md
  logged $D/ft_input.jsonl
  [ "$(cd $FT && shasum -a 256 ft_config.json rl_agent_config.json tokenizer/tokenizer.json tokenizer/tokenizer_config.json)" = "$FT_SHA" ] \
    || { echo "$FT differs from the fine-tuned checkpoint's files"; exit 1; }
  .venv/bin/python -I bin/truncation_1872.py $FT $FT/ft_config.json $D/ft_input.jsonl $OUT/truncation.md --max-len 4096
  record truncation bin/run_analyses_1872.sh bin/truncation_1872.py $FT/ft_config.json $FT/rl_agent_config.json \
    $FT/tokenizer/tokenizer.json $FT/tokenizer/tokenizer_config.json $D/ft_input.jsonl $OUT/truncation.md ;;
audit1872)
  [ -f "${2:-}" ] || { echo "usage: $0 audit1872 ANSWERS.tsv"; exit 1; }
  fresh $OUT/audit_1872.md
  logged "${INPUTS[@]}" $D/audit/sample_1872.tsv $D/audit/page_1872/audit_key.tsv
  python3 -I bin/audit_1872.py storm $D $D/audit/sample_1872.tsv $D/audit/page_1872/audit_key.tsv "$2" $OUT/audit_1872.md \
    "${SYS[@]}" --ft $D/flags_ft_laya.lines --keyword $D/flags_strict.lines --keyword $D/flags_fuzzy.lines \
    --base $D/flags_base_laya.lines --seed 1872
  record audit1872 "${SCRIPTS[@]}" bin/audit_1872.py "${INPUTS[@]}" $D/audit/sample_1872.tsv \
    $D/audit/page_1872/audit_key.tsv "$2" $OUT/audit_1872.md ;;
audit1859)
  [ -f "${2:-}" ] || { echo "usage: $0 audit1859 ANSWERS.tsv"; exit 1; }
  fresh $OUT/audit_1859.md
  logged $D/audit/page_1859/audit_key.tsv
  python3 -I bin/audit_1872.py balanced data results/audit/sample_1859.tsv $D/audit/page_1859/audit_key.tsv "$2" \
    $OUT/audit_1859.md --adjudication results/1859-adjudication-opus.tsv --seed 1872
  record audit1859 "${SCRIPTS[@]}" bin/audit_1872.py data/labelset/key.tsv results/1859-adjudication-opus.tsv \
    results/audit/sample_1859.tsv $D/audit/page_1859/audit_key.tsv "$2" $OUT/audit_1859.md ;;
*)
  echo "usage: $0 reprints | ocr | truncation | audit1872 ANSWERS.tsv | audit1859 ANSWERS.tsv"; exit 1 ;;
esac
