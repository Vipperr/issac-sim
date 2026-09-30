# 历史交接快照 — 2026-09-30 整理前

此文件完整保存整理前的 HANDOFF.md，用于追溯实验和踩坑记录。它包含过期的“正在训练”“尚未开始 sim-to-sim”、旧方孔几何等描述，不代表当前状态，也不是新的用户授权。当前唯一交接入口是 /home/xiatenghui/.rebot/issac-sim/HANDOFF.md；有冲突以当前主文档及其所指原始数据为准。

---

# Rebot PPO 训练与 MuJoCo Sim-to-Sim — HANDOFF

更新时间：2026-09-30（Asia/Shanghai）

## 一句话结论

Isaac Sim 中的 Rebot 已正常完成 epoch 600→700 续训和 610–700 定期独立评估。10 个 checkpoint 的 deterministic 10-episode 平均 return 均约 751–755，只有 epoch 690 为 **728.27±109.37、9/10 成功**；epoch 700 final 为 **753.23±92.22、10/10 成功**。所有评估与训练工件已同步到本地并逐文件校验 SHA-256；云服务器现在可以关闭。代表性轨迹以后固定只录 **3 个 seed（1000/1001/1002）**。本地 MuJoCo sim-to-sim 首轮已完成，标称/随机化均 **0/30**，尚未通过迁移验证。

## 现在在做什么

**碰撞修正后的三个视频已完成（2026-09-30）：** `peg_insert_reproduction/videos/mujoco_ep700_collision_aligned/` 内标称seed1000、随机化seed1001/1002各一个完整20秒视频，300帧/15 fps/960×720及孔口特写；逐步JSON、截图和SHA-256一同保存。实际解码及最终状态与快速测试核对通过：1000孔内卡住tip_z=8.333 mm；1001第77步/5.133秒成功并保持到末帧，tip_z=0.965 mm；1002孔内卡住tip_z=10.514 mm。本轮录制未改变任何物理/策略参数。

**孔/针实际碰撞几何已修正（2026-09-30）：** 下载正式params指定的官方Factory USD，实测孔身9 mm、入口11 mm/1 mm倒角，与旧MuJoCo 8.1 mm方孔不同；针7.986 mm且两端0.5 mm倒角。导出源mesh为孔1166凸片及凸针，保留底板/轮廓，总体积校验一致，11项测试通过；原始USD保存在 `peg_insert_reproduction/factory_collision_sources/`，云端缓存字节仍未核实，PhysX SDF/夹持/求解参数仍非完全一致。三个20秒episode（标称1000、随机化1001/1002）最终tip_z从孔口约25 mm降至8.33/0.97/10.51 mm，seed1001第77步成功并保持到末帧，其他两条孔内卡住；四元数跳变均0。详见 `peg_insert_reproduction/eval_results/mujoco_ep700/COLLISION_ALIGNMENT.md` 及 `quick_collision_alignment_20260930.json`。现有惯性增量视频均为本轮碰撞修正之前录制，不应当作新模型视频。

**0.01 I 后三个新视频已录制（2026-09-30）：** ep700 final，标称 seed1000、随机化 seed1001/1002 各一个完整 deterministic episode，位于 `peg_insert_reproduction/videos/mujoco_ep700_inertia001/`。三个视频均实际解码验证为20秒/300帧/15 fps、带孔口特写；最终径向误差0.307/4.949/24.924 mm，均未成功，轨迹与本轮惯性增量快速测试一致。逐步数据和截图一同保存；历史目录 `mujoco_ep700_three/` 的视频为这些修复之前录制，不应混用。

**0.01 I 惯性增量已加入并快速验证（2026-09-30）：** 按本地Factory基类逻辑给机器人10个刚体惯性张量加0.01 I kg·m²，不改质量/COM/armature、不影响插针/孔惯性、reset不累加；10项测试通过，包括实际关节空间质量矩阵校验。ep700 final标称seed1000一次及随机化seed1000/1001/1002各一次，均完整20秒、0次四元数跳变；标称0/1、随机化0/3。最终径向误差分别从25.54/151.44/107.35/192.11 mm降到0.31/0.91/4.95/24.92 mm，但tip仍停在相对孔底约25 mm（孔口附近），未完成插入。摩擦/PD/几何/夹持不变；云端基类仍未重新核实。详见 `peg_insert_reproduction/eval_results/mujoco_ep700/INERTIA_ALIGNMENT_QUICK_TEST.md` 和 `quick_inertia_alignment_20260930.json`。

**Tool / 插针质量已补齐并快速验证（2026-09-30）：** MuJoCo编译后的Tool质量10 g、插针19 g均实际参与动力学，插针自身重力按Isaac设置抵消；原始连杆质量不变，插针刚性连接方式不变，未加入0.01 I或调整摩擦/PD。新增质量/重力测试后9项测试通过。ep700 final标称seed1000一次及随机化seed1000/1001/1002各一次，均20秒/300步、0次输入符号跳变；标称0/1、随机化0/3，仍未通过迁移。结果见 `peg_insert_reproduction/eval_results/mujoco_ep700/MASS_ALIGNMENT_QUICK_TEST.md` 及 `quick_mass_alignment_20260930.json`。

**四元数符号连续性已修复并快速验证（2026-09-30）：** 每次 reset 匹配 Isaac ARM_HOME 半球，逐次 Tool pose 与上一四元数点积非负；新增回归测试能检出旧代码，8 项测试通过。ep700 final 跑标称 seed1000 一次及随机化 seed1000/1001/1002 各一次，每次完整20秒，网络输入均0次符号跳变；标称0/1、随机化0/3。标称最终径向误差192.50→22.90 mm，但随机化结果不一致改善。本轮未改变动力学或摩擦参数，迁移仍未通过；结果见 `peg_insert_reproduction/eval_results/mujoco_ep700/QUATERNION_FIX_QUICK_TEST.md` 和同目录 `quick_quaternion_fix_20260930.json`。下述首轮结果与三个视频为修复前历史记录。

**MuJoCo 三个完整 episode 视频已录制（2026-09-30）：** ep700 final、随机化配置、seed 1000/1001/1002 各一个 deterministic episode，均为 20 秒 / 300 帧 / 15 fps，均未成功；视频与逐步动作、位置、关节速度及摩擦力矩 JSON 位于 `peg_insert_reproduction/videos/mujoco_ep700_three/`。三条轨迹复现对应 seed 上次随机化评估的首个 episode；六个关节均测得非零干摩擦约束力矩，不能将当前失败直接归因于“MuJoCo 没有静摩擦/库伦摩擦”。本次录制未修改动力学或摩擦参数。

**本地 MuJoCo sim-to-sim 首轮已完成（2026-09-30）：epoch 700 final，seed 1000/1001/1002，每个 seed 标称/随机化各 10 episode；两种模式均 0/30 成功。** 已对齐力矩、重力补偿、关节限位、20 秒 episode、动作尺度、Kp 与观测/LSTM 接口；策略初始动作与 Isaac 录制差异约 2.15e-6，7 项测试通过。结果及复现说明位于 `peg_insert_reproduction/eval_results/mujoco_ep700/REPORT.md`。当前失败的具体动力学/接触原因尚未确定，不能直接归因于训练策略。

**ep600→700 训练及定期评估均已完成。**

```text
实验名：rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_diag_eval10_lrrestore_resume600to700_seed42_20260930_0955
起点：  epoch 600 final checkpoint
目标：  epoch 700（--max_iterations 是绝对上限）
启动：  2026-09-30 09:55 CST
完成：  正常到 epoch 700
学习率：3.901844231062336e-06（从 ep600 checkpoint optimizer 恢复）
诊断：  +agent.params.config.use_diagnostics=True
保存：  save_frequency=10，保留 epoch 610/620/.../700 checkpoint
```

epoch 601 已核对：KL=0.0050，explained variance=0.7777，clip fraction 四个 mini-epoch 为 0.089/0.114/0.150/0.160；epoch 602 Training Return=653.17。由于 horizon 256 < episode 300，新进程的 epoch 601 没有完整 episode，所以 Return/Length 从 epoch 602 开始；其余指标从 epoch 601 开始逐 epoch 记录。

定期评估采用固定策略、`num_envs=10`、`episodes=10`、seed 1000，并携带训练一致的三个 Hydra 覆盖。每个 checkpoint 的逐 episode return、均值、标准差和成功率：

