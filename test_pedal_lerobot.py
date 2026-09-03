#!/usr/bin/env python3
"""Prove the foot pedal drives LeRobot's recording controls. No robot needed."""
import sys
import time

from lerobot.utils.keyboard_input import init_keyboard_listener

EXPECTED = {
    "exit_early": "RIGHT pedal (n) - save episode, next",
    "rerecord_episode": "LEFT pedal (r) - discard and re-record",
    "stop_recording": "CENTER pedal x2 (q) - stop recording",
}


def main():
    listener, events = init_keyboard_listener()
    if listener is None:
        sys.exit("LeRobot could not start a keyboard listener here.")

    print("=" * 60)
    print("Pedal -> LeRobot control test")
    print("Backend:", type(listener).__name__)
    print("Keep THIS terminal focused. Press each pedal.")
    for k, v in EXPECTED.items():
        print("  %-18s %s" % (k, v))
    print("Ctrl+C to quit.")
    print("-" * 60)

    seen = set()
    prev = dict(events)
    try:
        while True:
            changed = [k for k in events if events[k] != prev.get(k)]
            if changed:
                for k in changed:
                    if events[k]:
                        seen.add(k)
                stamp = time.strftime("%H:%M:%S")
                body = ", ".join("%s=%s" % (k, events[k]) for k in changed)
                print("[%s] %s" % (stamp, body))
                for k in events:
                    events[k] = False
                print("    reset - triggered so far:", sorted(seen))
            prev = dict(events)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("-" * 60)
        missing = [k for k in EXPECTED if k not in seen]
        if missing:
            print("NOT triggered yet:")
            for k in missing:
                print("  -", k, ":", EXPECTED[k])
        else:
            print("All three controls fired. Pedal is ready for recording.")
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
