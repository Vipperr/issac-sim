#!/usr/bin/env bash
set -euo pipefail

experiment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lab_dir="$(cd "${experiment_dir}/../IsaacLab" && pwd)"
cd "${lab_dir}"

./isaaclab.sh -p scripts/environments/zero_agent.py \
  --task Isaac-Factory-PegInsert-Direct-v0 --num_envs 1 --headless

./isaaclab.sh -p scripts/environments/random_agent.py \
  --task Isaac-Factory-PegInsert-Direct-v0 --num_envs 1 --headless
