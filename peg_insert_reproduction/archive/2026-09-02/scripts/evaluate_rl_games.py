#!/usr/bin/env python3
"""Evaluate an RL-Games checkpoint with Factory's native success metric."""

import argparse
import json
import math
import random
import sys

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkpoint", required=True, help="Path to an RL-Games checkpoint.")
parser.add_argument("--task", default="Isaac-Factory-PegInsert-Direct-v0")
parser.add_argument("--agent", default="rl_games_cfg_entry_point")
parser.add_argument("--num_envs", type=int, default=128)
parser.add_argument("--episodes", type=int, default=1024, help="Must be divisible by --num_envs.")
parser.add_argument("--seed", type=int, default=1000, help="Evaluation environment seed.")
parser.add_argument("--output", help="Optional path for the JSON summary.")
parser.add_argument("--disable_fabric", action="store_true")
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
if args_cli.episodes <= 0 or args_cli.episodes % args_cli.num_envs:
    parser.error("--episodes must be positive and divisible by --num_envs")
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
    env_cfg.scene.num_envs = args_cli.num_envs
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device
    env_cfg.seed = args_cli.seed if args_cli.seed != -1 else random.randint(0, 10000)
    agent_cfg["params"]["seed"] = env_cfg.seed

    env = gym.make(args_cli.task, cfg=env_cfg)
    if isinstance(env.unwrapped, DirectMARLEnv):
        env = multi_agent_to_single_agent(env)

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
    agent_cfg["params"]["config"]["num_actors"] = env.unwrapped.num_envs
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

    completed = successes = 0
    success_step_sum = 0.0
    while completed < args_cli.episodes:
        with torch.inference_mode():
            actions = agent.get_action(agent.obs_to_torch(obs), is_deterministic=True)
            obs, _, dones, infos = env.step(actions)
        if torch.any(dones):
            if not torch.all(dones):
                raise RuntimeError("Factory episodes are expected to terminate synchronously")
            success_count = round(float(infos["successes"]) * args_cli.num_envs)
            successes += success_count
            if success_count:
                success_step_sum += float(infos["success_times"]) * success_count
            completed += args_cli.num_envs
            print(f"episodes={completed}/{args_cli.episodes} successes={successes}", flush=True)
            if agent.is_rnn and agent.states is not None:
                with torch.inference_mode():
                    for state in agent.states:
                        state[:, dones, :] = 0.0

    summary = {
        "checkpoint": checkpoint,
        "task": args_cli.task,
        "deterministic": True,
        "eval_seed": env_cfg.seed,
        "num_envs": args_cli.num_envs,
        "episodes": completed,
        "successes": successes,
        "success_rate": successes / completed,
        "mean_first_success_step": success_step_sum / successes if successes else None,
        "mean_first_success_seconds": success_step_sum / successes * env.unwrapped.step_dt if successes else None,
    }
    summary_json = json.dumps(summary, sort_keys=True)
    print(summary_json, flush=True)
    if args_cli.output:
        with open(args_cli.output, "w", encoding="utf-8") as output_file:
            output_file.write(f"{summary_json}\n")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
