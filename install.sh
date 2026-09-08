#!/usr/bin/env bash
# install.sh — 풋페달 브릿지 1회 설치 (Ubuntu)
#
#   bash install.sh          <- sudo 를 붙이지 마세요
#
# sudo 로 실행하면 evdev 가 conda/venv 가 아닌 시스템 파이썬에 설치되어
# 브릿지가 의존성을 못 찾습니다. 이 스크립트가 필요한 곳에서만 sudo 를 씁니다.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PEDAL_PATH="/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd"

if [[ $EUID -eq 0 ]]; then
  echo "sudo 없이 실행하세요:  bash install.sh" >&2
  echo "(root 로 돌리면 파이썬 의존성이 엉뚱한 곳에 설치됩니다)" >&2
  exit 1
fi

echo "=== [1/5] 파이썬 의존성 (evdev) ==="
python3 -m pip install -r "$HERE/requirements.txt"

echo
echo "=== [2/5] uinput 커널 모듈 (가상 키보드 생성용) ==="
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
echo "부팅 시 자동 로드되도록 등록했습니다."

echo
echo "=== [3/5] udev 규칙 (페달 + /dev/uinput 권한) ==="
sudo install -m 0644 "$HERE/udev/99-footpedal.rules" /etc/udev/rules.d/99-footpedal.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "설치됨: /etc/udev/rules.d/99-footpedal.rules"

echo
echo "=== [4/5] input 그룹에 사용자 추가 ==="
if id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  echo "'$USER' 는 이미 input 그룹입니다."
else
  sudo usermod -aG input "$USER"
  echo "'$USER' 를 input 그룹에 추가했습니다."
fi

echo
echo "=== [5/5] 설치 확인 ==="
FAIL=0

if python3 -c "import evdev" 2>/dev/null; then
  echo "  [OK]   evdev 임포트 가능"
else
  echo "  [실패] evdev 를 임포트할 수 없습니다 (python3 -m pip install evdev)"
  FAIL=1
fi

if [[ -e /dev/uinput ]]; then
  echo "  [OK]   /dev/uinput 존재  ($(stat -c '%G %a' /dev/uinput))"
else
  echo "  [실패] /dev/uinput 이 없습니다 (sudo modprobe uinput)"
  FAIL=1
fi

if [[ -e "$PEDAL_PATH" ]]; then
  echo "  [OK]   페달 인식됨  $PEDAL_PATH"
elif compgen -G "/dev/input/by-id/*FootSwitch*event-kbd" >/dev/null; then
  echo "  [OK]   페달 인식됨  $(ls /dev/input/by-id/*FootSwitch*event-kbd | head -1)"
else
  echo "  [주의] 페달을 찾지 못했습니다. USB 를 꽂았는지 확인하세요."
  echo "         (지금 안 꽂았을 뿐이면 무시해도 됩니다)"
fi

if id -nG | tr ' ' '\n' | grep -qx input; then
  echo "  [OK]   현재 세션에 input 그룹 적용됨"
  GROUP_READY=1
else
  echo "  [대기] input 그룹이 아직 이 세션에 반영되지 않았습니다"
  GROUP_READY=0
fi

echo
if [[ $FAIL -ne 0 ]]; then
  echo "설치 중 실패한 항목이 있습니다. 위 [실패] 줄을 확인하세요."
  exit 1
fi

echo "설치 완료."
if [[ $GROUP_READY -eq 0 ]]; then
  echo
  echo "마지막 한 단계 — input 그룹을 반영해야 합니다. 둘 중 하나:"
  echo "  A) 로그아웃 후 재로그인 (권장, 모든 터미널에 적용)"
  echo "  B) 지금 이 터미널만 즉시 적용:   newgrp input"
fi
echo
echo "그다음 동작 확인:"
echo "  python3 pedal_bridge.py"
echo "  (텍스트 편집기를 클릭한 뒤 페달을 밟아 n / r / q 가 찍히는지 확인)"
