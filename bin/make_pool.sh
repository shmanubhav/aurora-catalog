#!/usr/bin/env bash
# Build the label pool (Laya >= cutoff, or rg strict) and the loose-net-only set from scored outputs.
# Usage: bin/make_pool.sh freeze/config.json data
set -euo pipefail
cfg=$1 d=$2
cutoff=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["cutoff"])' "$cfg")
awk -F'\t' -v c="$cutoff" '$2 >= c {print $1}' "$d/laya_scores.tsv" > "$d/laya_flag.lines"
"$(dirname "$0")/rg_flags.sh" freeze/loose.rg "$d/window.txt" > "$d/rg_loose.lines"
sort -n -u "$d/laya_flag.lines" "$d/rg_strict.lines" > "$d/pool.lines"
# Loose hits outside the pool; awk sets, since comm needs lexical order.
awk 'NR == FNR {p[$1] = 1; next} !($1 in p)' "$d/pool.lines" "$d/rg_loose.lines" | sort -n -u > "$d/net_only.lines"
wc -l "$d/laya_flag.lines" "$d/rg_strict.lines" "$d/pool.lines" "$d/net_only.lines"
