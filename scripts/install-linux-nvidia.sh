#!/usr/bin/env bash
set -euo pipefail

mode="install"

usage() {
  cat <<'EOF'
Usage: ./scripts/install-linux-nvidia.sh [--dry-run|--check-only]

Installs the local big-brother Docker Compose stack on Linux servers with an
existing NVIDIA driver and NVIDIA Container Toolkit. This script does not
install GPU drivers or Kubernetes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      mode="dry-run"
      shift
      ;;
    --check-only)
      mode="check-only"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

has_command() {
  command -v "$1" >/dev/null 2>&1
}

print_missing_toolkit() {
  cat <<'EOF'
Missing prerequisite: NVIDIA Container Toolkit.
Install and configure it before running the stack:
  sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
EOF
}

check_prerequisites() {
  local missing=0

  printf 'Checking prerequisites for Linux/NVIDIA Compose install...\n'

  if [[ "${BIG_BROTHER_FAKE_NO_NVIDIA:-0}" == "1" ]]; then
    print_missing_toolkit
    return 1
  fi

  if has_command docker; then
    printf 'ok: docker found\n'
  else
    printf 'missing: docker CLI\n' >&2
    missing=1
  fi

  if docker compose version >/dev/null 2>&1; then
    printf 'ok: docker compose found\n'
  else
    printf 'missing: docker compose plugin\n' >&2
    missing=1
  fi

  if has_command nvidia-smi; then
    printf 'ok: NVIDIA driver visible through nvidia-smi\n'
  else
    printf 'missing: nvidia-smi; install a supported NVIDIA driver first\n' >&2
    missing=1
  fi

  if has_command nvidia-ctk; then
    printf 'ok: NVIDIA Container Toolkit found\n'
  else
    print_missing_toolkit >&2
    missing=1
  fi

  return "$missing"
}

print_install_commands() {
  cat <<'EOF'
Planned install commands:
  cp .env.example .env  # edit BIG_BROTHER_ADMIN_TOKEN before production use
  docker compose pull
  docker compose up -d --build
  ./scripts/health-check.sh
EOF
}

case "$mode" in
  dry-run)
    check_prerequisites || true
    print_install_commands
    ;;
  check-only)
    check_prerequisites
    ;;
  install)
    check_prerequisites
    if [[ ! -f .env ]]; then
      cp .env.example .env
      printf 'created .env from .env.example; edit admin token before production use\n'
    fi
    docker compose pull
    docker compose up -d --build
    ./scripts/health-check.sh
    ;;
esac
