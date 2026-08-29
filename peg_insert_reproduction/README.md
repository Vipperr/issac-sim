# Isaac Factory PegInsert 复现

本目录只保存复现实验的记录、日志、checkpoint 和运行脚本；官方任务代码位于相邻的 `../IsaacLab`，保持不修改。

## 固定配置

- Isaac Lab: `v2.3.2` (`37ddf626871758333d6ed89cf64ad702aef127d0`)
- Isaac Sim: `5.1.0.0`
- Conda: `isaaclab232` (`/home/xiatenghui/anaconda3/envs/isaaclab232`)
- Python: `3.11`
- PyTorch / CUDA wheel: `2.7.0+cu128`
- RL framework: `rl_games`
- Task: `Isaac-Factory-PegInsert-Direct-v0`

## 使用方式

```bash
conda activate isaaclab232
cd /home/xiatenghui/work_space/isaac-sim/IsaacLab

# 记录当前软件与硬件信息
bash ../peg_insert_reproduction/scripts/collect_system_info.sh

# 先执行单环境零动作与随机动作验证
bash ../peg_insert_reproduction/scripts/verify_factory.sh

# 验证完成后启动官方 PPO baseline；默认 1 个环境用于显存受限调试
bash ../peg_insert_reproduction/scripts/train_baseline.sh 1
```

RTX 4060 Laptop GPU 有 8 GB 显存，因此先以 1 个环境验证；计划中的 128 环境正式 baseline 很可能需要更大显存。不要将低并行度训练结果标记为严格的官方 baseline。

