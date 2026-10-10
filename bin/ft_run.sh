#!/usr/bin/env bash
# Run one Laya training job in the laya-batch app on llm02 under the approved run rules.
# Usage (on llm02, as app): bash ft_run.sh RUN_NAME [train_cli args...]; FT_ENTRY=score runs ft_score.py instead.
# Pre-checks: no laya container running, Ollama empty, junction < 60C (waits up to 15 min).
# Watchdog every 10 s: Ollama loads a model, or junction >= 105C / mem >= 104C three times running -> kill.
# Writes /srv/laya-batch/work/ft/RUN_NAME/DONE only after a clean exit; a run with DONE is skipped.
set -u
run=$1; shift
work=/srv/laya-batch/work/ft
dir=$work/$run
log=$work/$run.log
name=laya-ft-$run
gpu=/sys/bus/pci/devices/0000:03:00.0
hw=$(ls -d $gpu/hwmon/hwmon* | head -1)
# Reads fail while the card is runtime-suspended (idle, so cool): temp and vram read 0 then, fan reads "asleep".
temp() { local v; v=$(cat $hw/temp$1_input 2>/dev/null) || v=0; echo $(( v / 1000 )); }   # 2 = junction, 3 = mem
vram() { local v; v=$(cat $gpu/mem_info_vram_used 2>/dev/null) || v=0; echo $(( v / 1048576 )); }
fan() { local r p; r=$(cat $hw/fan1_input 2>/dev/null) && p=$(cat $hw/pwm1 2>/dev/null) && echo "${r}rpm/$(( p * 100 / 255 ))%" || echo asleep; }
ollama_empty() { curl -s -m5 127.0.0.1:11434/api/ps | grep -q '"models":\[\]'; }
say() { echo "$(date +%T) $*" | tee -a "$log"; }

[ -e "$dir/DONE" ] && { echo "SKIP: $run already DONE"; exit 0; }
mkdir -p "$dir"
sudo -n docker ps --format '{{.Names}}' | grep -q '^laya' && { say "ABORT: a laya container is already running"; exit 2; }
ollama_empty || { say "ABORT: Ollama has a model loaded"; exit 3; }
t=$(temp 2) waited=0   # one reading decides and is reported, so a flicker across 60C cannot abort a cooled card
while [ "$t" -ge 60 ] && [ "$waited" -lt 900 ]; do sleep 10; waited=$((waited + 10)); t=$(temp 2); done
[ "$t" -lt 60 ] || { say "ABORT: junction ${t}C after ${waited}s of cooling"; exit 4; }

say "START $run junction=$(temp 2)C mem=$(temp 3)C fan=$(fan) vram=$(vram)MiB args: $*"
start=$(date +%s)
cd /tmp
sudo -n docker compose --project-directory /opt/compose-apps/laya-batch run --rm -T --name "$name" laya \
  python -I $([ "${FT_ENTRY:-train}" = score ] && echo /work/ft/ft_score.py || echo /work/ft/ft_train.py) "$@" < /dev/null >> "$log" 2>&1 &
pid=$!

hot=0 peak=0 killed=""
while kill -0 $pid 2>/dev/null; do
  sleep 10
  v=$(vram); [ "$v" -gt "$peak" ] && peak=$v
  j=$(temp 2) m=$(temp 3)
  if ! ollama_empty; then killed="ollama"; fi
  if [ "$j" -ge 105 ] || [ "$m" -ge 104 ]; then hot=$((hot + 1)); else hot=0; fi
  [ "$hot" -ge 3 ] && killed="thermal j=${j}C m=${m}C fan=$(fan)"
  if [ -n "$killed" ]; then
    say "WATCHDOG: $killed, killing $name"
    sudo -n docker kill "$name" > /dev/null 2>&1
    wait $pid
    exit 5
  fi
  [ $(( ($(date +%s) - start) % 60 )) -lt 10 ] && say "tick junction=${j}C mem=${m}C fan=$(fan) vram=${v}MiB"
done
wait $pid; rc=$?
say "END $run rc=$rc wall=$(( $(date +%s) - start ))s peak_vram=${peak}MiB junction=$(temp 2)C fan=$(fan)"
[ "$rc" -eq 0 ] && touch "$dir/DONE"
exit $rc
