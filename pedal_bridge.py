#!/usr/bin/env python3
"""
Norimate pedal bridge.

Turns a 3-pedal USB foot switch into LeRobot `record` control keys, with
debouncing so accidental double-taps don't fire twice, and a hold-to-confirm
guard so a stray tap on the "stop" pedal doesn't end the whole session.

Default mapping (configurable in pedal_config.yaml):
    left   -> r  (re-record current episode)
    center -> q  (stop, encode & save)      [must be held briefly to fire]
    right  -> n  (save current & next episode)

How it works: we exclusively grab the physical pedal (so its raw keystrokes
don't leak to the terminal), debounce the presses, and re-emit clean key events
through a virtual keyboard (uinput). Those land in whichever window is focused,
so keep the terminal running `lerobot-record` focused while you pedal.

Usage:
    python3 pedal_bridge.py --list                     # list input devices
    python3 pedal_bridge.py --detect --device <path>   # print codes as you press
    python3 pedal_bridge.py                             # run the bridge
    python3 pedal_bridge.py --config other.yaml         # use a different config
"""
import argparse
import os
import sys
import time

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install PyYAML")

try:
    from evdev import InputDevice, UInput, categorize, list_devices, ecodes as e
except ImportError:
    sys.exit("Missing dependency: pip install evdev")


DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "pedal_config.yaml")


def cmd_list():
    """List all input devices so you can find the pedal."""
    paths = list_devices()
    if not paths:
        print("No input devices found (permissions? try: sudo, or join 'input' group).")
        return
    print(f"{'PATH':<32}  NAME")
    for path in sorted(paths):
        try:
            d = InputDevice(path)
            print(f"{path:<32}  {d.name}")
        except Exception as ex:
            print(f"{path:<32}  <unreadable: {ex}>")
    print("\nTip: a stable path lives under /dev/input/by-id/ — prefer that in the config.")


def cmd_detect(device):
    """Grab a device and print key-down codes as you step on each pedal."""
    dev = InputDevice(device)
    try:
        dev.grab()
    except Exception as ex:
        print(f"Could not grab device ({ex}); reading without exclusive grab.")
    print(f"Listening on: {dev.name}")
    print("Step on each pedal. Note the code= value for each. Ctrl-C to stop.\n")
    try:
        for ev in dev.read_loop():
            if ev.type == e.EV_KEY and ev.value == 1:  # key down only
                k = categorize(ev)
                print(f"  code={ev.code:<5} name={k.keycode}")
    except KeyboardInterrupt:
        pass
    finally:
        try:
            dev.ungrab()
        except Exception:
            pass


def build_maps(cfg):
    debounce = cfg.get("debounce", {}) or {}
    default_cd = float(debounce.get("cooldown_s", 0.5))
    lockout = float(debounce.get("global_lockout_s", 0.15))

    htc = cfg.get("hold_to_confirm") or {}
    htc_action = htc.get("action")
    htc_hold = float(htc.get("hold_s", 0.4))
    htc_cd = float(htc.get("cooldown_s", default_cd))

    code_map = {}
    emit_keys = set()
    for name, b in cfg["bindings"].items():
        code = int(b["code"])
        key_name = b["key"]
        key = getattr(e, key_name)
        emit_keys.add(key)
        is_hold = (name == htc_action)
        code_map[code] = {
            "name": name,
            "key": key,
            "key_name": key_name,
            "is_hold": is_hold,
            "cooldown": htc_cd if is_hold else default_cd,
            "hold_s": htc_hold,
        }
    return code_map, sorted(emit_keys), lockout


def run(cfg):
    code_map, emit_keys, lockout = build_maps(cfg)

    dev = InputDevice(cfg["device"])
    if cfg.get("grab", True):
        dev.grab()

    ui = UInput({e.EV_KEY: emit_keys}, name="norimate-pedal")
    time.sleep(0.2)  # let the virtual device register

    print(f"[norimate] bridging: {dev.name}  ({cfg['device']})")
    for code, m in sorted(code_map.items()):
        tag = "  (hold-to-confirm)" if m["is_hold"] else ""
        print(f"           pedal '{m['name']}' code={code} -> {m['key_name']}{tag}")
    print("[norimate] keep the lerobot-record terminal focused. Ctrl-C to quit.")

    last_fire = {}      # action name -> monotonic time it last fired
    last_any = 0.0      # monotonic time ANY action last fired
    press_t = {}        # action name -> key-down time (hold actions)

    def emit(key):
        ui.write(e.EV_KEY, key, 1)
        ui.write(e.EV_KEY, key, 0)
        ui.syn()

    def fire(m):
        nonlocal last_any
        now = time.monotonic()
        if now - last_fire.get(m["name"], 0.0) < m["cooldown"]:
            return  # same action still cooling down
        if now - last_any < lockout:
            return  # something else just fired; ignore near-simultaneous stomps
        emit(m["key"])
        last_fire[m["name"]] = now
        last_any = now
        print(f"[norimate] {m['name']} -> {m['key_name']}")

    try:
        for ev in dev.read_loop():
            if ev.type != e.EV_KEY:
                continue
            m = code_map.get(ev.code)
            if not m:
                continue
            if ev.value == 1:            # key down
                if m["is_hold"]:
                    press_t[m["name"]] = time.monotonic()
                else:
                    fire(m)
            elif ev.value == 0:          # key up
                if m["is_hold"]:
                    t0 = press_t.pop(m["name"], None)
                    if t0 is not None and time.monotonic() - t0 >= m["hold_s"]:
                        fire(m)
            # ev.value == 2 is auto-repeat while held — ignored on purpose
    except KeyboardInterrupt:
        pass
    finally:
        try:
            dev.ungrab()
        except Exception:
            pass
        ui.close()
        print("\n[norimate] bridge stopped.")


def main():
    p = argparse.ArgumentParser(description="Norimate foot-pedal -> LeRobot key bridge")
    p.add_argument("--list", action="store_true", help="list input devices and exit")
    p.add_argument("--detect", action="store_true", help="print pedal codes as you press")
    p.add_argument("--device", help="device path (for --detect)")
    p.add_argument("--config", default=DEFAULT_CONFIG, help="path to pedal_config.yaml")
    args = p.parse_args()

    if args.list:
        cmd_list()
        return
    if args.detect:
        if not args.device:
            sys.exit("--detect needs --device <path> (get it from --list)")
        cmd_detect(args.device)
        return

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    if "CHANGE_ME" in cfg.get("device", ""):
        sys.exit("Edit pedal_config.yaml first: set `device` and the pedal codes "
                 "(use --list and --detect).")
    run(cfg)


if __name__ == "__main__":
    main()