| epoch | Mean Eval Return ± Std | 成功率 |
| ---: | ---: | ---: |
| 610 | 754.74 ± 93.79 | 10/10 |
| 620 | 751.70 ± 100.53 | 10/10 |
| 630 | 752.65 ± 99.77 | 10/10 |
| 640 | 753.61 ± 97.02 | 10/10 |
| 650 | 751.23 ± 98.20 | 10/10 |
| 660 | 754.34 ± 93.49 | 10/10 |
| 670 | **755.11 ± 93.22** | 10/10 |
| 680 | 754.95 ± 93.27 | 10/10 |
| 690 | 728.27 ± 109.37 | 9/10 |
| 700 | 753.23 ± 92.22 | 10/10 |

本地归档：`peg_insert_reproduction/eval_results/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_diag_eval10_lrrestore_resume600to700_seed42_20260930_0955/`（10 个 JSON、评估日志、checkpoint 清单、评估曲线与训练诊断图）；`peg_insert_reproduction/training_logs/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_diag_eval10_lrrestore_resume600to700_seed42_20260930_0955/`（TensorBoard event、params、训练日志）。远端 `artifact_manifest.sha256` 的 **25 个**已传输文件均已在本地复算匹配。

### 关机前权重备份与清理（已完成）

本地 `peg_insert_reproduction/cloud_sync/ep700_20260930/` 已保留 **5 份完整权重**：ep700 final、训练 best（epoch 697）、定期评估对照 ep670、ep600 final、ep561 best。配套参数、事件、任务代码、实际云端 USD/configuration/meshes 和全部云端评估 JSON/日志均已备份，共 **201 个文件逐项 SHA-256 校验通过**。使用说明及清理记录见该目录 `README.md`。本地 sim-to-sim 默认使用 ep700 final。

已清理本地约 611 MiB 旧归档重复解压副本（保留校验一致的 tar.xz，可恢复）、Python 缓存、云端 0938/0946 弃用分支约 406 MiB 权重，以及两端临时传输 tar。正式实验、评估和视频保留。云端中间 610–690 checkpoints 除 ep670 外未回传，但仍保留云端。本地必要权重和复现数据已完整，允许关闭服务器；本轮未执行关机。

> 弃用实验 `...diagnostics_resume600to700_seed42_20260930_0938` 在 epoch 605 停止。根因是 RL-Games 恢复 optimizer 后没有同步 `last_lr`，把 checkpoint 的 `3.90e-6` 抬到配置默认值附近，导致 epoch 601 KL=13.51、clip fraction 近 1、Return 下降。该分支不得用于评估或续训。
> 弃用实验 `...diagnostics_lrrestore_resume600to700_seed42_20260930_0946` 的训练数值正常，但默认只每 100 epoch 保存 checkpoint，无法评估 610/620/... 中间策略，因此在 epoch 608 停止并从 ep600 重启当前正式分支。

下面的 ep500→600 启动参数保留作为历史复现记录。

```text
实验名：rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume500to600_seed42_20260929_1644
起点：  epoch 500 final checkpoint（不是 best ep482，因为 ep500 的 held-out 更高）
目标：  epoch 600
启动：  2026-09-29 16:44 CST
预计：  约 105 分钟。实测 17:00 时到 epoch 515（16 分钟 15 个 epoch，含启动开销后约 1.07 min/epoch），
        剩下 85 个 epoch 约 90 分钟，即约 18:30 CST
checkpoint 落点：nn/last_Factory_ep_600_rew_<R>.pth（每 100 epoch 存一次）
```

启动已核对：`params/agent.yaml` 里 `load_path` 指向 ep500 final、`max_epochs: 600`；
TensorBoard 首个 `info/epochs` 是 **501**（step 16,384,000 = 500×32768），确认是续训而不是从 1 重启。

```bash
cd /root/gpufree-data/isaac-sim/IsaacLab
CKPT=.../rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413/nn/last_Factory_ep_500_rew_624.67896.pth
NAME=rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume500to600_seed42_$(date +%Y%m%d_%H%M)
setsid nohup env TERM=xterm ./isaaclab.sh -p ../peg_insert_reproduction/scripts/train_rebot.py \
  --task Isaac-Rebot-Factory-PegInsert-Direct-v0 --headless --num_envs 128 --seed 42 --max_iterations 600 \
  --checkpoint $CKPT \
  "env.ctrl.pos_action_threshold=[0.005,0.005,0.030]" \
  "env.ctrl.default_task_prop_gains=[100,100,400,30,30,30]" \
  env.task.action_grad_penalty_scale=0.0 \
  agent.params.config.full_experiment_name=$NAME \
  > ../peg_insert_reproduction/logs/$NAME.out 2>&1 < /dev/null &
```

**看训练进度**（不要靠 `.out` 日志，stdout 会缓冲；也不要在本地挂轮询）：

```bash
# 云端一条命令，读 TensorBoard 里的 info/epochs 和 rewards/iter
/usr/bin/python3 /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/read_tb_events.py \
  /root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume500to600_seed42_20260929_1644 \
  info/epochs,rewards/iter
pgrep -af 'python3 .*train_rebot.py'      # 进程还在不在
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
```

训练正常完成到 epoch 600；`Factory.pth` 是 epoch 561 best，`last_Factory_ep_600_rew_642.4032.pth` 是 final。
held-out 结果：best **87.01% (891/1024)**，final **87.60% (897/1024)**。代表性轨迹只保留 seed 1000/1001/1002 作为正式评估集；held-out 1024 episode 协议不变。

held-out 评估的确切命令（从云端 history 抄录，注意 `LD_LIBRARY_PATH` 不能省）：

```bash
cd /root/gpufree-data/isaac-sim/IsaacLab
NAME=<实验名>                       # 如 ..._resume500to600_seed42_20260929_1644
CKPT=logs/rl_games/Factory/$NAME/nn/last_Factory_ep_600_rew_<R>.pth   # 或 nn/Factory.pth（best）
TERM=xterm LD_LIBRARY_PATH=/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/torch/lib \
  ./isaaclab.sh -p ../peg_insert_reproduction/scripts/evaluate_rl_games.py \
  --checkpoint $CKPT --task Isaac-Rebot-Factory-PegInsert-Direct-v0 \
  --num_envs 128 --episodes 1024 --seed 1000 \
  --output ../peg_insert_reproduction/eval_results/${NAME}_final_seed1000.json --headless \
  "env.ctrl.pos_action_threshold=[0.005,0.005,0.030]" \
  "env.ctrl.default_task_prop_gains=[100,100,400,30,30,30]" \
  env.task.action_grad_penalty_scale=0.0
```

> 上面三个 Hydra 覆盖**必须带**：评估脚本不会从 checkpoint 自动恢复环境参数（见「已踩过的坑」）。
> 起评估同样要 `setsid nohup ... &` 并把 stdin 重定向到 `/dev/null`。

### 上一轮（ep394 → ep500）回顾

实验 `rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413`：
起点 epoch 394 best，14:13 启动、15:49 正常写出 final checkpoint。

```text
best checkpoint：nn/Factory.pth                             epoch 482, frame 15,794,176, last_mean_rewards 652.0448
final checkpoint：nn/last_Factory_ep_500_rew_624.67896.pth  epoch 500, frame 16,384,000
```

Held-out 结果（seed 1000、128 env、1024 deterministic episode、摩擦随机化开启、以 episode 结束时 `infos["successes"]` 为准）：

| checkpoint | 成功数 | 成功率 | 平均首次成功时间 |
| --- | ---: | ---: | ---: |
| epoch 394 基线 | 345/1024 | 33.69% | 5.81 s |
| **本实验 best（epoch 482）** | 835/1024 | **81.54%** | 6.60 s |
| **本实验 final（epoch 500）** | 875/1024 | **85.45%** | 6.69 s |

两个评估都使用与训练完全一致的覆盖：`pos_action_threshold=[0.005,0.005,0.030]`、`default_task_prop_gains=[100,100,400,30,30,30]`、`action_grad_penalty_scale=0.0`。

> 注意：Codex 启动这两个评估时用的是**阻塞式 SSH 会话**（没有 `setsid ... &`），它额度耗尽断线后进程一度失去控制，但最终仍自行跑完并在 16:09 / 16:17 写出完整 JSON。**后续在云端起长任务一律用 `setsid nohup ... &`**，见「已踩过的坑」。

相对 epoch 394 原始训练配置，本轮覆盖：

