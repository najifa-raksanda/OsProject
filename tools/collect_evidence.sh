#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-evidence}"
mkdir -p "$OUTPUT_DIR"

{
  echo "Collected: $(date --iso-8601=seconds)"
  echo "Git revision: $(git rev-parse HEAD 2>/dev/null || echo unavailable)"
  echo "Git branch: $(git branch --show-current 2>/dev/null || echo unavailable)"
  echo
  uname -a
  echo
  python3 --version
  echo
  grep -E 'MemTotal|MemAvailable' /proc/meminfo || true
  echo
  cat /proc/pressure/memory 2>/dev/null || echo "Memory PSI unavailable"
  echo
  if [[ -f /sys/fs/cgroup/cgroup.controllers ]]; then
    echo "cgroup v2 controllers: $(cat /sys/fs/cgroup/cgroup.controllers)"
  else
    echo "cgroup v2 unavailable"
  fi
} > "$OUTPUT_DIR/system-info.txt"

python3 -m pytest -q | tee "$OUTPUT_DIR/pytest.txt"
echo "Evidence written to $OUTPUT_DIR"
