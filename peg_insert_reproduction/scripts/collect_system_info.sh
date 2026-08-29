#!/usr/bin/env bash
set -euo pipefail

experiment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lab_dir="$(cd "${experiment_dir}/../IsaacLab" && pwd)"

nvidia-smi > "${experiment_dir}/system_info.txt" || true
git -C "${lab_dir}" rev-parse HEAD > "${experiment_dir}/git_commit.txt"
python -m pip freeze > "${experiment_dir}/pip_freeze.txt"
python - <<'PY' > "${experiment_dir}/runtime_versions.txt"
import sys
import torch
import isaacsim
print(f"python={sys.version}")
print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cuda_available={torch.cuda.is_available()}")
print("isaacsim=5.1.0.0")
PY