```text
ctrl.pos_action_threshold:       [0.020, 0.020, 0.020] -> [0.005, 0.005, 0.030] m
ctrl.default_task_prop_gains:   [100,100,100,30,30,30] -> [100,100,400,30,30,30]
task.action_grad_penalty_scale: 0.0（保持关闭）
```

保持不变：20 s episode、horizon 256、128 env、seed 42、15 Hz 控制频率、EMA 0.2、旋转动作尺度 0.097 rad、重力补偿、摩擦随机化、PPO 超参数和网络结构。

原 epoch 394 checkpoint 没有覆盖；新实验写到独立目录。训练过程中 best 从 epoch 461（reward 639.26245）继续升到 epoch 482（reward 652.0448）。

**held-out 已做完**：best 81.54%、final 85.45%，见上文表格。训练 reward 只作辅助——本轮 final 的 `last_mean_rewards`（624.67896，见文件名指数）低于 best 的 652.0448，但 held-out 反而 final 更高，再次说明不能用 reward 选 checkpoint。

## 当前实验如何实现

策略输出原始归一化动作 `u_t ∈ [-1, 1]^6`，环境先做已有的 EMA：

```text
a_t = 0.2 * u_t + 0.8 * a_(t-1)
```

位置目标：

```text
p_target = p_current + a_t[:3] * [0.005, 0.005, 0.030]
```

- X/Y 每个控制步最大目标偏移由 ±20 mm 降到 ±5 mm，减少洞口横向过冲，同时避免前两轮 ±2 mm 横向动作过小。
- Z 最大目标偏移由 ±20 mm 增到 ±30 mm，并把 `Kp_z` 从 100 提到 400，目的是克服关节静摩擦并在对准后提供足够插入力。
- 旋转仍为 `a_t[3:6] * [0.097, 0.097, 0.097]` rad，不在本轮同时修改。

位置 action 在 **世界/每环境坐标系** 中解释；当前机器人基座未额外旋转，所以数值轴与基座轴重合。`+Z` 是向上、`-Z` 是向下插入；工位位于约 `x=+0.20 m`，所以 `+X` 是从基座指向工位的方向。旋转 action 也是绕这些世界/基座轴的增量，不是末端局部轴。

本轮不启用动作平滑惩罚。前一轮 `[2,2,5] mm + smooth=0.01` 退化严重，且无法区分尺度与惩罚各自贡献；后一轮 `[2,2,20] mm + no smooth` 仍显著低于基线，因此本轮优先恢复横向能力并增强 Z 控制。

## 固定策略评估与绘图协议（用户要求）

以后每次策略评估除 held-out 成功率外，代表性 episode **固定只录 3 个 seed：1000、1001、1002**，并同步记录和绘制以下三组时间序列：

1. **策略 raw action**：EMA 前 `u_t`，六维各一张静态 PNG。
2. **实际执行的 EMA action**：环境中的 `a_t = 0.2u_t + 0.8a_(t-1)`，六维各一张静态 PNG。
3. **机械臂末端实际响应**：实际末端世界/环境坐标位姿，位置 X/Y/Z 与由四元数换算的 Roll/Pitch/Yaw，六维各一张静态 PNG。

总计 **18 张独立 PNG**。不再把多维度叠在同一张图，也不再交付交互图。图形保持简单：统一时间轴、明确单位、标题和网格即可，不加动画、悬浮提示或装饰性控件。

每次 PPO 评估固定产出下列训练/评估诊断图：

1. **Training Episode Return**：训练期间 episode return 随 epoch 变化（当前 TensorBoard 标签 `rewards/iter`）。
2. **Evaluation Return**：关闭探索、用当前策略独立评估的 return；当前协议为每 10 个训练 epoch（610/620/.../700）各跑 10 episode，画 Mean Eval Return ± Std vs Epoch，不得用 training return 代替。
3. **Episode Length**：当前可用 `episode_lengths/iter`；但 Factory 成功后不终止，所以同时画 `first_success_step/time`，避免把固定 timeout 误解为效率。
4. **Final Return Distribution**：训练结束后关闭探索独立跑 50–100 episode，保存逐 episode return，画箱线图或小提琴图。这与 3 个代表性轨迹 seed 是两套不同产物。
5. **Success Rate**：固定 held-out 成功率为主，辅以训练 `successes/iter`。
6. **Actor / Policy Loss**：`losses/a_loss`。
7. **Critic / Value Loss**：`losses/c_loss` 和 `losses/cval_loss`（若两者都存在则都画并标明原始 tag）。
8. **Entropy**：`losses/entropy`。
9. **Approx KL Divergence**：`info/kl`。
10. **Clip Fraction**：必须记录真实 clipping 命中比例；`info/e_clip` 是 clip 阈值，**不是 clip fraction**，不得替代。
11. **Explained Variance**：记录 critic 对 return 的 explained variance。

ep500→600 旧 events 没有 clip fraction 和 explained variance；当前 ep600→700 实验已启用 RL-Games `use_diagnostics`，逐 epoch 记录真实 `diagnostics/clip_frac/0..3` 和 `diagnostics/exp_var`。定期 **evaluation return** 及逐 episode **final return distribution** 仍需通过独立 deterministic 评估采集；不对缺失指标做伪代替。

时间对齐约定：raw action 与按环境公式计算的本步 EMA action 在 `env.step()` 前记录，末端位姿在该控制步执行后记录；三者使用同一个 step 编号。不能在 episode 最终 timeout reset 后读取 `task.actions`，否则最后一个 EMA 样本会被 reset 成零。控制周期为 0.0666667 s。位置单位 m，姿态图使用连续展开的 RPY（建议 degree），action 为归一化值。JSON 同时保留末端原始 `wxyz` 四元数，避免只保存 Euler 导致信息损失。

## 已经完成

### 1. MuJoCo XML 与 Isaac 模型同步

动力学唯一基准：

```text
/home/xiatenghui/.rebot/rebot_blue/src/rebot_description/urdf/rebot.xml
SHA-256: 02e923dc78ea15851070c2fed3a919e978a61d2ec96eee235c52b1f3bae95bba
```

| 关节 | 限位 | 速度上限 |
| --- | --- | --- |
| Joint_1 | `[-90°, 90°]` | 3 rad/s |
| Joint_2 | `[0°, 180°]` | 3 rad/s |
| Joint_3 | `[-180°, 0°]` | 3 rad/s |
| Joint_4 | `[-90°, 90°]` | 3 rad/s |
| Joint_5 | `[-90°, 90°]` | 3 rad/s |
| Joint_6 | `[-90°, 90°]` | 3 rad/s |

- XML：`damping=0.2`、`frictionloss=2.0`、armature 0、motor `ctrlrange=[-50, 50]`。
- MuJoCo 没有原生关节速度约束；XML 中的 `<numeric name="rebot_arm_velocity_limit" ...>` 只是数据，评估端仍必须主动读取并截断。
- Isaac 桥接 URDF、运行时 ArticulationCfg 和云端训练用 `rebot.usd` 已按上述参数对齐。
- 云端训练用 USD SHA-256：`c5524c47f930f255801c264eb18f6c8e27638e2a21bdfae2a384967d14c47877`。
- `verify_rebot_model_sync.py` 曾通过：`model_sync=ok joints=8 bodies=8`；开环力矩回放确认主要质量、惯量和摩擦映射正确。

### 2. 摩擦域随机化

每次 reset 对每个环境重新采样：

```text
J1-J3 Coulomb friction: U(1.0, 2.0) N·m
J4-J6 Coulomb friction: U(0.0, 2.0) N·m
viscous friction:       U(0.1, 0.3) N·m·s/rad
static == dynamic
```

原因：PhysX 在低于摩擦阈值时更容易粘住，MuJoCo 的 `frictionloss` 会缓慢蠕动；轻量腕关节 J4–J6 差异最大，无法仅靠静态参数完全对齐。

### 3. 重力补偿

最早同步模型的训练视频显示机械臂直接下坠。随后以 MuJoCo 参数辨识结果为基准实现重力矩：

```text
/home/xiatenghui/.rebot/rebot_blue/src/rebot_py/rebot_min_param_sim.xlsx
```

- 根据参数辨识脚本使用的动力学回归模型，从 49 个最小惯性参数中取重力项需要的 10 个参数。
- 按 Rebot DH 关节偏置计算六轴重力矩。
- 每个物理控制周期执行 `arm_torque = J^T * wrench + gravity_torque(q)`，最后截断到 ±50 N·m。
- reset 夹爪闭合阶段也恢复重力，避免复位逻辑与训练阶段动力学不一致。
- 本地与云端 `rebot_gravity.py` SHA-256 均为 `7fd845bae1bfe1ba0cae1d90dcd19bbf6abd07f79d85fa48fe9f05f93b1ea36e`。

