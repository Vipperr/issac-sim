#!/bin/bash
# Record a batch of deterministic episodes with raw/EMA action + fingertip pose logging.
#
# Usage:
#   record_eval_batch.sh <checkpoint> <tag> <seed> [<seed> ...]
#
# Extra Hydra overrides go in the EPISODE_OVERRIDES env var (space separated), e.g.
#   EPISODE_OVERRIDES="env.ctrl.pos_action_threshold=[0.005,0.005,0.030]" record_eval_batch.sh ...
#
# IMPORTANT: the overrides must match the ones the checkpoint was trained with,
# otherwise the action scale at eval time differs from training.
set -u

CKPT="${1:?checkpoint path required}"
TAG="${2:?tag required}"
shift 2
SEEDS=("$@")
[ ${#SEEDS[@]} -gt 0 ] || { echo "at least one seed required" >&2; exit 2; }

ROOT=/root/gpufree-data/isaac-sim
LAB=$ROOT/IsaacLab
SCRIPT=$ROOT/peg_insert_reproduction/scripts/record_successful_episode.py
VID=$ROOT/peg_insert_reproduction/videos/${TAG}_batch
RES=$ROOT/peg_insert_reproduction/eval_results
LOG=$ROOT/peg_insert_reproduction/logs

# Overrides that must match training. Defaults: current [5,5,30] + Kp_z=400 experiment.
OVERRIDES="${EPISODE_OVERRIDES:-env.ctrl.pos_action_threshold=[0.005,0.005,0.030] env.ctrl.default_task_prop_gains=[100,100,400,30,30,30] env.task.action_grad_penalty_scale=0.0}"

mkdir -p "$RES" "$LOG" "$VID"

for SEED in "${SEEDS[@]}"; do
    echo "=== seed ${SEED} start $(date +%H:%M:%S) ==="
    cd "$LAB" || exit 1
    # shellcheck disable=SC2086
    ./isaaclab.sh -p "$SCRIPT" \
        --task Isaac-Rebot-Factory-PegInsert-Direct-v0 \
        --checkpoint "$CKPT" \
        --seed "$SEED" \
        --video_folder "$VID/seed${SEED}" \
        --action_output "$RES/${TAG}_seed${SEED}.json" \
        --headless --disable_fabric \
        $OVERRIDES \
        > "$LOG/rebot_record_${TAG}_seed${SEED}.out" 2>&1 < /dev/null
    rc=$?
    echo "=== seed ${SEED} done rc=${rc} $(date +%H:%M:%S) ==="
    if [ "$rc" -ne 0 ]; then
        echo "seed ${SEED} failed; tail of log:"
        tail -n 25 "$LOG/rebot_record_${TAG}_seed${SEED}.out"
    fi
done
echo "=== batch complete ==="
