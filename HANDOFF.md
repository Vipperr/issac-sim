# Isaac Factory PegInsert — Handoff

更新时间：2026-09-02（Asia/Shanghai）

## 现在在做什么

官方 `Isaac-Factory-PegInsert-Direct-v0` PPO baseline 已完成复现、跨随机种子评估、人工回放验收和本地归档。刚完成三条“首次成功即结束”的近景回放，解决了原 `--video_length 200` 视频会跨 episode、机械臂归位后再次插孔的问题。

当前没有云端训练、评估或录制任务在运行。下一项实际工作应是将本地提交推送到 GitHub；由于本环境没有 GitHub HTTPS 凭据，尚未推送。

## 已完成哪些

### 训练与评估

- 固定 Isaac Lab `v2.3.2`，commit `37ddf626871758333d6ed89cf64ad702aef127d0`；使用云端 RTX 4090（24 GB）。
- 使用官方 RL-Games PPO 配置完成 3 个训练 seed：128 环境、200 epoch、horizon 128、minibatch 512。未改动 Factory 任务、奖励、控制器、网络或 PPO 参数。

| 训练 seed | 最终 reward | 训练时间 |
| --- | ---: | ---: |
| 0 | 370.69455 | 6,237.39 s（103.96 min） |
| 1 | 360.96570 | 6,512.76 s（108.55 min） |
| 2 | 364.90952 | 6,276.39 s（104.61 min） |
| 均值 ± 样本标准差 | 365.52 ± 4.89 | 6,342.18 ± 149.01 s（105.70 ± 2.48 min） |

- 每个训练 seed 在未参与训练的评估 seed `1000`–`1004` 上评估 1,024 episode，共 15,360 episode。

| 训练 seed | 成功数 / 5,120 | 成功率 | 平均首次成功时间 |
| --- | ---: | ---: | ---: |
| 0 | 4,976 | 97.19% ± 0.50% | 1.79 ± 0.02 s |
| 1 | 5,033 | 98.30% ± 0.31% | 1.90 ± 0.03 s |
| 2 | 5,068 | 98.98% ± 0.27% | 1.90 ± 0.04 s |
| 跨训练 seed | 15,077 / 15,360 | 98.16% ± 0.91% | 1.86 ± 0.06 s |

### 视频回放

- 已人工检查默认回放；随后因相机过远，用近景相机重新录制。
- 新增专用录制脚本：从 reset 开始用确定性策略推理，检测 Factory 原生 `infos["logs_rew_curr_success"]`；第一次成功即停止。若任务失败，才在原生 timeout 停止。
- 三条新视频均为单环境、`eval_seed=1000`、1280×720 H.264；没有跨入第二个 episode。

| checkpoint seed | 首次成功步 | 时长 | 本地 SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 22 | 1.47 s | `4a4599037692879f96f9e86ae5e6313764d58b32d2747a70d4cfa509ae05ff86` |
| 1 | 23 | 1.53 s | `f0de978d37e3ce3827ad1a7621500b9c4a2a10420aa23c3ad2f78d3f690f3bc5` |
| 2 | 22 | 1.47 s | `7f612aba5ca3e45ce129f4d730df91996605c32ec83abd8a6ced437f3270596a` |

- 上述三条视频均已从云端同步到本机，并与云端 SHA-256 逐一一致。

### 归档与报告

- 云端最终 checkpoint、训练/评估日志、15 个评估 JSON、旧版近景视频、报告和评估脚本均已同步到本地归档。
- 归档 `peg_insert_reproduction/archive/2026-09-02/` 有 60 个文件、约 612 MB；压缩包 `peg_insert_reproduction/archive/2026-09-02.tar.zst` 为 563 MB。
- 压缩包 SHA-256：`b8e91fac185de086df245bdd7afe8e1314b2452846572933ba0f33a4e228a2ce`；已通过 `zstd -t` 和清单校验。
- 本次新增的“首次成功即停止”视频尚未并入该旧归档；视频已有云端与本地两份并且已经校验。

## 还有哪些没做

1. 为 GitHub 配置交互式 HTTPS 认证或 SSH key 后，执行 `git push origin main`。
2. 若目标是仿真泛化：对摩擦、质量、初始位姿、观测噪声、控制延迟和不同资产做单因素扰动评估。
3. 若目标是真机：先制定限力、限速、急停和人工监护方案，再做单件低速测试；当前仿真结果不能直接当作真机指标。
4. 如需长期保存本次新视频，可在用户确认后将它们加入一个新的归档版本；不要改写已校验的旧归档。

## 关键决策及原因

| 决策 | 原因 |
| --- | --- |
| 固定 Isaac Lab 版本与 commit | 防止任务 API、物理和默认参数漂移，保证结果可追溯。 |
| 正式训练使用云端 4090 | 本机 8 GB 显存仅适合调试，云端能稳定运行 128 环境。 |
| 三个训练 seed、五个 held-out 评估 seed | PPO 存在随机性；报告均值和标准差比单次最高 reward 更可信。 |
| 用原生 `successes` 衡量评估 | reward 不等价于实际插入成功率。 |
| 单环境回放加 `--disable_fabric` | 云镜像的单环境视频路径会出现 Fabric clone 问题；该开关只影响回放路径。 |
| 使用近景 viewer 相机 | 默认 `(7.5, 7.5, 7.5)` 使机械臂太小；当前相机聚焦工作台。 |
| 新视频首次成功即停止 | Factory 的成功不会终止 episode，固定 200 控制步会录到归位和第二次尝试。 |
| `max_episode_length` 仅作视频上限 | 它是失败时的原生 timeout 保护，不是成功视频的固定时长。 |
| 云端/本地使用 SHA-256 校验 | 文件存在或大小相同不足以证明 checkpoint、视频或日志未损坏。 |