### 4. PPO 训练配置升级

当前统一配置：

```text
episode_length_s: 20.0
control dt:       1/15 s（physics 1/120 s，decimation 8）
episode steps:    300
horizon_length:   256
num_envs:         128
transitions/epoch: 32768
seed:             42
```

网络与 PPO：

- 状态式 asymmetric recurrent PPO，不使用图像。
- Actor：19 维观测，2×1024 LSTM，MLP 512-128-64 ELU，输出六维高斯连续动作。
- Central critic：43 维 privileged state，类似网络。
- `gamma=0.995`、`lambda/tau=0.95`、学习率 `1e-4`、adaptive KL `0.008`、PPO clip `0.2`。
- minibatch 512、每 epoch 4 个 mini epochs、sequence length 128、critic coefficient 2、entropy 0、gradient clip 1、mixed precision。

Actor 观测 19 维：末端相对固定工件位置 3、末端四元数 4、末端线速度 3、角速度 3、上一时刻 EMA 动作 6。Actor **没有**真实 peg 位姿和接触力；critic 才有更多 privileged state。

### 5. 训练与评估结果

所有下列 held-out 结果均为：seed 1000、128 env、1024 deterministic episode、摩擦随机化开启、以 episode 结束时的 `infos["successes"]` 为准。

| 实验 | 训练范围 | best held-out | 平均首次成功时间 | 结论 |
| --- | ---: | ---: | ---: | --- |
| `rebot_ppo_identified_gravcomp_fricdr_seed42_20260928_0938` | 0→200 | 73/1024 = **7.13%** | 5.11 s | 重力补偿有效，但 10 s episode 太短 |
| `rebot_ppo_gravcomp_ep20_h256_stage300_seed42_20260928_1139` | 0→300 | 277/1024 = **27.05%** | 4.13 s | 20 s + horizon 256 显著提升 |
| `rebot_ppo_gravcomp_ep20_h256_resume300to400_seed42_20260928_1649` | 300→398 | 345/1024 = **33.69%** | 5.81 s | 续训有效，但洞口往复仍明显（**旧基线**） |
| `rebot_ppo_gravcomp_ep20_h256_smallact_xy2_z5mm_smooth001_resume394to500_seed42_20260929_0848` | 394→500 | best 14/1024 = **1.37%**；final 16/1024 = **1.56%** | 9.77 / 10.09 s | `[2,2,5] mm + smooth 0.01` 严重退化 |
| `rebot_ppo_gravcomp_ep20_h256_xy2_z20_nosmooth_resume394to500_seed42_20260929_1106` | 394→500 | best ep426 69/1024 = **6.74%**；final 97/1024 = **9.47%** | 5.30 / 7.36 s | 去掉 smooth、恢复 Z 后改善，但仍远低于基线 |
| `rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413` | 394→500 | best ep482 835/1024 = **81.54%**；final ep500 875/1024 = **85.45%** | 6.60 / 6.69 s | 相对旧基线 +51.8 pp；final>best，无后期回退。**用户判定 85.45% 仍不够好** |
| `rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume500to600_seed42_20260929_1644` | 500→600 | **训练中**（16:44 启动，17:00 时到 epoch 515，预计约 18:30 结束） | — | 同一分叉继续训 100 epoch，覆盖与 seed 完全不变 |

epoch 300 实验补充：

```text
best training reward: 345.1027 @ epoch 282
best held-out:         277/1024 = 27.0508%
final held-out:        270/1024 = 26.3672%
```

300→400 续训补充：

```text
进程实际写到 TensorBoard epoch 398，未正常写 final checkpoint
best checkpoint epoch: 394
best training reward:  357.925964
对应训练 success:      0.390625
held-out:              345/1024 = 33.6914%
```

相对 epoch 300 best，held-out 提升 6.64 个百分点、相对提升约 24.5%，失败数由 747 降到 679。平均首次成功时间变长，说明新增成功中有不少是长时间洞口调整后才插入。

两轮小尺度实验说明：不能把失败简单归因于“20 mm 太大”。横向缩到 2 mm 后，策略从旧 checkpoint 继续训练 106 epoch 仍未恢复到基线；`[2,2,5] + smooth` 和 `[2,2,20] + no smooth` 都失败。

`[5,5,30] + Kp_z=400` 这个分叉**成功**：held-out 从 33.69% 提到 85.45%（final）。
关键是横向恢复到 5 mm 而不是继续缩到 2 mm，同时把 Z 加大到 30 mm、`Kp_z` 提到 400 来克服静摩擦。
**但不要再外推这个方向**——失败样本的下探深度已经和成功样本一样（§8.3），继续加大 Z 没有意义。

### 6. 视频与失败模式诊断

epoch 300 best 已录制并下载两段成功、两段失败：

```text
/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/rebot_gravcomp_stage300_selected/seed1001/rl-video-step-0.mp4
/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/rebot_gravcomp_stage300_selected/seed1004/rl-video-step-0.mp4
/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/rebot_gravcomp_stage300_selected/seed1000/rl-video-step-0.mp4
/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/rebot_gravcomp_stage300_selected/seed1002/rl-video-step-0.mp4
```

主要失败模式：peg 到达洞口后横向往复、反复进入又退出，最终超时。它不是主要由缺少图像造成：策略已有精确末端相对孔位状态；更直接的原因是 20 mm 原位置动作尺度远大于 0.057 mm 径向间隙，且旧奖励没有动作平滑惩罚、成功后也不会终止 episode。

几何条件：孔直径 8.1 mm、peg 直径 7.986 mm、直径间隙 0.114 mm、径向间隙约 0.057 mm。

### 7. epoch 394 六维 raw action 诊断

已用 seed 1000 录制一个完整 deterministic episode，并在 `env.step()` 前保存策略原始输出 `u_t`，即 **EMA 前的 raw policy action**：

```text
轨迹 JSON：peg_insert_reproduction/eval_results/rebot_ep394_seed1000_action_trajectory.json
六张 PNG：peg_insert_reproduction/eval_results/epoch394_action_plots/
交互图：  /home/xiatenghui/.codex/visualizations/2026/09/29/01a0eafc-cd27-7a32-b4e4-0d010ee49307/epoch394_action_curves.html
episode： seed 1000，299 step，19.93 s，未成功
```

raw action 统计：

| 维度 | 含义 | 关键现象 |
| --- | --- | --- |
| `a0` | 世界/基座 X 平移 | 全程 `+1.0`，100% 饱和 |
| `a1` | 世界/基座 Y 平移 | `[-1.0, 0.742]`，约 3 s 周期振荡 |
| `a2` | 世界/基座 Z 平移 | 前 2 s 均值 `-0.214`，之后均值 `+0.236`；89% 样本为正（向上命令） |
| `a3` | 绕世界/基座 X 旋转 | 均值 `-0.090` |
| `a4` | 绕世界/基座 Y 旋转 | 12.7% 样本饱和，约 3 s 周期振荡 |
| `a5` | 绕世界/基座 Z 旋转 | 幅度较小，均值 `+0.121` |

重要限定：**raw action 曲线不是末端运动轨迹。** 用户从视频观察到机械臂并没有随 `a0=+1` 一直向前顶，这与数值并不矛盾。执行链中还有 EMA、相对当前位置生成目标、相对工位 ±50 mm 裁剪、任务空间 PD、Jacobian 力矩映射、重力补偿、关节摩擦、接触与力矩限幅。该 episode 从打印的初末 peg-hole 相对位置看，X 实际只变化约 `-0.183 mm`，并没有持续向 `+X` 运动。

因此当前能确认的是“策略持续请求 `+X` 目标偏移、后段多数时间请求 `+Z` 目标偏移”，不能仅凭 action 图断言机械臂实际速度或位移方向。下一次诊断必须在同一个 rollout 同步记录 raw action、EMA 后 action、位置目标、末端实际 XYZ、peg XYZ 和成功状态，再与视频逐帧对齐。

### 8. 新评估数据协议已落地并已产出结果

`record_successful_episode.py` 已扩展为同步保存：

