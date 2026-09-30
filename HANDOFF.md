# Rebot PPO / Isaac Sim → MuJoCo — 当前交接

更新时间：2026-09-30（Asia/Shanghai）。本轮仅整理文档，没有新增训练、评估、录制、云端操作或清理。

## 1. 当前任务与最重要结论

**当前任务是本地 sim-to-sim 对齐和孔内卡住原因诊断，不是继续 PPO 训练。** Isaac 正式训练已结束到 epoch 700；MuJoCo 已完成接口、四元数、质量、机器人惯性增量和孔/针碰撞几何修正，并录完最新三个视频。

当前可以确认：

- Isaac ep700 final：独立 deterministic **10/10 成功**，Evaluation Return **753.23 ± 92.22**。这是10个episode的小样本结果，不是1024-episode泛化成功率。
- 最新 MuJoCo：标称 seed1000 孔内卡住；随机化 seed1001 成功并保持到结束；随机化 seed1002 孔内卡住。**一条标称加两条压力测试不能合并宣称“迁移成功率33.3%”，更不能说迁移已完成。**
- 最新三个视频已完整录制、解码检查并与同配置快速测试核对。没有仍在等待完成的录制/评估会话。
- 必要训练权重、事件、参数、任务代码和机器人USD已备份。**本轮重新校验云端备份清单201个文件，全部通过。** 没有执行关机；最近一次SSH检查是 Connection refused，不能据此断言实例已经关闭。
- **孔/针输入表面按官方USD修正，不等于复现PhysX cooked SDF、夹持和接触求解。** 云端缓存的孔/针USD，以及云端未备份的Factory基类仍未直接核实。

工作目录约定（下文相对路径按对应根目录解释）：

~~~text
Isaac工作区 / 文档和结果根：
/home/xiatenghui/.rebot/issac-sim

MuJoCo / ROS工作区：
/home/xiatenghui/.rebot/rebot_blue

当前MuJoCo包：
/home/xiatenghui/.rebot/rebot_blue/src/rebot_sim2sim_eval

隔离Python：
/home/xiatenghui/.rebot/rebot_blue/.venv/sim2sim/bin/python
~~~

本地运行不需要云服务器，不操作真机。后续任务以用户当前请求为授权范围；本文件的“下一步”是建议，不是自动启动训练、改奖励、清理或发起云端任务的授权。

## 2. 已经完成

### 2.1 正式训练、独立评估和本地备份

正式实验名：

~~~text
rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_diag_eval10_lrrestore_resume600to700_seed42_20260930_0955
~~~

从ep600 final续训到ep700，128 env、seed42、20秒episode、horizon256；开启PPO diagnostics，save_frequency=10，恢复checkpoint学习率约3.901844e-6。训练已正常结束，不要再把旧“ep600训练中”描述当现状。

610/620/.../700各做一次独立评估：num_envs=10、seed1000、deterministic、每个checkpoint10个episode，使用训练一致的三个Hydra覆盖：

~~~text
env.ctrl.pos_action_threshold=[0.005,0.005,0.030]
env.ctrl.default_task_prop_gains=[100,100,400,30,30,30]
env.task.action_grad_penalty_scale=0.0
~~~

| epoch | Mean Eval Return ± Std | episode末成功 |
| ---: | ---: | ---: |
| 610 | 754.74 ± 93.79 | 10/10 |
| 620 | 751.70 ± 100.53 | 10/10 |
| 630 | 752.65 ± 99.77 | 10/10 |
| 640 | 753.61 ± 97.02 | 10/10 |
| 650 | 751.23 ± 98.20 | 10/10 |
| 660 | 754.34 ± 93.49 | 10/10 |
| 670 | 755.11 ± 93.22 | 10/10 |
| 680 | 754.95 ± 93.27 | 10/10 |
| 690 | 728.27 ± 109.37 | 9/10 |
| 700 | 753.23 ± 92.22 | 10/10 |

已产出逐episode return、评估日志、checkpoint清单、Evaluation Return mean±std图和8面板PPO训练诊断图（Return、Length、Actor/Value Loss、Entropy、KL、平均Clip Fraction、Explained Variance）。epoch601没有完整episode，Return/Length从602开始，其他指标从601记录；不能补造601的episode指标。

Isaac根目录下：

