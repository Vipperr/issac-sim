"""Rebot-specific robot layer for Isaac Lab's Factory PegInsert task."""

from pathlib import Path

import carb
import torch

import isaacsim.core.utils.torch as torch_utils

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg
from isaaclab.managers import EventTermCfg, SceneEntityCfg
from isaaclab.utils import configclass
from isaaclab.utils.math import axis_angle_from_quat
from isaaclab_tasks.direct.factory import factory_control, factory_utils
from isaaclab_tasks.direct.factory.factory_env import FactoryEnv
from isaaclab_tasks.direct.factory.factory_env_cfg import CtrlCfg, FactoryTaskPegInsertCfg

from .rebot_gravity import gravity_torque


ARM_JOINTS = [f"Joint_{index}" for index in range(1, 7)]
# Tool pointing down at x=0.20 m.  Valid for the XML J2 range [0, 180 deg] with
# >=25 deg margin on every arm joint (the old 60-deg-limit pose left J4 8 deg).
ARM_HOME = [0.000061041, 1.340906024, -0.903939962, 1.133828998, 0.000241180, -0.000004485]
REBOT_ARM_EFFORT_LIMIT = 50.0
# Real-robot joint speed cap, mirrored in rebot.xml <numeric name="rebot_arm_velocity_limit">.
REBOT_ARM_VELOCITY_LIMIT = 3.0
# Per-reset joint friction randomization.  The XML nominal is frictionloss=2.0 N*m and
# damping=0.2 N*m*s/rad.  MuJoCo's soft frictionloss lets joints creep under loads
# below 2 N*m while PhysX sticks, which matters most for the light wrist joints, so
# J4-J6 are randomized down to zero.  Static == dynamic because MuJoCo has one value.
REBOT_JOINT_FRICTION_RANGES = {"Joint_[1-3]": (1.0, 2.0), "Joint_[4-6]": (0.0, 2.0)}
REBOT_JOINT_VISCOUS_FRICTION_RANGE = (0.1, 0.3)
REBOT_PEG_TIP_OFFSET_M = 0.075
REBOT_USD = str(Path(__file__).resolve().parents[1] / "rebot_assets/rebot.usd")


def randomize_arm_joint_friction(env, env_ids, asset_cfg: SceneEntityCfg, friction_ranges, viscous_range):
    """Resample static/dynamic (Coulomb) and viscous joint friction for the reset envs."""
    robot = env.scene[asset_cfg.name]
    if env_ids is None:
        env_ids = torch.arange(env.scene.num_envs, device=robot.device)
    joint_ids, coulomb_bounds = [], []
    for expr, bounds in friction_ranges.items():
        ids, _ = robot.find_joints(expr)
        joint_ids += ids
        coulomb_bounds += [bounds] * len(ids)
    low, high = torch.tensor(coulomb_bounds, device=robot.device).T
    shape = (len(env_ids), len(joint_ids))
    coulomb = low + (high - low) * torch.rand(shape, device=robot.device)
    viscous = torch.empty(shape, device=robot.device).uniform_(*viscous_range)
    robot.write_joint_friction_coefficient_to_sim(
        joint_friction_coeff=coulomb,
        joint_dynamic_friction_coeff=coulomb,
        joint_viscous_friction_coeff=viscous,
        joint_ids=joint_ids,
        env_ids=env_ids,
    )


@configclass
class RebotEventCfg:
    arm_joint_friction = EventTermCfg(
        func=randomize_arm_joint_friction,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("robot"),
            "friction_ranges": REBOT_JOINT_FRICTION_RANGES,
            "viscous_range": REBOT_JOINT_VISCOUS_FRICTION_RANGE,
        },
    )


@configclass
class RebotCtrlCfg(CtrlCfg):
    reset_joints = ARM_HOME
    default_dof_pos_tensor = ARM_HOME


