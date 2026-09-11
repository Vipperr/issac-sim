# Isaac Lab Rebot 竖直插孔复现 — HANDOFF

更新时间：2026-09-11（Asia/Shanghai）

## 现在在做什么

目标是在 Isaac Lab 中用用户的六轴 Rebot 复现 PPO 小孔插入；当前任务是完成“平面上的竖直插孔”场景、验证工作位姿，再开始新的 Rebot 专用 PPO 训练。

当前 Rebot Isaac Lab 环境已使用最新 URDF、J2 `0～π` 限位、专用插头偏置和新孔位。云端已经成功加载并渲染该场景，但最后一次 SSH 空闲检查被服务器拒绝连接；恢复连接后先做一次 smoke test，再启动训练。

> 本文档的 Rebot 结论与旧 Fraka Factory baseline 分开。旧 baseline 已归档，只能作为 Isaac Lab/PPO 流程参考，**不能**作为当前 Rebot 任务的性能结论或 checkpoint。

## 已完成哪些

### Rebot 模型、限位与 USD

- Rebot 资产使用 `rebot_blue` 中最新 URDF；Isaac Lab 项目内副本与源 URDF SHA-256 一致。
- J2 已按用户要求扩至 `lower="0.0" upper="3.1415926"`；云端 USD 已重新转换。
- 云端 Isaac Lab 读取 USD 的实际 J2 软限位为 `[0.0, 3.141592264175415]`，不是只修改了 XML 文本。
- USD 转换保留固定关节（`--fix-base --joint-target-type none`，不使用 `--merge-joints`），因此 `Tool` 仍是独立 body，Rebot 任务可按名称取得末端雅可比。
- Rebot 工程的 MuJoCo XML 已同步为 `Joint_2 range="0 3.1415926"`，并通过 XML 解析校验。

### Rebot 专用竖直插孔环境

- 建立任务 `Isaac-Rebot-Factory-PegInsert-Direct-v0`，入口在 `rebot_task`。
- 插头相对 `Tool` 的尖端偏置固定为 55 mm；抓取资产由已有 Factory 逻辑生成，不改 Isaac Lab Factory 源码。
- reset 时把孔根自动放在插头尖端下方 40 mm，孔平面为 `z=0`；因此只改初始关节姿态即可一致地移动孔位和插头，不会出现手工写死的二者脱节。
- 新预插入姿态（单位 rad）：

  ```text
  [0.000050628, 1.377286420, -0.805942139,
   0.999452022, 0.000213108, 0.0]
  ```

- 云端单环境实际验证结果：

  ```text
  Tool      = (0.200000, 0.000000, 0.095000) m
  插头尖端  = (0.200000, 0.000000, 0.040000) m
  孔根      = (0.200000, 0.000000, 0.000000) m
  插头轴向  = (约 0, 约 0, 1)
  ```

  位置/轴向误差约 `2e-6 m` / `1.5e-6`。四个视角的验证图已同步到本地：`/home/xiatenghui/文档/ChatGPT/issac_sim/rebot_workspace_x020/`。

### 工作空间计算

- 使用最新 Rebot URDF 的原始 `origin/rpy/axis` 逐链正运动学和数值约束 IK；不是 Franka 模型，也不是把用户 DH 参数直接当成 URDF 坐标。
- 约束：孔平面 `z=0`、插头尖端起始高度 `0.04 m`、工具轴竖直向下、孔在机器人正前方中心线。
- 理论中心线可达范围：`X ≈ 0.0246～0.4956 m`。两端贴近关节边界，不能当作训练工位。
- 采样的灵活区域：`X=0.15～0.30 m、|Y|≤0.05 m`。在该区域 5 自由度插入雅可比条件数约 `4.58～6.10`；越过 `X=0.35 m` 后条件数和关节余量明显变差。
- 选定孔位 `(0.20, 0, 0) m`：相比原来 `X=0.12 m` 前移 80 mm；中心线条件数约 `4.85`，最小归一化关节余量约 `18%`，比边界姿态更适合策略探索。

### 验证与录制工具

- `check_rebot_usd.py`：加载 USD、确认 `Joint_1..6` / 手指 / `Tool`、检查有限状态，并断言 J2 限位为 `0～π`。
- `capture_rebot_views.py`：一环境、四视角并打印实际 Tool/插头尖端/孔根/轴向；该脚本为避免单环境实例化问题设置 `env_cfg.sim.use_fabric = False`。
- `record_successful_episode.py`：已调整到新孔位的相机取景；旧 checkpoint 只可用于调试动作，不能用于当前任务成功率。

### 已归档的旧 Factory baseline

- 官方 Fraka `Isaac-Factory-PegInsert-Direct-v0` 的三 seed PPO baseline、评估 JSON、报告和视频已归档在 `peg_insert_reproduction/archive/2026-09-02/`。
- 该 baseline 的跨 seed 成功率为 98.16%，但资产、末端、孔位与 Rebot 均不同；绝不能拿来证明 Rebot 成功。
- 归档和压缩包是大文件，**不要加入 Git，不要删除或重打包已校验归档**。

