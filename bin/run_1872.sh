#!/usr/bin/env bash
# Run one stage of the frozen 1872 holdout with the literal settings of freeze/config_1872.json.
# Usage: bin/run_1872.sh STAGE   (repo root, on branch run-1872 cut from the registered commit; README, Reproducing).
# Re-running a stage that has any row in the stage log needs ATTEMPT=n REASON="...".
# Every stage first checks the branch and its public root, that each file in prereg/MANIFEST.tsv still has its frozen
# hash and that the previous stage completed; it publishes a start row before doing anything, and afterwards appends
# each output's SHA-256 (and HEAD) to results/1872_stage_log.tsv, commits and pushes run-1872 (never the default branch).
# Agents (Sonnet labelers, Opus checkers, Opus adjudicators) run isolated through bin/run_agents.py; a *_run stage's
# MAX_STAGE_RUNS-th and any later run is final: agents still not done go to the frozen failure rules. A run after the
# third happens only if the third stopped before finishing, and is listed as a deviation.
set -euo pipefail
STAGES=(download extract base_laya ft_score pool labelset checker_inputs qwen opus_checker_render opus_checker_run
        opus_checker_collect label_render label_run label_collect gemma check adjudication_render adjudication_run
        adjudication_collect score audit)
stage=$1
D=data/1872
SB=$HOME/scratch/aurora-1872-sandbox
LOG=results/1872_stage_log.tsv
[ -f local.env ] || { echo "local.env missing: copy local.env.example and fill in the host settings"; exit 1; }
# shellcheck source=/dev/null
source local.env
LLM02=(ssh -i "$GPU_SSH_KEY" -o BatchMode=yes -o ServerAliveInterval=30 "$GPU_HOST")
SCP=(scp -q -i "$GPU_SSH_KEY" -o BatchMode=yes)
REV=77e27fa69c4788dfaad1c9efd8a226d5a32d3e9a
ARCHIVE_SHA=8b246fb4894f5ce54ed841e3f66dbbcb832b378551ca51f4ba23af75d9087f67
BASE_REV=7b928d828b7b0e022f929d9bd2e44165aa270148
FT_IMAGE_ID=sha256:7db9c7e879c57e8e530fc5504577aa6b2a274198b44b9b5a4ebae5169760b58f
FT_REMOTE_SHA="193acb46be4bbf060c5d1d919e4de393d618f1b6ca53d2e2f4cb12912b688d0d  ft_run.sh
133b1e2c76e1c3e111991a2fc21168cd5215bee9151987490d839f535d7c26cc  ft_score.py
e3238ee4b9d5e0378b0ab533cb3660c69af80ffa35f00d4155b519605c83a57e  config.json
687f84e722a8fc7584d5f763308d8315986ce5b7e42b30e04a655f153e57ab70  all/model.safetensors
afd200541042bfdd51a6da4821e554b71fb58999a4ece9ef7bb1adf435eb0079  all/rl_agent_config.json
300ce0aa7f2caf72e1c3ef2572ba02038f63836a1776c423b9aed76215b001c5  all/questions.json"
QWEN="qwen3.8:27b-q4_K_M 25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e"
GEMMA="gemma4:26b-a4b-it-mtp-q4_K_M 08ae7ec1744bd7f451c4a530afb39d2673ad9d07a8369b8a33a3613b41212a68"
OLLAMA_VERSION=0.34.4
CLAUDE_VERSION=2.1.296
SONNET=claude-sonnet-5-5
OPUS=claude-opus-5-5
RUN_BRANCH=run-1872
PUBLIC_ROOT_SHA=not-yet-set   # the public root commit, set in the commit after it (a commit cannot name itself)
MAX_STAGE_RUNS=3
export DISABLE_AUTOUPDATER=1
mkdir -p "$D" results/1872
touch "$LOG"

claude_version() {
  [ "$(claude --version | awk '{print $1}')" = "$CLAUDE_VERSION" ] || { echo "Claude Code is not $CLAUDE_VERSION"; exit 1; }
}

