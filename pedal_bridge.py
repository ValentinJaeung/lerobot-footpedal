#!/usr/bin/env python3
"""Norimate pedal bridge: foot switch -> LeRobot record keys, with debounce
and a double-tap guard on the stop pedal."""
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
    dev = InputDevice(device)
    try:
        dev.grab()
    except Exception as ex:
        print(f"Could not grab device ({ex}); reading without exclusive grab.")
    print(f"Listening on: {dev.name}")
    print("Step on each pedal. Note the code= value for each. Ctrl-C to stop.\n")
    try:
        for ev in dev.read_loop():
            if ev.type == e.EV_KEY and ev.value == 1:
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

    dt = cfg.get("double_tap") or {}
    dt_action = dt.get("action")
    dt_window = float(dt.get("window_s", 2.0))

    code_map = {}
    emit_keys = set()
    for name, b in cfg["bindings"].items():
        code = int(b["code"])
        key_name = b["key"]
        key = getattr(e, key_name)
        emit_keys.add(key)
        code_map[code] = {
            "name": name,
            "key": key,
            "key_name": key_name,
            "needs_double": (name == dt_action),
            "window_s": dt_window,
            "cooldown": default_cd,
        }
    return code_map, sorted(emit_keys), lockout


def run(cfg):
    code_map, emit_keys, lockout = build_maps(cfg)

    dev = InputDevice(cfg["device"])
    if cfg.get("grab", True):
        dev.grab()

    ui = UInput({e.EV_KEY: emit_keys}, name="norimate-pedal")
    time.sleep(0.2)

    print(f"[norimate] bridging: {dev.name}  ({cfg['device']})")
    for code, m in sorted(code_map.items()):
        tag = f"  (tap twice within {m['window_s']:g}s)" if m["needs_double"] else ""
        print(f"           pedal '{m['name']}' code={code} -> {m['key_name']}{tag}")
    print("[norimate] keep the lerobot-record terminal focused. Ctrl-C to quit.")

    last_fire = {}
    last_any = 0.0
    first_tap = {}

    def emit(key):
        ui.write(e.EV_KEY, key, 1)
        ui.write(e.EV_KEY, key, 0)
        ui.syn()

    def fire(m):
        nonlocal last_any
        now = time.monotonic()
        if now - last_fire.get(m["name"], 0.0) < m["cooldown"]:
            return
        if now - last_any < lockout:
            return
        emit(m["key"])
        last_fire[m["name"]] = now
        last_any = now
        print(f"[norimate] {m['name']} -> {m['key_name']}")

    try:
        for ev in dev.read_loop():
            if ev.type != e.EV_KEY or ev.value != 1:
                continue
            m = code_map.get(ev.code)
            if not m:
                continue
            if m["needs_double"]:
                now = time.monotonic()
                t0 = first_tap.get(m["name"])
                if t0 is not None and now - t0 <= m["window_s"]:
                    first_tap.pop(m["name"], None)
                    fire(m)
                else:
                    first_tap[m["name"]] = now
                    print(f"[norimate] {m['name']}: tap again within "
                          f"{m['window_s']:g}s to confirm STOP")
            else:
                fire(m)
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