## 还有哪些没做

1. 恢复云服务器 SSH 后，先运行一次新姿态 smoke test 与一环境 reset；尚未开始适用于新布局的 PPO 训练。
2. 为 Rebot 的 ROS2 + MuJoCo 运行链路增加“仅仿真生效”的 J2 `0～π` 控制器限位覆盖。当前 `rebot.xml` 已更新，但 `ros2_controllers.yaml` 中三个控制器仍把 J2 限制为 60°；新初始姿态的 J2 为 78.9°，因此该链路会拒绝/截断它。
3. 在新布局重新训练、训练后按固定 held-out seed 评估、再录一条完整单 episode 视频。此前 300 epoch Rebot checkpoint 的评估为 `0/1024`，且当时插头/孔几何尚未正确，已失效。
4. 检查 Rebot 专用 PPO 的训练时长和 `num_envs` 后再定 epoch；不要复用旧 Fraka 结论或直接声称已收敛。
5. 用户未要求 Git 提交；待用户确认后再整理非归档文件并提交。不要把 archive、`__pycache__` 或凭据加入提交。

## 关键决策及原因

| 决策 | 原因 |
| --- | --- |
| 使用 URDF FK 计算工作空间 | Isaac Lab 使用的是 URDF→USD 链；这样得到的 Tool 位姿与仿真一致，避免 DH offset/坐标轴重复转换。 |
| 孔位设为 `(0.20, 0, 0)` | 位于正前方高灵活度区域，避开理论边界及其低余量/较差条件数。 |
| 孔由 reset 从插头姿态推导 | 使孔与插头保持 40 mm 的竖直 approach，移动工作位姿时不会遗漏其中一个资产。 |
| 保留 `Tool` 固定 body | Factory 控制和雅可比查询依赖该 body；USD 转换不能 merge fixed joints。 |
| J2 先只改 URDF/USD/MuJoCo XML | 用户明确要求扩展仿真模型；全局 ROS2 控制器 YAML 同时服务真实机械臂，直接扩至 180°会扩大真机软件安全边界。 |
| 真机控制器 YAML 暂保持 60° | 这是有意的安全隔离。若只需 MuJoCo，应做 sim-only override；只有用户明确确认真机 J2 可安全到 180°，才可修改共用 YAML。 |
| 不复用旧 Rebot checkpoint | 其训练发生在插头挂载/孔位修正之前，评估 `0/1024`，不具备可比性。 |

## 改过哪些重要文件

### Isaac Lab 项目：`/home/xiatenghui/.rebot/issac-sim`

- `peg_insert_reproduction/rebot_assets/rebot_description/urdf/rebot.urdf`：Rebot 资产副本；J2 为 `0～π`，与源 URDF 同步。
- `peg_insert_reproduction/rebot_assets/rebot.usd`：云端已由新 URDF 重建；本地不依赖该二进制副本。
- `peg_insert_reproduction/rebot_task/__init__.py`：注册 `Isaac-Rebot-Factory-PegInsert-Direct-v0`。
- `peg_insert_reproduction/rebot_task/rebot_factory_env.py`：Rebot 控制器参数、55 mm 插头偏置、自动竖直孔位和新的 `ARM_HOME`。
- `peg_insert_reproduction/scripts/train_rebot.py`：注册 Rebot task 后复用 Isaac Lab 原生 RL-Games trainer。
- `peg_insert_reproduction/scripts/check_rebot_usd.py`：USD 限位/结构 smoke test。
- `peg_insert_reproduction/scripts/capture_rebot_views.py`：四视图与数值布局验证。
- `peg_insert_reproduction/scripts/record_successful_episode.py`：新孔位相机视角；录制时需先处理 Fabric 开关问题。
- `peg_insert_reproduction/scripts/run_rebot_diff_ik.py`：Rebot Tool DLS-IK 检查脚本。

### Rebot 工程：`/home/xiatenghui/.rebot/rebot_blue`

- `src/rebot_description/urdf/rebot.urdf`：J2 URDF 限位 `0～π`。
- `src/rebot_description/urdf/rebot.xml`：MuJoCo `Joint_2 range="0 3.1415926"`。
- `src/rebot_moveit_config/config/ros2_controllers.yaml`：**目前故意仍为 J2 上限 60°**；这是下一步必须区分 sim/real 的位置。

## 当前问题和风险

1. 云服务器最后一次 SSH 检查返回 `Connection refused`。此前 USD 转换和新孔位一环境渲染均以 exit code 0 完成；重新连接后不要假设 GPU 空闲，应先 `pgrep` 检查训练/评估/录制/转换进程。
2. MuJoCo XML 与 URDF 限位已更新，但共用 ROS2 controller YAML 仍为 60°。在未做 sim-only override 前，不要尝试通过 Rebot ROS2 规划器执行新姿态；它会被软件限位截断。
3. `capture_rebot_views.py` 即使禁用 Fabric，云镜像仍可能记录 Fabric clone warning；本次退出码为 0 且四图已生成。应以退出码、打印的位姿和图像文件为准，而不是只看 warning。
4. `record_successful_episode.py` 的 `--disable_fabric` 参数当前只是解析，未写入 `env_cfg.sim.use_fabric`；下次录制前应补上该一行，否则单环境录像可能重现 Fabric 问题。
5. 当前 Rebot 任务工作树包含大量未跟踪内容和旧 archive；不要 `git clean`、`git reset --hard`、覆盖 `rebot_task/`，也不要把大归档/`__pycache__/` 提交。
6. 所有 Rebot 结论目前是仿真几何和单环境布局验证，尚无新训练成功率，更没有真机结果。