```text
raw_actions                    # step 前，策略 EMA 前输出
ema_actions                    # step 前，按环境同一公式计算的本步执行 action
fingertip_positions            # step 后，末端实际世界/环境坐标 XYZ
fingertip_quaternions_wxyz     # step 后，末端实际世界姿态
initial_fingertip_position
initial_fingertip_quaternion_wxyz
```

非终止步会用 `torch.allclose` 校验记录的 EMA action 与环境 `task.actions` 一致。
本地版（sha256 `4da62246…`）已同步到云端并实际跑通；云端旧版没有 `ema_actions` 字段。

### 8.1 采集结果

| 批次 | checkpoint | seed | 结果 |
| --- | --- | --- | --- |
| ep500 | `last_Factory_ep_500_rew_624.67896.pth` | 1000 / 1001 / 1002 / 1003 / 1004 | 成功，首次成功 2.07 / 11.13 / 1.53 / 13.73 / 13.60 s |
| ep500 | 同上 | 1005 | **失败**（299 步超时） |
| ep394 基线 | `Factory.pth`（epoch 394） | 1001 | 成功 @6.00 s |
| ep394 基线 | 同上 | 1000 / 1005 | **失败** |

ep500 批次 5/6 成功，与非同 seed 的 held-out 85.45% 一致，说明单环境录制没有引入偏差。
每批次用各自训练时的环境覆盖：ep500 用 `[0.005,0.005,0.030] + Kp_z=400`，
ep394 用默认 `[0.020,0.020,0.020] + Kp_z=100`。**两者不可互换。**

### 8.2 定性结论：策略行为确实变了

同一 seed 1000 对照（ep394 失败 → ep500 2.07 s 成功）：

| 指标 | ep394 基线 | ep500 新策略 |
| --- | --- | --- |
| raw `|a0|` 均值 | 1.000（**100% 满量程饱和**） | 0.144 |
| raw `a0` 饱和占比 | 100% | 0.7% |
| 10% 之后 raw `a2` 均值 | **+0.237（命令向上）** | **−1.000（命令向下）** |
| 最大下探深度 | −14.60 mm | −50.21 mm（到底） |

三个 ep394 seed 里，两个失败 seed 的 10% 后 `raw a2` 均值都是**正**（+0.237 / +0.308），
唯一成功的 seed1001 是 **−0.865**。这正是旧基线「对准后反而上抬」的失败特征。
新策略在全部三个 seed 上都稳定输出 `a2 ≈ −0.9 ~ −1.0`，最大下探深度全部到 −50.2 mm。

### 8.3 剩余失败模式：横向搜索不收敛，不是 Z 不够

失败的 ep500 seed1005 与成功的 seed1000 **下探深度相同**（−50.18 vs −50.21 mm），
差别在横向：

| 指标 | seed1000（成功 2.07 s） | seed1005（失败） |
| --- | ---: | ---: |
| 末段 25% 的 X 带宽 | 1.71 mm | **5.90 mm** |
| `|ema a0|` 均值 | 0.136 | **0.578** |
| raw `a0` 饱和占比 | 0.7% | 29.4% |
| raw `a1` 振荡周期 | 无 | 0.85 s（21 次过零） |

即：成功的 episode 横向很快锁死，失败的在 X 方向以约 1.7 s 周期持续来回搜索。
**下一步若要继续提升，应该针对横向对准，而不是再加大 Z 尺度或 Kp_z。**

### 8.4 产出文件

```text
peg_insert_reproduction/eval_results/rebot_xy5_z30_kpz400_ep500_policy_eval/
  <seed>/                     # 每个 seed 18 张独立 PNG
  rebot_xy5_z30_kpz400_ep500_seed<seed>.json
  summary_ep500.json          # 命令-响应定量摘要

peg_insert_reproduction/eval_results/rebot_ep394_baseline_policy_eval/
  <seed>/                     # 同上，3 个 seed
  summary_ep394.json

peg_insert_reproduction/videos/rebot_xy5_z30_kpz400_ep500_batch/seed<seed>/rl-video-step-0.mp4
peg_insert_reproduction/videos/rebot_ep394_baseline_batch/seed<seed>/rl-video-step-0.mp4
```

共 162 张 PNG（ep500 6×18 + ep394 3×18），已回传本地。

held-out 批量评估的两个结果 JSON 一度**只留在云端**（HANDOFF 之前误记为已回传），
2026-09-29 16:50 已补拉回本地 `eval_results/`，本地/云端 sha256 一致：

```text
eval_results/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413_best_ep482_seed1000.json   # 835/1024
eval_results/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413_final_ep500_seed1000.json  # 875/1024
```

### 8.5 新增脚本

- `scripts/record_eval_batch.sh` — 批量录制多个 seed，覆盖用 `EPISODE_OVERRIDES` 传入。
- `scripts/plot_policy_eval.py` — 从轨迹 JSON 生成 18 张静态 PNG，并输出命令-响应摘要。
- `scripts/read_tb_events.py` — 纯标准库读 TensorBoard event 文件，用来确认续训起点和当前 epoch
  （容器里没有能同时 import numpy 和 tensorboard 的 python）。本地与云端已同步，哈希一致。

## 还没有完成

1. ~~等 ep394→500 实验结束、评估 best 与 final~~ — **已完成**，见上文表格。
2. ~~用匹配覆盖评估 best 与 final~~ — **已完成**。
3. ~~同步录像脚本到云端并跑新轨迹~~ — **已完成**，ep500 六个 seed + ep394 三个 seed。
4. ~~生成 18 张独立静态 PNG~~ — **已完成**，162 张已回传本地，见 §8.4。
5. **ep500→600 续训正在进行**（16:44 启动，17:00 时到 epoch 515，预计约 18:30 结束）；结束后要跑 held-out 并出图，见「接下来按这个顺序做」。
6. 轨迹 JSON 里仍缺：**控制目标位姿、peg-hole 相对位姿、成功标记随步、控制/接触 wrench**。现有数据能看命令与末端响应，但无法区分「被静摩擦卡住」和「被接触力挡住」。
7. **视频与轨迹尚未逐帧对齐**，目前只能按时间轴目视对照；`a0>0` 时实际 X 位移偏小这一点已在数值上确认（见 §8.3），但未与视频帧一一对应。
8. **成功后不终止 episode 仍然存在**：ep500 成功 episode 在插入后仍继续输出约 17 s 的满量程向下命令（此时末端几乎不动）。虽然不影响 held-out 计数（成功状态保持住），但白耗 17 s 且掩盖了「已卡死」这一事实。
9. **横向失败模式的根因未定位**：ep500 失败样本的横向搜索为何不收敛，尚未区分是奖励塑形、观测不足（actor 看不到真实 peg 位姿与接触力）还是单纯探索不充分。
10. 只有 Isaac 结果足够好时，才重构并运行 MuJoCo sim-to-sim；**用户已明确 85.45% 不够好，所以 sim-to-sim 继续搁置**，先把 ep600 训出来看结果。
11. `rebot_blue/src/rebot_sim2sim_eval/` 仍需改为：直接使用基准 XML、读取 3 rad/s 自定义速度上限、`torque_limit=50`、启用重力、接入重力补偿和当前 recurrent policy 状态。
12. MuJoCo nominal/stress 评估需记录成功率、失败类型、轨迹，以及 XML/USD/checkpoint 哈希。
13. **云端 checkpoint 和 events 文件尚未回传**（JSON、PNG、视频已回传，含 16:50 补拉的两个 held-out JSON）。
    释放实例前必须备份 `nn/`、`params/`、`summaries/`。
14. 官方 Isaac URDF 转换器完整重建 USD、夹爪映射对比和 PhysX/MuJoCo 接触对比仍未做。
15. 本地/云端 `rebot.usd` 哈希差异（§问题 14）仍未查明。

## 关键决策以及为什么这么选

