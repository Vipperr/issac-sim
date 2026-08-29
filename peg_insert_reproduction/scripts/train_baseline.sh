#!/usr/bin/env bash
set -euo pipefail

num_envs="${1:-1}"
experiment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lab_dir="$(cd "${experiment_dir}/../IsaacLab" && pwd)"
cd "${lab_dir}"

args=(--task Isaac-Factory-PegInsert-Direct-v0 --headless)
if [[ "${num_envs}" != "128" ]]; then
  args+=(--num_envs "${num_envs}")
fi

./isaaclab.sh -p scripts/reinforcement_learning/rl_games/train.py "${args[@]}"
