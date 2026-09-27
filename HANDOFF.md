# Rebot PPO 模型同步、重新训练与 MuJoCo Sim-to-Sim — HANDOFF

更新时间：2026-09-28 00:05（Asia/Shanghai）

## 一句话结论

Isaac Sim 侧的 Rebot 模型已与 **J2 限位 0～180°、带 3 rad/s 速度约束** 的 MuJoCo XML 同步，并加入关节摩擦随机化；基于该模型的新 PPO 已在云端 RTX 4090 上从头开训（2026-09-27 23:21 启动，预计 **2026-09-28 00:55 左右** 结束）。训练结果、held-out 评估和 MuJoCo sim-to-sim 都还没做。

## 现在在做什么

按顺序推进：

1. 以 `rebot_blue/src/rebot_description/urdf/rebot.xml` 为唯一动力学基准（不再改它）。
2. Isaac 侧（桥接 URDF、`rebot.usd`、运行时 ArticulationCfg）与 XML 对齐。——已完成
3. 用开环力矩回放确认两边动力学差异，对无法对齐的部分做域随机化。——已完成
4. 在同步后的模型上重新训练 PPO。——**进行中**
5. 用 held-out seeds 在 Isaac 评估新 checkpoint。——未开始
6. 重构 `rebot_blue/src/rebot_sim2sim_eval/`，用新 checkpoint 跑 MuJoCo nominal/stress sim-to-sim。——未开始

## 唯一模型基准

