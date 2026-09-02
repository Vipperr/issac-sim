# Isaac Factory PegInsert 官方 PPO Baseline 复现报告

**完成日期：** 2026-09-02（Asia/Shanghai）
**任务：** `Isaac-Factory-PegInsert-Direct-v0`

## 结论

在冻结的 Isaac Lab v2.3.2 配置下，三次独立 PPO 训练均完成 200 epoch。对每个最终 checkpoint 使用 5 个未参与训练的评估随机种子（`1000`–`1004`），每个组合评估 1024 episode；共 15,360 个 episode 中成功 15,077 个，合并成功率为 **98.16%**。以三个训练 seed 的平均表现计算，成功率为 **98.16% ± 0.91%**（样本标准差），平均首次成功时间为 **1.86 ± 0.06 s**。

人工查看三段最终模型回放后未发现异常动作。

## 固定实验条件

- Isaac Lab `v2.3.2`，提交 `37ddf626871758333d6ed89cf64ad702aef127d0`
- Isaac Sim `5.1.0.0`；云端 RTX 4090 24 GB
- 官方 RL-Games PPO 配置：128 环境、200 epoch、horizon 128、minibatch 512
- 训练 seed：`0`、`1`、`2`
- 未修改 Factory 任务、奖励函数、控制器、网络或 PPO 参数
- 评估采用确定性策略；128 环境；每组合 1024 episode；评估 seed `1000`–`1004`
- 成功判据保持 Factory 原生定义：横向偏差小于 2.5 mm，并达到任务规定的插入深度

## 训练结果

| 训练 seed | 最终 reward | 训练时间 |
| --- | ---: | ---: |
| 0 | 370.69455 | 6,237.39 s（103.96 min） |
| 1 | 360.96570 | 6,512.76 s（108.55 min） |
| 2 | 364.90952 | 6,276.39 s（104.61 min） |
| 均值 ± 样本标准差 | 365.52 ± 4.89 | 6,342.18 ± 149.01 s（105.70 ± 2.48 min） |

## Held-out headless 评估

表中每行汇总该训练 seed 在 5 个评估 seed 上的 5,120 episode；行内 `±` 是这 5 个评估 seed 的样本标准差。

| 训练 seed | 成功数 / episode | 成功率 | 平均首次成功时间 |
| --- | ---: | ---: | ---: |
| 0 | 4,976 / 5,120 | 97.19% ± 0.50% | 1.79 ± 0.02 s |
| 1 | 5,033 / 5,120 | 98.30% ± 0.31% | 1.90 ± 0.03 s |
| 2 | 5,068 / 5,120 | 98.98% ± 0.27% | 1.90 ± 0.04 s |
| 跨训练 seed | 15,077 / 15,360 | 98.16% ± 0.91% | 1.86 ± 0.06 s |

最后一行的 `±` 是三个训练 seed 的平均结果之间的样本标准差；合并成功率按全部 episode 直接计算。

## 回放验收

三个最终 checkpoint 均已使用 `eval_seed=1000`、单环境、200 控制步录制 headless 视频，并已人工验收。云镜像在单环境录制时需加 `--disable_fabric` 以绕过 Fabric 克隆错误；这只影响录制启动路径，不改变训练或任务配置。

## 结果位置

```text
/root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/baseline_128_seed{0,1,2}/nn/
/root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/baseline_128_seed{0,1,2}/videos/play/rl-video-step-0.mp4
/root/gpufree-data/isaac-sim/peg_insert_reproduction/logs/eval_seed{0,1,2}_seed{1000..1004}.json
```

## 边界

本报告验证的是该固定仿真设置下的官方 baseline 可重复性，不能直接外推为真实机器人插入成功率，也不覆盖物体、摩擦、传感器或控制延迟等域外变化。后续若研究泛化能力，应单独定义并报告这些扰动实验。