- 评估：peg_insert_reproduction/eval_results/正式实验名/
- 训练事件/参数/日志：peg_insert_reproduction/training_logs/正式实验名/
- 完整云端备份：peg_insert_reproduction/cloud_sync/ep700_20260930/

本地保留5份完整RL-Games权重（含网络、归一化、optimizer）：ep700 final、训练best ep697、对照ep670、ep600 final、best ep561。默认sim-to-sim使用**ep700 final**，不要用Factory.pth文件名推断final：

~~~text
/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/cloud_sync/ep700_20260930/IsaacLab/logs/rl_games/Factory/rebot_ppo_gravcomp_ep20_h256_xy5_z30_kpz400_nosmooth_diag_eval10_lrrestore_resume600to700_seed42_20260930_0955/nn/last_Factory_ep_700_rew_656.40564.pth
~~~

ep600历史1024-episode held-out：final897/1024=87.60%，best891/1024=87.01%。**ep700的10/10与ep600的87.60%样本量不同，不作同协议提升结论。**

备份范围不含云端完整Isaac安装/Factory基类，也不含当时云端缓存的官方孔/针USD；新下载的两份官方USD另存本地，不能说201文件已包含所有物理引擎依赖。610–690中间权重本地只保留ep670，其余最近确认仍在云端，释放实例后不能保证可恢复。

已做清理：本地旧重复解压归档约611 MiB（保留tar.xz，可恢复）；两端临时传输tar；云端0938/0946弃用分支权重约406 MiB（未备份，不能恢复）。正式权重/结果/视频保留；不继续批量删除。

### 2.2 MuJoCo接口、控制和运动学

- Actor19维：相对孔顶位置3、Tool四元数wxyz4、差分线/角速度各3、上一EMA动作6。**推理确实使用四元数。** Actor无图像、无真实独立peg位姿/接触力；central critic使用43维privileged state。
- ep700 actor适配：观测归一化eps=1e-5并clip±5，2×1024 LSTM → LayerNorm → ELU MLP512/128/64 → mu6并clip±1；每episode清空hidden/cell。初始Isaac动作复算最大差约2.15e-6，不代表所有动态状态已完全匹配。
- physics dt=1/120秒，decimation8，policy dt=1/15秒，20秒/300控制步，reset settle0.25秒。
- EMA0.2；平移[5,5,30] mm，旋转各0.097 rad；世界坐标增量；相对工位位置裁剪±50 mm；Jᵀ任务空间PD，Kp=[100,100,400,30,30,30]，Kd=2√Kp。
- 实际actuator限幅50 Nm；物理重力开启并添加同训练的辨识重力补偿，reset同样补偿。100姿态float64与训练Torch函数最大差2.22e-16 Nm。
- 关节限位：J1/J4–6 ±90°，J2 0–180°，J3 -180–0°；3 rad/s。MuJoCo步后裁剪qpos增量/qvel只是近似，不是PhysX原生速度约束等价实现。
- 102静态姿态FK比较：Tool最大位置差1.73e-7 m、姿态差约2.67e-5°。关节零位、顺序、正方向和Tool offset一致到模型舍入精度。两边重力DH偏置均[0°,180°,167.42°,12.58°,-90°,-90°]，仅在动力学函数内使用，不能再加到qpos。
- 不改真机/原始基准XML：rebot_blue/src/rebot_description/urdf/rebot.xml，SHA-256为02e923dc78ea15851070c2fed3a919e978a61d2ec96eee235c52b1f3bae95bba。评估改变发生在专用MJCF和适配层。

### 2.3 已修复的三个动力学/观测问题

| 修改 | 具体做法及证据 | 仍有限制 |
| --- | --- | --- |
| q / -q输入跳变 | reset匹配Isaac ARM_HOME半球；逐次Tool pose与上次四元数点积非负。旧第2步存在符号翻转，网络归一化后会裁剪到±5并改变动作；新快速轨迹符号跳变均0 | 这是表示连续性，不是修DH或改变物理姿态；不能删四元数4维后继续用旧权重 |
| Tool / peg质量 | 独立固定Tool刚体10 g；peg独立无自由度子刚体19 g，实际进入质量矩阵，peg自身重力抵消 | peg仍刚性固定，不是Isaac独立被夹爪接触夹持的资产 |
| 机器人0.01 I | 10个机器人刚体构造时各主惯性加0.01 kg·m²；mj_setConst重建；reset不累加。不改mass/COM/主轴/armature，peg/孔除外 | 根据本地Factory源码实现；未直接重新核实云端基类 |

