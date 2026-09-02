# Isaac Factory PegInsert — Handoff

更新时间：2026-09-02（Asia/Shanghai）

## 1. 现在在做什么

官方 `Isaac-Factory-PegInsert-Direct-v0` PPO baseline 的复现、定量评估、回放验收和本地归档均已完成。

当前唯一未完成的收尾事项是将已有本地 Git 提交推送到 GitHub：提交已创建，但当前环境没有 GitHub HTTPS 凭据，`git push origin main` 尚未成功。

不要重复训练；云端没有待完成的训练或评估任务。后续工作应在此 baseline 基础上开展泛化/消融实验，或进入受控的真机验证。

## 2. 已完成事项

### 训练与复现

- 固定 Isaac Lab `v2.3.2`，提交 `37ddf626871758333d6ed89cf64ad702aef127d0`。
- 云端 RTX 4090（24 GB）上完成三个独立训练 seed（`0`、`1`、`2`）。
- 每轮使用官方 RL-Games PPO 配置：128 环境、200 epoch、horizon 128、minibatch 512。
- Factory task、奖励函数、控制器、网络和 PPO 参数均未修改。

| 训练 seed | 最终 reward | 训练时间 |
| --- | ---: | ---: |
| 0 | 370.69455 | 6,237.39 s（103.96 min） |
| 1 | 360.96570 | 6,512.76 s（108.55 min） |
| 2 | 364.90952 | 6,276.39 s（104.61 min） |
| 均值 ± 样本标准差 | 365.52 ± 4.89 | 6,342.18 ± 149.01 s（105.70 ± 2.48 min） |

### 定量评估

- 新增专用评估脚本，加载最终 checkpoint 并用确定性策略计算 Factory 原生 `infos["successes"]`。
- 每个训练 seed 在 5 个未参与训练的评估 seed（`1000`–`1004`）上评估；每个组合 128 环境、1024 episode。
- 共完成 15 个组合、15,360 episode；成功 15,077 个，合并成功率为 98.16%。

| 训练 seed | 成功数 / 5,120 | 成功率 | 平均首次成功时间 |
| --- | ---: | ---: | ---: |
| 0 | 4,976 | 97.19% ± 0.50% | 1.79 ± 0.02 s |
| 1 | 5,033 | 98.30% ± 0.31% | 1.90 ± 0.03 s |
| 2 | 5,068 | 98.98% ± 0.27% | 1.90 ± 0.04 s |
| 跨训练 seed | 15,077 / 15,360 | 98.16% ± 0.91% | 1.86 ± 0.06 s |

最后一行的标准差在三个训练 seed 的平均表现上计算；每个训练 seed 行内的标准差在五个评估 seed 上计算。

### 回放与人工验收

- 三个最终 checkpoint 已在 `eval_seed=1000`、单环境、200 控制步条件下录制 headless 视频。
- 初版视频已人工检查，未发现异常动作；因默认相机过远，已用近景相机重新录制当前三段视频。
- 当前视频使用 `env.viewer.eye=[2.0,2.0,1.5]`、`env.viewer.lookat=[0.5,0.0,0.5]`，机械臂和工作台占据画面主体。

### 归档与报告

- 云端最终 checkpoint、全部日志、15 个评估 JSON、视频、报告和评估脚本均已同步到本地。
- 本地归档包含 60 个文件、约 612 MB；其中新视频和近景录制日志已与云端逐项 SHA-256 比对。
- 归档已压缩为 563 MB 的 `.tar.zst`，并通过 `zstd -t` 和文件清单比对。
- 最终报告和实验记录已经同步回云端数据盘。

## 3. 关键决策与原因

| 决策 | 原因 |
| --- | --- |
| 固定 Isaac Lab 版本与 commit | 防止任务 API、物理或默认参数漂移，保证结果可追溯。 |
| 正式训练使用云端 4090 | 本机 8 GB 显存只适合调试，云端已验证可稳定运行 128 环境。 |
| 源码与结果放在云端 `/root/gpufree-data` | 数据盘比系统盘更适合保存长训练的源码、日志和 checkpoint。 |
| 训练 seed 串行运行 | 单张 4090 并行 Isaac Sim 容易竞争 GPU/Kit 资源，降低稳定性。 |
| 用三训练 seed，而不是单次最高 reward | PPO 具有随机性；需报告跨训练 seed 的均值与标准差。 |
| 用 `successes` 而非 reward 判断任务表现 | reward 是优化目标，不等价于 Peg Insert 的实际成功率。 |
| 评估使用独立 seed `1000`–`1004` | 避免只重演训练随机轨迹，衡量固定仿真设置下的随机初态泛化。 |
| 回放保持单环境但加入 `--disable_fabric` | 云镜像在单环境录制时 Fabric 克隆会卡住；该官方开关只影响录制路径。 |
| 回放使用近景 viewer 相机 | 默认 `(7.5, 7.5, 7.5)` 使机械臂过小；当前相机聚焦工作台中心。 |
| 归档后做两端 SHA-256 校验 | 文件存在或大小相同不能证明 checkpoint 未损坏。 |

