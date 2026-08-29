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
- [ ] 3 seeds 的训练与量化评估

## 备注

只要官方 baseline 尚未完成，不修改 task、reward、控制器、网络或 PPO 参数。