质量补齐后的标称末径向误差25.54 mm，加0.01 I后降为0.31 mm，但四个旧孔几何episode仍全未成功，tip_z约25 mm。**不能把惯性改善等同于接触对齐或迁移成功。**

### 2.4 孔/针实际碰撞几何与最新结果

按正式params中的官方Isaac5.1 URL下载factory_hole_8mm.usd、factory_peg_8mm.usd，保留在Isaac根下peg_insert_reproduction/factory_collision_sources/。**文件名/任务8.1 mm元数据不是实际碰撞mesh尺寸。**

| 几何 | 已移除的旧MuJoCo近似 | 当前官方USD源表面 |
| --- | --- | --- |
| 孔身 | 8.1 mm方孔 | 9.0 mm圆形孔身、25 mm深 |
| 孔口 | 直角，无倒角 | 11.0 mm入口，z=24–25 mm为1 mm倒角 |
| 孔底/轮廓 | 四块40 mm外宽方壁，无底板 | 保留z=-3–0 mm底板/法兰、实际外轮廓及安装孔 |
| 插针 | 7.986 mm直径、50 mm无倒角圆柱 | 直径/长度不变，两端各0.5 mm倒角、端面直径6.986 mm |

孔和针USD标为SDF。MuJoCo针使用源凸mesh；孔以源顶面/倒角/底板三角形挤出为**1166凸片**，避免非凸整孔取凸包封洞；总体积1.60589011547e-5 m³与闭合源mesh一致。原孔visual mesh不参与碰撞，默认缩放1；reset对全部凸片设置摩擦。体积和插入探针检查是验证证据，不是整个SDF接触响应等价证明。

针仍19 g，倒角mesh重新推导主惯性约[4.01523e-6,4.01523e-6,1.51114e-7] kg·m²，比旧圆柱约小0.5%；不能声称本次惯性数值完全未变。机器人质量/惯性、PD/摩擦未额外调参。

最新**11项测试通过**：包含中心和偏心0.3 mm可进入孔身、0.7 mm偏心碰壁、倒角入口容许1 mm偏心但窄孔身不容许、低于孔底碰底板；还覆盖质量/重力、0.01 I实际质量矩阵和reset不累加、四元数连续性等。

最新快速测试和对应视频，每条deterministic、完整20秒/300步：

| 模式 / seed | 最终径向误差mm | 最终tip_z mm | 首次成功 | episode末成功 |
| --- | ---: | ---: | --- | --- |
| 标称1000 | 0.713 | 8.333 | 无 | 否 |
| 随机化1001 | 0.534 | 0.965 | 第77步 / 5.133秒 | 是 |
| 随机化1002 | 0.588 | 10.514 | 无 | 否 |

三条四元数符号跳变均0，最大实际命令力矩约6.48/7.89/7.67 Nm。旧孔修正前这三条tip_z约24.93/25.07/24.96 mm；现均进入孔中，但两条孔内卡住，根因尚未定位。

当前结果和视频入口：

- [碰撞对齐报告](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/eval_results/mujoco_ep700/COLLISION_ALIGNMENT.md)
- [最新快速测试JSON](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/eval_results/mujoco_ep700/quick_collision_alignment_20260930.json)
- [最新视频索引/校验记录](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/mujoco_ep700_collision_aligned/README.md)
- [标称1000视频](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/mujoco_ep700_collision_aligned/nominal/seed1000.mp4)
- [随机化1001视频](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/mujoco_ep700_collision_aligned/randomized/seed1001.mp4)
- [随机化1002视频](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/videos/mujoco_ep700_collision_aligned/randomized/seed1002.mp4)

MP4实际解码确认960×720、15 fps、300帧/20秒，带孔口特写；首次成功步和末帧位置与快速测试一致到1e-6 mm。视频每帧对应同号控制步；JSON有raw/EMA action、tool/peg tip位置、速度、干摩擦力矩、actuator力矩、逐步success。**这些JSON还没有接触法向/wrench或完整目标位姿。**

## 3. 尚未完成 / 当前问题