# ---- preamble: right branch, everything published, frozen files unchanged, stage order, no silent re-runs ----
guard() {   # only the run branch of the public history may run, commit or push: private history can never leave
  [ "$(git branch --show-current)" = "$RUN_BRANCH" ] && [ "$(git rev-list --max-parents=0 HEAD)" = "$PUBLIC_ROOT_SHA" ] \
    || { echo "not on $RUN_BRANCH with public root $PUBLIC_ROOT_SHA"; exit 1; }
}
publish() {   # publish MESSAGE: commit the stage log and results/1872, then push the run branch (guard checked again)
  guard
  git add "$LOG"
  git add results/1872 2> /dev/null || true
  git commit -q -m "$1"
  git push -q origin "$RUN_BRANCH:$RUN_BRANCH"
}
guard
git remote get-url origin > /dev/null 2>&1 || { echo "no origin: create the public repository first (README, Reproducing)"; exit 1; }
git push -q origin "$RUN_BRANCH:$RUN_BRANCH" || { echo "push to origin failed: fix it before running a stage"; exit 1; }
tail -n +2 prereg/MANIFEST.tsv | while IFS=$'\t' read -r f sha _; do
  [ "$f" = prereg/MANIFEST.tsv ] && continue
  [ "$(shasum -a 256 "$f" | cut -d' ' -f1)" = "$sha" ] || { echo "frozen file changed: $f"; exit 1; }
done
idx=-1
for i in "${!STAGES[@]}"; do [ "${STAGES[$i]}" = "$stage" ] && idx=$i; done
[ "$idx" -ge 0 ] || { echo "unknown stage $stage"; exit 2; }
if [ "$idx" -gt 0 ]; then   # the previous stage's latest row must be an output row, not a start or rerun row
  prev=${STAGES[$((idx - 1))]}
  awk -F'\t' -v s="$prev" '$1 == s {last = $2} END {exit !(last != "" && last != "start" && last != "rerun")}' "$LOG" \
    || { echo "stage $prev has not completed"; exit 1; }
fi
row=start
note=
if awk -F'\t' -v s="$stage" '$1 == s {f = 1} END {exit !f}' "$LOG"; then   # any row, start rows included
  [ -n "${ATTEMPT:-}" ] && [ -n "${REASON:-}" ] || { echo "$stage already ran; set ATTEMPT=n REASON=... to re-run"; exit 1; }
  tarball="$D/attempts/$stage.$ATTEMPT.tar"
  [ ! -e "$tarball" ] || { echo "$tarball exists: use a new ATTEMPT number"; exit 1; }
  mkdir -p "$D/attempts"
  prior=$(awk -F'\t' -v s="$stage" '$1 == s && $2 != "start" && $2 != "rerun" {print $3}' "$LOG" | sort -u | sed "s|^SB/|$SB/|" \
    | while IFS= read -r p; do if [ -e "$p" ]; then printf '%s\n' "$p"; fi; done)   # files moved by a re-render are already archived
  if [ -n "$prior" ]; then printf '%s\n' "$prior" | tar -cf "$tarball" -T -; fi
  case $stage in   # a re-render starts from a fresh sandbox; the old one is moved aside, never deleted
    opus_checker_render) role=checker ;; label_render) role=labeler ;; adjudication_render) role=adjudicator ;; *) role= ;;
  esac
  if [ -n "$role" ] && [ -e "$SB/$role" ]; then mv "$SB/$role" "$SB/$role.attempt$ATTEMPT"; fi
  row=rerun
  note="attempt $ATTEMPT: $(printf '%s' "$REASON" | tr '\t\n' '  ')"
fi
case $stage in *_render|*_run) claude_version ;; esac   # a wrong Claude Code version must not use up a run
printf '%s\t%s\t%s\t%s\t%s\n' "$stage" "$row" "$(date -u +%FT%TZ)" "$(git rev-parse --short HEAD)" "$note" >> "$LOG"
publish "1872 stage $stage $row"
stage_run=$(awk -F'\t' -v s="$stage" '$1 == s && ($2 == "start" || $2 == "rerun") {n++} END {print n + 0}' "$LOG")

