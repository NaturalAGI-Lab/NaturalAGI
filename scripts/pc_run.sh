#!/bin/bash
# pc_run.sh <job> <dir> <command...>
# Copies <dir> to the GPU PC, runs the command there in tmux session <job> and streams its log live.
# The command runs inside the copy of <dir> and writes its results into out/. When it ends, out/ and
# logs/ (run.log, exit) are copied back into <dir>, and the script exits with the command's exit code.
# Windows stays awake from the upload until the copy-back ends.
# Before the upload it waits until the PC runs no gd-* tmux session and uses less than
# ${PC_GPU_FREE_MIB:-2048} MiB of VRAM, so a job never starts on top of a Golden Delta render.
# Host: ${PC_HOST:-gd-wsl}. Remote folder: ${PC_JOBS:-naturalagi-jobs}/<job> under the PC's $HOME.
set -eu

host="${PC_HOST:-gd-wsl}"
jobs_root="${PC_JOBS:-naturalagi-jobs}"
gpu_limit="${PC_GPU_FREE_MIB:-2048}"

usage() {
  echo "usage: pc_run.sh <job> <dir> <command...>" >&2
  exit 2
}

[ $# -ge 3 ] || usage
job="$1"
dir="$2"
shift 2
case "$job" in
  '' | *[!A-Za-z0-9_-]*) echo "not a job name: $job (use letters, digits, _ and -)" >&2; exit 2 ;;
esac
[ -d "$dir" ] || { echo "no such folder: $dir" >&2; exit 2; }
dir="$(cd "$dir" && pwd)"
remote="$jobs_root/$job"

session_state() {
  local status=0
  ssh -o ConnectTimeout=10 "$host" "tmux has-session -t '=$job'" >/dev/null 2>&1 || status=$?
  case "$status" in
    0) echo running ;;
    1) echo ended ;;
    *) echo unreachable ;;
  esac
}

case "$(session_state)" in
  running)
    echo "tmux session $job is still running on $host: wait for it to end" >&2
    exit 1
    ;;
  unreachable)
    echo "cannot reach $host over ssh: run make pc_wake" >&2
    exit 1
    ;;
esac

# Prints "<gd-* session count> <VRAM used in MiB>", or nothing when ssh fails.
gpu_state() {
  ssh -o ConnectTimeout=10 "$host" \
    "echo \$(tmux ls -F '#{session_name}' 2>/dev/null | grep -c '^gd-') \$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1)" \
    2>/dev/null || true
}

# Windows desktop alone holds about 1 GB of VRAM after a wake, hence the 2048 MiB default.
last_state=""
failures=0
while :; do
  state="$(gpu_state)"
  if [ -z "$state" ]; then
    failures=$((failures + 1))
    if [ "$failures" -ge 5 ]; then
      echo "lost $host while waiting for its GPU: run make pc_wake" >&2
      exit 1
    fi
  else
    failures=0
    read -r gd_sessions vram <<< "$state"
    case "${vram:-}" in
      '' | *[!0-9]*) vram=unknown ;;
    esac
    if [ "$gd_sessions" = 0 ] && [ "$vram" != unknown ] && [ "$vram" -lt "$gpu_limit" ]; then
      break
    fi
    if [ "$state" != "$last_state" ]; then
      echo "waiting for the GPU on $host: $gd_sessions gd-* tmux sessions, $vram MiB VRAM used (limit $gpu_limit)"
      last_state="$state"
    fi
  fi
  sleep 60
done

work="$(mktemp -d "${TMPDIR:-/tmp}/pc-run.XXXXXX")"
trap 'rm -rf "$work"' EXIT

# Windows sleeps after 30 minutes without keyboard or mouse input, so it went down the moment the job's own
# gd-awake let go, before the copy-back. This second gd-awake spans the whole run: its remote cat reads fd 4
# of this script and ends, letting Windows go, when the script exits however it exits.
mkfifo "$work/awake"
ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "$host" '$HOME/.local/bin/gd-awake cat > /dev/null' < "$work/awake" &
exec 4> "$work/awake"

quoted=""
for arg in "$@"; do
  quoted="$quoted $(printf '%q' "$arg")"
done

# The runner executes on the host, inside the tmux session.
{
  echo '#!/bin/bash'
  echo 'export PATH="$HOME/.local/bin:$PATH"'
  echo 'cd "$(dirname "$0")"'
  echo 'rm -rf out logs'
  echo 'mkdir -p out logs'
  # The PC sleeps after 30 idle minutes and WSL load does not count; gd-awake holds Windows up while the command runs.
  echo "gd-awake$quoted > logs/run.log 2>&1"
  echo 'echo $? > logs/exit'
} > "$work/.pc_run.sh"
chmod +x "$work/.pc_run.sh"

ssh "$host" "mkdir -p '$remote'"
rsync -a --exclude='/out/' --exclude='/logs/' --exclude='.venv/' --exclude='__pycache__/' "$dir/" "$host:$remote/"
rsync -a "$work/.pc_run.sh" "$host:$remote/.pc_run.sh"

started="$(date +%s)"
ssh "$host" "tmux new-session -d -s '$job' \"bash \$HOME/$remote/.pc_run.sh\""
echo "job started: $host tmux $job"
echo "attach: ssh -t $host tmux attach -t $job"

stream() {
  ssh -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "$host" "
    pid=\$(tmux list-panes -s -t '=$job' -F '#{pane_pid}' 2>/dev/null | head -n 1)
    cd '$remote' || exit 1
    if [ -n \"\$pid\" ]; then
      exec tail -n $1 -F --pid=\$pid logs/run.log 2>/dev/null
    elif [ '$1' = '+1' ]; then
      cat logs/run.log 2>/dev/null
    fi"
}

tail_from='+1'
failures=0
while :; do
  stream "$tail_from" || true
  tail_from=0
  while :; do
    case "$(session_state)" in
      ended) break 2 ;;
      running)
        failures=0
        sleep 1
        break
        ;;
      *)
        failures=$((failures + 1))
        if [ "$failures" -ge 12 ]; then
          echo "lost $host: 12 checks in a row failed. tmux session $job keeps running there; fetch the results later with:" >&2
          echo "  rsync -a --delete $host:$remote/out/ $dir/out/" >&2
          echo "  rsync -a --delete $host:$remote/logs/ $dir/logs/" >&2
          exit 1
        fi
        sleep 5
        ;;
    esac
  done
done

elapsed=$(( $(date +%s) - started ))
mkdir -p "$dir/out" "$dir/logs"
rsync -a --delete "$host:$remote/out/" "$dir/out/"
rsync -a --delete "$host:$remote/logs/" "$dir/logs/"

code="$(cat "$dir/logs/exit" 2>/dev/null || true)"
echo "job $job finished in $elapsed s, exit code ${code:-missing}"
[ "${code:-missing}" = 0 ]
