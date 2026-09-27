#!/usr/bin/env python3
"""Verify the Isaac USD/URDF bridge against the source MuJoCo XML."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


ARM_JOINTS = [f"Joint_{index}" for index in range(1, 7)]
FINGER_JOINTS = ["Joint_ee_1", "Joint_ee_2"]
DYNAMIC_BODIES = [f"Link_{index}" for index in range(1, 7)] + ["ee_1", "ee_2"]


def _numbers(value: str) -> np.ndarray:
    return np.fromstring(value, sep=" ", dtype=np.float64)


def _assert_close(label: str, actual, expected, atol: float = 1.0e-5) -> None:
    if not np.allclose(actual, expected, rtol=1.0e-5, atol=atol):
        raise AssertionError(f"{label}: actual={actual}, expected={expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--xml", required=True, type=Path, help="Source rebot.xml")
    parser.add_argument(
        "--urdf",
        type=Path,
        default=root / "rebot_assets/rebot_description/urdf/rebot.urdf",
    )
    parser.add_argument("--usd", type=Path, default=root / "rebot_assets/rebot.usd")
    args = parser.parse_args()

    try:
        from pxr import Usd
    except ImportError as exc:
        raise RuntimeError("USD validation requires the temporary usd-core package") from exc

    mjcf = ET.parse(args.xml).getroot()
    urdf = ET.parse(args.urdf).getroot()
    stage = Usd.Stage.Open(str(args.usd.resolve()))
    if not stage:
        raise RuntimeError(f"Unable to open USD stage: {args.usd}")

    xml_joints = {joint.get("name"): joint for joint in mjcf.findall(".//joint")}
    urdf_joints = {joint.get("name"): joint for joint in urdf.findall("joint")}
    motors = {
        motor.get("joint"): motor for motor in mjcf.findall("actuator/motor")
    }
    velocity_numeric = mjcf.find("custom/numeric[@name='rebot_arm_velocity_limit']")
    if velocity_numeric is None:
        raise AssertionError("XML is missing <numeric name='rebot_arm_velocity_limit'>")
    xml_velocity_limits = _numbers(velocity_numeric.get("data"))

    for name in ARM_JOINTS + FINGER_JOINTS:
        xml_joint = xml_joints[name]
        urdf_joint = urdf_joints[name]
        xml_range = _numbers(xml_joint.get("range"))
        urdf_limit = urdf_joint.find("limit")
        urdf_range = np.array(
            [float(urdf_limit.get("lower")), float(urdf_limit.get("upper"))]
        )
        _assert_close(f"{name} URDF range", urdf_range, xml_range)

        dynamics = urdf_joint.find("dynamics")
        _assert_close(
            f"{name} damping", float(dynamics.get("damping")), float(xml_joint.get("damping"))
        )
        _assert_close(
            f"{name} friction", float(dynamics.get("friction")), float(xml_joint.get("frictionloss"))
        )

        usd_joint = stage.GetPrimAtPath(f"/robot/joints/{name}")
        if not usd_joint:
            raise AssertionError(f"USD is missing {name}")
        usd_range = np.array(
            [
                usd_joint.GetAttribute("physics:lowerLimit").Get(),
                usd_joint.GetAttribute("physics:upperLimit").Get(),
            ]
        )
        if name in ARM_JOINTS:
            usd_range = np.deg2rad(usd_range)
        _assert_close(f"{name} USD range", usd_range, xml_range)

        if name in ARM_JOINTS:
            xml_velocity = xml_velocity_limits[ARM_JOINTS.index(name)]
            _assert_close(f"{name} URDF velocity", float(urdf_limit.get("velocity")), xml_velocity)
            usd_velocity = np.deg2rad(usd_joint.GetAttribute("physxJoint:maxJointVelocity").Get())
            _assert_close(f"{name} USD velocity", usd_velocity, xml_velocity)

            xml_effort = max(abs(_numbers(motors[name].get("ctrlrange"))))
            urdf_effort = float(urdf_limit.get("effort"))
            usd_effort = usd_joint.GetAttribute("drive:angular:physics:maxForce").Get()
            _assert_close(f"{name} URDF effort", urdf_effort, xml_effort)
            _assert_close(f"{name} USD effort", usd_effort, xml_effort)

    for name in DYNAMIC_BODIES:
        xml_body = mjcf.find(f".//body[@name='{name}']")
        xml_inertial = xml_body.find("inertial")
        usd_body = stage.GetPrimAtPath(f"/robot/{name}")
        _assert_close(
            f"{name} mass",
            usd_body.GetAttribute("physics:mass").Get(),
            float(xml_inertial.get("mass")),
            atol=2.0e-6,
        )
        _assert_close(
            f"{name} center of mass",
            usd_body.GetAttribute("physics:centerOfMass").Get(),
            _numbers(xml_inertial.get("pos")),
            atol=2.0e-6,
        )
        _assert_close(
            f"{name} principal inertia",
            np.sort(usd_body.GetAttribute("physics:diagonalInertia").Get()),
            np.sort(_numbers(xml_inertial.get("diaginertia"))),
            atol=2.0e-7,
        )

    layer_data = stage.GetRootLayer().customLayerData
    source = layer_data.get("rebot_sync_source")
    if source != "rebot_description/urdf/rebot.xml":
        raise AssertionError(f"Unexpected USD synchronization source: {source!r}")
    xml_sha256 = hashlib.sha256(args.xml.read_bytes()).hexdigest()
    if layer_data.get("rebot_sync_source_sha256") != xml_sha256:
        raise AssertionError(
            f"USD was synced from XML {layer_data.get('rebot_sync_source_sha256')}, current XML is {xml_sha256}"
        )
    print(f"model_sync=ok joints={len(ARM_JOINTS) + len(FINGER_JOINTS)} bodies={len(DYNAMIC_BODIES)}")
    print(f"xml={args.xml.resolve()}")
    print(f"urdf={args.urdf.resolve()}")
    print(f"usd={args.usd.resolve()}")


if __name__ == "__main__":
    main()
