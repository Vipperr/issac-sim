#!/usr/bin/env python3
"""Plot policy output vs arm response for recorded Factory episodes.

Follows the fixed evaluation protocol: for every recorded episode emit 18 independent
static PNGs, one per dimension, in three groups:

  1-6   raw policy action (pre-EMA `u_t`)
  7-12  executed EMA action (`a_t = ema*u_t + (1-ema)*a_(t-1)`)
  13-18 fingertip pose actually reached (X/Y/Z in m, roll/pitch/yaw in deg)

No overlay of multiple dimensions, no interactive output.

Usage:
    plot_policy_eval.py --out_dir DIR [--label LABEL] TRAJECTORY.json [TRAJECTORY.json ...]
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ACTION_NAMES = ["dx", "dy", "dz", "rx", "ry", "rz"]
ACTION_DESC = [
    "translation X (world/base)",
    "translation Y (world/base)",
    "translation Z (world/base, +Z up)",
    "rotation about X (world/base)",
    "rotation about Y (world/base)",
    "rotation about Z (world/base)",
]
POSE_NAMES = ["x", "y", "z", "roll", "pitch", "yaw"]
POSE_DESC = [
    "fingertip X (m)",
    "fingertip Y (m)",
    "fingertip Z (m)",
    "fingertip roll (deg)",
    "fingertip pitch (deg)",
    "fingertip yaw (deg)",
]


def euler_xyz_from_quat_wxyz(quat: np.ndarray):
    """Roll/pitch/yaw (radians) from wxyz quaternions, Isaac Lab convention."""
    w, x, y, z = quat[:, 0], quat[:, 1], quat[:, 2], quat[:, 3]
    roll = np.arctan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2.0 * (w * y - z * x), -1.0, 1.0))
    yaw = np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return roll, pitch, yaw


RESET_JUMP_M = 5e-3  # a single control step cannot move the fingertip this far here
RESET_NEAR_M = 2e-3  # ... and a reset snapshot lands back on the initial pose


def drop_reset_artifact(poses: np.ndarray, initial_pose) -> tuple:
    """Drop the trailing pose sample if it is a post-reset snapshot.

    The recording loop samples fingertip pose *after* env.step(); on the terminating
    step DirectRLEnv has already reset the env, so the last sample is the reset pose,
    not the pose the policy actually reached.  It shows up as a jump that is both
    physically impossible for one control step and lands back on the initial pose.
    Returns (poses, dropped).
    """
    if len(poses) < 3:
        return poses, False
    init = np.asarray(initial_pose, dtype=float)
    last, prev = poses[-1], poses[-2]
    jumped = np.linalg.norm(last - prev) > RESET_JUMP_M
    back_at_start = np.linalg.norm(last - init) < RESET_NEAR_M
    if jumped and back_at_start:
        return poses[:-1], True
    return poses, False


def _style(ax, t_end, first_success_t):
    ax.axhline(0, color="0.45", linewidth=0.7, linestyle="--")
    ax.set_xlim(0, t_end)
    ax.grid(True, alpha=0.25)
    if first_success_t is not None:
        ax.axvline(first_success_t, color="tab:green", linewidth=1.1, linestyle=":")
        ax.annotate(
            f"first success @ {first_success_t:.2f}s",
            xy=(first_success_t, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(4, -12),
            textcoords="offset points",
            color="tab:green",
            fontsize=8,
        )


def make_plots(traj: dict, out_dir: Path, label: str) -> list:
    dt = float(traj["control_dt_seconds"])
    seed = traj.get("seed")
    first_success_step = traj.get("first_success_step")
    first_success_t = None if first_success_step is None else (first_success_step - 1) * dt

    raw = np.asarray(traj["raw_actions"], dtype=float)
    ema = np.asarray(traj["ema_actions"], dtype=float)
    pose = np.asarray(traj["fingertip_positions"], dtype=float)
    quat = np.asarray(traj["fingertip_quaternions_wxyz"], dtype=float)

    pose, _ = drop_reset_artifact(pose, traj["initial_fingertip_position"])
    quat = quat[: len(pose)]
    roll, pitch, yaw = euler_xyz_from_quat_wxyz(quat)
    rpy = np.degrees(np.stack([np.unwrap(roll), np.unwrap(pitch), np.unwrap(yaw)], axis=1))

    t_raw = np.arange(len(raw)) * dt
    t_ema = np.arange(len(ema)) * dt
    t_pose = np.arange(len(pose)) * dt

    written = []
    groups = [
        ("raw_action", raw, ACTION_NAMES, ACTION_DESC, "raw policy action (pre-EMA), normalized", -1.05, 1.05),
        ("ema_action", ema, ACTION_NAMES, ACTION_DESC, "executed EMA action, normalized", -1.05, 1.05),
        ("fingertip", np.hstack([pose, rpy]), POSE_NAMES, POSE_DESC, "fingertip pose reached after the step", None, None),
    ]

    idx = 0
    for group_name, data, names, descs, ylab, ylo, yhi in groups:
        for dim in range(data.shape[1]):
            idx += 1
            t = t_pose if group_name == "fingertip" else (t_raw if group_name == "raw_action" else t_ema)
            y = data[:, dim]
            fig, ax = plt.subplots(figsize=(10, 3.2), dpi=160)
            ax.plot(t, y, linewidth=1.15)
            _style(ax, t[-1] if len(t) else 1.0, first_success_t if group_name != "fingertip" else None)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel(ylab)
            if ylo is not None:
                ax.set_ylim(ylo, yhi)
            ax.set_title(f"{label} — seed {seed} — {group_name} {names[dim]}: {descs[dim]}")
            fig.tight_layout()
            path = out_dir / f"{idx:02d}_{group_name}_{names[dim]}.png"
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            written.append(path)

    return written


def summarise(traj: dict) -> dict:
    """Quantitative command-vs-response check for this episode.

    Alignment: ema[k] is the action applied during control step k, and pose[k] is the
    fingertip pose sampled right after that step.  So the displacement produced by
    ema[k] is pose[k] - pose[k-1] (pose[-1] being the initial pose), NOT pose[k+1]-pose[k].
    """
    dt = float(traj["control_dt_seconds"])
    raw = np.asarray(traj["raw_actions"], dtype=float)
    ema = np.asarray(traj["ema_actions"], dtype=float)
    init = np.asarray(traj["initial_fingertip_position"], dtype=float)
    pose, dropped = drop_reset_artifact(np.asarray(traj["fingertip_positions"], dtype=float), init)

    pose_ext = np.vstack([init, pose])  # pose_ext[k] = pose after k steps
    disp = np.diff(pose_ext, axis=0)  # disp[k] = response to ema[k]
    n = min(len(ema), len(disp))
    disp_mm = disp[:n, :3] * 1000.0

    out = {
        "n_action_samples": len(raw),
        "n_pose_samples": len(pose),
        "reset_artifact_dropped": bool(dropped),
        "duration_s": len(raw) * dt,
    }
    if traj.get("first_success_step"):
        out["first_success_s"] = (traj["first_success_step"] - 1) * dt

    for dim, name in enumerate(ACTION_NAMES[:3]):
        cmd = ema[:n, dim]
        d = disp_mm[:, dim]
        strong = np.abs(cmd) > 0.5
        moving = np.abs(d) > 0.01  # ignore sub-micron numerical noise
        agree = (np.sign(d[moving]) == np.sign(cmd[moving])).mean() if moving.sum() else float("nan")
        out[f"{name}_cmd_mm_per_step_when_pos"] = float(d[cmd > 0.5].mean()) if (cmd > 0.5).sum() else None
        out[f"{name}_cmd_mm_per_step_when_neg"] = float(d[cmd < -0.5].mean()) if (cmd < -0.5).sum() else None
        out[f"{name}_sign_agreement"] = float(agree)
        out[f"{name}_n_strong_steps"] = int(strong.sum())
        # steps where the policy pushes hard but the arm does not move: jam / saturation
        out[f"{name}_jammed_steps"] = int((strong & ~moving).sum())
        out[f"{name}_total_travel_mm"] = float(np.abs(d).sum())
        out[f"{name}_net_mm"] = float(d.sum())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trajectories", nargs="+", type=Path)
    ap.add_argument("--out_dir", type=Path, required=True)
    ap.add_argument("--label", default=None, help="Label used in titles (default: file stem)")
    ap.add_argument("--summary", type=Path, default=None, help="Write the command-vs-response summary JSON here")
    args = ap.parse_args()

    summaries = {}
    for path in args.trajectories:
        traj = json.loads(path.read_text())
        label = args.label or path.stem
        out_dir = args.out_dir / path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        written = make_plots(traj, out_dir, label)
        summaries[path.stem] = summarise(traj)
        print(f"{path.stem}: wrote {len(written)} PNGs to {out_dir}")

    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summaries, indent=2, sort_keys=True) + "\n")
        print(f"summary -> {args.summary}")


if __name__ == "__main__":
    main()
