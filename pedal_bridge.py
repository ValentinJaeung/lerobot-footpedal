#!/usr/bin/env python3
"""
pedal_bridge.py — PCsensor 3-pedal foot switch -> LeRobot record control keys.

  Left   (KEY_A) -> r   re-record current episode
  Center (KEY_B) -> q   quit/stop  (requires a DOUBLE-TAP to confirm)
  Right  (KEY_C) -> n   save + next episode

What this does:
  1. Opens the pedal by its stable by-id path.
  2. grab()s it so the raw A/B/C never leak into the desktop / LeRobot
     (otherwise LeRobot would get BOTH the raw keys and our clean keys).
  3. Acts only on the "press" moment; ignores release and auto-repeat.
  4. Debounces each pedal so an accidental fast double-press = one action.
  5. Guards the STOP pedal with a double-tap: one stray press never ends
     the session.
  6. Re-emits clean n / r / q through a virtual uinput keyboard that
     LeRobot sees as a normal keyboard.

Run (after install.sh + re-login, no sudo needed):
    python3 pedal_bridge.py

Override the device path if your pedal shows up elsewhere:
    NORIMATE_PEDAL_PATH=/dev/input/eventX python3 pedal_bridge.py
"""

import os
import sys
import glob
import time

try:
    from evdev import InputDevice, UInput, ecodes as e
except ImportError:
    sys.exit("Missing dependency. Install it with:  pip install evdev")

# ------------------------- Config (tune these) --------------------------
# Stable path for the PCsensor FootSwitch keyboard node. Same for anyone
# using this exact pedal model. Override with NORIMATE_PEDAL_PATH if needed.
DEFAULT_PATH = "/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd"

# raw pedal key  ->  LeRobot control key
MAPPING = {
    e.KEY_A: e.KEY_R,   # left   -> re-record
    e.KEY_B: e.KEY_Q,   # center -> quit  (double-tap guarded below)
    e.KEY_C: e.KEY_N,   # right  -> next
}

CONFIRM_KEY = e.KEY_B   # the pedal that needs a double-tap before it fires
DEBOUNCE_S  = 0.30      # ignore a repeat of the same (non-confirm) pedal within this
DT_MIN_GAP  = 0.15      # 2nd confirm tap must be at least this far from the 1st (else = bounce)
DT_WINDOW_S = 2.00      # ...and no later than this, or the 1st tap is forgotten
# ------------------------------------------------------------------------

LABEL = {e.KEY_R: "re-record (r)", e.KEY_N: "next (n)", e.KEY_Q: "STOP (q)"}


def find_pedal():
    """Resolve the pedal device path: env override -> default -> glob search."""
    override = os.environ.get("NORIMATE_PEDAL_PATH")
    if override:
        return override
    if os.path.exists(DEFAULT_PATH):
        return DEFAULT_PATH
    hits = sorted(glob.glob("/dev/input/by-id/*FootSwitch*event-kbd"))
    return hits[0] if hits else DEFAULT_PATH


def main():
    path = find_pedal()
    try:
        dev = InputDevice(path)
    except FileNotFoundError:
        sys.exit(
            f"Pedal not found at {path}.\n"
            "Is it plugged in? List devices with:  ls -l /dev/input/by-id/\n"
            "Then set NORIMATE_PEDAL_PATH to the right ...-event-kbd path."
        )
    except PermissionError:
        sys.exit(
            f"No permission to read {path}.\n"
            "Run ./install.sh once and log out/in, or run with sudo for a quick test."
        )

    try:
        ui = UInput({e.EV_KEY: [e.KEY_N, e.KEY_R, e.KEY_Q]}, name="norimate-pedal-kbd")
    except PermissionError:
        dev.close()
        sys.exit(
            "No permission to create a virtual keyboard at /dev/uinput.\n"
            "Run ./install.sh once and log out/in, or run with sudo for a quick test."
        )

    dev.grab()  # exclusive: raw A/B/C stop here and never reach anything else
    print(
        f"Pedal bridge running on '{dev.name}'.\n"
        "  Left = re-record   Center = STOP (tap twice)   Right = next\n"
        "  Ctrl+C to quit.\n"
    )

    last_accept = {}       # keycode -> time of last accepted press (debounce)
    confirm_first = None   # time of the 1st center tap, or None

    def tap(keycode):
        ui.write(e.EV_KEY, keycode, 1)   # press
        ui.syn()
        time.sleep(0.01)
        ui.write(e.EV_KEY, keycode, 0)   # release
        ui.syn()

    try:
        for event in dev.read_loop():
            # Only key events, only the press moment.
            # value 0 = release, value 2 = auto-repeat -> both ignored here.
            if event.type != e.EV_KEY or event.value != 1:
                continue
            code = event.code
            if code not in MAPPING:
                continue

            now = event.timestamp()  # kernel event time (robust to clock changes)

            # ---- Center pedal: double-tap to confirm STOP -----------------
            if code == CONFIRM_KEY:
                if confirm_first is None:
                    confirm_first = now
                    print(f"STOP armed — tap center again within {DT_WINDOW_S:.0f}s to confirm.")
                    continue
                gap = now - confirm_first
                if gap < DT_MIN_GAP:
                    continue                     # too fast -> bounce, ignore
                if gap <= DT_WINDOW_S:
                    confirm_first = None
                    print("-> STOP confirmed (q)")
                    tap(MAPPING[code])
                else:
                    confirm_first = now          # window expired -> re-arm
                    print(f"STOP armed — tap center again within {DT_WINDOW_S:.0f}s to confirm.")
                continue

            # ---- Left / Right pedals: debounce, then fire immediately ------
            if now - last_accept.get(code, 0.0) < DEBOUNCE_S:
                continue                         # accidental fast re-press -> ignore
            last_accept[code] = now

            if confirm_first is not None:        # pressed another pedal -> cancel pending STOP
                confirm_first = None
                print("STOP cancelled.")

            key = MAPPING[code]
            print(f"-> {LABEL[key]}")
            tap(key)

    except KeyboardInterrupt:
        pass
    finally:
        dev.ungrab()
        ui.close()
        print("\nPedal bridge stopped.")


if __name__ == "__main__":
    main()