```text
/home/xiatenghui/work_space/rebot_blue/src/rebot_description/urdf/rebot.xml
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

- 关节 `damping=0.2`、`frictionloss=2.0`（N·m），armature 0。
- 臂电机 `ctrlrange=[-50, 50]`；Isaac 的 effort 上限按这个取 50（不是 `actuatorfrcrange=100`）。
- 速度上限记录在 `<custom><numeric name="rebot_arm_velocity_limit" data="3 3 3 3 3 3"/>`。**MuJoCo 没有原生关节速度约束**，这个值只是数据，仿真/评估端必须自己读取并截断速度。3 rad/s 是真机刻意保留的安全限制，不能放宽。
- 基准历史：原始 XML（J2 0～60°，SHA `d521ad5b…`）→ 2026-09-27 用户把 J2 改为 0～180°（`83c68baa…`）→ 同日加速度约束（当前 `02e923dc…`）。基于前两个哈希的结论都已过期。

## 已经完成

### 1. Isaac 模型与 XML 静态参数对齐

- 桥接 URDF `peg_insert_reproduction/rebot_assets/rebot_description/urdf/rebot.urdf`：六个臂关节限位与 XML 一致（J2 upper=π），effort 50，velocity 3，`damping=0.2`、`friction=2.0`。
- `rebot.usd`（root layer override）：J2 `upperLimit=180`，臂关节 `maxForce=50`、`physxJoint:maxJointVelocity=171.887°/s`（=3 rad/s），drive stiffness/damping 0/0，`customLayerData.rebot_sync_source_sha256` 指向当前 XML。当前 SHA-256 `c5524c47f930f255801c264eb18f6c8e27638e2a21bdfae2a384967d14c47877`。
- `scripts/verify_rebot_model_sync.py` 检查：8 个关节限位/阻尼/摩擦、臂关节 effort 与速度上限、8 个动态刚体的质量/质心/主惯量、USD 记录的 XML 哈希与当前 XML 一致。结果 `model_sync=ok joints=8 bodies=8`。
- 本地额外核对（一次性）：8 个刚体完整惯性张量相对误差 ≤4e-6，q=0 时各刚体世界位姿误差 0.000 mm / 0.000°。

### 2. 确认云端版本与摩擦语义

- 云端：Isaac Sim **5.1.0-rc.19**，Isaac Lab **2.3.2**（commit `37ddf62`），RTX 4090 24 GB，Xeon Gold 6430（容器配额 14 核）。
- Isaac Sim ≥5.0 的关节摩擦模型是 static/dynamic 库仑摩擦（力矩单位）+ viscous 项，因此 Isaac `friction=dynamic_friction=2.0` 对应 XML `frictionloss=2.0`，`viscous_friction=0.2` 对应 XML `damping=0.2`。4.x 下 friction 是无量纲系数，这个映射不成立。

### 3. 开环力矩回放对比（2026-09-27）

同一段力矩序列分别在 MuJoCo（源 XML）和 Isaac（训练用的同一份 ArticulationCfg）里施加，对比关节轨迹：

- 对得上：带摩擦 3 N·m 时 J1/J2/J3 末端角度比 0.998/0.997/0.988；关摩擦 1.5 N·m 时 J2/J3 误差 <1°；重力补偿+正弦力矩下 J1–J3 全程误差 <1.2°。说明质量、惯量、摩擦数值映射正确。
- 对不上：
  - 速度上限：Isaac 截在 3 rad/s，XML（当时）无上限。已通过给 XML 补速度约束解决（真机限制）。
  - 摩擦粘滞 vs 蠕动：力矩 <2 N·m 时 PhysX 关节完全粘住，MuJoCo 软约束 frictionloss 会缓慢滑动（0.3 s 内 J6 23°、J5 6.5°、J4 3.6°）。J4–J6 惯量小，影响明显。参数对齐解决不了，改用域随机化覆盖。

### 4. 关节摩擦域随机化

在 `rebot_task/rebot_factory_env.py` 加 `RebotEventCfg`，`mode="reset"`，每次 reset 对每个 env 重采样：

- J1–J3 库仑摩擦 U(1.0, 2.0) N·m；J4–J6 U(0.0, 2.0) N·m（下限到 0，覆盖 MuJoCo 低力矩蠕动）。
- static == dynamic（MuJoCo 只有一个值）。
- viscous U(0.1, 0.3)。
- 实现直接调 `write_joint_friction_coefficient_to_sim`，没用 Isaac Lab 的 `randomize_joint_parameters`（它对 static/dynamic/viscous 共用同一个分布，不能分开设范围）。

### 5. 复位姿态

`ARM_HOME = [0.000061041, 1.340906024, -0.903939962, 1.133828998, 0.000241180, -0.000004485]`：Tool 朝下、位于 x=0.20 m，J2=76.8°。在 J2 0～180° 下每个臂关节离限位 ≥25°。旧的 J2=60° 贴限位姿态（J4 只剩 8°）已废弃。

### 6. 云端同步与开训前 smoke

- 上传前把云端原文件打包到 `peg_insert_reproduction/rebot_assets/backups/cloud_before_xmlsync_20260927_231410.tgz`（云端）。
- 上传的 8 个文件本地/云端 SHA-256 逐个一致。
- `scripts/smoke_rebot_env.py`（16 env、400 步、随机动作）：状态全部有限，关节最大速度 2.958 rad/s，离限位最小 0.437 rad，摩擦在 reset 后确实重采样。`smoke=ok`。
- `scripts/check_rebot_usd.py` 本次**没有在云端跑**（用户中断）；smoke 已覆盖其主要检查项。

### 7. 新 PPO 训练（进行中）

```text
实验名：rebot_ppo_xmlsync_j2_180_fricdr_seed42_20260927_2321
任务：  Isaac-Rebot-Factory-PegInsert-Direct-v0
参数：  --num_envs 128 --seed 42 --max_iterations 200 --headless
启动：  2026-09-27 23:21:31 CST（setsid nohup，SSH 断开不影响）
日志：  /root/gpufree-data/isaac-sim/peg_insert_reproduction/logs/<实验名>.out
产物：  /root/gpufree-data/isaac-sim/IsaacLab/logs/rl_games/Factory/<实验名>/nn/
```

- 00:00 时到第 85 个 epoch，每个 epoch 约 26 s，reward 最高 38.87。
- 预计 00:50–00:55 结束。用户按此设置云服务器关机时间（建议 01:15 之后）。
- 资源实测（训练中）：显存 5.4 GB；GPU 利用率 75–85%，但功耗只有约 105 W / 450 W；训练进程 CPU 约 1.35 核。说明 128 env 时 GPU 大部分算力闲置，时间主要花在大量小 kernel 的启动/同步上，CPU 不是瓶颈。

## 还没有完成

1. 等训练结束，确认最终 checkpoint 写出（`last_Factory_ep_200_*.pth`），把 checkpoint 和训练日志拷回本地（checkpoint 不进 Git）。
2. 用 held-out seeds（如 1000–1004）做 Isaac 定量评估：`scripts/evaluate_rl_games.py --task Isaac-Rebot-Factory-PegInsert-Direct-v0`。评估时摩擦随机化仍会生效；如需 nominal 评估，要另外关掉 `events`。
3. 重构 `rebot_blue/src/rebot_sim2sim_eval/`：
   - 机器人定义直接来自源 `rebot.xml`，不再用专用 eval XML（它的关节限位全放宽成 ±π）。
   - 速度上限从 XML 的 `rebot_arm_velocity_limit` 读取，替换 `environment.py` 里写死的 3.0。
   - `config/rebot_peg_insert.yaml` 里的旧参数要改：`torque_limit: 20` → 50，`disable_gravity: true` → false。home 已和新 `ARM_HOME` 一致。
4. 用新 checkpoint 跑 MuJoCo nominal/stress，记录失败类型、轨迹和模型哈希。
5. `rebot_moveit_config`/`mujoco_ros2_control` 的 MuJoCo 仿真也加载同一个 `rebot.xml`，但 `mujoco_ros2_control` 没有读这个速度约束。需要确认 ROS 侧是否也要截速度（`joint_limits.yaml` 里 J2 规划速度是 2.5 rad/s）。
6. 用官方 Isaac URDF 转换器从桥接 URDF 完整重建 USD（当前仍是 root override，见"问题"）。
7. 核对夹爪映射：XML 是单 position actuator + equality 耦合两指，Isaac 是两指各一个独立 PD（500/0），没做对比实验。
8. 接触行为（PhysX vs MuJoCo 软接触）没有实验对比。

## 关键决策以及为什么这么选

| 决策 | 原因 |
| --- | --- |
| `rebot.xml` 是唯一动力学基准，不再修改 | 用户明确要求 XML 不变，Isaac 与它同步；避免为了凑评估结果反过来改评估模型。 |
| J2 限位 0～180° | 用户 2026-09-27 修改 XML 后确定为新基准。 |
| 3 rad/s 速度上限写进 XML | 真机刻意保留的安全限制；Isaac 本来就截在 3 rad/s，XML 补上后两边一致。用 `<numeric>` 是因为 MuJoCo 没有关节速度约束元素。 |
| Isaac `friction=2.0` 直接对应 `frictionloss=2.0` | 云端是 Isaac Sim 5.1，friction 是力矩单位；开环回放验证了 J1–J3 数值吻合。 |
| 摩擦随机化，J4–J6 下限到 0 | PhysX 粘滞与 MuJoCo 蠕动是求解器行为差异，不能靠调参对齐；让策略对摩擦不敏感是最直接的办法。轻关节受影响最大，所以范围更宽。 |
| static == dynamic | MuJoCo 只有一个 frictionloss，没有静/动摩擦之分。 |
| 自己写 reset event，不用 `randomize_joint_parameters` | 官方函数对三种摩擦共用一个分布，无法给 viscous 单独设范围。 |
| 从头训练，不在旧 checkpoint 上微调 | 旧策略训练于不同的限位、零摩擦、无重力、无 self-collision 模型，微调会混淆"模型同步是否有效"。 |
| 继续用 4090，不换 T4/16G | 训练约 1.5 h；T4 预计慢 2–4 倍且非 Isaac Sim 官方支持，一次训练总费用不一定更省；4090 已验证通过，且有余量将来开更多 env。显存不是瓶颈（只用 5.4 GB），16G 卡能否更快取决于型号而非显存。 |
| 不做多 seed 并行来"提速" | 多 seed 不会让单个模型更好，只改善统计；并行还会抢算力。 |
| 暂不加相机图像观测 | 孔径 8.1 mm、成功判据 2.5 mm，通用图像编码器难以提供毫米级位置；Isaac RTX 与 MuJoCo OpenGL 渲染差异大会破坏 sim-to-sim；吞吐会降一个数量级以上。若真机拿不到孔位，优先做独立视觉定位模块给现有策略喂孔位。 |
| USD 暂用 root layer override | 本地没有完整 Isaac 转换环境；override 能先闭环验证参数链，最终仍需官方重建。 |

## 改过的重要文件

`isaac-sim/`（本仓库只同步 HANDOFF 和必要脚本，资产、日志、视频、checkpoint 不进 Git）：

```text
HANDOFF.md
peg_insert_reproduction/rebot_task/rebot_factory_env.py      # ARM_HOME、速度/力矩常量、摩擦随机化 event
peg_insert_reproduction/scripts/verify_rebot_model_sync.py   # 新增速度上限与 XML 哈希校验
peg_insert_reproduction/scripts/smoke_rebot_env.py           # 新增：开训前 smoke
peg_insert_reproduction/scripts/check_rebot_usd.py           # J2 期望改为 [0, π]，新 articulation 参数
peg_insert_reproduction/rebot_assets/rebot_description/urdf/rebot.urdf   # 桥接 URDF（已在 Git 中跟踪）
peg_insert_reproduction/rebot_assets/rebot.usd                          # root override（不进 Git）
peg_insert_reproduction/rebot_assets/config.yaml                         # 转换配置（不进 Git）
```

`rebot_blue/`：

```text
src/rebot_description/urdf/rebot.xml    # J2 0～180°，新增 rebot_arm_velocity_limit
src/rebot_description/urdf/rebot.urdf   # J2 upper=π
src/rebot_sim2sim_eval/                 # MuJoCo sim-to-sim 评估包（待重构）
```

## 现在存在的问题

1. **训练还没结束**：结果未知。reward 00:00 时约 35–39，和旧实验（ep200 约 423）不可直接比较，因为模型、摩擦、重力、self-collision 都变了。
2. **USD 是过渡结构**：root layer override 盖住了 `configuration/rebot_physics.usd` 的旧值（sublayer 里 J2 upper 是 179.99998°，速度也是旧的）。只读 root 或只读 sublayer 都会得出错误结论，必须检查 composed stage。
3. **云端项目目录已被覆盖为新版**：云端 `peg_insert_reproduction/` 下 8 个文件已换成本地同步版；旧版只在 `rebot_assets/backups/cloud_before_xmlsync_20260927_231410.tgz`。
4. **sim2sim 评估包参数过期**：`torque_limit: 20`、`disable_gravity: true`、专用 eval XML 限位 ±π，与当前基准不一致。
5. **摩擦粘滞/蠕动差异仍存在**，只是靠随机化让策略鲁棒，并没有消除；MuJoCo 里 J4–J6 的行为仍可能和训练分布有偏差。
6. **夹爪、接触、Tool 刚体**：Isaac 多一个 0.01 kg 的 fixed `Tool` body；夹爪耦合方式不同；接触求解不同。都没做量化对比。
7. **evaluate 时摩擦随机化默认开启**：`RebotFactoryPegInsertCfg.events` 在评估也会生效，结果是"随机摩擦下"的成功率。
8. **SSH 凭据暴露**：云服务器密码出现在对话记录中，应尽快更换并改用密钥登录。

## 接下来按这个顺序做

1. 00:55 后确认训练结束：`pgrep -af train_rebot` 无进程，`nn/` 下有 `last_Factory_ep_200_*.pth`。关机前把 checkpoint 和 `.out` 日志拷回本地。
2. Isaac held-out 评估（seed 1000–1004，128 env，每 seed 1024 episode），分别跑随机摩擦和 nominal 摩擦两组。
3. 重构 `rebot_sim2sim_eval`：直接加载源 XML，速度上限从 XML 读取，修正 torque/gravity 配置，删除专用 eval XML 里的放宽限位。
4. 用新 checkpoint 跑 MuJoCo nominal/stress，结果写入 `peg_insert_reproduction/sim2sim_results/` 并带上 XML/USD/checkpoint 哈希。
5. 若 sim-to-sim 仍失败，再按失败类型定位（先看 J4–J6 摩擦、夹爪、接触）。
6. 云端可用时用官方转换器重建 USD，重跑 `verify_rebot_model_sync.py`、`check_rebot_usd.py`、`smoke_rebot_env.py`。

## 常用命令

本地同步检查：

```bash
source /tmp/rebot_sim2sim_venv/bin/activate   # 本机临时环境，不是工程依赖
python peg_insert_reproduction/scripts/verify_rebot_model_sync.py \
  --xml /home/xiatenghui/work_space/rebot_blue/src/rebot_description/urdf/rebot.xml
