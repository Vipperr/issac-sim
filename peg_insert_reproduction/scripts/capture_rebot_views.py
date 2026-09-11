#!/usr/bin/env python3
"""Capture the initial Rebot peg-in-hole layout from four camera views."""

import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--task", default="Isaac-Rebot-Factory-PegInsert-Direct-v0")
parser.add_argument("--agent", default="rl_games_cfg_entry_point")
parser.add_argument("--output_dir", required=True)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
args_cli.enable_cameras = True
sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch
from PIL import Image

from isaaclab_tasks.utils.hydra import hydra_task_config
from isaaclab.utils.math import quat_apply

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rebot_task  # noqa: E402,F401


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg, _agent_cfg):
    env_cfg.scene.num_envs = 1
    env_cfg.sim.use_fabric = False
    env_cfg.viewer.resolution = (1280, 720)
    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    env.reset()
    task = env.unwrapped
    peg_axis = quat_apply(task.held_quat, torch.tensor([[0.0, 0.0, 1.0]], device=task.device))
    print(
        f"tool={task.fingertip_midpoint_pos[0].tolist()} peg_tip={task.held_pos[0].tolist()} "
        f"hole_root={task.fixed_pos[0].tolist()} peg_axis={peg_axis[0].tolist()}",
        flush=True,
    )

    target = (0.20, 0.0, 0.12)
    views = {
        "front": ((0.87, 0.0, 0.32), target),
        "side": ((0.20, 0.75, 0.32), target),
        "oblique": ((0.77, 0.65, 0.45), target),
        "top": ((0.20, 0.01, 0.90), (0.20, 0.0, 0.0)),
    }
    output_dir = Path(args_cli.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, (eye, lookat) in views.items():
        env.unwrapped.sim.set_camera_view(eye=eye, target=lookat)
        for _ in range(3):
            frame = env.render()
        Image.fromarray(frame).save(output_dir / f"{name}.png")
        print(f"saved={output_dir / f'{name}.png'}", flush=True)
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