1. **MuJoCo迁移尚未通过**：最新标称仍失败，随机化两条只一条成功；没有修正后独立批量验证。两条失败由“孔口挡住”变为“孔内卡住”，尚未区分倾斜卡楔、刚性夹持、摩擦或求解器响应。
2. **夹持和手指驱动不同**：Isaac是独立peg，禁用peg重力，由双手指接触夹持；MuJoCo是无自由度刚性peg、单finger位置驱动+两指等位移equality，无同样双驱动/0.1 m/s指速度约束。
3. **接触求解不同**：MuJoCo凸片可能有接缝/CCD容差，PhysX SDF有离散误差；Isaac contact_offset=5 mm/rest_offset=0、位置/速度迭代192/1，与MuJoCo margin0、solref/solimp、Newton/implicitfast/noslip不是一一对应。没有逐接触法向/力矩对照；不要直接把5 mm作为活跃margin加厚碰撞体。
4. **未核实的云端依赖**：官方下载的当前文件不证明云端缓存字节相同；0.01 I继承逻辑仅本地基类证据。原本地和云端机器人USD字节hash差异的完整composition原因未查清；参数/FK已比较，不能盲目覆盖原训练USD。
5. **压力测试不是训练同分布**：MuJoCo额外孔XY±1 mm、joint σ=.002 rad、观测位置σ=.25 mm/速度σ=.002、接触摩擦U[.7,1.3]和力矩缩放U[.9,1.1]；云端自定义reset固定ARM_HOME/布局、观测孔噪声置零、接触摩擦.75。标称把关节干摩擦取中值，也不是Isaac某一条实测摩擦样本；相同seed的Torch/NumPy不生成相同样本。
6. **成功口径未统一**：MuJoCo evaluator遇成功即break，统计期间曾成功；record继续20秒，能看末帧success；正式Isaac按episode末infos['successes']。MuJoCo tip成功在世界系，Isaac按独立peg的孔局部系；倾斜/滑移时区别更大。
7. **日志仍缺诊断量**：完整控制目标位姿、peg轴/孔轴夹角、孔局部位姿、接触geom对/点/法向/穿透/力、控制wrench、自由peg相对Tool位姿（当前刚性模型不存在滑移）未同步采集。不能仅凭视频认定“摩擦没有”或“Z力不够”。
8. **用户要求的部分最终图未补齐**：当前有610–700每checkpoint10episode及8面板诊断图；未见ep700另跑50–100episode的Final Return Distribution及独立箱线/小提琴图，也未见该轮独立Success Rate图。当前MuJoCo三个视频有逐步数据，尚未生成各episode18张独立action/pose图。不要宣称所有后续绘图要求都完成；需按需要补齐，不自动扩成大评估。
9. **遗留训练代码风险**：旧action_penalty_ee使用全局torch.norm而非dim=-1；当前scale=0所以未影响该项，但将来启用前必须修。当前无新训练计划，也没有改奖励、观测维度或成功终止逻辑。
10. **运行和资料管理**：两个工作区存在大量修改/未跟踪工件及历史清理删除；未统一提交。不要reset/clean/stage全部。云备份README、早期REPORT/ALIGNMENT_AUDIT含历史叙述，必须看时间/阶段说明；本HANDOFF作为当前入口。

## 4. 关键决策与理由

| 决策 | 为什么这样选 / 边界 |
| --- | --- |
| 当前使用ep700 final，不另训策略 | 先修跨引擎接口和物理差异；迁移失败不能直接当成源策略不足 |
| 原始rebot.xml不改，用专用eval MJCF | 保持机器人/真机参数基准，避免为成功篡改基准；运行时Factory惯性增量单独表达 |
| 保留Actor19维和reset半球连续性 | 固定权重依赖四元数训练分布，q/-q物理等价但网络不等价 |
| 0.01 I加在机器人刚体，不加armature/peg/孔 | 匹配本地Factory处理路径，避免误改质量或重复累加 |
| 采用实际USD源几何，不任意放大孔 | 8.1 mm任务元数据不是9 mm实际mesh；修倒角/孔底来自源资产证据 |
| 孔拆凸片，保留原mesh仅作visual | MuJoCo普通mesh碰撞用凸形；整孔凸包会封洞。仍明确非PhysX SDF同求解器 |
| 固定PD/摩擦不继续盲调Z | 几何修正已改变结果；需要定位孔内卡住，一次只改一个变量 |
| 不凭“三条里一条成功”报总体成功率 | 模式混合且样本小；先报告逐条结果，再做同协议的独立验证 |
| 最近视频保持完整20秒 | 观察曾成功之后是否保持，避免把成功即终止的统计与末帧成功混淆 |
| 同时保留raw action、EMA和实际响应 | action是目标增量，不是实际位移/速度；不能单凭动作符号解释画面 |
| 云端工件先校验后关机/清理 | 防数据盘释放丢失；201文件本地备份不意味着所有610–690权重/基类都在本地 |
| 旧文档归档，主文档只留现状 | 防止“ep600训练中 / sim-to-sim搁置 / 8.1mm实孔”等旧结论重复引导错误操作 |

