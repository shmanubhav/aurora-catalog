#!/usr/bin/env bash
# Print the 1-based article line numbers a pattern file flags in the text view.
# Usage: bin/rg_flags.sh freeze/strict.rg data/window.txt
set -euo pipefail
patterns=$(grep -v -E '^\s*(#|$)' "$1" || true)
# An empty pattern list would make rg match every line.
[ -n "$patterns" ] || { echo "no patterns in $1" >&2; exit 1; }
rg --no-filename -n -i -f <(printf '%s\n' "$patterns") "$2" | cut -d: -f1
