# PegInsert 实验记录

## 环境冻结

- [x] Isaac Lab v2.3.2 源码固定
- [x] Isaac Sim 5.1.0 安装
- [x] 创建标准 Conda 环境 `isaaclab232`
- [x] 安装 PyTorch 2.7.0 + cu128 与 rl_games
- [x] Isaac Sim 运行时识别 RTX 4060 Laptop GPU
- [ ] 保存 `system_info.txt`、`pip_freeze.txt` 和完整版本记录

## 验收进度

- [x] Cartpole（16 env）
- [x] Factory PegInsert 零动作（1 env）
- [x] Factory PegInsert 随机动作（1 env）
- [x] Factory 云端资产可访问并已缓存
- [ ] PPO debug（1/4/16 env）
- [ ] 正式 128 env baseline
- [x] 3 seeds 的训练与量化评估
- [x] 最终 checkpoint 单环境回放视频

## 128 环境 PPO baseline（云端 RTX 4090）

| 训练 seed | 最终 reward |
| --- | ---: |
| 0 | 370.69455 |
| 1 | 360.96570 |
| 2 | 364.90952 |

## Headless 定量评估（最终，2026-09-02）

统一使用确定性策略、`eval_seed=1000–1004`、128 环境、每个模型每个评估 seed 1024 episode。成功判据使用 Factory 原生 `infos["successes"]`，不改变任务阈值。

| 训练 seed | 成功数 / 5,120 | 成功率 | 平均首次成功时间 |
| --- | ---: | ---: | ---: |
| 0 | 4,976 | 97.19% ± 0.50% | 1.79 ± 0.02 s |
| 1 | 5,033 | 98.30% ± 0.31% | 1.90 ± 0.03 s |
| 2 | 5,068 | 98.98% ± 0.27% | 1.90 ± 0.04 s |
| 跨训练 seed | 15,077 / 15,360 | 98.16% ± 0.91% | 1.86 ± 0.06 s |

## 回放

- 三个最终 checkpoint 均以 `seed=1000`、单环境、200 控制步完成 headless 录制。
- 录制时使用 `--disable_fabric`；这是云镜像中单环境录制避开 Fabric 克隆错误所需的官方启动选项。

## 备注

只要官方 baseline 尚未完成，不修改 task、reward、控制器、网络或 PPO 参数。