@configclass
class RebotFactoryPegInsertCfg(FactoryTaskPegInsertCfg):
    episode_length_s = 20.0
    ctrl = RebotCtrlCfg()
    events = RebotEventCfg()
    robot = ArticulationCfg(
        prim_path="/World/envs/env_.*/Robot",
        spawn=sim_utils.UsdFileCfg(
            usd_path=REBOT_USD,
            activate_contact_sensors=True,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=False,
                max_depenetration_velocity=5.0,
                linear_damping=0.0,
                angular_damping=0.0,
                max_linear_velocity=1000.0,
                max_angular_velocity=3666.0,
                enable_gyroscopic_forces=True,
                solver_position_iteration_count=192,
                solver_velocity_iteration_count=1,
                max_contact_impulse=1e32,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True,
                solver_position_iteration_count=192,
                solver_velocity_iteration_count=1,
            ),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.005, rest_offset=0.0),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            joint_pos={**dict(zip(ARM_JOINTS, ARM_HOME)), "Joint_ee_[12]": 0.005},
        ),
        actuators={
            "arm": ImplicitActuatorCfg(
                joint_names_expr=ARM_JOINTS,
                stiffness=0.0,
                damping=0.0,
                friction=2.0,
                dynamic_friction=2.0,
                viscous_friction=0.2,
                armature=0.0,
                effort_limit_sim=REBOT_ARM_EFFORT_LIMIT,
                velocity_limit_sim=REBOT_ARM_VELOCITY_LIMIT,
            ),
            "fingers": ImplicitActuatorCfg(
                joint_names_expr=["Joint_ee_[12]"],
                stiffness=500.0,
                damping=0.0,
                friction=2.0,
                dynamic_friction=2.0,
                viscous_friction=0.2,
                effort_limit_sim=100.0,
                velocity_limit_sim=0.1,
            ),
        },
    )