## 5. 改过的重要文件（当前有效版本）

MuJoCo根目录下：

| 文件 | 当前职责 / 重要修改 |
| --- | --- |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/environment.py | PD/重力/限幅、LSTM观测接口、q符号连续性、0.01 I、全孔凸片摩擦、完整episode step |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/model_builder.py | 专用MJCF参数化，加载factory_collision.xml，按实际孔/针尺寸缩放；不再构造旧四方壁 |
| src/rebot_sim2sim_eval/mjcf/rebot_peg_insert_eval.xml | 真实限位、50 Nm、Tool/19g peg固定子刚体、孔visual和针mesh；不是原始rebot.xml |
| src/rebot_sim2sim_eval/mjcf/factory_collision.xml | 自动导出的针源mesh、孔visual及1166凸碰撞片；不要手工改大量vertex去调孔径 |
| src/rebot_sim2sim_eval/mjcf/export_factory_collision.py | USD → 凸片资产的离线导出，校验源/分解体积；需pxr，仅离线导出时使用 |
| src/rebot_sim2sim_eval/config/rebot_peg_insert_nominal.yaml | 无额外扰动基线，当前实际孔径9 mm/20秒/重力补偿/50 Nm |
| src/rebot_sim2sim_eval/config/rebot_peg_insert.yaml | 有额外扰动的压力测试，不可叫“训练完全一致配置” |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/config.py | 类型配置及尺寸检查，孔径默认9 mm |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/gravity.py | 与训练同辨识重力补偿，DH偏置仅在这里的映射链使用 |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/policy.py | 现有RL-Games actor适配/归一化/LSTM状态；已核对，不要无依据重写 |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/cli.py、evaluator.py | 模型/网格路径和独立评估入口；evaluator成功即终止的口径仍未统一 |
| src/rebot_sim2sim_eval/rebot_sim2sim_eval/record.py | 完整20秒视频、孔口特写、逐步JSON及截图，成功不提前退出 |
| src/rebot_sim2sim_eval/test/test_environment.py | reset/限幅、质量/重力、惯性实际质量矩阵和不累加、四元数回归 |
| src/rebot_sim2sim_eval/test/test_factory_collision.py | 编译后自由针探测：开孔、偏心、倒角、底板；防止凸包封洞或缩孔回归 |
| src/rebot_sim2sim_eval/test/test_model_builder.py、test_gravity.py、README.md | 模型/重力测试及当前运行说明；整包目前11项测试 |

Isaac根目录下：

| 文件/目录 | 当前用途 |
| --- | --- |
| HANDOFF.md | 本次重整的唯一当前交接入口 |
| peg_insert_reproduction/rebot_task/rebot_factory_env.py、rebot_gravity.py | 源训练任务reset/摩擦/PD/辨识重力；本轮未继续改训练逻辑 |
| peg_insert_reproduction/scripts/train_rebot.py | 训练入口；真正正式运行参数以云端备份params/日志为准，不能靠本地默认值推断 |
| peg_insert_reproduction/scripts/evaluate_rl_games.py | Isaac deterministic评估，携带训练覆盖 |
| peg_insert_reproduction/scripts/record_successful_episode.py、record_eval_batch.sh | Isaac录制/action轨迹，注意终止reset伪影 |
| peg_insert_reproduction/scripts/plot_policy_eval.py | 18张单维静态PNG，连续RPY和末帧reset剔除 |
| peg_insert_reproduction/scripts/plot_ppo_diagnostics.py、read_tb_events.py | PPO图及真实diagnostics；纯标准库读取TensorBoard |
| peg_insert_reproduction/factory_collision_sources/ | 新下载的官方孔/针USD，非“云端缓存已验真” |
| peg_insert_reproduction/eval_results/mujoco_ep700/ | 分阶段REPORT、对齐审计和quick_* JSON；必须区分历史模型 |
| peg_insert_reproduction/videos/mujoco_ep700_collision_aligned/ | 唯一当前模型三个视频，JSON/截图/README/哈希 |
| peg_insert_reproduction/cloud_sync/ep700_20260930/ | 201文件不可变云快照；不要覆盖成当前工作目录版本 |

