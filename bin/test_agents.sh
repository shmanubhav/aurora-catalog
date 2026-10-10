#!/usr/bin/env bash
# Offline tests for bin/run_agents.py, bin/collect_agents.py and bin/check_labels.py with a stand-in `claude`.
# Covers: resume asks only for missing batches and keeps attested answers; exit 3 until the final stage run, which
# sends failures to the MISSING rule; a changed attested answer, another model or a proxy variable stops the run;
# agents get --restricted and the trimmed environment. Exits non-zero on any mismatch.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d)
mkdir -p "$T/bin" "$T/batches"
printf '===== a1 =====\ntext one\n===== a2 =====\ntext two\n' > "$T/batches/b001.txt"; printf 'a1\na2\n' > "$T/batches/b001.ids"
printf '===== a3 =====\ntext three\n' > "$T/batches/b002.txt"; printf 'a3\n' > "$T/batches/b002.ids"
cat > "$T/bin/claude" <<FAKE
#!/bin/bash
cat > /dev/null
mode=\$(cat "$T/mode")
basename "\$PWD" >> "$T/calls"
env | cut -d= -f1 | sort > "$T/env_seen"; echo "\$@" > "$T/args_seen"
model=claude-sonnet-5-5; [ "\$mode" = wrongmodel ] && model=claude-haiku-5-5
for t in b*.txt; do
  b=\${t%.txt}
  [ "\$mode" = failb002 ] && [ "\$b" = b002 ] && continue
  grep -o '===== a[0-9]* =====' "\$t" | awk '{print \$2"\tNO"}' > "\$b.tsv"
done
printf '{"modelUsage":{"%s":{}},"total_cost_usd":0,"permission_denials":[]}\n' "\$model"
FAKE
chmod +x "$T/bin/claude"
fail() { echo "FAIL: $1"; exit 1; }
agents() { rc=0; PATH="$T/bin:$PATH" python3 -I "$here/run_agents.py" "$@" --columns 2 2> "$T/err" || rc=$?; }
render() { python3 -I "$here/render_agent_prompts.py" labeler "$T/batches" "$T/$1" 2> /dev/null; }

render sb1; echo failb002 > "$T/mode"
agents "$T/sb1" claude-sonnet-5-5 "$T/batches" --stage-run 1
[ "$rc" = 3 ] || fail "incomplete first stage run should exit 3, got $rc"
[ "$(cut -f2 "$T/sb1/_verified.tsv")" = b001 ] || fail "only b001 should be attested after run 1"
h1=$(grep b001 "$T/sb1/_verified.tsv")
: > "$T/calls"; echo ok > "$T/mode"
agents "$T/sb1" claude-sonnet-5-5 "$T/batches" --stage-run 2
[ "$rc" = 0 ] || fail "complete second run should exit 0, got $rc"
[ "$(cat "$T/calls")" = b002 ] || fail "the re-run should ask only b002, asked: $(tr '\n' ' ' < "$T/calls")"
[ "$(grep b001 "$T/sb1/_verified.tsv")" = "$h1" ] || fail "b001 attestation changed on resume"
[ "$(wc -l < "$T/sb1/_verified.tsv" | tr -d ' ')" = 2 ] || fail "attestations not merged"
grep -q -- '--restricted' "$T/args_seen" || fail "agent not started with --restricted"
grep -qx CLAUDE_CODE_DISABLE_AUTO_MEMORY "$T/env_seen" || fail "auto memory not disabled"
! grep -q -E '^(CLAUDE_CODE_SESSION_ID|CLAUDE_CODE_MESSAGING_TOKEN|CLAUDECODE)$' "$T/env_seen" || fail "session variables leaked to the agent"
echo "resume: only the missing batch re-asked, attestation kept; agents get --restricted and a trimmed environment"