```

云端（根目录 `/root/gpufree-data/isaac-sim`，先确认路径仍存在）：

```bash
cd /root/gpufree-data/isaac-sim/IsaacLab
# 开训前 smoke
./isaaclab.sh -p ../peg_insert_reproduction/scripts/smoke_rebot_env.py --num_envs 16 --steps 400
# 训练（实验名必须新起，禁止覆盖旧目录）
NAME=rebot_ppo_<描述>_seed42_$(date +%Y%m%d_%H%M)
setsid nohup ./isaaclab.sh -p ../peg_insert_reproduction/scripts/train_rebot.py \
  --task Isaac-Rebot-Factory-PegInsert-Direct-v0 --headless --num_envs 128 --seed 42 --max_iterations 200 \
  agent.params.config.full_experiment_name=$NAME \
  > ../peg_insert_reproduction/logs/$NAME.out 2>&1 < /dev/null &
```

训练进度看 TensorBoard 事件文件（`summaries/events*` 里的 `info/epochs`、`rewards/iter`），`.out` 日志里 rl_games 不打印逐 epoch 进度。

## 历史结果（保留，但不能当作当前结论）

- 旧 checkpoint `IsaacLab/logs/rl_games/Factory/rebot_ppo_x020_clearance20_seed42_20260914_1124/nn/last_Factory_ep_200_rew_423.31128.pth`（SHA-256 `a1f9c7b7…`）：训练于 J2 0～180°（但无 XML 同步）、零关节摩擦/阻尼、关闭重力和 self-collision、effort 20 的旧模型。Isaac 内固定工位 1024/1024、三个泛化工位各 128/128。
- 旧 MuJoCo sim-to-sim：nominal 0/10，stress 0/100（`peg_insert_reproduction/sim2sim_results/`）。
- 这些只能用来定位差异，不能用来证明同步后的模型。

## 已踩过的坑，后面不要重复

- **不要再改 `rebot.xml`**，除非用户明确要求。发现不一致时改 Isaac 侧（桥接 URDF / USD / 运行时 cfg）或评估适配层。用户改了基准后，要同步更新本文件里的哈希，并把旧结论标为过期。
- **分清"XML 不变"指的是哪个版本**。2026-09-27 用户说"XML 不变，USD 与其同步"时，指的是**改过 J2 之后**的 XML；曾误把 XML 撤回到 60°，又重做一遍。基准变更时先确认用户说的是哪一版。
- **不要放宽 3 rad/s 速度上限**。它是真机安全限制，不是仿真缺陷。
- **MuJoCo 不会自己执行 `rebot_arm_velocity_limit`**。任何用 XML 的仿真/评估都要读取并截断关节速度。
- **friction 的单位取决于 Isaac Sim 版本**。5.x 是力矩，4.x 是无量纲系数。换云端镜像或降级前先查版本。
- **参数对齐 ≠ 动力学一致**。同步脚本只保证静态参数一致；求解器行为（摩擦粘滞/蠕动、接触、速度截断）只能用开环力矩回放等实验验证。
- **`nvidia-smi` 利用率高不代表 GPU 忙**。128 env 时利用率约 80%，功耗却只有约 105 W；看功耗和 SM 时钟判断算力是否跑满。
- **显存大小不决定算力**。16G 卡里既有 4080 级也有 4060 Ti 级，换卡看型号。
- **云端没有 rsync**，传文件用 `tar czf - ... | ssh ... "tar xzf -"`，上传后逐个比对 SHA-256。
- **上传前先备份云端原文件**，云端可能有本地没有的修改（这次就发现云端 ARM_HOME、摩擦、USD 与本地不同）。
- **Isaac 脚本结束后可能挂在 `app.close()`**，结果写完了进程不退出。用结果文件判断完成，再 `pkill` 对应脚本。
- **`isaaclab.sh` 训练要用 `setsid nohup` 并重定向 stdin**，否则 SSH 断开会带走训练。
- **不要同时跑多个 Isaac 训练/评估/转换进程**，会抢 GPU、拖慢正在进行的训练，使时间预估失效。每次开新进程前先 `pgrep -af "kit|isaac"`、`nvidia-smi`。
- **rl_games 的 `.out` 日志不打印 epoch 进度**，要读 TensorBoard 事件文件。
- **root override 会遮住旧 sublayer**。检查 USD 要看 composed stage。
- **改 URDF 不等于改 USD**，最终必须用官方转换器重建。
- **不要把 reset pose 放在关节限位上直接训练**，训练噪声会立即顶限。
- **Factory success 不会自动终止 episode**，评估/录像要在首次成功时停计数。
- **单环境渲染可能触发 Fabric clone warning**，必要时 `--disable_fabric`；以退出码、数值位姿和实际输出文件判断结果。
- **`isaac-sim` 的 Git 元数据在 `.git-metadata/`**（`core.worktree=..`），不是 `.git`。用 `git --git-dir=.git-metadata --work-tree=.` 操作；不要 `git clean`/`reset --hard`。
- **`isaac-sim` 仓库只放 HANDOFF 和必要脚本**。USD/网格资产、checkpoint、视频、日志、`.sync-backups/`、临时 venv、`__pycache__` 都不进 Git。
- **不要把 SSH 密码、token、云服务器地址写进文档、脚本、命令历史或 Git**。