| 决策 | 原因 |
| --- | --- |
| `rebot.xml` 是唯一动力学基准 | 避免为了得到更好结果反向修改评估模型；Isaac 应适配 MuJoCo/真机参数。 |
| J2 使用 0～180°，全臂速度上限 3 rad/s | 这是用户确认的新基准和真机安全限制。 |
| effort limit 使用 50 N·m | 对应 XML motor `ctrlrange`，不是误用 `actuatorfrcrange=100`。 |
| 用辨识的最小惯性参数实现显式重力补偿 | 视频已证明无补偿会下坠；直接复用已有回归模型比重新辨识或人工调常数可靠。 |
| 20 s episode + horizon 256 | 旧 10 s episode 经常在完成洞口调整前超时；256 horizon 在计算量和长时信用分配之间合理。 |
| 300 epoch 是观察点，继续到约 400 | epoch 300 曲线仍在上升；续训到 epoch 394 后 held-out 从 27.05% 提到 33.69%，验证训练不足确实是部分原因。 |
| 使用 epoch 394 best 作为新实验起点 | 300→400 进程在 398 被中断，没有 final；checkpoint 内明确记录 epoch 394，且这是后期训练回报最高点。 |
| 曾尝试 `[2,2,5]` mm + smooth 0.01 | 原假设是减小横向过冲并平滑振荡；held-out 仅 1.37%～1.56%，该组合已判定失败，不应复用。 |
| 曾尝试 `[2,2,20]` mm + no smooth | 用于区分“Z 太小/平滑惩罚”影响；虽升到 6.74%～9.47%，仍远低于基线，说明 2 mm 横向尺度或尺度突变本身也有问题。 |
| 当前选择 `[5,5,30]` mm、`Kp_z=400`、smooth=0 | 用户观察到插入孔后不继续下压；增大 Z 目标偏移并提高 Z 刚度以克服静摩擦，同时把 X/Y 从失败的 2 mm 恢复到 5 mm。关闭 smooth，避免再把变量混在一起。 |
| 从 ep500 **final** 而不是 best ep482 续训 | held-out 上 final(85.45%) > best(81.54%)，续训就是要把这条轨迹接着往下走；而且 394→500 只训了 106 epoch，用户要求再训 100 epoch。`Factory.pth` 是 best，直接拿它续训会丢掉后面 18 个 epoch 的进展。 |
| ep600 这一轮只改 `--max_iterations=600` | 尺度、Kp、smooth、seed、env 数、网络全部保持不变，保证与 ep500 的 held-out 可比；一次只动训练量这一个变量。 |
| 保留 EMA 0.2 | 已有低通平滑是执行链的一部分；本轮只改变尺度和显式惩罚，避免再增加变量。 |
| action 诊断优先记录 EMA 前 raw output | 用户要求看 RL 策略本身输出；但必须与 EMA 后动作和实际末端轨迹并列解释，不能把 raw action 当位移/速度。 |
| 每次评估输出 18 张独立静态 PNG | 用户明确要求 raw action 6 张、EMA action 6 张、实际末端 XYZ+RPY 6 张；单维图比交互图或多维叠图更容易逐轴核对策略命令与机械臂响应。 |
| action 轴保持世界/基座坐标系 | 现有 Factory 控制直接把前三维加到 world-frame fingertip position，改成末端坐标会改变任务定义并使旧 checkpoint 失配。 |
| 暂不加图像 | 仿真已有精确相对位姿，图像不能直接解决动作过冲；渲染域差异和训练成本会显著增加。真机若拿不到孔位，应优先独立做视觉定位。 |
| 训练不好就不做 sim-to-sim | 先保证源仿真策略可用，否则 MuJoCo 失败无法区分是策略能力不足还是仿真域差异。 |
| 评估固定 seed 1000、1024 episode | 保证不同 checkpoint 可直接比较，减小小样本波动。 |

## 改过的重要文件

`/home/xiatenghui/.rebot/issac-sim/`：

```text
HANDOFF.md
peg_insert_reproduction/rebot_task/rebot_factory_env.py
  - Rebot 模型、复位姿态、摩擦随机化
  - 任务空间 PD + 辨识重力矩
  - episode_length_s = 20.0
  - reset 时恢复重力

peg_insert_reproduction/rebot_task/rebot_gravity.py
  - 新增：从最小惯性参数实现六轴重力矩
  - 含最小自检

peg_insert_reproduction/scripts/train_rebot.py
  - 默认 horizon_length = 256
  - 未显式指定时默认 max_iterations = 300

peg_insert_reproduction/scripts/evaluate_rl_games.py
  - 批量 deterministic held-out 评估

peg_insert_reproduction/scripts/record_successful_episode.py
  - 录制并报告 first_success_step / timeout_step
  - 可选 `--action_output` 导出 EMA 前 raw action、EMA 后 action、实际末端 XYZ、末端 wxyz 四元数、控制周期和首次成功 step
  - raw 与本步 EMA action 在 step 前记录；末端位姿在该控制步执行后采样
  - 非终止步用 `torch.allclose` 校验记录的 EMA 与环境实际 `task.actions` 一致

peg_insert_reproduction/scripts/record_eval_batch.sh
  - 新增：按 seed 批量调用上面的录制脚本，环境覆盖走 `EPISODE_OVERRIDES`
  - 用法：`EPISODE_OVERRIDES="..." record_eval_batch.sh <checkpoint> <tag> <seed>...`

peg_insert_reproduction/scripts/plot_policy_eval.py
  - 新增：从轨迹 JSON 生成 18 张独立静态 PNG（raw action 6 / EMA action 6 / 末端 XYZ+RPY 6）
  - 自动剔除末帧 reset 伪影；RPY 用 Isaac Lab 的 `euler_xyz_from_quat` 约定并 unwrap 成连续角
  - 附带 `--summary` 输出命令-响应定量摘要（每步位移、符号一致率、卡死步数）

peg_insert_reproduction/scripts/read_tb_events.py
  - 新增：只用标准库解析 TensorBoard event 文件（容器里没有能同时 import numpy 和 tensorboard 的 python）
  - 手写 TFRecord + protobuf 解析；用法 `read_tb_events.py <experiment_dir> [tag,tag,...]`
  - 用来核对续训是否从正确的 epoch 开始（看 `info/epochs` 首个值）

peg_insert_reproduction/eval_results/rebot_xy5_z30_kpz400_ep500_policy_eval/
  - 新增：ep500 六个 seed 的 18×6 张 PNG、轨迹 JSON、命令-响应摘要

peg_insert_reproduction/eval_results/rebot_ep394_baseline_policy_eval/
  - 新增：ep394 基线三个 seed 的同协议对照数据

peg_insert_reproduction/eval_results/rebot_ep394_seed1000_action_trajectory.json
  - epoch 394、seed 1000 单 episode 六维 raw action（旧格式，只有 `actions` 字段）

peg_insert_reproduction/eval_results/epoch394_action_plots/
  - 六个 action 维度各一张 PNG 曲线（旧格式产物）

peg_insert_reproduction/scripts/verify_rebot_model_sync.py
peg_insert_reproduction/scripts/smoke_rebot_env.py
peg_insert_reproduction/scripts/check_rebot_usd.py
peg_insert_reproduction/rebot_assets/rebot_description/urdf/rebot.urdf
peg_insert_reproduction/rebot_assets/rebot.usd
```

`/home/xiatenghui/.rebot/rebot_blue/`：

```text
src/rebot_description/urdf/rebot.xml
  - J2 0～180°
  - rebot_arm_velocity_limit = 3 rad/s

src/rebot_description/urdf/rebot.urdf
  - J2 upper = π

src/rebot_py/rebot_min_param_sim.xlsx
  - MuJoCo 仿真辨识的最小惯性参数集，重力补偿数据来源

src/rebot_sim2sim_eval/
  - 仍是旧实现，待重构
```

几轮动作尺度实验都没有改默认配置源码，只通过 Hydra 覆盖，避免污染 epoch 394 基线：

```text
已完成失败实验 1：
env.ctrl.pos_action_threshold=[0.002,0.002,0.005]
env.task.action_grad_penalty_scale=0.01

已完成失败实验 2：
env.ctrl.pos_action_threshold=[0.002,0.002,0.020]
env.task.action_grad_penalty_scale=0.0

成功实验（ep394→500）与当前实验（ep500→600）用的是同一组覆盖，两个实验只差 --max_iterations：
env.ctrl.pos_action_threshold=[0.005,0.005,0.030]
env.ctrl.default_task_prop_gains=[100,100,400,30,30,30]
env.task.action_grad_penalty_scale=0.0
```

## 现在存在的问题

1. **总体成功率 85.45%，用户判定不够好**：失败集中在横向对准（§8.3），且 394→500 只训了 106 个 epoch，
   用户判断训练量不足。**已从 ep500 续训到 ep600**（16:44 启动），结果待评估。
