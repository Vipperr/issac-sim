# Factory 单环境冒烟测试（2026-08-24）

使用 `isaaclab232` 与官方 `Isaac-Factory-PegInsert-Direct-v0`，分别运行了零动作和随机动作测试。为防止无界面 agent 持续运行，两次均在 120 秒后以 `SIGINT` 正常终止观察。

两次运行都确认：

- Isaac Sim 5.1 识别 RTX 4060 Laptop GPU（8 GB）并创建 GPU PhysX context（device 0）。
- 官方云端 Factory 资产可读取：`franka_mimic.usd`、`factory_hole_8mm.usd`、`factory_peg_8mm.usd`。
- SDF cooking 完成，仿真进入 `onResume`。
- 日志中没有 Python exception、USD 打开失败或 CUDA/PhysX 初始化失败。

`Failed to clone in Fabric` 出现在单环境启动日志中，但不阻止环境进入仿真；后续扩展到多环境时需再次观察该条目。
