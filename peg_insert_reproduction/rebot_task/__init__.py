"""Register the Rebot Factory peg-insertion task."""

import gymnasium as gym


gym.register(
    id="Isaac-Rebot-Factory-PegInsert-Direct-v0",
    entry_point="rebot_task.rebot_factory_env:RebotFactoryEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "rebot_task.rebot_factory_env:RebotFactoryPegInsertCfg",
        "rl_games_cfg_entry_point": "isaaclab_tasks.direct.factory.agents:rl_games_ppo_cfg.yaml",
    },
)
