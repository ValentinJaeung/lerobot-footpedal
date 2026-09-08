# lerobot-footpedal

텔레오퍼레이션 중 **양손이 로봇 팔에 묶여 있을 때**, 3구 USB 풋페달로 녹화 흐름을 제어하는 브릿지.

[LeRobot](https://github.com/huggingface/lerobot)의 `lerobot-record`는 이미 키보드로 에피소드를
제어하도록 만들어져 있다. 이 도구는 그 키를 **발로 대신 눌러줄 뿐**이라 LeRobot을 한 줄도 고치지 않는다.

| 페달 | 보내는 키 | 동작 |
|------|----------|------|
| 왼쪽 | `r` (←) | 현재 에피소드를 버리고 **다시 녹화** |
| 중앙 | `q` (ESC) | **종료** · 영상 인코딩 · 저장 — **두 번 탭해야 발동** |
| 오른쪽 | `n` (→) | 저장하고 **다음 에피소드** |

```
[USB 페달] --a/b/c--> [pedal_bridge.py] --n/r/q--> [lerobot-record]
                       독점 점유 + 디바운스 + 더블탭 확인
```

LeRobot이 아니어도 된다. **키보드 입력을 받는 프로그램이면 무엇이든** 붙일 수 있다.

---

## 준비물

- **Ubuntu** (22.04 / 24.04에서 확인). evdev·uinput은 리눅스 커널 기능이라 Windows·macOS에서는 동작하지 않는다.
- **PCsensor 3구 풋페달** (USB ID `3553:b001`). 이 제품 기준으로 고정돼 있다.
- Python 3 (conda·venv 무관)
- `sudo` 권한 1회

> 다른 제품을 쓴다면 [다른 페달 쓰기](#다른-페달-쓰기)를 참고. 수정할 곳이 3군데다.

---

## 설치

### 1단계 — 페달을 USB에 꽂는다

포트 번호를 찾을 필요는 없다. 브릿지가 `/dev/input/by-id/`에서 알아서 찾는다.
제대로 꽂혔는지만 확인하면 된다.

```bash
lsusb | grep 3553
# Bus 001 Device 00X: ID 3553:b001 PCsensor FootSwitch
```

아무것도 안 나오면 USB를 다시 꽂거나 다른 포트에 꽂아본다.

### 2단계 — 저장소를 받아 설치 스크립트를 돌린다

```bash
git clone https://github.com/ValentinJaeung/lerobot-footpedal.git
cd lerobot-footpedal
bash install.sh
```

> **`sudo bash install.sh` 로 실행하지 말 것.** root로 돌리면 `evdev`가 conda나 venv가 아닌
> 시스템 파이썬에 설치되어, 정작 브릿지를 실행할 때 의존성을 못 찾는다.
> 스크립트가 필요한 곳(모듈 로드·udev·그룹 추가)에서만 알아서 `sudo`를 쓴다.

이 스크립트가 하는 일은 5가지다.

1. `evdev` 설치
2. `uinput` 커널 모듈 로드 + 부팅 시 자동 로드 등록 — 가상 키보드를 만들려면 필요하다
3. udev 규칙 설치 — 페달과 `/dev/uinput`을 `input` 그룹에 열어준다
4. 현재 사용자를 `input` 그룹에 추가 — 이게 있어야 `sudo` 없이 실행된다
5. 위 4가지가 실제로 됐는지 항목별로 확인 후 출력

끝나면 `[OK]` 목록이 뜬다. `[실패]`가 있으면 그 줄의 안내를 따른다.

### 3단계 — input 그룹 반영

리눅스는 그룹 변경을 **새 로그인 세션부터** 적용한다. 둘 중 하나를 택한다.

```bash
# A) 권장 — 로그아웃 후 재로그인 (모든 터미널에 적용, 영구)
# B) 지금 이 터미널만 즉시 적용
newgrp input
```

확인:

```bash
groups | tr ' ' '\n' | grep input      # input 이 나와야 한다
```

여기서 `input`이 안 나오면 다음 단계는 반드시 `PermissionError`로 실패한다.

### 4단계 — 페달 키 굽기 (최초 1회, 이미 돼 있으면 건너뜀)

브릿지는 페달이 `a` / `b` / `c`를 보낸다고 가정한다. PCsensor 페달은 프로그래머블이라
출고 상태가 다를 수 있다. 먼저 지금 뭘 보내는지 확인한다.

```bash
sudo evtest /dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd
# 페달을 하나씩 밟으며 KEY_A / KEY_B / KEY_C 가 나오는지 본다. Ctrl+C 로 종료.
```

`evtest`가 없으면 `sudo apt install evtest`.

`a`/`b`/`c`가 아니라면 [footswitch](https://github.com/rgerganov/footswitch) 도구로 한 번 구워둔다.

```bash
sudo apt install libhidapi-dev
git clone https://github.com/rgerganov/footswitch.git
cd footswitch && make
sudo ./footswitch -1 -k a -2 -k b -3 -k c
```

굽고 나서 `evtest`로 다시 확인한다. 한 번 구우면 페달 자체에 저장되므로 다시 할 필요 없다.

---

## 동작 확인

로봇도 LeRobot도 없이 확인할 수 있다.

```bash
python3 pedal_bridge.py
```

이렇게 뜨면 정상이다.

```
Pedal bridge running on 'PCsensor FootSwitch'.
  Left = re-record   Center = STOP (tap twice)   Right = next
  Ctrl+C to quit.
```

텍스트 편집기나 빈 터미널을 클릭한 뒤 페달을 밟는다.

- 오른쪽 → `n` 입력됨
- 왼쪽 → `r` 입력됨
- 중앙 → 첫 탭엔 브릿지 터미널에 `STOP armed`만 뜨고, 2초 안에 다시 밟아야 `q` 입력됨
- 원래의 `a` / `b` / `c` 는 **절대 새어 나오지 않는다**
- 같은 페달을 빠르게 두 번 밟아도 한 번만 입력된다

### LeRobot 연동까지 확인 (선택)

LeRobot이 설치돼 있다면, 로봇 없이 LeRobot의 제어 이벤트가 실제로 발동하는지 볼 수 있다.

```bash
python3 pedal_bridge.py          # 터미널 A
python3 test_pedal_lerobot.py    # 터미널 B, 이 창을 포커스한 채로 페달 밟기
```

| 페달 | 떠야 하는 이벤트 |
|------|-----------------|
| 오른쪽 | `exit_early` |
| 왼쪽 | `rerecord_episode` |
| 중앙 (두 번) | `stop_recording` |

`Ctrl+C`로 끝냈을 때 `All three controls fired.` 가 나오면 준비 완료다.

---

## 사용법

### 터미널 2개 (기본)

```bash
# 터미널 A — 브릿지를 띄워둔다
python3 pedal_bridge.py

# 터미널 B — 녹화. 반드시 이 창을 포커스한 채로 페달을 쓴다
lerobot-record --robot.type=... --dataset.repo_id=...
```

가상 키보드는 **포커스된 창**으로 키를 보낸다. 녹화 중에 다른 창을 클릭하면 그쪽으로 들어가니 주의.

### 터미널 1개

`run_record.sh`가 브릿지를 백그라운드로 띄우고, 넘긴 인자를 그대로 `lerobot-record`에 전달한 뒤,
끝날 때 브릿지를 정리한다.

```bash
./run_record.sh \
  --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=my_follower \
  --teleop.type=so101_leader  --teleop.port=/dev/ttyACM1 --teleop.id=my_leader \
  --dataset.repo_id="$HF_USER/my_dataset" \
  --dataset.num_episodes=30 \
  --dataset.single_task="pick up the cube"
```

> 이 스크립트는 브릿지가 제대로 떴는지 확인하지 않는다. 시작할 때
> `Pedal bridge running on ...` 줄이 보이는지 눈으로 확인할 것.

---

## 동작 원리

`pedal_bridge.py`는 163줄짜리 단일 파일이고, 외부 의존성은 `evdev` 하나뿐이다.

1. **독점 점유(`grab`)** — 페달을 배타적으로 잡아, 원신호 `a`/`b`/`c`가 화면이나 터미널로 새지 않게 막는다. 이게 없으면 받는 프로그램이 원신호와 변환된 키를 둘 다 받는다.
2. **눌리는 순간만 인식** — 발을 올려둘 때 나오는 auto-repeat(value 2)와 뗄 때 신호(value 0)는 버린다.
3. **디바운스** — 좌/우는 `DEBOUNCE_S = 0.30s` 쿨다운. 스위치 채터링과 실수 연타를 걸러낸다.
4. **더블탭 확인** — 중앙(종료)은 `DT_MIN_GAP = 0.15s` 이후 `DT_WINDOW_S = 2.0s` 이내에 두 번 밟아야 발동. 첫 탭 후 좌/우를 밟으면 예약이 취소된다. 실수로 한 번 스쳤다고 몇 시간짜리 세션이 끝나지 않는다.
5. **가상 키보드로 재전송(`uinput`)** — 커널 레벨이라 X11이든 Wayland든 포커스된 창에 그대로 전달된다.

---

## 설정 바꾸기

모든 설정은 `pedal_bridge.py` 상단 상수에 있다. 별도 설정 파일은 없다.

```python
MAPPING = {
    e.KEY_A: e.KEY_R,   # 왼쪽   -> 재수집
    e.KEY_B: e.KEY_Q,   # 중앙   -> 종료
    e.KEY_C: e.KEY_N,   # 오른쪽 -> 다음
}
CONFIRM_KEY = e.KEY_B   # 더블탭이 필요한 페달
DEBOUNCE_S  = 0.30      # 좌/우 쿨다운 (초)
DT_MIN_GAP  = 0.15      # 더블탭 최소 간격
DT_WINDOW_S = 2.00      # 더블탭 제한 시간
```

### 보내는 키를 바꿀 때 — 반드시 두 곳을 고친다

`MAPPING`만 고치면 **조용히 실패한다.** 가상 키보드가 낼 수 있는 키 목록도 함께 바꿔야 한다.

```python
# 86번째 줄 근처
ui = UInput({e.EV_KEY: [e.KEY_N, e.KEY_R, e.KEY_Q]}, name="footpedal-kbd")
#                       ^^^^^^^^^^^^^^^^^^^^^^^^^ 여기에 없는 키는 나가지 않는다
```

로그 출력용 `LABEL` 딕셔너리도 맞춰주면 좋다.

### 다른 페달 쓰기

1. `lsusb`로 vendor/product ID 확인 → `udev/99-footpedal.rules`의 `idVendor`/`idProduct` 수정 → `bash install.sh` 재실행
2. `sudo evtest`로 각 페달이 보내는 키 확인 → `MAPPING`의 왼쪽 항목 수정
3. 장치 경로가 다르면 환경변수로 지정

```bash
FOOTPEDAL_PATH=/dev/input/eventX python3 pedal_bridge.py
```

---

## 트러블슈팅

**`Missing dependency` / `ModuleNotFoundError: evdev`**
브릿지를 실행하는 파이썬과 `evdev`를 설치한 파이썬이 다르다. `which python3` 확인 후
그 파이썬으로 `python3 -m pip install evdev`.

**`No permission to read /dev/input/...`**
`input` 그룹이 반영되지 않았다. `groups`에 `input`이 있는지 확인하고, 없으면 재로그인 또는 `newgrp input`.

**`No permission to create a virtual keyboard at /dev/uinput`**
같은 원인이거나 uinput 모듈이 안 올라왔다. `ls -l /dev/uinput`으로 그룹이 `input`인지 확인,
없으면 `sudo modprobe uinput` 후 `bash install.sh` 재실행.

**`Pedal not found at ...`**
`ls -l /dev/input/by-id/`로 실제 경로를 확인하고 `FOOTPEDAL_PATH`로 지정한다.
같은 장치에 `event*` 노드가 여러 개면 다른 쪽을 시도해 본다.

**브릿지는 도는데 페달을 밟아도 아무 반응이 없다**
가장 흔한 원인은 페달이 `a`/`b`/`c`가 아닌 다른 키를 보내는 것이다. `sudo evtest`로 확인 후
[4단계](#4단계--페달-키-굽기-최초-1회-이미-돼-있으면-건너뜀)를 진행한다. 이 경우 오류 메시지가 안 뜬다.

**키가 엉뚱한 창에 입력된다**
가상 키보드는 포커스된 창으로 간다. 녹화 터미널을 클릭해 포커스를 유지할 것.

**중앙 페달을 밟았는데 안 끝난다**
정상이다. 두 번 밟아야 한다. 첫 탭 후 브릿지 터미널에 `STOP armed`가 뜨는지 확인하고
0.15~2.0초 사이에 다시 밟는다.

---

## 참고

- LeRobot 실사용 문서: https://huggingface.co/docs/lerobot/il_robots
- PCsensor 페달 리눅스 프로그래밍 툴: https://github.com/rgerganov/footswitch
- 이 브릿지를 쓰는 양팔 데이터 수집 파이프라인: https://github.com/ValentinJaeung/Norimate

## License

MIT — `LICENSE` 참고.
