#!/usr/bin/env python3
"""Record one deterministic Factory episode, stopping at its first success."""

import argparse
import math
import sys

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", required=True)
parser.add_argument("--task", default="Isaac-Factory-PegInsert-Direct-v0")
parser.add_argument("--agent", default="rl_games_cfg_entry_point")
parser.add_argument("--seed", type=int, default=1000)
parser.add_argument("--video_folder", required=True)
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
from isaaclab_rl.rl_games import RlGamesGpuEnv, RlGamesVecEnvWrapper
import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import hydra_task_config


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg: dict):
    env_cfg.scene.num_envs = 1
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = args_cli.seed
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
    if isinstance(obs, dict):
        obs = obs["obs"]
    _ = agent.get_batch_size(obs, 1)
    if agent.is_rnn:
        agent.init_rnn()

    for step in range(1, env.unwrapped.max_episode_length + 1):
        with torch.inference_mode():
            actions = agent.get_action(agent.obs_to_torch(obs), is_deterministic=True)
            obs, _, dones, infos = env.step(actions)
        if bool(infos["logs_rew_curr_success"].item()):
            print(f"first_success_step={step} seconds={step * env.unwrapped.step_dt:.2f}", flush=True)
            break
        if bool(dones.item()):
            print(f"timeout_step={step}", flush=True)
            break
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
