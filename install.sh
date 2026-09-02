#!/usr/bin/env bash
# install.sh — one-time setup so the pedal bridge runs WITHOUT sudo.
#
#   sudo ./install.sh
#
# Adds you to the 'input' group, installs the udev rule that opens the pedal
# and /dev/uinput to that group, and makes the uinput kernel module load at
# boot. Log out and back in (or reboot) afterwards for the group to take hold.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo:  sudo ./install.sh"
  exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"

echo "Installing udev rule..."
install -m 0644 "$HERE/udev/99-norimate-pedal.rules" /etc/udev/rules.d/99-norimate-pedal.rules

echo "Adding '$TARGET_USER' to the 'input' group..."
usermod -aG input "$TARGET_USER"

echo "Enabling the uinput kernel module at boot..."
echo uinput > /etc/modules-load.d/uinput.conf
modprobe uinput

echo "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

echo
echo "Done. Log out and back in (or reboot) for the group change to take effect."
echo "Then verify with:  groups   (you should see 'input')"