## 接下来要做什么

1. 云服务器恢复后，检查无残留 Isaac 进程和 GPU 资源。
2. 用户确认范围：
   - 仅 MuJoCo：为 `rebot_arm_controller` 和 `rebot_trajectory_planner_controller` 注入 sim-only 的 J2 上限 `3.1415926`；真实硬件配置不动。
   - 真机也使用 180°：必须由用户明确确认物理限位、安全区域和监护措施后，再更新共用 ROS2 YAML、MoveIt 和测试限位。
3. 执行 USD smoke test，并用新 `ARM_HOME` 跑一环境 reset/四视图检查。
4. 启动新的 Rebot PPO baseline；记录训练命令、seed、环境数、epoch、耗时和 checkpoint 路径。
5. 用未参与训练的评估 seed 执行成功率评估；合格后录制一条完整单 episode 视频，再决定是否增加多 seed 训练。
6. 训练、评估和视频完成后，更新本文件、生成最终报告，并在用户确认的范围内 Git 提交。

## 云端命令参考

云端根目录：`/root/gpufree-data/isaac-sim`；项目：`/root/gpufree-data/isaac-sim/peg_insert_reproduction`；Isaac Lab：`/root/gpufree-data/isaac-sim/IsaacLab`。

运行前：

```bash
cd /root/gpufree-data/isaac-sim/IsaacLab
TORCH_LIB=/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/torch/lib
```

验证更新后的 USD：

```bash
env LD_LIBRARY_PATH="$TORCH_LIB:$LD_LIBRARY_PATH" ./isaaclab.sh -p \
  /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/check_rebot_usd.py \
  --asset /root/gpufree-data/isaac-sim/peg_insert_reproduction/rebot_assets/rebot.usd \
  --arm_joints 0.000050628 1.377286420 -0.805942139 0.999452022 0.000213108 0 \
  --steps 60 --headless
```

渲染新孔位：

```bash
env LD_LIBRARY_PATH="$TORCH_LIB:$LD_LIBRARY_PATH" ./isaaclab.sh -p \
  /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/capture_rebot_views.py \
  --task Isaac-Rebot-Factory-PegInsert-Direct-v0 --headless \
  --output_dir /tmp/rebot_workspace_x020
```

新的 Rebot PPO 训练模板（开始前先确认 sim-only 限位和 GPU 空闲）：

```bash
env LD_LIBRARY_PATH="$TORCH_LIB:$LD_LIBRARY_PATH" ./isaaclab.sh -p \
  /root/gpufree-data/isaac-sim/peg_insert_reproduction/scripts/train_rebot.py \
  --task Isaac-Rebot-Factory-PegInsert-Direct-v0 --headless \
  --num_envs 128 --seed SEED \
  agent.params.config.full_experiment_name=rebot_ppo_x020_seedSEED
```

## 已踩过的坑：后续不要重复

- 修改 URDF 关节限位后，必须重新生成 USD；仅同步 `.urdf` 不会改变 Isaac Lab 已有 USD。
- Rebot 有 URDF、MuJoCo XML、ROS2 controller YAML、MoveIt/测试等多个限位消费者。先区分仿真和真机，不要为修复仿真静默扩大真实机械臂安全范围。
- 用户给出的 DH offset/限位是 DH 坐标系；不要直接当作 URDF joint 值。Isaac 工作空间和姿态必须用实际 URDF 链验证。
- 圆孔竖直插入不需要固定工具 yaw，但必须检查 Tool、插头尖端和孔根的真实世界坐标；不要只凭渲染画面中资产颜色判断是否对齐。
- Factory success 不会自动终止 episode；固定长度视频会录进复位和下一次尝试。完整录制必须首次成功后停，失败才走原生 timeout。
- 单环境渲染/视频容易触发 Fabric clone warning；用 `sim.use_fabric=False`、退出码、打印位姿和实际文件共同验证。
- 不要同时运行多个 Isaac Sim 训练、评估、录制或转换任务；4090 单卡会互相抢显存，云端开始前用 `pgrep` 检查。
- 旧 Rebot checkpoint 和旧 Fraka archive 都不能用于新垂直插孔布局的性能声明。
- archive、checkpoint、视频很大；同步后做 SHA-256 校验，且不要加入 Git。云端没有 `rsync` 时使用 `scp`。
- 不要把云服务器密码、GitHub token、SSH 私钥写入命令历史、日志、Git remote 或本文件。