log() {   # log FILE...: append stage, UTC, file (sandbox paths as SB/...), SHA-256, line count, HEAD; publish
  for f in "$@"; do
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$stage" "$(date -u +%FT%TZ)" "${f/#"$SB"/SB}" "$(shasum -a 256 "$f" | cut -d' ' -f1)" \
      "$(wc -l < "$f" | tr -d ' ')" "$(git rev-parse --short HEAD)" >> "$LOG"
  done
  publish "1872 stage $stage"
  echo "logged and pushed $stage"
}

collect() {   # collect ROLE BATCH_DIR DEST COLUMNS: accept only answers bin/run_agents.py verified (bin/collect_agents.py)
  python3 -I bin/collect_agents.py "$1" "$SB/$1" "$2" "$3" "$4" "$D/${1}_failed_ids.txt"
}

ollama_pins() {   # ollama_pins "NAME DIGEST": check the model digest and Ollama version on llm02, print them
  "${LLM02[@]}" "curl -s -m5 127.0.0.1:11434/api/version; echo; curl -s -m5 127.0.0.1:11434/api/tags" < /dev/null \
    | python3 -I -c 'import json, sys
first, rest = sys.stdin.read().split("\n", 1)
ver = json.loads(first)["version"]
tags = {m["name"]: m["digest"] for m in json.loads(rest)["models"]}
name, digest = sys.argv[1].split()
assert ver == sys.argv[2], f"Ollama {ver} is not {sys.argv[2]}"
assert tags.get(name) == digest, f"{name} digest {tags.get(name)} is not {digest}"
print(f"ollama {ver}\t{name}\t{digest}")' "$1" "$OLLAMA_VERSION"
}

case $stage in
download)
  mkdir -p "$D/raw"
  curl -fL --retry 3 -o "$D/raw/faro_1872.tar.gz.part" \
    "https://huggingface.co/datasets/dell-research-harvard/AmericanStories/resolve/$REV/faro_1872.tar.gz"
  [ "$(shasum -a 256 "$D/raw/faro_1872.tar.gz.part" | cut -d' ' -f1)" = "$ARCHIVE_SHA" ] || { echo "archive hash mismatch"; exit 1; }
  mv "$D/raw/faro_1872.tar.gz.part" "$D/raw/faro_1872.tar.gz"
  log "$D/raw/faro_1872.tar.gz" ;;
extract)
  python3 -I bin/extract_window.py "$D/raw/faro_1872.tar.gz" 1872-02-01 1872-03-03 "$D/window.jsonl" > "$D/extract_stats.json"
  python3 -I bin/make_text_view.py "$D/window.jsonl" "$D/window.txt"
  cp "$D/extract_stats.json" results/1872/
  cat "$D/extract_stats.json"
  log "$D/window.jsonl" "$D/window.txt" "$D/extract_stats.json" ;;
base_laya)
  .venv/bin/python -I -c 'import laya; assert laya.__version__ == "0.4.1", laya.__version__'
  # Integrity from content, not cache pointers: laya hashes every listed file before loading any weight.
  digests=$(python3 -I -c 'import json, sys; print(json.dumps(json.load(open(sys.argv[1]))["systems"]["base_laya"]["sha256"]))' freeze/config_1872.json)
  LAYA_SHA256_DIGESTS=$digests LAYA_DEVICE=mps LAYA_REVISION=$BASE_REV HF_HUB_OFFLINE=1 caffeinate -is \
    .venv/bin/python -I bin/laya_score.py freeze/config.json "$D/window.txt" "$D/laya_scores.tsv"
  log "$D/laya_scores.tsv" ;;
ft_score)
  python3 -I -c 'import json, sys
