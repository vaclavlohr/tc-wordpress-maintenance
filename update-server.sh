#!/usr/bin/env bash
# Run from a checked-out or extracted source directory; no network needed.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'ERROR: Run as root via sudo.' >&2; exit 1; }
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$DIR/install.sh" && -f "$DIR/tc-wp-maintenance" ]] || {
    echo "ERROR: Missing maintenance files under $DIR" >&2
    exit 1
}
echo "Deploying source files from: $DIR"
bash "$DIR/install.sh"
echo
echo 'Running read-only verification; this also sends a report to both e-mail addresses:'
/usr/local/sbin/tc-wp-maintenance --check
echo
echo 'Deployment completed. Existing timer was not enabled or disabled.'