关键哈希：

~~~text
原始rebot.xml:
02e923dc78ea15851070c2fed3a919e978a61d2ec96eee235c52b1f3bae95bba
当前environment.py:
0361fed68b7c1270fb9a0d1817bcc201d921af55ad66e018bac463d3aebb23b2
当前factory_collision.xml:
178b59a6dd37817d0ed5d9ac918ce790df18c28ce611a57a1b3c94421df31056
官方下载factory_hole_8mm.usd:
4bad48cde5a2e523454f9ed584023fae53d619a5ffb3d6ab08f29a6240014c28
官方下载factory_peg_8mm.usd:
b5040c8c639f3dc0731adfb6022c0d63383b7550354e413dc24e7417b600869d
~~~

## 6. 接下来建议按这个顺序做（尚未执行）

1. **先诊断当前卡住，不继续放大孔或盲加Kp/Z。** 以标称1000、失败1002和成功1001为对照，补逐步孔局部tip/轴姿态、倾角、控制目标、contact geom对/法向/穿透/接触力与力矩；在接触进入孔内和最终稳态比较。复用现有记录器，先不改物理参数。
2. **验证剩余夹持/接触差异。** 优先判定刚性peg是否造成过约束和倾斜卡楔；若用户要求修，再考虑独立free peg+接触夹持/受约束连接、双指驱动。不能凭猜测直接换模型后混报旧结果。
3. **有云访问时核实源基准。** 只读比对实际缓存孔/针USD哈希及composed几何、Factory基类和运行时惯性；不为这一步自动重开实例或覆盖训练资产。本地可以继续，云端限制不是停止所有工作的理由。
4. **每项改变后先11项测试、再三条完整20秒回归。** 固定checkpoint、config、seed与输入噪声样本；记录新模型哈希、ever/final success和first_success，产物放新目录，避免覆盖历史。需要估计成功率时另做同模式/同协议批量验证，不能重复无随机标称当独立样本。
5. **之后再补图或讨论训练。** 当前视频数据可画每seed18张独立PNG；PPO最终distribution/success图按用户需要补齐。若要改观测维度、奖励或重训，先取得明确请求，不能给已有19维权重直接扩维输入。
6. 凭据维护由用户另行确认：曾在对话出现密码，建议更换并用SSH密钥；不写入文件、history或Git。清理仅针对确定可恢复且已授权的目标，不自动继续清理必要工件。

最小自检（只跑本地测试）：

~~~bash
cd /home/xiatenghui/.rebot/rebot_blue
env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src/rebot_sim2sim_eval \
  .venv/sim2sim/bin/python -m pytest -q src/rebot_sim2sim_eval/test
~~~

云端备份复核（**必须在快照目录内**运行；清单相对路径不在工作区根）：

~~~bash
cd /home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/cloud_sync/ep700_20260930
sha256sum --check --quiet peg_insert_reproduction/cloud_backup_ep700/SHA256SUMS
~~~

本地录制复现：从MuJoCo根设置PYTHONPATH=src/rebot_sim2sim_eval，用隔离Python执行python -m rebot_sim2sim_eval.record，传上文完整checkpoint、nominal config+seed1000；stress config+seeds1001/1002。输出到**新的**目录，设置MUJOCO_GL=egl、LP_NUM_THREADS=2、OMP_NUM_THREADS=1、MKL_NUM_THREADS=1。不要覆盖mujoco_ep700_collision_aligned原视频。CLI evaluator成功即终止，不能代替20秒record验证保持能力。

## 7. 踩过的坑：后面不要重复

### 7.1 仿真与策略接口