with open(sys.argv[2], "w") as out:
    for n, t in enumerate(open(sys.argv[1]).read().splitlines(), 1):
        out.write(json.dumps({"id": f"L{n}", "line": n, "state": t}) + "\n")' "$D/window.txt" "$D/ft_input.jsonl"
  {
    "${LLM02[@]}" "cd /srv/laya-batch/work/ft && sha256sum ft_run.sh ft_score.py config.json all/model.safetensors all/rl_agent_config.json all/questions.json" < /dev/null
    "${LLM02[@]}" "sudo -n docker image inspect laya-batch:e974cca5eb42 --format '{{.Id}}'; cd /tmp && sudo -n docker compose --project-directory /opt/compose-apps/laya-batch config --images; sudo -n docker compose --project-directory /opt/compose-apps/laya-batch config | grep -c 'LAYA_CUDA_AMP: fp16'" < /dev/null
  } > "$D/ft_remote.txt"
  [ "$(head -6 "$D/ft_remote.txt")" = "$FT_REMOTE_SHA" ] || { echo "llm02 scoring files differ from the frozen hashes"; exit 1; }
  [ "$(sed -n 7,9p "$D/ft_remote.txt")" = "$(printf '%s\nlaya-batch:e974cca5eb42\n1' "$FT_IMAGE_ID")" ] || { echo "laya-batch image or fp16 setting differs"; exit 1; }
  "${LLM02[@]}" "mkdir -p /srv/laya-batch/work/ft1872" < /dev/null
  "${SCP[@]}" "$D/ft_input.jsonl" "$GPU_HOST":/srv/laya-batch/work/ft1872/
  caffeinate -is "${LLM02[@]}" "FT_ENTRY=score bash /srv/laya-batch/work/ft/ft_run.sh score-1872 /work/ft/all /work/ft/config.json /work/ft1872/ft_input.jsonl /work/ft1872/ft_scores.tsv 4096" < /dev/null
  "${SCP[@]}" "$GPU_HOST":/srv/laya-batch/work/ft1872/ft_scores.tsv "$D/ft_scores.tsv"
  log "$D/ft_remote.txt" "$D/ft_input.jsonl" "$D/ft_scores.tsv" ;;
pool)
  bash bin/make_pool_1872.sh freeze/config_1872.json "$D" | tee "$D/pool_counts.txt"
  cp "$D/pool_counts.txt" results/1872/
  log "$D"/flags_{base_laya,ft_laya,strict,fuzzy}.lines "$D/pool.lines" "$D/rg_loose.lines" "$D/net_only.lines" "$D/pool_counts.txt" ;;
labelset)
  python3 -I bin/draw_labelset.py freeze/config_1872.json "$D/window.txt" "$D/pool.lines" "$D/net_only.lines" "$D/labelset" 2> "$D/labelset_draw.txt"
  cat "$D/labelset_draw.txt"
  cp "$D/labelset_draw.txt" "$D/labelset/key.tsv" results/1872/   # line numbers and weights only, no article text
  log "$D/labelset/key.tsv" "$D/labelset/items.jsonl" "$D/labelset_draw.txt" ;;
checker_inputs)
  mkdir -p "$D/checker"
  python3 -I -c 'import json, random, sys
key = {int(r.split()[1]): r.split()[0] for r in list(open(sys.argv[1]))[1:]}
texts = {json.loads(l)["id"]: json.loads(l)["text"] for l in open(sys.argv[2])}
ids = [key[int(x)] for x in open(sys.argv[3]) if x.strip()]   # every fine-tuned flag is in the pool, so labeled
random.Random(1872).shuffle(ids)
with open(sys.argv[4], "w") as out:
    for i in ids:
        out.write(json.dumps({"id": i, "text": texts[i]}) + "\n")' "$D/labelset/key.tsv" "$D/labelset/items.jsonl" "$D/flags_ft_laya.lines" "$D/checker/items.jsonl"
  log "$D/checker/items.jsonl" ;;
