# lerobot-footpedal

Hands-free episode control for [LeRobot](https://github.com/huggingface/lerobot)
data collection using a **PCsensor 3-pedal USB foot switch**.

While teleoperating with both hands on the leader arm(s), you have no free hand
to press keys. This bridge lets your feet drive the LeRobot recording flow:

| Pedal  | Sends | LeRobot action                              |
|--------|-------|---------------------------------------------|
| Left   | `r`   | Re-record — delete current episode and retry|
| Center | `q`   | Stop — encode + upload (**tap twice**)      |
| Right  | `n`   | Save current episode and move to the next   |

It reads the pedal exclusively, filters switch bounce and accidental fast
re-presses (debounce), and guards the **stop** pedal with a double-tap so a
single stray press can never end your session. Clean keystrokes are re-emitted
through a virtual keyboard that LeRobot sees as a normal keyboard — **no changes
to LeRobot are needed.**

## Requirements

- Ubuntu (tested on 22.04 / 24.04)
- A PCsensor FootSwitch, 3-pedal (USB ID `3553:b001`), programmed to emit
  `a` / `b` / `c` (left / center / right). These pedals are programmable, so
  burn the keys once with [footswitch](https://github.com/rgerganov/footswitch):
  `sudo footswitch -1 -k a -2 -k b -3 -k c`
- LeRobot installed and working (`lerobot-record` on your PATH)
- Python with `evdev`: `pip install evdev`

## Install

```bash
git clone https://github.com/ValentinJaeung/Norimate.git
cd Norimate/pedal
pip install -r requirements.txt

sudo ./install.sh      # one-time: group + udev + uinput module
# then log out and back in (or reboot)
```

If you are using the whole Norimate repo, run `bash setup/install.sh` from the
repo root instead — it does the same thing *and* installs the Python dep.

`install.sh` adds you to the `input` group and opens the pedal and `/dev/uinput`
to that group, so after re-login you can run the bridge **without sudo**.

## Test it (without LeRobot)

```bash
python3 pedal_bridge.py
```

Click into any text editor or empty terminal and press the pedals:

- Right pedal types `n`, left types `r`
- Center pedal: first press shows `STOP armed`, a second press within 2 s types `q`
- Rapid double-tap of a side pedal registers only **once**
- The raw `a` / `b` / `c` never leak through

## Use it with LeRobot

`run_record.sh` starts the bridge, launches `lerobot-record`, and cleans up the
bridge on exit. Pass it the same arguments you'd give `lerobot-record`:

```bash
./run_record.sh \
  --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=my_follower \
  --teleop.type=so101_leader  --teleop.port=/dev/ttyACM1 --teleop.id=my_leader \
  --dataset.repo_id="$HF_USER/my_dataset" \
  --dataset.num_episodes=30 \
  --dataset.single_task="pick up the cube" \
  --display_data=true
```

Keep the `run_record.sh` terminal focused while recording so the keystrokes land
in the right place.

> `run_record.sh` does not check whether the bridge actually came up — if the
> bridge exits on a permission error, recording still starts, just without the
> pedal. Watch for the `Pedal bridge running on ...` line.

**Inside the Norimate repo** the bimanual arguments are long, so the usual flow
is two terminals instead: `python3 pedal/pedal_bridge.py` in one, and
`bash scripts/4_record.sh` in the other (keep the second one focused).

## Customize

All settings are at the top of `pedal_bridge.py`. (`pedal_config.yaml` in this
folder is **not read by the bridge** — it is a leftover; editing it does
nothing.)

- `MAPPING` — which pedal sends which control key
- `DEBOUNCE_S` — accidental fast re-press window, left/right only (default 0.30 s)
- `DT_WINDOW_S` — how long you have to complete the stop double-tap (default 2.0 s)
- `DT_MIN_GAP` — minimum gap between the two stop taps, bounce guard (default 0.15 s)
- `CONFIRM_KEY` — which pedal needs the double-tap (default center, `KEY_B`)

Pressing left or right while a stop is armed cancels it.

Different pedal or key layout? Check what each pedal emits with
`sudo evtest /dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd`, then update
`MAPPING`. Point the bridge at a different device with
`NORIMATE_PEDAL_PATH=/dev/input/eventX python3 pedal_bridge.py`.

## Troubleshooting

- **`Missing dependency`** — `pip install evdev` in the same Python you run the
  bridge with.
- **Permission errors after install** — did you log out and back in? Check
  `groups` includes `input`, and `ls -l /dev/uinput` shows group `input`.
- **Nothing happens on press** — another node may carry the signal. List with
  `ls -l /dev/input/by-id/` and try the other `...event*` paths via
  `NORIMATE_PEDAL_PATH`.
- **Running with `sudo` can't find evdev** — if evdev lives in conda, run
  `sudo "$(which python3)" pedal_bridge.py`. (Doing the one-time `install.sh`
  removes the need for sudo entirely.)

## How it works

```
[USB pedal] --raw a/b/c--> [pedal_bridge.py] --clean n/r/q--> [lerobot-record]
                            grab + debounce + double-tap
```

The bridge only acts on the key-press moment (ignoring release and
auto-repeat), applies a per-pedal debounce, and requires two center taps before
sending `q`. It never modifies LeRobot — it just speaks the keyboard language
LeRobot already listens to.

## License

MIT
