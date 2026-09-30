"""Gravity torque from Rebot's MuJoCo-identified minimal dynamic model."""

import torch


DH_OFFSETS = (0.0, torch.pi, 2.922030233688906, 0.219562419900887, -torch.pi / 2, -torch.pi / 2)

# Relevant entries from rebot_min_param_sim.xlsx. At dq=ddq=0 the generated
# 6x36 regressor only uses these ten parameters (zero-based indices shown).
P06, P07 = 1.2304649143480979, 0.0070016720775324254
P13, P14 = 0.71747672865512901, -0.062130363550261317
P20, P21 = 0.1534572423183084, -0.010993987787996861
P27, P28 = 0.003972735893533216, 0.059300147931318672
P34, P35 = 0.001194476814541463, -0.0031005282679134648


def gravity_torque(joint_pos: torch.Tensor) -> torch.Tensor:
    """Return identified gravity compensation torque for motor-frame joint positions."""
    q = joint_pos + joint_pos.new_tensor(DH_OFFSETS)
    q2, q3, q4, q5, q6 = q.unbind(dim=-1)[1:]
    q23, q234 = q2 + q3, q2 + q3 + q4
    s2, c2 = torch.sin(q2), torch.cos(q2)
    s23, c23 = torch.sin(q23), torch.cos(q23)
    s234, c234 = torch.sin(q234), torch.cos(q234)
    s5, c5 = torch.sin(q5), torch.cos(q5)
    s6, c6 = torch.sin(q6), torch.cos(q6)

    g2 = 9.81 * (-P06 * c2 + P07 * s2)
    g3 = 9.81 * (-P13 * c23 + P14 * s23)
    g4 = 9.81 * (-P20 * c234 + P21 * s234)
    g5 = 9.81 * c234 * (-P27 * c5 + P28 * s5)
    g6 = 9.81 * (
        -P34 * (s6 * s234 + c5 * c6 * c234)
        + P35 * (s6 * c5 * c234 - s234 * c6)
    )
    tau5 = 9.81 * s234 * (P27 * s5 + P28 * c5 + P34 * s5 * c6 - P35 * s5 * s6)
    tau6 = 9.81 * (
        P34 * (s6 * s234 * c5 + c6 * c234)
        + P35 * (-s6 * c234 + s234 * c5 * c6)
    )
    zero = torch.zeros_like(g2)
    return torch.stack(
        (zero, g2 + g3 + g4 + g5 + g6, g3 + g4 + g5 + g6, g4 + g5 + g6, tau5, tau6),
        dim=-1,
    )


def _self_check() -> None:
    positions = torch.tensor(
        [
            [0.000061041, 1.340906024, -0.903939962, 1.133828998, 0.000241180, -0.000004485],
            [0.0, 0.0, -1.5, 0.3, -0.4, 0.7],
            [0.4, 2.2, -2.0, -0.5, 0.8, -0.9],
        ],
        dtype=torch.float64,
    )
    expected = torch.tensor(
        [
            [
                0.0,
                -4.416652634354195,
                -7.100368942008225,
                -0.09613598305977651,
                -0.00841600129078483,
                -0.000002864601439606,
            ],
            [
                0.0,
                13.05438396864982,
                0.9835231588949841,
                -0.6624678865617437,
                0.2311083225160067,
                -0.01605918748316659,
            ],
            [
                0.0,
                -15.98050009163394,
                -8.821252308977485,
                -1.79607483571337,
                -0.1210822962802007,
                -0.03033824079812556,
            ],
        ],
        dtype=torch.float64,
    )
    torch.testing.assert_close(gravity_torque(positions), expected, rtol=1e-12, atol=1e-12)


if __name__ == "__main__":
    _self_check()