## 4. 重要文件与路径

### 本机仓库

仓库根目录：`/home/xiatenghui/.rebot/issac-sim`

- `peg_insert_reproduction/final_report.md`
  - 最终结果、统计口径、边界和云端产物位置。
- `peg_insert_reproduction/experiment_log.md`
  - 实验过程记录与最终汇总。
- `peg_insert_reproduction/scripts/evaluate_rl_games.py`
  - 专用 headless 评估脚本；参数包括 `--checkpoint`、`--num_envs`、`--episodes`、`--seed`、`--output`。
- `peg_insert_reproduction/archive/2026-09-02/`
  - 云端产物的本地副本，60 个文件，**不应提交 Git**。
- `peg_insert_reproduction/archive/2026-09-02.tar.zst`
  - 归档压缩包，563 MB，SHA-256：
    `b8e91fac185de086df245bdd7afe8e1314b2452846572933ba0f33a4e228a2ce`。
- `IsaacLab/`
  - 固定版本的官方源码；维持不修改 Factory 实现的原则。

### 云端

云端根目录：`/root/gpufree-data/isaac-sim`

- `IsaacLab/_isaac_sim -> /isaac-sim`
  - Isaac Lab 查找镜像运行时的软链接；不要删除。
- `IsaacLab/logs/rl_games/Factory/baseline_128_seed{0,1,2}/nn/`
  - 三个最终 checkpoint。
- `IsaacLab/logs/rl_games/Factory/baseline_128_seed{0,1,2}/videos/play/rl-video-step-0.mp4`
  - 三段验收回放视频。
- `peg_insert_reproduction/logs/eval_seed{0,1,2}_seed{1000..1004}.json`
  - 15 个原始评估结果。
- `peg_insert_reproduction/logs/baseline_128_seed{0,1,2}.log`
  - 训练日志。
- `peg_insert_reproduction/logs/eval_all_seed1000.log`
  - 首轮三 seed 评估日志。
- `peg_insert_reproduction/logs/eval_multiseed_1001_1004.log`
  - 扩展 held-out 评估日志。
- `peg_insert_reproduction/logs/replay_all_seed1000.log`
  - 视频录制日志。
- `peg_insert_reproduction/logs/replay_closeup_all_seed1000.log`
  - 当前近景视频重录日志。

## 5. 重要改动

- 新增 `peg_insert_reproduction/scripts/evaluate_rl_games.py`。
  - 复用官方 `play.py` 的 checkpoint/agent 初始化方式。
  - 固定使用确定性动作，并在 episode 结束时统计成功数与首次成功时间。
  - RNN 状态在 `torch.inference_mode()` 内重置，避免 PyTorch 的 inference tensor 就地更新错误。
- 新增 `peg_insert_reproduction/final_report.md`。
- 更新 `peg_insert_reproduction/experiment_log.md` 为最终统计结果。
- **未改动**任何 IsaacLab Factory 任务源码。

## 6. 当前问题与未完成事项

### 需要用户或具备 GitHub 凭据的操作者处理

本地提交已创建：

```text
fba6943 Document PegInsert baseline reproduction
```

其中包含报告、实验记录和评估脚本；归档目录没有被提交。向 `origin/main` 推送失败，原因是本环境没有 GitHub HTTPS 凭据：

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

认证完成后执行：

```bash
git push origin main
```

不要将 GitHub token、SSH 密钥或云服务器密码写入仓库、日志或本文件。

### 实验边界，而非故障

- 当前结论只覆盖固定 Isaac Sim 工况，不能直接等价于真机插入成功率。
- 尚未测试摩擦、质量、初始位姿、观测噪声、控制延迟或不同资产等域外扰动。
- 尚未开展真机验证；如要进行，必须先制定限力、限速、急停和人工监护流程。