## 改过哪些重要文件

### 本机仓库：`/home/xiatenghui/.rebot/issac-sim`

- `peg_insert_reproduction/scripts/evaluate_rl_games.py`：专用 headless 评估脚本；确定性动作，按原生成功指标统计成功数与首次成功时间。
- `peg_insert_reproduction/scripts/record_successful_episode.py`：本次新增；录制一条首次成功即结束的近景 episode，不改 Factory 源码。
- `peg_insert_reproduction/videos/play_until_success/seed{0,1,2}/rl-video-step-0.mp4`：本次新增的三条已校验视频。
- `peg_insert_reproduction/final_report.md`：最终实验结果、统计口径、边界和云端产物位置。
- `peg_insert_reproduction/experiment_log.md`：实验过程和最终汇总。
- `HANDOFF.md`：当前交接文档。
- `peg_insert_reproduction/archive/2026-09-02/` 和 `.tar.zst`：归档；**绝不提交 Git**。

### 云端：`/root/gpufree-data/isaac-sim`

- `IsaacLab/_isaac_sim -> /isaac-sim`：Isaac Lab 运行时软链接；不要删除。
- `IsaacLab/logs/rl_games/Factory/baseline_128_seed{0,1,2}/nn/`：三个最终 checkpoint（注意它们在 `IsaacLab/logs`，不在 `peg_insert_reproduction/logs`）。
- `IsaacLab/logs/rl_games/Factory/baseline_128_seed{0,1,2}/videos/play/rl-video-step-0.mp4`：旧版固定步数的近景回放。
- `peg_insert_reproduction/videos/play_until_success/seed{0,1,2}/rl-video-step-0.mp4`：当前的首次成功即停止近景回放。
- `peg_insert_reproduction/logs/eval_seed{0,1,2}_seed{1000..1004}.json`：15 个原始评估结果。
- `peg_insert_reproduction/logs/baseline_128_seed{0,1,2}.log`：训练日志。

## 当前问题

- GitHub remote 使用 HTTPS，但当前环境没有凭据；此前 `git push origin main` 报错：`fatal: could not read Username for 'https://github.com': No such device or address`。不要把 token、SSH 私钥或云服务器密码写入仓库、日志或本文件。
- 结论仅覆盖固定 Isaac Sim 工况；没有域随机化或真机验证。这是实验边界，不是当前训练故障。

## 接下来怎么做

1. 完成 GitHub 认证后推送本地提交。
2. 用户验收新视频画面与时长；如需更长的成功后停留画面，再给录制脚本增加少量 tail steps，不要恢复固定 200 步录制。
3. 如开展新实验，以当前三 seed 结果为 baseline；每次只改变一个因素，并保留同一 held-out 评估协议。

## 云端命令参考

每次运行 Isaac Lab 前：

```bash
cd /root/gpufree-data/isaac-sim/IsaacLab
TORCH_LIB=/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/torch/lib
export HOME=/root/gpufree-data/home
export LD_LIBRARY_PATH="$TORCH_LIB:$LD_LIBRARY_PATH"
```

训练：

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rl_games/train.py \
  --task Isaac-Factory-PegInsert-Direct-v0 \
  --headless --num_envs 128 --seed SEED \
  agent.params.config.full_experiment_name=baseline_128_seedSEED
```

评估：

```bash
./isaaclab.sh -p /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/evaluate_rl_games.py \
  --task Isaac-Factory-PegInsert-Direct-v0 \
  --headless --num_envs 128 --episodes 1024 --seed EVAL_SEED \
  --checkpoint /absolute/path/to/final_checkpoint.pth \
  --output /root/gpufree-data/isaac-sim/peg_insert_reproduction/logs/eval.json
```

首次成功视频：

```bash
./isaaclab.sh -p /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/record_successful_episode.py \
  --task Isaac-Factory-PegInsert-Direct-v0 --headless --disable_fabric --seed 1000 \
  --checkpoint /absolute/path/to/final_checkpoint.pth \
  --video_folder /root/gpufree-data/isaac-sim/peg_insert_reproduction/videos/play_until_success/seedN
```

## 已踩过的坑：不要重复

- 本机 8 GB GPU 不适合 128 环境正式训练；单张 4090 也不要并发跑多个 Isaac Sim 训练、评估或录制任务。
- `num_envs=1` 不能沿用 PPO 正式训练配置：`1 × 128` batch 小于 `minibatch_size=512` 且无法整除。
- `nvidia-smi` 有占用不代表训练成功；须检查 `MAX EPOCHS NUM!`、`Training time:` 和最终 checkpoint。
- 漏设 `LD_LIBRARY_PATH` 会报 `libtorch_cuda_linalg.so` 缺失；完整运行使用 `./isaaclab.sh -p ...`，不要裸用 `/isaac-sim/python.sh`。
- 单环境视频需要 `--disable_fabric`；默认 viewer 太远，必须使用当前近景相机。
- Factory success 不会结束 episode；`play.py --video_length 200` 会录进重置和新的插孔尝试。用 `record_successful_episode.py`。
- 评估脚本中 RNN state 重置必须在 `torch.inference_mode()` 内，否则会报 inference tensor 的就地更新错误。
- 云端没有 `rsync`；用 `scp` 同步后必须做 SHA-256 校验。
- 归档目录和 `.tar.zst` 约 1.2 GB，不能加入 Git；不要删除云端原始产物。
- 不要把 GitHub token、SSH 私钥或云服务器密码写进命令、Git remote、日志或 `HANDOFF.md`。
