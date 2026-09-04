#!/usr/bin/env python3
"""Move Rebot's Tool by a small six-axis DLS-IK command and verify convergence.

Run from IsaacLab with a converted Rebot USD, for example:
  ./isaaclab.sh -p /path/to/run_rebot_diff_ik.py --headless --asset /path/to/rebot.usd
"""

import argparse

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--asset", required=True, help="Path to the converted Rebot USD.")
parser.add_argument("--steps", type=int, default=600, help="Physics steps used to settle on the target.")
parser.add_argument("--base-height", type=float, default=0.50, help="Robot base height above the test floor [m].")
parser.add_argument(
    "--delta-pose",
    nargs=6,
    type=float,
    default=(0.02, 0.01, 0.02, 0.0, 0.0, 0.03),
    metavar=("DX", "DY", "DZ", "DR", "DP", "DYAW"),
    help="Tool-frame target delta: meters followed by axis-angle radians.",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.sim import SimulationContext
from isaaclab.utils.math import compute_pose_error, subtract_frame_transforms


ARM_HOME = {
    "Joint_1": 0.0,
    "Joint_2": 3.92699082,
    "Joint_3": 4.10012748,
    "Joint_4": 0.21956242,
    "Joint_5": -1.57079633,
    "Joint_6": -1.57079633,
}


def pose_errors(ee_pos, ee_quat, goal_pos, goal_quat):
    pos_error, rot_error = compute_pose_error(ee_pos, ee_quat, goal_pos, goal_quat, rot_error_type="axis_angle")
    return torch.linalg.vector_norm(pos_error, dim=1), torch.linalg.vector_norm(rot_error, dim=1)


def main():
    sim = SimulationContext(sim_utils.SimulationCfg(dt=1 / 120, device=args_cli.device))
    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Rebot",
            spawn=sim_utils.UsdFileCfg(
                usd_path=args_cli.asset,
                rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=True),
            ),
            init_state=ArticulationCfg.InitialStateCfg(pos=(0.0, 0.0, args_cli.base_height), joint_pos=ARM_HOME),
            soft_joint_pos_limit_factor=0.98,
            actuators={
                "arm": ImplicitActuatorCfg(
                    joint_names_expr=["Joint_[1-6]"],
                    stiffness=1000.0,
                    damping=100.0,
                    effort_limit_sim=100.0,
                    velocity_limit_sim=3.0,
                ),
                "gripper_motor_lock": ImplicitActuatorCfg(
                    joint_names_expr=["Joint_7"], stiffness=100.0, damping=10.0, effort_limit_sim=1.0
                ),
                "fingers": ImplicitActuatorCfg(
                    joint_names_expr=["Joint_ee_[12]"], stiffness=500.0, damping=50.0, effort_limit_sim=100.0
                ),
            },
        )
    )
    sim.reset()

    arm_ids, arm_names = robot.find_joints([f"Joint_{i}" for i in range(1, 7)], preserve_order=True)
    tool_ids, tool_names = robot.find_bodies("Tool")
    assert arm_names == list(ARM_HOME), arm_names
    assert tool_names == ["Tool"], tool_names
    assert robot.is_fixed_base
    tool_id = tool_ids[0]
    tool_jacobian_id = tool_id - 1

    joint_pos = robot.data.default_joint_pos.clone()
    joint_vel = torch.zeros_like(joint_pos)
    robot.write_joint_state_to_sim(joint_pos, joint_vel)
    robot.set_joint_position_target(joint_pos)
    robot.reset()
    robot.write_data_to_sim()
    sim.step()
    robot.update(sim.get_physics_dt())

    controller = DifferentialIKController(
        DifferentialIKControllerCfg(command_type="pose", use_relative_mode=True, ik_method="dls", ik_params={"lambda_val": 0.10}),
        num_envs=1,
        device=sim.device,
    )
    root_pose_w = robot.data.root_pose_w
    tool_pose_w = robot.data.body_pose_w[:, tool_id]
    tool_pos_b, tool_quat_b = subtract_frame_transforms(
        root_pose_w[:, :3], root_pose_w[:, 3:7], tool_pose_w[:, :3], tool_pose_w[:, 3:7]
    )
    delta_pose = torch.tensor(args_cli.delta_pose, dtype=torch.float32, device=sim.device).unsqueeze(0)
    controller.set_command(delta_pose, tool_pos_b, tool_quat_b)
    initial_pos_error, initial_rot_error = pose_errors(
        tool_pos_b, tool_quat_b, controller.ee_pos_des, controller.ee_quat_des
    )

    for _ in range(args_cli.steps):
        jacobian = robot.root_physx_view.get_jacobians()[:, tool_jacobian_id, :, arm_ids]
        root_pose_w = robot.data.root_pose_w
        tool_pose_w = robot.data.body_pose_w[:, tool_id]
        tool_pos_b, tool_quat_b = subtract_frame_transforms(
            root_pose_w[:, :3], root_pose_w[:, 3:7], tool_pose_w[:, :3], tool_pose_w[:, 3:7]
        )
        arm_target = controller.compute(tool_pos_b, tool_quat_b, jacobian, robot.data.joint_pos[:, arm_ids])
        arm_limits = robot.data.soft_joint_pos_limits[:, arm_ids]
        arm_target = torch.clamp(arm_target, arm_limits[..., 0], arm_limits[..., 1])
        joint_target = robot.data.default_joint_pos.clone()
        joint_target[:, arm_ids] = arm_target
        robot.set_joint_position_target(joint_target)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim.get_physics_dt())

    root_pose_w = robot.data.root_pose_w
    tool_pose_w = robot.data.body_pose_w[:, tool_id]
    tool_pos_b, tool_quat_b = subtract_frame_transforms(
        root_pose_w[:, :3], root_pose_w[:, 3:7], tool_pose_w[:, :3], tool_pose_w[:, 3:7]
    )
    final_pos_error, final_rot_error = pose_errors(tool_pos_b, tool_quat_b, controller.ee_pos_des, controller.ee_quat_des)
    limits = robot.data.soft_joint_pos_limits[:, arm_ids]
    assert torch.isfinite(robot.data.joint_pos).all()
    assert torch.all(robot.data.joint_pos[:, arm_ids] >= limits[..., 0])
    assert torch.all(robot.data.joint_pos[:, arm_ids] <= limits[..., 1])
    assert final_pos_error.item() < initial_pos_error.item() * 0.5, (initial_pos_error, final_pos_error)
    assert final_rot_error.item() < initial_rot_error.item() * 0.5, (initial_rot_error, final_rot_error)
    print(f"arm_joint_names={arm_names}")
    print(f"tool_position_world={tool_pose_w[0, :3].tolist()}")
    print(f"position_error_m={initial_pos_error.item():.6f}->{final_pos_error.item():.6f}")
    print(f"rotation_error_rad={initial_rot_error.item():.6f}->{final_rot_error.item():.6f}")
    print(f"dls_ik_steps={args_cli.steps}")


if __name__ == "__main__":
    main()
    simulation_app.close()