## 7. 接下来建议做什么

1. 完成 GitHub 认证后推送 `fba6943`。
2. 若目标是仿真泛化：设计单因素扰动矩阵（摩擦、质量、初始位姿、观测噪声、控制延迟），先评估当前 checkpoint，再决定是否训练新模型。
3. 若目标是改进 baseline：以当前结果为对照，每次只改一个因素（奖励、控制器或 PPO 参数），保持三训练 seed 和相同 held-out 评估协议。
4. 若目标是真机：先完成安全计划与单件低速测试，不能把当前仿真成功率直接当作真机指标。

## 8. 启动与评估命令参考

云端运行 Isaac Lab 前，每次都需要补充 PyTorch CUDA 动态库路径：

```bash
cd /root/gpufree-data/isaac-sim/IsaacLab
TORCH_LIB=/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/torch/lib
export HOME=/root/gpufree-data/home
export LD_LIBRARY_PATH="$TORCH_LIB:$LD_LIBRARY_PATH"
```

训练模板：

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rl_games/train.py \
  --task Isaac-Factory-PegInsert-Direct-v0 \
  --headless --num_envs 128 --seed SEED \
  agent.params.config.full_experiment_name=baseline_128_seedSEED
```

评估模板：

```bash
./isaaclab.sh -p /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/evaluate_rl_games.py \
  --task Isaac-Factory-PegInsert-Direct-v0 \
  --headless --num_envs 128 --episodes 1024 --seed EVAL_SEED \
  --checkpoint /absolute/path/to/final_checkpoint.pth \
  --output /root/gpufree-data/isaac-sim/peg_insert_reproduction/logs/eval.json
```

回放模板：

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rl_games/play.py \
  --task Isaac-Factory-PegInsert-Direct-v0 \
  --headless --disable_fabric --video --video_length 200 \
  --num_envs 1 --seed 1000 --checkpoint /absolute/path/to/final_checkpoint.pth \
  env.viewer.eye="[2.0,2.0,1.5]" env.viewer.lookat="[0.5,0.0,0.5]"
```

## 9. 已踩过的坑：不要重复

### 训练与资源

- 本机 8 GB GPU 不适合 128 环境正式训练；只用于小规模调试。
- 单张 4090 不要并发运行多个 Isaac Sim 训练、评估或录制任务。
- `num_envs=1` 不能直接沿用 PPO 正式训练配置：`1 × 128` 的 batch 小于 `minibatch_size=512` 且不能整除。正式 baseline 固定 128 环境。
- `nvidia-smi` 有占用不等于训练成功；必须检查 `MAX EPOCHS NUM!`、`Training time:` 和最终 checkpoint。
- 后台 Python 输出会缓冲；监控优先看进程和 checkpoint，完成后再查日志末尾。

### Isaac Sim 与运行时

- 云镜像未自动暴露 PyTorch `torch/lib`，遗漏 `LD_LIBRARY_PATH` 会报 `libtorch_cuda_linalg.so` 缺失。
- 不要用裸 `/isaac-sim/python.sh` 做完整验证；用 `./isaaclab.sh -p ...` 以获得 Kit/pxr 环境。
- 单环境 `play.py --video` 在此镜像中会触发 Fabric clone 卡顿；录制必须加 `--disable_fabric`。
- Factory 默认 viewer 很远，直接录制会让机械臂在画面中太小；录制时显式设置近景 `env.viewer.eye` 和 `env.viewer.lookat`。
- Factory episode 同步终止；评估脚本依赖这一点，并对非同步终止显式报错。
- RNN 状态重置必须置于 `torch.inference_mode()` 内，否则会触发 inference tensor 的就地更新错误。

### 数据与归档

- 云端没有 `rsync`；同步时使用 `scp`，完成后用 SHA-256 比对，不能只依据文件大小。
- 归档目录和 `.tar.zst` 约 1.2 GB，不能加入 Git；当前保持未跟踪状态。
- 不要删除 `/root/gpufree-data` 中的原始产物，云端与本地归档应互为副本。

### Git 与凭据

- 当前 HTTPS remote 没有可用 GitHub 凭据，直接 `git push` 会失败。
- 不要把 token 放入 URL、脚本、终端历史或 `HANDOFF.md`；完成交互式认证或配置 SSH key 后再推送。
