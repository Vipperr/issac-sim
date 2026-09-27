#!/usr/bin/env python3
"""Pre-training smoke test for the Rebot PegInsert env (random actions, several resets)."""

import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--num_envs", type=int, default=16)
parser.add_argument("--steps", type=int, default=400)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.headless = True
simulation_app = AppLauncher(args_cli).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rebot_task  # noqa: E402, F401
from rebot_task.rebot_factory_env import (  # noqa: E402
    ARM_JOINTS,
    REBOT_ARM_VELOCITY_LIMIT,
    REBOT_JOINT_FRICTION_RANGES,
    RebotFactoryPegInsertCfg,
)

cfg = RebotFactoryPegInsertCfg()
cfg.scene.num_envs = args_cli.num_envs
env = gym.make("Isaac-Rebot-Factory-PegInsert-Direct-v0", cfg=cfg)
task = env.unwrapped
robot = task._robot
arm_ids = task.arm_joint_ids
limits = robot.data.soft_joint_pos_limits[0, arm_ids]
env.reset()


def friction_snapshot():
    props = robot.root_physx_view.get_dof_friction_properties()[:, arm_ids]
    return props.to(task.device)


def check_friction(props, label):
    for expr, (low, high) in REBOT_JOINT_FRICTION_RANGES.items():
        ids = [ARM_JOINTS.index(n) for n in robot.find_joints(expr, preserve_order=True)[1]]
        coulomb = props[:, ids, 0]
        assert torch.all((coulomb >= low - 1e-6) & (coulomb <= high + 1e-6)), (label, expr, coulomb)
        assert torch.allclose(props[:, ids, 1], coulomb), (label, "dynamic != static")
    assert props[:, :, 0].std(dim=0).min() > 0.0, (label, "friction not randomized across envs")


first = friction_snapshot()
check_friction(first, "reset0")
print("friction_env0_static", first[0, :, 0].tolist())
print("friction_env0_viscous", first[0, :, 2].tolist())

max_speed = 0.0
min_margin = float("inf")
resets = 0
for step in range(args_cli.steps):
    actions = 2.0 * torch.rand((task.num_envs, task.cfg.action_space), device=task.device) - 1.0
    _, _, terminated, truncated, _ = env.step(actions)
    q = robot.data.joint_pos[:, arm_ids]
    qd = robot.data.joint_vel[:, arm_ids]
    assert torch.isfinite(q).all() and torch.isfinite(qd).all(), f"non-finite state at step {step}"
    assert torch.isfinite(task.fingertip_midpoint_pos).all(), f"non-finite Tool pose at step {step}"
    max_speed = max(max_speed, float(qd.abs().max()))
    min_margin = min(min_margin, float(torch.minimum(q - limits[:, 0], limits[:, 1] - q).min()))
    if torch.any(terminated | truncated):
        resets += 1

after = friction_snapshot()
check_friction(after, "final")
resampled = bool(resets == 0 or not torch.allclose(first, after))
assert resampled, "friction was not resampled on reset"
assert max_speed <= REBOT_ARM_VELOCITY_LIMIT * 1.05, max_speed
assert min_margin > -1e-3, f"joint limit exceeded by {-min_margin} rad"
print(
    f"smoke=ok envs={task.num_envs} steps={args_cli.steps} resets={resets} "
    f"max_joint_speed={max_speed:.3f} min_limit_margin_rad={min_margin:.4f} friction_resampled={resampled}",
    flush=True,
)
env.close()
simulation_app.close()
