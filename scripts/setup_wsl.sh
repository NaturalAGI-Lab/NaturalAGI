#!/usr/bin/env bash
# One-time setup of an Ubuntu WSL2 distro for NaturalAGI on a weak Windows laptop.
# Installs Docker Engine *inside* WSL (no Docker Desktop: saves ~1.5 GB of RAM), nuctl, uv, make.
# Usage (inside Ubuntu, from the repo root):  bash scripts/setup_wsl.sh
set -euo pipefail

NUCTL_VERSION="${NUCTL_VERSION:-1.15.20}"

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "This script is meant for WSL2 (Ubuntu). On plain Linux install docker, nuctl and uv yourself." >&2
  exit 1
fi

case "$(pwd)" in
  /mnt/*) echo "WARNING: the repo is on a Windows drive ($(pwd)). Clone it into ~ inside WSL: /mnt/c is 5-10x slower and breaks line endings." >&2 ;;
esac

echo "==> apt packages"
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends ca-certificates curl git make unzip python3 python3-venv

if docker version >/dev/null 2>&1 && docker info 2>/dev/null | grep -qi "docker desktop"; then
  echo "==> Docker Desktop integration detected; keeping it (consider quitting Docker Desktop and re-running to save RAM)."
elif ! command -v dockerd >/dev/null 2>&1; then
  echo "==> Docker Engine"
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER" || true

# Docker needs systemd (or a manual `sudo service docker start` after every WSL start).
if [ "$(ps -p 1 -o comm= 2>/dev/null)" != "systemd" ]; then
  if ! grep -q "systemd *= *true" /etc/wsl.conf 2>/dev/null; then
    printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf >/dev/null
  fi
  NEED_RESTART=1
else
  sudo systemctl enable --now docker
fi

echo "==> nuctl ${NUCTL_VERSION}"
if ! command -v nuctl >/dev/null 2>&1 || ! nuctl version 2>/dev/null | grep -q "${NUCTL_VERSION}"; then
  sudo curl -fsSL -o /usr/local/bin/nuctl \
    "https://github.com/nuclio/nuclio/releases/download/${NUCTL_VERSION}/nuctl-${NUCTL_VERSION}-linux-amd64"
  sudo chmod +x /usr/local/bin/nuctl
fi

echo "==> uv"
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

echo "==> make profile"
[ -f local.mk ] || echo "PROFILE = lowspec" > local.mk
grep -q "MLFLOW_TRACKING_URI" "$HOME/.bashrc" || echo 'export MLFLOW_TRACKING_URI=file:./mlruns' >> "$HOME/.bashrc"

echo
if [ "${NEED_RESTART:-0}" = "1" ]; then
  echo "Done, but systemd was just enabled. In Windows PowerShell run:  wsl --shutdown"
  echo "then reopen Ubuntu, cd back here and run:  make doctor"
else
  echo "Done. Close and reopen the terminal (docker group), then run:  make doctor"
fi