- **模型姿态正确不代表NN输入正确**：q/-q、最大分量分支切换都会改变原始4维和归一化；逐步连续并在每次reset恢复训练半球。180°附近不能只用w正负选符号。
- **不要重复加DH偏置**；仿真qpos已经在对应零位，偏置只用于重力公式。q符号翻转不是DH框架物理跳变。
- **geom写mass不保证参与惯性**：在Link_6有显式inertial时，旧19g geom没增加质量；检查编译后body_mass/body_inertia与关节空间质量矩阵，不只看XML字符串。
- **0.01 I不是0.01 kg、不是armature**；只加一次，机器人十刚体，peg/孔除外；改惯性后重建常数。
- **旧“8.1mm孔径/0.057mm间隙”是名义参数推断，不是当前实际mesh**；必须检查USD碰撞面、变换、倒角、底板、approximation。
- **凹孔不能整块convex hull**，会封孔；源表面体积一致仍不能证明SDF数值响应一致。不要用随意增大孔径代替真实对齐。
- **USD metersPerUnit元数据不能不看场景引用就二次缩放**；这里源点坐标0.05按任务米制使用，乘.01会把50mm针缩成.5mm。
- **MuJoCo不是“没有静摩擦/库伦摩擦”**：frictionloss已有非零干摩擦约束力矩；须对照静止/滑动行为，不能仅凭运动猜测。
- **50 Nm不是100 Nm**：motor ctrlrange才是实际控制限幅。3 rad/s numeric不会被MuJoCo自动执行；步后裁剪仍不是完全等价原生约束。
- **重力补偿要在reset也生效**；不以disable_gravity替代原训练控制。peg禁用重力不等于取消机器人重力。
- **同seed不等于同物理抽样**：Torch/NumPy RNG及额外随机化不同；pressure stress不是Isaac同分布，先分别报告模式。
- **raw action不是位移/速度，轴不是屏幕方向**：后面还有EMA、目标裁剪、PD、Jacobian、摩擦、接触。动作+Z和末端上移不能直接划等号。
- **各自最小radial与最小tip_z可能不在同一步**，不能拼成成功。必须在同一步满足阈值。
- **actor改维度需新权重/训练**，不允许删除四元数或增加接触量后继续装旧19维actor。
- **老视频和新模型不可混用**：mujoco_ep700_three是四元数/质量/惯性/碰撞修正前；mujoco_ep700_inertia001是惯性修正后、碰撞修正前；当前只看mujoco_ep700_collision_aligned。

### 7.2 训练、评估与绘图

- **恢复学习率的0938坑**：optimizer恢复后调度器last_lr未同步，原3.90e-6被抬高，epoch601 KL约13.51/clip接近1；该分支605停止并废弃，不能用于续训/评估。恢复optimizer后同时检查调度器和实际LR。
- **0946保存频率坑**：只每100epoch保存，无法评610/620/...；608停止并从ep600重启正式0955分支。开跑前检查save_frequency=10及diagnostics开启。
- **max_iterations是绝对epoch上限**；600→700设700，不设100；看checkpoint epoch/frame与TensorBoard首个info/epochs确认接续。
- **Factory.pth是训练best，不是final**；用元数据确认。训练reward高不保证独立成功率高，ep500 final85.45%反而优于best81.54%。
- **checkpoint不恢复环境Hydra覆盖**：当前三项覆盖必须齐；ep394默认[20,20,20]mm/Kpz100不是ep700[5,5,30]mm/Kpz400。
- **Actor Loss不是Evaluation Reward，也不要求单调下降**；看异常震荡/爆炸；Evaluation Return独立采集，不用Training Return代替。
- **info/e_clip是clip阈值，不是Clip Fraction**；当前真实diagnostics/clip_frac/0..3取均值，exp_var用真实diagnostics/exp_var。缺失指标明确写缺失，不造替代量。
- **成功期间ever和episode末final不同**；record要满20秒，批量评估必须声明协议；不能把10/10小样本当高精度泛化验证。
- **timeout auto-reset伪影**：Isaac step后可能已回初始pose/清零action；raw与本步EMA在step前记录，非终止步核对；末帧reset位置不能画成真实50mm跳变。剔除条件应同时看跳变和回初始，不只看接近初始。
- **命令/响应差一步**：ema[k]对应pose[k]-pose[k-1]（首步用初始pose），不是pose[k+1]-pose[k]；振荡轴逐步符号相关性低不等于方向映射反了。
- **18张action/pose图用单维静态PNG**；不回到交互图/六维叠图。用户指定代表seed1000/1001/1002；新训练每10epoch独立10episode mean±std。历史1024 held-out及50–100最终distribution是另外协议，不默认再发起重评估。
- **[2,2,5]mm+smooth=.01失败（约1.4–1.6%）；[2,2,20]mm无smooth也失败（约6.7–9.5%）**，不要不说明就重复。保留EMA.2；当前[5,5,30]/Kpz400/smooth0。旧ep500横向失败下探已足，不自动继续增强Z。
- **action_penalty_ee的全局norm问题**：scale当前0；启用之前必须dim=-1，否则随env数量改变惩罚。

