#!/usr/bin/env bash
set -euo pipefail

CGROUP_ROOT="/sys/fs/cgroup/exam-resource-manager"
OWNER="${SUDO_USER:-$USER}"

if [[ ! -f /sys/fs/cgroup/cgroup.controllers ]]; then
  echo "Error: cgroup v2 is not mounted." >&2
  exit 1
fi

if ! grep -qw memory /sys/fs/cgroup/cgroup.controllers; then
  echo "Error: the cgroup v2 memory controller is unavailable." >&2
  exit 1
fi

if ! grep -qw memory /sys/fs/cgroup/cgroup.subtree_control; then
  echo +memory > /sys/fs/cgroup/cgroup.subtree_control
fi

mkdir -p "$CGROUP_ROOT"
if ! grep -qw memory "$CGROUP_ROOT/cgroup.subtree_control"; then
  echo +memory > "$CGROUP_ROOT/cgroup.subtree_control"
fi
mkdir -p "$CGROUP_ROOT/restricted" "$CGROUP_ROOT/protected"
chown -R "$OWNER":"$OWNER" "$CGROUP_ROOT"

echo "Managed exam cgroups are ready at $CGROUP_ROOT"
echo "Owner: $OWNER"