qwen)
  ollama_pins "$QWEN" > "$D/checker/qwen_server.txt"
  "${LLM02[@]}" "mkdir -p /srv/laya-batch/work/verify1872" < /dev/null
  "${SCP[@]}" bin/verify_ollama.py freeze/labeler_prompt_1872.md "$D/checker/items.jsonl" "$GPU_HOST":/srv/laya-batch/work/verify1872/
  caffeinate -is "${LLM02[@]}" "cd /srv/laya-batch/work/verify1872 && OLLAMA_URL=http://127.0.0.1:11434 VERIFY_MODEL=qwen3.8:27b-q4_K_M VERIFY_THINK=1 VERIFY_CTX=131072 python3 -I verify_ollama.py labeler_prompt_1872.md items.jsonl qwen.tsv" < /dev/null
  "${SCP[@]}" "$GPU_HOST":/srv/laya-batch/work/verify1872/qwen.tsv "$D/checker/qwen.tsv"
  log "$D/checker/qwen_server.txt" "$D/checker/qwen.tsv" ;;
opus_checker_render)
  claude_version
  python3 -I bin/make_batches.py "$D/checker/items.jsonl" "$D/checker/opus_batches" 60000
  python3 -I bin/render_agent_prompts.py checker "$D/checker/opus_batches" "$SB/checker" --agents 4
  log "$D/checker/opus_batches"/b*.txt "$SB/checker"/_prompts/*.md "$SB/checker/_owners.tsv" ;;
opus_checker_run)
  claude_version
  caffeinate -is python3 -I bin/run_agents.py "$SB/checker" "$OPUS" "$D/checker/opus_batches" --parallel 4 --columns 2 \
    --stage-run "$stage_run" --max-stage-runs "$MAX_STAGE_RUNS"
  log "$SB/checker/agents.tsv" "$SB/checker/_verified.tsv" ;;
opus_checker_collect)
  collect checker "$D/checker/opus_batches" "$D/checker/opus" 2
  shopt -s nullglob; f=("$D/checker/opus"/b*.tsv); shopt -u nullglob   # no verified batch: an empty file, not an abort
  cat /dev/null ${f[@]+"${f[@]}"} > "$D/checker/opus.tsv"
  log "$D/checker/opus.tsv" "$D/checker_failed_ids.txt" ;;
label_render)
  claude_version
  python3 -I bin/make_batches.py "$D/labelset/items.jsonl" "$D/labelset/claude_batches" 60000
  python3 -I bin/render_agent_prompts.py labeler "$D/labelset/claude_batches" "$SB/labeler"
  log "$D/labelset/claude_batches"/b*.txt "$SB/labeler"/_prompts/*.md "$SB/labeler/_owners.tsv" ;;
label_run)
  claude_version
  caffeinate -is python3 -I bin/run_agents.py "$SB/labeler" "$SONNET" "$D/labelset/claude_batches" --parallel 6 --columns 2 \
    --stage-run "$stage_run" --max-stage-runs "$MAX_STAGE_RUNS"
  log "$SB/labeler/agents.tsv" "$SB/labeler/_verified.tsv" ;;
label_collect)
  collect labeler "$D/labelset/claude_batches" "$D/labels/claude" 2
  log "$D/labels/claude"/b*.tsv "$D/labeler_failed_ids.txt" ;;
gemma)
  mkdir -p "$D/labels"
  ollama_pins "$GEMMA" > "$D/labels/gemma_server.txt"
  LLM_KEY=$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null) \
  GEMMA_BASE=$GATEWAY_URL GEMMA_MODEL=gemma4:26b-a4b-it-mtp-q4_K_M GEMMA_CONTEXT=131072 \
  GEMMA_WORKERS=1 GEMMA_MAX_TOKENS=4096 caffeinate -is .venv/bin/python -I bin/label_gemma.py \
    freeze/labeler_prompt_1872.md "$D/labelset/items.jsonl" "$D/labels/gemma.tsv" 2> "$D/labels/gemma_run.log"
  "${LLM02[@]}" "curl -s -m5 127.0.0.1:11434/api/ps" < /dev/null >> "$D/labels/gemma_server.txt"
  log "$D/labels/gemma_server.txt" "$D/labels/gemma.tsv" "$D/labels/gemma_run.log" ;;
check)
  python3 -I bin/check_labels.py "$D/labelset" "$D/labels" | tee "$D/labels/check.txt"
  log "$D/labels/check.txt" ;;
adjudication_render)
  claude_version
  python3 -I bin/make_adjudication.py freeze/config_1872.json freeze/labeler_prompt_1872.md "$D/labelset" "$D/labels" "$D/adjudication"
  python3 -I -c 'import json, sys
ids = [l.split("\t")[0] for l in open(sys.argv[1])][1:]
texts = {json.loads(l)["id"]: json.loads(l)["text"] for l in open(sys.argv[2])}
with open(sys.argv[3], "w") as out:
    for i in ids:
        out.write(json.dumps({"id": i, "text": texts[i]}) + "\n")' "$D/adjudication/manifest.tsv" "$D/labelset/items.jsonl" "$D/adjudication/opus_items.jsonl"
  python3 -I bin/make_batches.py "$D/adjudication/opus_items.jsonl" "$D/adjudication/opus_batches" 45000
  python3 -I bin/render_agent_prompts.py adjudicator "$D/adjudication/opus_batches" "$SB/adjudicator"
  log "$D/adjudication/manifest.tsv" "$D/adjudication/opus_batches"/b*.txt "$SB/adjudicator"/_prompts/*.md "$SB/adjudicator/_owners.tsv" ;;
adjudication_run)
  claude_version
  caffeinate -is python3 -I bin/run_agents.py "$SB/adjudicator" "$OPUS" "$D/adjudication/opus_batches" --parallel 5 --columns 3 \
    --stage-run "$stage_run" --max-stage-runs "$MAX_STAGE_RUNS"
  log "$SB/adjudicator/agents.tsv" "$SB/adjudicator/_verified.tsv" ;;
adjudication_collect)
  collect adjudicator "$D/adjudication/opus_batches" "$D/adjudication/opus" 3
  shopt -s nullglob; f=("$D/adjudication/opus"/b*.tsv); shopt -u nullglob
  cat /dev/null ${f[@]+"${f[@]}"} > "$D/adjudication/adjudication_opus.tsv"
  log "$D/adjudication/adjudication_opus.tsv" "$D/adjudicator_failed_ids.txt" ;;
score)
  python3 -I bin/score_1872.py "$D" results/1872/results.md --seed 1872 --adjudication "$D/adjudication/adjudication_opus.tsv" \
    --system base_laya=lines:"$D/flags_base_laya.lines" --system strict=lines:"$D/flags_strict.lines" \
    --system fuzzy=lines:"$D/flags_fuzzy.lines" --system ft_laya=lines:"$D/flags_ft_laya.lines" \
    --checker ft+qwen=ft_laya:"$D/checker/qwen.tsv" --checker ft+opus=ft_laya:"$D/checker/opus.tsv" \
    --h1 ft_laya --strict strict --fuzzy fuzzy
  log results/1872/results.md ;;
audit)
  mkdir -p "$D/audit"
  python3 -I bin/draw_audit.py storm "$D" "$D/audit/items_1872.jsonl" "$D/audit/sample_1872.tsv" --size 250 --seed 1872 \
    --ft "$D/flags_ft_laya.lines" --keyword "$D/flags_strict.lines" --keyword "$D/flags_fuzzy.lines" --base "$D/flags_base_laya.lines"
  python3 -I bin/make_audit_page.py freeze/labeler_prompt_1872.md "$D/audit/items_1872.jsonl" "$D/audit/page_1872" --set 1872 --repeats 10 --seed 1872
  python3 -I bin/make_audit_page.py freeze/labeler_prompt.md results/audit/items_1859.jsonl "$D/audit/page_1859" --set 1859 --repeats 10 --seed 1872
  cp "$D/audit/sample_1872.tsv" results/1872/
  log "$D/audit/sample_1872.tsv" "$D/audit/page_1872/audit.html" "$D/audit/page_1872/audit_key.tsv" \
      "$D/audit/page_1859/audit.html" "$D/audit/page_1859/audit_key.tsv" ;;
esac