### 7.3 云端运行与数据安全

- **进程消失不等于完成，stdout会缓冲**：检查最终checkpoint、TensorBoard info/epochs，不看.out最后几行猜进度；旧398中断无final的原因仍未查清。
- **云端长任务必须脱离SSH**：setsid nohup，stdin=/dev/null并重定向输出；另会话查pgrep/ps SID。SSH wrapper没返回不证明训练未启动，不要重复发起。
- **同一GPU不要同时跑Isaac训练/评估/录制/转换**：先pgrep/nvidia-smi；曾出现Fabric/KVDB锁警告。这里三个CPU MuJoCo渲染会话并行不代表允许Isaac并发。
- **LD_LIBRARY_PATH不可遗漏**：历史云端held-out需要/isaac-sim/exts/omni.isaac.ml_archive/pip_prebundle/torch/lib。Kit/系统Python依赖冲突时用纯标准库read_tb_events.py，不污染容器；TFRecord头含独立4字节CRC。
- **app.close挂住时先验完整工件，再只结束对应脚本**；不kill所有Python。
- **USD override/sublayer会遮旧属性**：看composed stage；改URDF不代表改USD；上传前备份、核参，不能为hash不同盲覆盖。
- **“已回传”要逐文件验真**：旧held-out JSON曾误记已下载；现201备份清单在快照内部，不在Isaac工作区根。云端无rsync时可tar over SSH后hash核对。
- **镜像不保存数据盘**：关/释放前确认所需权重/参数/events/代码/结果本地齐全；只备5权重并不意味着全部checkpoint齐全。
- **密码/token不落盘、不进history/Git**；不要从对话复制凭据到脚本。不要git clean、reset --hard或全量stage脏工作区。

## 8. 历史追溯（不是当前任务）

整理前739行完整保留在[历史HANDOFF快照](/home/xiatenghui/.rebot/issac-sim/peg_insert_reproduction/notes/HANDOFF_HISTORY_before_consolidation_20260930.md)，其中“正在训练/尚未做sim-to-sim/8.1mm实孔”等过期叙述不得作为当前操作指令。

阶段对应产物（Isaac根peg_insert_reproduction/eval_results/mujoco_ep700/）：

| 阶段 | 报告/数据 | 正确解释 |
| --- | --- | --- |
| 首轮未修正 | REPORT.md、summary.json、nominal/stress_seed*.json | 标称0/30、压力0/30，旧模型历史结果，不是当前成功率 |
| 对齐诊断 | ALIGNMENT_AUDIT.md | 运动学/DH/四元数/物理差异证据，含显式历史状态说明 |
| 四元数修正 | QUATERNION_FIX_QUICK_TEST.md、quick_quaternion_fix_20260930.json | 0符号跳变；仍失败，不证实唯一原因 |
| 质量补齐 | MASS_ALIGNMENT_QUICK_TEST.md、quick_mass_alignment_20260930.json | 质量参与动力学；旧孔仍全失败 |
| 0.01 I | INERTIA_ALIGNMENT_QUICK_TEST.md、quick_inertia_alignment_20260930.json | 横向发散减小；旧孔tip停约25mm |
| 实际碰撞几何 | COLLISION_ALIGNMENT.md、quick_collision_alignment_20260930.json | 当前三条，一成功两孔内卡住；云端缓存/求解器/夹持仍有限制 |

历史云根：/root/gpufree-data/isaac-sim，正式训练目录为其IsaacLab/logs/rl_games/Factory/正式实验名/。**没有当前正在训练的云目录。** 旧checkpoint（零摩擦/关闭重力/20Nm/旧限位）只供历史定位，不与当前策略直接比较。
