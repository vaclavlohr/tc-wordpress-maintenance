#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'ERROR: Run as root (sudo).' >&2; exit 1; }
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for f in tc-wp-maintenance install.sh; do
    bash -n "$DIR/$f"
done
if systemctl is-active --quiet tc-wp-maintenance.service; then
    echo 'ERROR: Maintenance service is currently running. Try again after completion.' >&2
    exit 1
fi
STAMP="$(date +%Y%m%d-%H%M%S)"
SAFE_DIR="/var/backups/tc-wordpress/updater-installs/$STAMP"
install -d -o root -g root -m 700 "$SAFE_DIR"
for file in /usr/local/sbin/tc-wp-maintenance \
            /etc/systemd/system/tc-wp-maintenance.service \
            /etc/systemd/system/tc-wp-maintenance.timer; do
    [[ -f "$file" ]] && cp -a -- "$file" "$SAFE_DIR/"
done
install -o root -g root -m 750 "$DIR/tc-wp-maintenance" /usr/local/sbin/tc-wp-maintenance
install -o root -g root -m 644 "$DIR/tc-wp-maintenance.service" /etc/systemd/system/tc-wp-maintenance.service
install -o root -g root -m 644 "$DIR/tc-wp-maintenance.timer" /etc/systemd/system/tc-wp-maintenance.timer
systemctl daemon-reload
printf 'Installed. Previous configuration backed up under %s\n' "$SAFE_DIR"
echo 'Timer state unchanged. Verify with:'
echo '  /usr/local/sbin/tc-wp-maintenance --check'
echo '  systemctl list-timers --all | grep tc-wp'
