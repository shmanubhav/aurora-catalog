#!/usr/bin/env bash
# Build the 1872 label pool: base Laya >= 0.5, fine-tuned Laya >= t*, strict rg, fuzzy rg (freeze/config_1872.json),
# and the loose-net-only set outside it. Flags use the 4-decimal scores as written.
# Usage: bin/make_pool_1872.sh freeze/config_1872.json DATA
#   DATA holds window.txt, laya_scores.tsv (line<TAB>p) and ft_scores.tsv (id<TAB>line<TAB>p).
set -euo pipefail
cfg=$1 d=$2
read -r base_cut ft_cut < <(python3 -I -c 'import json,sys; s=json.load(open(sys.argv[1]))["systems"]; print(s["base_laya"]["cutoff"], s["ft_laya"]["cutoff"])' "$cfg")
here=$(dirname "$0")
awk -F'\t' -v c="$base_cut" '$2 >= c {print $1}' "$d/laya_scores.tsv" | sort -n -u > "$d/flags_base_laya.lines"
awk -F'\t' -v c="$ft_cut" '$3 >= c {print $2}' "$d/ft_scores.tsv" | sort -n -u > "$d/flags_ft_laya.lines"
"$here/rg_flags.sh" freeze/strict.rg "$d/window.txt" | sort -n -u > "$d/flags_strict.lines"
"$here/rg_flags.sh" freeze/fuzzy.rg "$d/window.txt" | sort -n -u > "$d/flags_fuzzy.lines"
"$here/rg_flags.sh" freeze/loose.rg "$d/window.txt" | sort -n -u > "$d/rg_loose.lines"
sort -n -u "$d"/flags_{base_laya,ft_laya,strict,fuzzy}.lines > "$d/pool.lines"
# Loose hits outside the pool; awk sets, since comm needs lexical order.
awk 'NR == FNR {p[$1] = 1; next} !($1 in p)' "$d/pool.lines" "$d/rg_loose.lines" | sort -n -u > "$d/net_only.lines"
wc -l "$d"/flags_{base_laya,ft_laya,strict,fuzzy}.lines "$d/pool.lines" "$d/rg_loose.lines" "$d/net_only.lines"
