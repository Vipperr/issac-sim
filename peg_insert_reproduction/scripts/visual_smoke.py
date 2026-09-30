#!/usr/bin/env python3
"""Low-load, time-bounded visual check for the official PegInsert task.

This script deliberately does not modify the task, rewards, or controller.  It
only drives zero actions at a low rate so that a laptop GPU can keep the Isaac
Sim UI responsive during the M3 visual inspection.
"""

import argparse
import time

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Run a low-load visual PegInsert check.")
parser.add_argument("--task", type=str, default="Isaac-Factory-PegInsert-Direct-v0")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--disable_fabric", action="store_true", help="Use USD I/O instead of Fabric for this visual check.")
parser.add_argument("--duration", type=float, default=90.0, help="Maximum run time in seconds.")
parser.add_argument("--step_interval", type=float, default=0.1, help="Delay after each environment step in seconds.")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(device="cpu")
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


def main() -> None:
    env_cfg = parse_env_cfg(
        args_cli.task,
        device=args_cli.device,
        num_envs=args_cli.num_envs,
        use_fabric=not args_cli.disable_fabric,
    )
    env = gym.make(args_cli.task, cfg=env_cfg)
    env.reset()
    print(f"[VISUAL-CHECK] task={args_cli.task}, device={env.unwrapped.device}, duration={args_cli.duration}s", flush=True)

    started_at = time.monotonic()
    next_report_at = 5.0
    while simulation_app.is_running():
        elapsed = time.monotonic() - started_at
        if elapsed >= args_cli.duration:
            break
        with torch.inference_mode():
            actions = torch.zeros(env.action_space.shape, device=env.unwrapped.device)
            env.step(actions)
        if elapsed >= next_report_at:
            print(f"[VISUAL-CHECK] alive at {elapsed:.1f}s", flush=True)
            next_report_at += 5.0
        time.sleep(args_cli.step_interval)

    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