class RebotFactoryEnv(FactoryEnv):
    cfg: RebotFactoryPegInsertCfg

    def get_handheld_asset_relative_pose(self):
        pos, quat = super().get_handheld_asset_relative_pose()
        pos[:, 2] = REBOT_PEG_TIP_OFFSET_M
        return pos, quat

    def _init_tensors(self):
        self.ctrl_target_joint_pos = torch.zeros((self.num_envs, self._robot.num_joints), device=self.device)
        self.ema_factor = self.cfg.ctrl.ema_factor
        self.dead_zone_thresholds = None
        self.fixed_pos_obs_frame = torch.zeros((self.num_envs, 3), device=self.device)
        self.init_fixed_pos_obs_noise = torch.zeros((self.num_envs, 3), device=self.device)

        self.arm_joint_ids, arm_names = self._robot.find_joints(ARM_JOINTS, preserve_order=True)
        self.finger_joint_ids, finger_names = self._robot.find_joints("Joint_ee_[12]")
        assert arm_names == ARM_JOINTS, arm_names
        assert set(finger_names) == {"Joint_ee_1", "Joint_ee_2"}, finger_names
        self.left_finger_body_idx = self._robot.body_names.index("ee_1")
        self.right_finger_body_idx = self._robot.body_names.index("ee_2")
        self.fingertip_body_idx = self._robot.body_names.index("Tool")

        self.last_update_timestamp = 0.0
        self.prev_fingertip_pos = torch.zeros((self.num_envs, 3), device=self.device)
        self.prev_fingertip_quat = torch.tensor([1.0, 0.0, 0.0, 0.0], device=self.device).repeat(
            self.num_envs, 1
        )
        self.prev_joint_pos = torch.zeros((self.num_envs, len(ARM_JOINTS)), device=self.device)
        self.ep_succeeded = torch.zeros((self.num_envs,), dtype=torch.long, device=self.device)
        self.ep_success_times = torch.zeros((self.num_envs,), dtype=torch.long, device=self.device)

    def _compute_intermediate_values(self, dt):
        self.fixed_pos = self._fixed_asset.data.root_pos_w - self.scene.env_origins
        self.fixed_quat = self._fixed_asset.data.root_quat_w
        self.held_pos = self._held_asset.data.root_pos_w - self.scene.env_origins
        self.held_quat = self._held_asset.data.root_quat_w

        tool_data = self._robot.data
        self.fingertip_midpoint_pos = tool_data.body_pos_w[:, self.fingertip_body_idx] - self.scene.env_origins
        self.fingertip_midpoint_quat = tool_data.body_quat_w[:, self.fingertip_body_idx]
        self.fingertip_midpoint_linvel = tool_data.body_lin_vel_w[:, self.fingertip_body_idx]
        self.fingertip_midpoint_angvel = tool_data.body_ang_vel_w[:, self.fingertip_body_idx]
        jacobians = self._robot.root_physx_view.get_jacobians()
        self.fingertip_midpoint_jacobian = jacobians[
            :, self.fingertip_body_idx - 1, 0:6, self.arm_joint_ids
        ]
        self.joint_pos = tool_data.joint_pos.clone()
        self.joint_vel = tool_data.joint_vel.clone()

        self.ee_linvel_fd = (self.fingertip_midpoint_pos - self.prev_fingertip_pos) / dt
        self.prev_fingertip_pos = self.fingertip_midpoint_pos.clone()
        rot_diff_quat = torch_utils.quat_mul(
            self.fingertip_midpoint_quat, torch_utils.quat_conjugate(self.prev_fingertip_quat)
        )
        rot_diff_quat *= torch.sign(rot_diff_quat[:, 0]).unsqueeze(-1)
        self.ee_angvel_fd = axis_angle_from_quat(rot_diff_quat) / dt
        self.prev_fingertip_quat = self.fingertip_midpoint_quat.clone()
        arm_pos = self.joint_pos[:, self.arm_joint_ids]
        self.joint_vel_fd = (arm_pos - self.prev_joint_pos) / dt
        self.prev_joint_pos = arm_pos.clone()
        self.last_update_timestamp = self._robot._data._sim_timestamp

    def _get_factory_obs_state_dict(self):
        obs_dict, state_dict = super()._get_factory_obs_state_dict()
        arm_pos = self.joint_pos[:, self.arm_joint_ids]
        state_dict["joint_pos"] = torch.cat((arm_pos, torch.zeros_like(arm_pos[:, :1])), dim=1)
        return obs_dict, state_dict

    def _get_curr_successes(self, success_threshold, check_rot=False):
        held_pos, _ = factory_utils.get_held_base_pose(
            self.held_pos, self.held_quat, self.cfg_task.name, self.cfg_task.fixed_asset_cfg, self.num_envs, self.device
        )
        target_pos, _ = factory_utils.get_target_held_base_pose(
            self.fixed_pos, self.fixed_quat, self.cfg_task.name, self.cfg_task.fixed_asset_cfg, self.num_envs, self.device
        )
        local_error = torch_utils.quat_rotate_inverse(self.fixed_quat, held_pos - target_pos)
        centered = torch.linalg.vector_norm(local_error[:, :2], dim=1) < 0.0025
        return torch.logical_and(centered, local_error[:, 2] < self.cfg_task.fixed_asset_cfg.height * success_threshold)

    def generate_ctrl_signals(
        self, ctrl_target_fingertip_midpoint_pos, ctrl_target_fingertip_midpoint_quat, ctrl_target_gripper_dof_pos
    ):
        pos_error, rot_error = factory_control.get_pose_error(
            self.fingertip_midpoint_pos,
            self.fingertip_midpoint_quat,
            ctrl_target_fingertip_midpoint_pos,
            ctrl_target_fingertip_midpoint_quat,
            jacobian_type="geometric",
            rot_error_type="axis_angle",
        )
        pose_error = torch.cat((pos_error, rot_error), dim=1)
        self.applied_wrench = factory_control._apply_task_space_gains(
            pose_error,
            self.fingertip_midpoint_linvel,
            self.fingertip_midpoint_angvel,
            self.task_prop_gains,
            self.task_deriv_gains,
        )
        arm_torque = (self.fingertip_midpoint_jacobian.transpose(1, 2) @ self.applied_wrench.unsqueeze(-1)).squeeze(-1)
        arm_torque += gravity_torque(self.joint_pos[:, self.arm_joint_ids])
        self.joint_torque = torch.zeros_like(self.joint_pos)
        self.joint_torque[:, self.arm_joint_ids] = torch.clamp(
            arm_torque, -REBOT_ARM_EFFORT_LIMIT, REBOT_ARM_EFFORT_LIMIT
        )
        self.ctrl_target_joint_pos[:, self.finger_joint_ids] = ctrl_target_gripper_dof_pos
        self._robot.set_joint_position_target(self.ctrl_target_joint_pos)
        self._robot.set_joint_effort_target(self.joint_torque)

    def close_gripper_in_place(self):
        self.generate_ctrl_signals(self.fingertip_midpoint_pos, self.fingertip_midpoint_quat, 0.0)

    def _apply_action(self):
        if self.last_update_timestamp < self._robot._data._sim_timestamp:
            self._compute_intermediate_values(dt=self.physics_dt)
        pos_target = self.fingertip_midpoint_pos + self.actions[:, :3] * self.pos_threshold
        fixed_frame = self.fixed_pos_obs_frame + self.init_fixed_pos_obs_noise
        pos_target = fixed_frame + torch.clip(
            pos_target - fixed_frame, -self.cfg.ctrl.pos_action_bounds[0], self.cfg.ctrl.pos_action_bounds[1]
        )
        rot_action = self.actions[:, 3:6] * self.rot_threshold
        angle = torch.linalg.vector_norm(rot_action, dim=-1)
        axis = rot_action / angle.unsqueeze(-1)
        delta_quat = torch_utils.quat_from_angle_axis(angle, axis)
        delta_quat = torch.where(
            angle.unsqueeze(-1) > 1e-6,
            delta_quat,
            torch.tensor([1.0, 0.0, 0.0, 0.0], device=self.device).repeat(self.num_envs, 1),
        )
        self.generate_ctrl_signals(pos_target, torch_utils.quat_mul(delta_quat, self.fingertip_midpoint_quat), 0.0)

    def set_pos_inverse_kinematics(
        self, ctrl_target_fingertip_midpoint_pos, ctrl_target_fingertip_midpoint_quat, env_ids
    ):
        ik_time = 0.0
        while ik_time < 0.25:
            pos_error, rot_error = factory_control.get_pose_error(
                self.fingertip_midpoint_pos[env_ids],
                self.fingertip_midpoint_quat[env_ids],
                ctrl_target_fingertip_midpoint_pos[env_ids],
                ctrl_target_fingertip_midpoint_quat[env_ids],
                jacobian_type="geometric",
                rot_error_type="axis_angle",
            )
            delta_pose = torch.cat((pos_error, rot_error), dim=-1)
            delta_joint_pos = factory_control.get_delta_dof_pos(
                delta_pose, "dls", self.fingertip_midpoint_jacobian[env_ids], self.device
            )
            arm_pos = self.joint_pos[env_ids][:, self.arm_joint_ids] + delta_joint_pos
            limits = self._robot.data.soft_joint_pos_limits[env_ids][:, self.arm_joint_ids]
            self.joint_pos[env_ids[:, None], self.arm_joint_ids] = torch.clamp(
                arm_pos, limits[..., 0], limits[..., 1]
            )
            self.joint_vel[env_ids] = 0.0
            self.ctrl_target_joint_pos[env_ids[:, None], self.arm_joint_ids] = self.joint_pos[
                env_ids[:, None], self.arm_joint_ids
            ]
            self._robot.write_joint_state_to_sim(self.joint_pos, self.joint_vel)
            self._robot.set_joint_position_target(self.ctrl_target_joint_pos)
            self.step_sim_no_action()
            ik_time += self.physics_dt
        return pos_error, rot_error

    def _set_franka_to_default_pose(self, joints, env_ids):
        joint_pos = self._robot.data.default_joint_pos[env_ids].clone()
        joint_pos[:, self.arm_joint_ids] = torch.tensor(self.cfg.ctrl.reset_joints, device=self.device)
        joint_pos[:, self.finger_joint_ids] = self.cfg_task.held_asset_cfg.diameter / 2 * 1.25
        joint_vel = torch.zeros_like(joint_pos)
        self.ctrl_target_joint_pos[env_ids] = joint_pos
        self._robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        self._robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
        self._robot.reset(env_ids)
        self._robot.set_joint_effort_target(torch.zeros_like(joint_pos), env_ids=env_ids)
        self.step_sim_no_action()

    def randomize_initial_state(self, env_ids):
        """Reset to the planned 4 cm approach pose along the peg/hole axis."""
        physics = sim_utils.SimulationContext.instance().physics_sim_view
        physics.set_gravity(carb.Float3(0.0, 0.0, 0.0))
        self._set_franka_to_default_pose([], env_ids)

        flip = torch.tensor([0.0, 0.0, 1.0, 0.0], device=self.device).repeat(self.num_envs, 1)
        identity = torch.tensor([1.0, 0.0, 0.0, 0.0], device=self.device).repeat(self.num_envs, 1)
        peg_quat, peg_pos = torch_utils.tf_combine(
            self.fingertip_midpoint_quat, self.fingertip_midpoint_pos, flip, torch.zeros((self.num_envs, 3), device=self.device)
        )
        relative_pos, relative_quat = self.get_handheld_asset_relative_pose()
        asset_quat, asset_pos = torch_utils.tf_inverse(relative_quat, relative_pos)
        held_quat, held_pos = torch_utils.tf_combine(peg_quat, peg_pos, asset_quat, asset_pos)
        _, approach = torch_utils.tf_combine(
            peg_quat, torch.zeros_like(held_pos), identity, torch.tensor([0.0, 0.0, 0.04], device=self.device).repeat(self.num_envs, 1)
        )

        fixed_state = self._fixed_asset.data.default_root_state.clone()
        fixed_state[:, :3] = held_pos - approach + self.scene.env_origins
        fixed_state[:, 3:7] = peg_quat
        fixed_state[:, 7:] = 0.0
        self._fixed_asset.write_root_pose_to_sim(fixed_state[:, :7], env_ids=env_ids)
        self._fixed_asset.write_root_velocity_to_sim(fixed_state[:, 7:], env_ids=env_ids)
        self._fixed_asset.reset(env_ids)

        held_state = self._held_asset.data.default_root_state.clone()
        held_state[:, :3] = held_pos + self.scene.env_origins
        held_state[:, 3:7] = held_quat
        held_state[:, 7:] = 0.0
        self._held_asset.write_root_pose_to_sim(held_state[:, :7], env_ids=env_ids)
        self._held_asset.write_root_velocity_to_sim(held_state[:, 7:], env_ids=env_ids)
        self._held_asset.reset(env_ids)
        self.step_sim_no_action()

        physics.set_gravity(carb.Float3(*self.cfg.sim.gravity))
        self.task_prop_gains = self.default_gains
        self.task_deriv_gains = factory_utils.get_deriv_gains(self.default_gains)
        for _ in range(int(0.25 / self.physics_dt)):
            self.close_gripper_in_place()
            self.step_sim_no_action()

        tip_local = torch.tensor([0.0, 0.0, self.cfg_task.fixed_asset_cfg.height], device=self.device).repeat(self.num_envs, 1)
        _, self.fixed_pos_obs_frame = torch_utils.tf_combine(self.fixed_quat, self.fixed_pos, identity, tip_local)
        self.init_fixed_pos_obs_noise.zero_()
        self.prev_joint_pos = self.joint_pos[:, self.arm_joint_ids].clone()
        self.prev_fingertip_pos = self.fingertip_midpoint_pos.clone()
        self.prev_fingertip_quat = self.fingertip_midpoint_quat.clone()
        self.actions.zero_()
        self.prev_actions = torch.zeros_like(self.actions)
        self.ee_angvel_fd.zero_()
        self.ee_linvel_fd.zero_()