2. **训练 success 仍不等于 held-out**：本轮 final 训练 reward 指数（`last_Factory_ep_500_rew_624.67896`）低于 best 保存时的 652.0448，但 held-out 反而 final(85.45%) > best(81.54%)，**再次说明 reward 不能用来选 checkpoint**。
3. **raw action 与视频观感不一致的原因已基本查清**：action 是「相对当前位姿的目标偏移」，后面还有 EMA、裁剪、任务空间 PD、Jacobian、重力补偿、关节摩擦和接触；`a0` 大不等于 X 实际位移大。ep500 里 `a0` 已不再饱和，X 带宽只有 4.5～6.1 mm。
4. ~~Z 后段多数向上~~ — **新策略已解决**：ep500 三个 seed 的 10% 后 `raw a2` 均值均为负（−0.90 ~ −1.00）。
5. **`30 mm + Kp_z=400` 确实会放大双向命令，但本轮策略学会了稳定负 Z**，因此没有出现担心的退化；这条风险在当前策略上不成立，但换策略后要重新验证。
6. **洞口往复已定位到 X 轴**：不是 Y/Z/rotation。失败样本 X 带宽 5.9 mm、`|ema a0|` 均值 0.578、raw `a0` 饱和 29.4%，成功样本分别是 1.71 mm / 0.136 / 0.7%。
7. **成功不会终止 episode**：环境 `_get_dones()` 只在 300 步 timeout；插入成功后策略仍继续输出约 17 s 的满量程向下命令。held-out 计数不受影响，但浪费时长且掩盖卡死现象。
8. **成功指标有两种语义**：录像脚本按“第一次达到成功”选片，批量评估按 episode 结束时成功计数。二者不能混用。
9. **Actor 缺少接触信息和真实 peg 位姿**：只看到末端状态与上一动作；洞口精细接触完全依赖状态历史和动力学反馈。
10. **奖励缺少明确的插入进展方向**：主要是对称的 keypoint distance dense reward；对准后没有独立的持续向下/插入深度进展项，策略可能学到靠近孔口、退回和周期搜索的局部最优。
11. **`action_penalty_ee` 有维度 bug**：当前代码 `torch.norm(self.actions, p=2)` 会把所有环境一起求全局范数。其 scale 目前为 0，所以不影响训练；若将来启用，必须先改为 `dim=-1`。
12. **300→400 续训被异常中断**：TensorBoard 到 398，无 traceback、无当前 OOM 记录、无 final checkpoint。原因尚不确定。
13. **`.out` 日志可能严重滞后**：stdout 缓冲会造成误判；进度必须看 TensorBoard/checkpoint 元数据，
    用 `scripts/read_tb_events.py` 读 `info/epochs`。
14. **本地与云端 USD 文件字节哈希不同**：云端训练用 `c5524c47…`，本地 `rebot.usd` 为 `a2a647f3…`。重新同步或做 sim-to-sim 前必须查明差异，不能直接覆盖云端训练资产。
15. **sim2sim 包参数过期**：旧 `torque_limit=20`、`disable_gravity=true`、专用 eval XML 放宽限位，都与当前基准不一致。
16. **摩擦、夹爪与接触求解器仍存在域差异**：随机化只能提高鲁棒性，不能证明两边等价。
17. **云端数据盘不会随镜像保存**：checkpoint、日志和事件文件若未回传，释放实例会丢失。
18. **SSH 密码已出现在对话记录中**：应更换密码并改用密钥登录；不要把凭据写入此文档、脚本或 Git。

## 接下来按这个顺序做

1. ep600 best/final held-out 和 seed 1000/1001/1002 轨迹已完成；本地已有 54 张轨迹图、摘要和 `losses/a_loss` + `rewards/iter` 的 epoch 曲线。
2. **若 87.60% 仍不够好，只针对横向对准改**，不要再动 Z 尺度或 `Kp_z`（§8.3 已证明失败与 Z 深度无关）。候选方向，一次只改一个：
   - 给 actor 补真实 peg 位姿 / 接触力（当前 actor 只有 19 维，看不到接触）；
   - 奖励里加「对准后插入深度增量」，惩罚横向反复；
   - 考虑成功后终止 episode，缩短无效时长并让 return 信号更干净。
3. **补齐轨迹日志**：控制目标位姿、peg-hole 相对位姿、每步成功标记、接触/控制 wrench。没有这些无法区分「静摩擦卡死」和「接触抵住」。
4. 把视频帧与轨迹 step 对齐，重点核对：插入到底后那 17 s 末端是否真的完全不动、`a0` 振荡与孔壁接触的对应关系。
5. 训练结果确认可接受后，先修 `rebot_sim2sim_eval` 的 XML、速度上限、力矩、重力补偿和 recurrent state，再跑 MuJoCo nominal/stress。
6. 关机前必要备份已完成：五份正式权重及复现工件位于 `cloud_sync/ep700_20260930/`，ep700 的三个视频位于 `videos/rebot_xy5_z30_kpz400_ep700_three_batch/`。不再依赖云服务器进行下一步本地 sim-to-sim。
7. 处理遗留项：SSH 改密钥登录并更换密码（密码已多次出现在对话记录里）；查明本地/云端 `rebot.usd` 哈希差异。

## 关键云端路径

```text
项目根：/root/gpufree-data/isaac-sim

当前训练日志：
/root/gpufree-data/isaac-sim/peg_insert_reproduction/logs/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume500to600_seed42_20260929_1644.out

当前训练目录（正在训练，结束后会有 last_Factory_ep_600_*.pth）：
/root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume500to600_seed42_20260929_1644/

上一轮训练日志：
/root/gpufree-data/isaac-sim/peg_insert_reproduction/logs/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413.out

上一轮训练目录（含 best 与 final checkpoint）：
/root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413/
  nn/Factory.pth                                # best, epoch 482
  nn/last_Factory_ep_500_rew_624.67896.pth      # final, epoch 500

本轮 held-out 评估：
/root/gpufree-data/isaac-sim/peg_insert_reproduction/eval_results/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413_best_ep482_seed1000.json
/root/gpufree-data/isaac-sim/peg_insert_reproduction/eval_results/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_resume394to500_seed42_20260929_1413_final_ep500_seed1000.json

本轮逐 episode 轨迹（raw/EMA action + 末端位姿）：
/root/gpufree-data/isaac-sim/peg_insert_reproduction/eval_results/rebot_xy5_z30_kpz400_ep500_seed{1000..1005}.json
/root/gpufree-data/isaac-sim/peg_insert_reproduction/eval_results/rebot_ep394_baseline_seed{1000,1001,1005}.json

保留的 epoch 394 checkpoint：
/root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/rebot_ppo_gravcomp_ep20_h256_resume300to400_seed42_20260928_1649/nn/Factory.pth

epoch 394 held-out 评估：
/root/gpufree-data/isaac-sim/peg_insert_reproduction/eval_results/rebot_ppo_gravcomp_ep20_h256_resume300to400_seed42_20260928_1649_best_ep394_seed1000.json

epoch 394 raw action 轨迹（旧格式）：
/root/gpufree-data/isaac-sim/peg_insert_reproduction/eval_results/rebot_ep394_seed1000_action_trajectory.json
```

不要在 HANDOFF、Git 或 shell 脚本里保存 SSH 密码。

## 已踩过的坑，后面不要重复

- **不要再改基准 `rebot.xml`**，除非用户明确要求。发现不一致时改 Isaac 侧或评估适配层。
- **分清 J2 新旧基准**：旧版是 0～60°，当前唯一有效基准是 0～180°；不要再回退。
- **不要放宽 3 rad/s 速度上限**；MuJoCo 也不会自动执行 XML `<numeric>`，评估端必须主动截断。
- **Isaac 5.x 和 4.x 的 friction 语义不同**；当前 5.1 才能把数值按力矩解释。
- **没有重力补偿时机械臂会直接下坠**；不要再训练或评估 `disable_gravity=false` 且无补偿的控制器。
- **重力补偿必须在 reset/夹爪闭合阶段也生效**，否则 episode 开始状态会漂移。
- **resume 的 `max_iterations` 是绝对 epoch 上限，不是追加数量**。从 epoch 394 再训约 100 epoch 要设 500；
  当前从 500 再训 100 epoch 要设 **600**，都不是 100。写错会直接少训或立刻结束。
- **加载 checkpoint 后先看 TensorBoard 首个 `info/epochs`**，确认它接在起点 epoch 之后（本轮的判据是 **501**，且 `first_step` 等于 500×32768 = 16,384,000），而不是从 1 重启。
  用 `scripts/read_tb_events.py` 读，不要靠 `.out` 日志（会缓冲）。
