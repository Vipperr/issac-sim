#!/usr/bin/env python3
"""Register Rebot PegInsert, then run Isaac Lab's stock RL-Games trainer."""

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import rebot_task  # noqa: E402, F401

runpy.run_path(str(ROOT.parent / "IsaacLab/scripts/reinforcement_learning/rl_games/train.py"), run_name="__main__")
