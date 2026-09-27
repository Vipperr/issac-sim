#!/usr/bin/env python3
"""Verify that a converted Rebot USD spawns and simulates in Isaac Lab."""

import argparse

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--asset", required=True, help="Path to the converted Rebot USD.")
parser.add_argument("--steps", type=int, default=60)
parser.add_argument("--arm_joints", nargs=6, type=float, metavar=("Q1", "Q2", "Q3", "Q4", "Q5", "Q6"))
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import isaacsim.core.utils.torch as torch_utils

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.sim import SimulationContext


def main():
    sim = SimulationContext(sim_utils.SimulationCfg(device=args_cli.device))
    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Rebot",
            spawn=sim_utils.UsdFileCfg(usd_path=args_cli.asset),
            init_state=ArticulationCfg.InitialStateCfg(
                joint_pos={
                    "Joint_1": 0.0,
                    "Joint_2": 0.52359878,
                    "Joint_3": -1.57079633,
                    "Joint_4": 0.0,
                    "Joint_5": 0.0,
                    "Joint_6": 0.0,
                }
            ),
            actuators={
                "arm": ImplicitActuatorCfg(
                    joint_names_expr=["Joint_[1-6]"],
                    stiffness=0.0,
                    damping=0.0,
                    friction=2.0,
                    dynamic_friction=2.0,
                    viscous_friction=0.2,
                    effort_limit_sim=50.0,
                ),
                "fingers": ImplicitActuatorCfg(
                    joint_names_expr=["Joint_ee_[12]"],
                    stiffness=500.0,
                    damping=0.0,
                    friction=2.0,
                    dynamic_friction=2.0,
                    viscous_friction=0.2,
                    effort_limit_sim=100.0,
                ),
            },
        )
    )
    sim.reset()
    if args_cli.arm_joints:
        joint_pos = robot.data.default_joint_pos.clone()
        joint_pos[:, :6] = torch.tensor(args_cli.arm_joints, device=sim.device)
        robot.write_joint_state_to_sim(joint_pos, torch.zeros_like(joint_pos))
        sim.step()
        robot.update(sim.get_physics_dt())
    expected_joints = {*(f"Joint_{index}" for index in range(1, 7)), "Joint_ee_1", "Joint_ee_2"}
    assert expected_joints <= set(robot.joint_names), robot.joint_names
    assert "Tool" in robot.body_names, robot.body_names
    j2_limits = robot.data.soft_joint_pos_limits[0, robot.joint_names.index("Joint_2")]
    assert torch.allclose(
        j2_limits, torch.tensor([0.0, 3.141592653589793], device=sim.device), atol=1e-5
    ), j2_limits

    for _ in range(args_cli.steps):
        robot.set_joint_effort_target(torch.zeros_like(robot.data.joint_pos))
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim.get_physics_dt())
    assert torch.isfinite(robot.data.joint_pos).all()
    tool_index = robot.body_names.index("Tool")
    tool_euler = torch_utils.get_euler_xyz(robot.data.body_quat_w[0, tool_index].unsqueeze(0))
    print(f"joints={robot.joint_names}", flush=True)
    print(f"joint_2_limits={j2_limits.tolist()}", flush=True)
    print(f"bodies={robot.body_names}", flush=True)
    print(f"tool_position={robot.data.body_pos_w[0, tool_index].tolist()}", flush=True)
    print(f"tool_quaternion={robot.data.body_quat_w[0, tool_index].tolist()}", flush=True)
    print(f"tool_euler={[angle[0].item() for angle in tool_euler]}", flush=True)
    print(f"smoke_test_steps={args_cli.steps}", flush=True)


if __name__ == "__main__":
    main()
    simulation_app.close()
