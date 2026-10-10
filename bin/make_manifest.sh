#!/usr/bin/env bash
# Write prereg/MANIFEST.tsv: every freeze file and pipeline script with its SHA-256 and every commit that touched it.
# Usage: bin/make_manifest.sh   (run from the repo root after committing, so the commit list is complete)
set -euo pipefail
files=(freeze/*.json freeze/*.md freeze/*.rg bin/*.py bin/*.sh paper/*.md prereg/1872_preregistration.md results/score_1872_repro_1859.md results/1859-adjudication-opus.tsv results/audit/sample_1859.tsv results/audit/items_1859.jsonl)
{
  printf 'file\tsha256\tcommits_oldest_first\n'
  for f in "${files[@]}"; do
    [ -f "$f" ] || continue
    printf '%s\t%s\t%s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(git log --reverse --format=%h -- "$f" | paste -sd, -)"
  done
} > prereg/MANIFEST.tsv
git diff --quiet HEAD -- "${files[@]}" || echo "warning: uncommitted changes in manifest files; commit, then rerun" >&2
wc -l < prereg/MANIFEST.tsv
