#!/usr/bin/env bash
# run_record.sh — start the foot-pedal bridge, then run lerobot-record.
#
# Everything you pass to this script is forwarded straight to lerobot-record,
# so use it exactly like lerobot-record, e.g.:
#
#   ./run_record.sh \
#     --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=my_follower \
#     --teleop.type=so101_leader  --teleop.port=/dev/ttyACM1 --teleop.id=my_leader \
#     --robot.cameras="{ wrist: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30} }" \
#     --dataset.repo_id="$HF_USER/my_dataset" \
#     --dataset.num_episodes=30 \
#     --dataset.single_task="pick up the cube" \
#     --display_data=true
#
# While recording, keep THIS terminal focused. Then:
#   right pedal = save + next     left pedal = re-record     center x2 = stop

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start the pedal bridge in the background.
python3 "$HERE/pedal_bridge.py" &
BRIDGE_PID=$!

# Always stop the bridge when this script exits, for any reason.
cleanup() { kill "$BRIDGE_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

sleep 1  # let the bridge grab the pedal and create its virtual keyboard

# Hand off to lerobot-record with whatever arguments you passed in.
lerobot-record "$@"