- **`Factory.pth` 是 best，不代表 final**；用 checkpoint 内 `epoch`、`frame`、`last_mean_rewards` 判断它实际对应哪一轮。
- **进程消失不等于正常完成**；必须检查 TensorBoard 最终 epoch 和 `last_Factory_ep_*.pth`。
- **`.out` 会缓冲**；进度以 TensorBoard event 为准，日志末行不能作为最终 epoch。
- **评估 checkpoint 必须使用和训练匹配的环境覆盖，评估脚本不会自动从 checkpoint 恢复**。
  小尺度失败实验（`[0.002,0.002,0.005]`）评估时必须照样传它，否则会按默认 20 mm 执行动作、结论完全错。
  当前所有有效模型评估一律传 `[0.005,0.005,0.030]` + `[100,100,400,30,30,30]` + `action_grad_penalty_scale=0.0`。
- **当前 `[5,5,30] + Kp_z=400` 模型评估必须同时恢复两个覆盖**：动作尺度和 `default_task_prop_gains`；checkpoint 不会替你恢复环境 Hydra 参数。
- **训练 success 和 held-out success 不等价**；报告模型质量以固定协议的 held-out 1024 episode 为主。
- **录像中的“曾经成功”不等于 episode 结束时仍成功**；Factory 默认成功后不终止。
- **raw action 不是位移、速度或实际执行 action**。策略输出先过 EMA，再转成“相对当前位姿的目标偏移”，之后还有边界裁剪、PD、Jacobian、摩擦、接触和力矩限幅。看到 `a0=1` 不能写成“机械臂一直向前运动”。
- **action 坐标轴不是相机画面轴**。前三维是世界/环境坐标；当前基座与世界轴重合，`+Z` 向上，工位在 `+X`，但斜视相机里的屏幕前后/左右投影不同。判断方向要看数值轨迹或显示坐标轴，不能只凭画面直觉。
- **增大 `pos_action_threshold` 或 Kp 会同时放大正负方向**。epoch 394 后段经常输出正 Z；把 Z 改成 30 mm、Kp 改成 400 不保证只增强向下插入。
- **action 诊断必须同步记录 raw、EMA 后 action 和实际 pose**。只保存 raw action 会造成“曲线和视频不一致”但无法定位是裁剪、摩擦、接触还是控制映射导致。
- **不要在 timeout 的 `env.step()` 返回后读取最后一个 EMA action**；DirectRLEnv 可能已经 reset 并清零 `task.actions`。应在 step 前按同一 EMA 公式计算本步执行值，并在非终止步与环境值校验。
- **末端位姿同样有 reset 伪影，而且更隐蔽**：位姿是在 `env.step()` 之后采样的，因此 episode 终止那一步的位姿是 reset 之后的初始位姿（本项目里表现为 Z 突然跳回 0.125）。不处理就会在曲线上留下一个 50 mm 的假尖峰。`plot_policy_eval.py` 已自动剔除（判据：单步跳变 > 5 mm **且** 落回初始位姿 2 mm 以内）。**不要只按「接近初始位姿」判断**，reset 姿态与初始位姿在 X 上可以差 0.15 mm，容差取 1e-4 会漏检。
- **命令与响应的对齐是 off-by-one 陷阱**：`ema[k]` 是本控制步执行的动作，`pose[k]` 是该步执行后的位姿，所以 `ema[k]` 造成的位移是 `pose[k] − pose[k−1]`（`pose[−1]` 为初始位姿），**不是** `pose[k+1] − pose[k]`。用后者会把命令和下一步的响应配对。
- **逐步符号一致率对振荡轴是弱指标**：action 是「相对当前位姿的目标偏移」，响应本来就有滞后；Z 轴命令恒为负时一致率能到 95%，但 Y 轴来回振荡时一致率会掉到接近 0，这不代表控制映射有问题。判断控制方向要看整段趋势或累计位移，不要看逐步相关。
- **评估时必须按各自 checkpoint 的训练覆盖跑**：ep500 用 `[0.005,0.005,0.030] + [100,100,400,30,30,30]`，ep394 基线用默认 `[0.020,0.020,0.020] + [100,100,100,30,30,30]`。两者曲线不可直接互相比较，混用会得出完全错误的结论。
- **在云端起长任务必须 `setsid nohup ... &` 并重定向 stdin/stdout**。本次 Codex 用阻塞式 SSH 会话跑 1024-episode 评估，它断线后进程失去控制；虽然这次侥幸自己跑完了，但不能依赖。判断任务是否真的在跑要看 `pgrep` 和产物文件，不要只看发起它的那个会话是否还在。
- **策略评估图不要再做交互图或多维叠图**。用户明确要求每个维度一张简单静态 PNG：raw action 6 张、EMA action 6 张、实际末端 XYZ+RPY 6 张。
- **不要启用 `action_penalty_ee_scale` 后忘记修 `dim=-1`**，否则惩罚随并行环境数量变化。
- **动作平滑惩罚当前基于 EMA 后动作**；解释或迁移到 MuJoCo 时不要误写成原始动作差。
- **改变动作尺度会立即造成策略分布偏移**；前几个 epoch 成功率掉到 0 不足以说明实验失败。
- **不要同时跑多个 Isaac 训练、评估或转换进程**；每次启动前先查 `pgrep` 和 `nvidia-smi`。
  **ep600 训练没完全退出之前不要起 held-out 评估**——1024 episode 的评估很重，和训练抢 GPU/Kit 会互相拖慢甚至写出不完整的 JSON。
- **本次曾在训练进行时并行跑单环境录像/action 采集**，出现 Fabric clone 和 KVDB lock warning；虽然文件完整写出且训练未退出，但这会争抢 GPU/Kit 资源，后续不要重复，等训练空闲再采集。
- **训练必须用 `setsid nohup` 且 stdin 重定向到 `/dev/null`**，否则 SSH 退出可能带走进程。
- **即使 `setsid nohup` 正确，发起训练的那条 ssh 命令本身也会挂住不返回**：SSH 通道要等所有继承的文件描述符关闭。
  不要等它、也不要因此以为训练没起来；**另开一条 SSH 会话用 `pgrep` + `ps -o sid` 确认**（`sid` 与发起它的 wrapper 不同、`TT` 为 `?` 才算真正脱离）。
  本次启动命令就是这么被本地超时转后台的，训练本身 16:44 已正常开始。
- **不要用 `/usr/bin/python3` 或 Kit 的 python 直接读 TensorBoard events**：Kit python 有 tensorboard 但 import 不到 numpy，
  系统 python 两者都没有，pip 装又会污染容器。用 `peg_insert_reproduction/scripts/read_tb_events.py`（纯标准库）。
  注意 TFRecord 头是 `uint64 length` + **它自己的 4 字节 CRC** 共 12 字节，读数据要跳过这 4 字节，否则从第一条记录起就错位。
- **Isaac 脚本可能在结果写完后挂在 `app.close()`**；先确认输出文件完整，再只终止对应脚本。
- **Factory actor 没有图像并不是当前首要瓶颈**；先处理动作尺度、平滑、成功保持和接触观测。
- **root USD override 会遮住旧 sublayer**；检查参数必须读取 composed stage。
- **改 URDF 不等于改 USD**；重建或同步资产后必须重跑模型校验和 smoke。
- **本地和云端 USD 当前哈希不同**；上传前先备份、比较 composed 参数，禁止盲目覆盖。
- **云端没有 rsync**；传文件可用 tar over SSH，上传后逐文件校验 SHA-256。
- **云端数据盘不会随镜像保存**；释放实例前先下载 checkpoint 和日志。
- **不要把 SSH 密码、token 或其他凭据写入文档、脚本、命令历史或 Git**。
- **当前 `isaac-sim` checkout 使用普通 `.git/`**，用 `git -C /home/xiatenghui/.rebot/issac-sim ...`；不要 `git clean` 或 `reset --hard`。

## 历史结果，仅供定位差异

- 旧 checkpoint `rebot_ppo_x020_clearance20_seed42_20260914_1124`：训练于零关节摩擦/阻尼、关闭重力和 self-collision、effort 20 的旧模型。其 Isaac 成功率不能和当前模型直接比较。
- 旧 MuJoCo sim-to-sim：nominal 0/10、stress 0/100；使用的是过期评估模型和参数，只能说明旧链路失败，不能代表当前重力补偿策略。
- 最早 XML 同步但没有重力补偿的训练结果已废弃；视频表现为机械臂下坠，不应继续基于其 checkpoint 做实验。