mkdir -p "$T/sb1/_attempts/b001.run9.before1"; mv "$T/sb1/b001/b001.tsv" "$T/sb1/_attempts/b001.run9.before1/"
: > "$T/calls"
agents "$T/sb1" claude-sonnet-5-5 "$T/batches" --stage-run 3
[ "$rc" = 0 ] || fail "a run interrupted after attesting should resume, got $rc: $(cat "$T/err")"
[ ! -s "$T/calls" ] || fail "a fully attested sandbox should start no agent"
[ "$(grep b001 "$T/sb1/_verified.tsv")" = "$h1" ] && [ -f "$T/sb1/b001/b001.tsv" ] || fail "attested answer not restored from _attempts"
grep -q "taken from _attempts" "$T/err" || fail "using an _attempts copy must print a notice"
printf 'changed\tYES\n' >> "$T/sb1/b001/b001.tsv"
agents "$T/sb1" claude-sonnet-5-5 "$T/batches" --stage-run 3
[ "$rc" = 0 ] && [ "$(grep b001 "$T/sb1/_verified.tsv")" = "$h1" ] || fail "an intact attested copy should be used"
ls "$T/sb1/b001/" | grep -q 'b001.tsv.changed-run' || fail "the differing folder copy must be kept aside"
echo "interrupted runs resume from the attested copy; a differing folder copy is kept aside with a notice"
for f in "$T/sb1/b001/b001.tsv" "$T"/sb1/_attempts/*/b001.tsv; do printf 'tampered\tYES\n' >> "$f"; done
agents "$T/sb1" claude-sonnet-5-5 "$T/batches" --stage-run 3
[ "$rc" = 1 ] && grep -q "changed since it was verified" "$T/err" || fail "a changed attested answer with no intact copy must stop the run"

render sb2; echo failb002 > "$T/mode"
agents "$T/sb2" claude-sonnet-5-5 "$T/batches" --attempts 1 --stage-run 3 --max-stage-runs 3
[ "$rc" = 0 ] || fail "final stage run should exit 0 and leave failures to the rules, got $rc"
python3 -I "$here/collect_agents.py" labeler "$T/sb2" "$T/batches" "$T/labels/claude" 2 "$T/failed.txt" 2> /dev/null
[ "$(cat "$T/labels/claude/b002.tsv")" = "$(printf 'a3\tMISSING')" ] || fail "failed batch should be MISSING"
mkdir -p "$T/labelset"; cp -R "$T/batches" "$T/labelset/claude_batches"
printf 'id\tline\tstratum\tweight\na1\t1\tpool\t1\na2\t2\tpool\t1\na3\t3\tpool\t1\n' > "$T/labelset/key.tsv"
printf 'a1\tYES\na2\tNO\na3\tYES\n' > "$T/labels/gemma.tsv"
python3 -I "$here/check_labels.py" "$T/labelset" "$T/labels" > "$T/check.txt" || fail "check_labels must accept MISSING: $(cat "$T/check.txt")"
grep -q 'claude MISSING (Sonnet batch failed every attempt, to adjudication): 1' "$T/check.txt" || fail "MISSING count not reported"
echo "final run: failure goes to MISSING, check_labels accepts and counts it"

render sb3; echo wrongmodel > "$T/mode"
agents "$T/sb3" claude-sonnet-5-5 "$T/batches"
[ "$rc" = 1 ] || fail "another model must exit 1, got $rc"
[ ! -s "$T/sb3/_verified.tsv" ] || fail "another model's answers were attested"
render sb4; : > "$T/calls"; echo ok > "$T/mode"
rc=0; ANTHROPIC_BASE_URL=http://127.0.0.1:9 PATH="$T/bin:$PATH" python3 -I "$here/run_agents.py" "$T/sb4" claude-sonnet-5-5 "$T/batches" --columns 2 2> "$T/err" || rc=$?
[ "$rc" = 1 ] && [ ! -s "$T/calls" ] || fail "a proxy variable must stop the run before any agent starts"
echo "another model, a changed attested answer and a proxy variable all stop the run"
