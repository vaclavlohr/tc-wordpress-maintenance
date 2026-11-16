#!/usr/bin/env bash
# Run this script as the Git checkout owner (normally lohr), not as root.
set -Eeuo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ -d "$DIR/.git" ]] || { echo "ERROR: $DIR is not a Git checkout." >&2; exit 1; }
command -v git >/dev/null || { echo 'ERROR: git is not installed.' >&2; exit 1; }
[[ -z "$(git -C "$DIR" status --porcelain --untracked-files=no)" ]] || {
    echo 'ERROR: Working tree contains local changes. Commit/stash or resolve them first.' >&2
    exit 1
}
git -C "$DIR" pull --ff-only
if [[ $EUID -eq 0 ]]; then
    bash "$DIR/update-server.sh"
else
    sudo bash "$DIR/update-server.sh"
fi
