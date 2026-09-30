#!/usr/bin/env python3
"""Record one complete deterministic Factory episode."""

import argparse
import json
import math
import sys
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", required=True)
parser.add_argument("--task", default="Isaac-Factory-PegInsert-Direct-v0")
parser.add_argument("--agent", default="rl_games_cfg_entry_point")
parser.add_argument("--seed", type=int, default=1000)
parser.add_argument("--video_folder", required=True)
parser.add_argument("--action_output")
parser.add_argument("--disable_fabric", action="store_true")
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
args_cli.enable_cameras = True
sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch
from rl_games.common import env_configurations, vecenv
from rl_games.torch_runner import Runner

from isaaclab.envs import DirectMARLEnv, DirectMARLEnvCfg, DirectRLEnvCfg, ManagerBasedRLEnvCfg, multi_agent_to_single_agent
from isaaclab.utils.assets import retrieve_file_path
from isaaclab.utils.math import quat_apply
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper
import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import hydra_task_config

if args_cli.task.startswith("Isaac-Rebot-"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import rebot_task  # noqa: F401


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg: dict):
    env_cfg.scene.num_envs = 1
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = args_cli.seed
    if args_cli.task.startswith("Isaac-Rebot-"):
        env_cfg.viewer.eye = (0.53, 0.45, 0.28)
        env_cfg.viewer.lookat = (0.20, 0.0, 0.06)
    else:
        env_cfg.viewer.eye = (2.0, 2.0, 1.5)
        env_cfg.viewer.lookat = (0.5, 0.0, 0.5)
    agent_cfg["params"]["seed"] = args_cli.seed

    env = gym.make(args_cli.task, cfg=env_cfg, render_mode="rgb_array")
    if isinstance(env.unwrapped, DirectMARLEnv):
        env = multi_agent_to_single_agent(env)
    env = gym.wrappers.RecordVideo(
        env,
        video_folder=args_cli.video_folder,
        step_trigger=lambda step: step == 0,
        video_length=env.unwrapped.max_episode_length,
        disable_logger=True,
    )

    rl_device = agent_cfg["params"]["config"]["device"]
    env = RlGamesVecEnvWrapper(
        env,
        rl_device,
        agent_cfg["params"]["env"].get("clip_observations", math.inf),
        agent_cfg["params"]["env"].get("clip_actions", math.inf),
        agent_cfg["params"]["env"].get("obs_groups"),
        agent_cfg["params"]["env"].get("concate_obs_groups", True),
    )
    vecenv.register("IsaacRlgWrapper", lambda config_name, num_actors, **kwargs: RlGamesGpuEnv(config_name, num_actors, **kwargs))
    env_configurations.register("rlgpu", {"vecenv_type": "IsaacRlgWrapper", "env_creator": lambda **kwargs: env})

    checkpoint = retrieve_file_path(args_cli.checkpoint)
    agent_cfg["params"]["load_checkpoint"] = True
    agent_cfg["params"]["load_path"] = checkpoint
    agent_cfg["params"]["config"]["num_actors"] = 1
    runner = Runner()
    runner.load(agent_cfg)
    agent = runner.create_player()
    agent.restore(checkpoint)
    agent.reset()

    obs = env.reset()
    task = env.unwrapped
    peg_axis = quat_apply(task.held_quat, torch.tensor([[0.0, 0.0, 1.0]], device=task.device))
    print(f"peg_tip={task.held_pos[0].tolist()} hole_root={task.fixed_pos[0].tolist()} peg_axis={peg_axis[0].tolist()}", flush=True)
    if isinstance(obs, dict):
        obs = obs["obs"]
    _ = agent.get_batch_size(obs, 1)
    if agent.is_rnn:
        agent.init_rnn()

    success_reported = False
    first_success_step = None
    action_norm_sum = 0.0
    raw_action_history = []
    ema_action_history = []
    fingertip_position_history = []
    fingertip_quaternion_history = []
    initial_fingertip_position = task.fingertip_midpoint_pos[0].detach().cpu().tolist()
    initial_fingertip_quaternion = task.fingertip_midpoint_quat[0].detach().cpu().tolist()
    for step in range(1, env.unwrapped.max_episode_length + 1):
        with torch.inference_mode():
            actions = agent.get_action(agent.obs_to_torch(obs), is_deterministic=True)
            raw_action_history.append(actions[0].detach().cpu().tolist())
            ema_actions = task.ema_factor * actions + (1 - task.ema_factor) * task.actions
            ema_action_history.append(ema_actions[0].detach().cpu().tolist())
            obs, _, dones, infos = env.step(actions)
        if not bool(dones.item()):
            assert torch.allclose(task.actions, ema_actions, atol=1e-6)
        fingertip_position_history.append(task.fingertip_midpoint_pos[0].detach().cpu().tolist())
        fingertip_quaternion_history.append(task.fingertip_midpoint_quat[0].detach().cpu().tolist())
        action_norm_sum += torch.linalg.vector_norm(actions, dim=1).mean().item()
        if not success_reported and bool(infos["logs_rew_curr_success"].item()):
            print(f"first_success_step={step} seconds={step * env.unwrapped.step_dt:.2f}", flush=True)
            success_reported = True
            first_success_step = step
        if bool(dones.item()):
            print(f"timeout_step={step}", flush=True)
            break
    print(
        f"mean_action_norm={action_norm_sum / step:.6f} "
        f"peg_minus_hole={(task.held_pos[0] - task.fixed_pos[0]).tolist()}",
        flush=True,
    )
    assert len(raw_action_history) == len(ema_action_history) == len(fingertip_position_history) == len(
        fingertip_quaternion_history
    ) == step
    if args_cli.action_output:
        output = Path(args_cli.action_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "checkpoint": checkpoint,
                    "seed": args_cli.seed,
                    "deterministic": True,
                    "action_kind": "raw_policy_output_pre_ema",
                    "control_dt_seconds": env.unwrapped.step_dt,
                    "first_success_step": first_success_step,
                    "sample_timing": "raw_and_ema_action_pre_step; pose_post_step",
                    "initial_fingertip_position": initial_fingertip_position,
                    "initial_fingertip_quaternion_wxyz": initial_fingertip_quaternion,
                    "raw_actions": raw_action_history,
                    "ema_actions": ema_action_history,
                    "fingertip_positions": fingertip_position_history,
                    "fingertip_quaternions_wxyz": fingertip_quaternion_history,
                },
                indent=2,
            )
            + "\n"
        )
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
