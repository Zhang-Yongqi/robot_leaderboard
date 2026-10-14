# RP1 与 G1 共同动作评测说明

本评测比较两套固定发布学生策略的离线仿真表现。公开指标为全程身体与手腕的位置、姿态四项误差；motion 跟踪任务完成率正在离线核验。Common40 覆盖 **40个配对动作（N=40）**，Extreme5 独立报告 **5个配对动作（N=5）** 的空翻／转体测试。科学来源、原始轨迹与历史实验保留在来源项目，当前公开投影按回合身份关联冻结结果。 每条结果还保留已记录的科学协议、执行协议、配置和来源摘要；科学评分协议与执行文件版本分别记录，原未记录的字段为 null。

## 评测条件

### 动作覆盖与配对

配对按 `phase / dataset / condition / mode / motion_id / seed` 的精确交集建立，并核验相同协议与运行口径。`condition` 使用有效条件；修正时钟后的 `aligned_nominal` 归入 `nominal`，使用冻结身份清单选定的记录。机器人专属配置和 checkpoint 各自保留。入选依据为身份交集，不根据任务结局筛选；可配对的删失或缺失成绩保留 null 与原因。

| 数据组 | 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | --- | ---: | ---: | ---: |
| Common40 主组 | nominal / native_position | 40 | 40 | 80 |
| Extreme5 主组 | nominal / native_position | 5 | 5 | 10 |
| Common40 部署敏感性 | explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| Common40 名义重复 | repeat_nominal / native_position | 5 | 15 | 30 |
| Common40 初态扰动 | robust_initial_velocity / native_position | 5 | 25 | 50 |

共 **45 个动作、90 个条件/seed 配对、180 个机器人回合和 5 个评测组**。公开 `data.json` 的 190 条记录包含 180 条回合记录与 10 条机器人聚合记录，各组分别统计。`episodes.csv` 保留 180 条回合，`comparisons.csv` 保留 10 条机器人聚合记录；硬件表的 29 个槽位属于模型参数记录。

两个主组使用 seed=0。双方配对的时钟、条件与扰动文件一致；Extreme5 的五个动作在核验前预先指定。原始轨迹完整保留，四项误差覆盖全部共同评分窗口。

### 策略与运行配置

RP1 为 28 DoF 原版 robot-matched ROA student，来源 [Roboparty/MimicLite](https://github.com/Roboparty/MimicLite#released-checkpoints)；G1 为 29 DoF MimicLite v1.1 发布策略。发布方均声明 8×8192 环境，RP1 静态配置与 checkpoint 记每 rank 8192。两者的训练数据、retarget 和机器人控制参数各自保留。Phase B 同配置正式重训尚未开始。

运行环境为原生 MuJoCo + CPU ONNX，policy 50 Hz / physics 200 Hz。共同 solver 下使用各机器人的原生 PD、effort、armature 与几何参数，连续记录完整回合，评测过程不触发状态重置。

Common40 nominal 与 Extreme5 主组使用参考姿态和零初速；本次主评测未启用观测噪声、域随机化、外力 push 或随机动作延迟。`robust_initial_velocity` 实际扰动自由根节点的 vx、vy 与本地 yaw 角速度，标准差分别为 **0.05 m/s、0.05 m/s、0.05 rad/s**，属于根速度扰动。

### 全程误差定义

| 字段 | 口径与单位 |
| --- | --- |
| full_body_pos_mm / full_body_ori_rad | 全程 Common14 身体位置 / 姿态误差，mm / rad；沿用 ankle-roll 语义映射及 RP1 pelvis/torso 映射。 |
| full_wrist_pos_mm / full_wrist_ori_rad | 全程手腕位置 / 姿态误差，mm / rad。 |

窗口为 `full_replay_50hz_first_substep`：每个既有回合的全部 **50 Hz 首次物理子步**误差样本，`motion_t=1..N_common−1`，覆盖完整保存轨迹。这里的 `N_common` 为共同参考帧数，与统计单位 N=40 / N=5 分开使用；frame0 是初始化，200 Hz 末端 hold 不新增评分。每回合样本等权，同一配对两侧的评分帧数与参考窗口一致。

全程位置字段已经是 mm，可直接显示；姿态为 rad。任务完成率核验沿用这批既有回合，四项误差的评分窗口与数值保持冻结来源。

### Motion 跟踪任务完成率定义

因摔倒而无法继续后续动作跟踪，记为未完成；未发生这类不可继续中断，记为完成。中途摔倒后恢复并跟踪到动作末尾，仍记为完成。判定需对照参考动作，识别参考翻滚、倒地起身与允许的低姿态动作，并核验摔倒后是否恢复跟踪。仿真记录运行至末端只表示记录长度，低高度也不能单独作为摔倒判据。

恢复后跟踪至末尾计为完成的规则已确定；正式回合标签、判定证据及多 seed 动作统计仍待离线核验与冻结，完成率保持 `null/pending`，**当前不展示百分比**。各组的统计单位、有效分母与多 seed 汇总随冻结结果一并记录。已冻结的四项全程误差可先独立正式发布，完成率在正式统计冻结后更新。

### 硬件模型与关节参数

硬件附件中的模型和原生位置控制与共同动作比较一致。模型质量是 body 惯性质量之和：RP1 **40.726 kg**、G1 **33.741 kg**；驱动轴分别为 **28 / 29**。关节表共 **29 个解剖槽位、28 对同名关节**；G1 的 `waist_pitch_joint` 在 RP1 列为 n/a，表示该驱动关节不存在。

| 参数层级 | 字段含义与单位 |
| --- | --- |
| 有效关节约束 | MuJoCo 激活的角度约束，rad / degree；ROM=upper−lower。局部轴按右手规则定义，安装 frame、零位及串联顺序各自保留，有符号端点按各坐标解释。 |
| 执行器 force caps | 发布配置与有效模型的力矩限制，N·m；PD 计算后应用的 force range 在 gear=1 时对应关节力矩。厂家额定／峰值扭矩、实体止挡和热工况另列为未知。 |
| 声明速度 | rad/s，另列 degree/s；属于资产 metadata，当前原生运行器未施加速度包络限幅。 |
| PD 与动作目标 | kp 为 N·m/rad，kd 为 N·m·s/rad；目标角为 q_default + action × scale。scale 单位为 rad/action unit，kd 与被动阻尼分别记录。 |
| 训练惩罚软限 | RP1 从保存配置的 factor=0.9 在硬 range 中点两侧推导，单位 rad，供奖励惩罚使用；训练 tensor 尚未直接核验。G1 原权重级历史软限保留 unknown。 |

完整逐槽位轴、角限、默认目标、PD、惯量与接触参数见 [hardware.json](hardware.json) 和 [hardware.csv](hardware.csv)。

## 全程误差结果

### 全程主指标：Common40（N=40）

| 指标 | RP1 | G1 | RP1−G1 | 95% 配对区间 | 单位 |
| --- | ---: | ---: | ---: | --- | --- |
| 身体位置误差 | 121.598 | 156.490 | -34.891 | [-76.304, -3.484] | mm |
| 身体姿态误差 | 0.4041 | 0.5477 | -0.1435 | [-0.2675, -0.0391] | rad |
| 手腕位置误差 | 128.573 | 166.508 | -37.935 | [-88.584, -0.302] | mm |
| 手腕姿态误差 | 0.4276 | 0.5680 | -0.1404 | [-0.2701, -0.0245] | rad |

四项全程误差均值均为 RP1 较低，RP1−G1 的配对差值区间均位于零以下。

### 全程主指标：Extreme5（N=5）

| 指标 | RP1 | G1 | RP1−G1 | 95% 配对区间 | 单位 |
| --- | ---: | ---: | ---: | --- | --- |
| 身体位置误差 | 318.475 | 307.636 | 10.839 | [-5.097, 32.489] | mm |
| 身体姿态误差 | 0.9061 | 0.9713 | -0.0652 | [-0.1968, 0.1038] | rad |
| 手腕位置误差 | 322.826 | 307.383 | 15.442 | [-37.720, 68.052] | mm |
| 手腕姿态误差 | 0.9850 | 1.1266 | -0.1416 | [-0.3103, -0.0098] | rad |

身体与手腕位置误差均值为 G1 较低，姿态误差均值为 RP1 较低；仅手腕姿态差值区间位于零以下，其余三项跨零。两个动作组独立报告，不合并为 N=45 的主估计。完整精度、每机器人均值区间及逐回合记录见 [data.json](data.json)、[episodes.csv](episodes.csv) 和 [comparisons.csv](comparisons.csv)。

## 结果分析

聚合先对完整相同 seed 集求每动作均值，再按动作等权计算组均值。四项全程误差的 95% 区间采用 10,000 次 paired motion percentile bootstrap，PCG64 随机种子 20261013、线性分位数，每组和指标重置；两侧共享重采样索引。每机器人均值区间与 RP1−G1 配对差值区间分别保存。组内名次依据配对身份、协议与有效指标分母齐全一致计算；任务结局不用于排除全程误差记录。

Common40 主组以 **40 对动作**、Extreme5 以 **5 对动作**为重采样单位。名义重复、初态扰动与显式部署敏感性三组均为 **N=5**，各自四项全程配对区间均跨零；seed 重复不扩大独立动作分母。

实质限制集中如下：

- 结果范围为离线仿真，实机表现待验证。区间描述固定 checkpoint 与当前动作的条件分布，训练 seed 总体和本体形态效应未在本设计中单独分离。四项描述性 CI 未作多重比较校正。
- 全程均值涵盖完整保存轨迹，各阶段误差及持续时长共同影响数值；误差与任务完成率分别报告。
- 30 条名义重复逐值、逐字节一致，独立动作数和训练 seed 数保持原统计单位。
- 公开 retarget 按源动作名和完整时长匹配，原始 BVH 输入哈希血缘尚未完全闭合。
- 发布方尚未明确独立 RP1 v1.1 标签；独立完整八卡训练 run 日志、GPU 型号和阶段执行证据不足。RP1 发布包 seed=42，G1 v1.1 配方 seed=0；本次 G1 权重的历史训练 seed 尚缺直接证据。共同声明的训练规模之外，训练数据、retarget 和控制参数仍有差异。
- Extreme5 区间来自本组 5 对动作；历史人类源哈希与完整训练暴露信息暂无记录，已核验的对应关系包括共同动作身份、时序和根部运动。
- 硬件表按同名解剖关节映射；局部轴、安装零位及有符号角端点需要坐标转换后比较。单关节 ROM 描述该轴跨度，全身可达性还涉及串联几何与碰撞条件。固定策略、训练数据、retarget、本体与控制参数共同影响结果，当前设计未单独识别硬件因素的因果效应。

## 数据、报告与资料

当前公开投影：[配对结果 JSON](data.json)、[180 回合 CSV](episodes.csv)、[10 条机器人聚合记录 CSV](comparisons.csv)。模型参数：[JSON](hardware.json) / [CSV](hardware.csv)。科学来源与历史原始实验在来源项目和 Git 历史中保留。

统一报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。原链接正在按“全程误差与跟踪任务完成率”的新口径更新；完成率的正式回合标签、判定证据和多 seed 动作统计待冻结。相关飞书资料需要组织访问权限。

既有同步视频的两侧来源回合均对应 Common40 共有数据。新公开视频为 **0/40**，索引见 [media.json](media.json)；Extreme5 的 5 个视频尚未制作。

## 附录：冻结来源与 SHA256

| 冻结来源 | SHA256 |
| --- | --- |
| 全程科学输入 public_fullwindow.json | `119d981f07983b060b038e860ac0da9b2d5c10c166fc637b83d179cbf6bda5dd` |
| hardware.json | `5815d8d7e1a28305124849990dc682c85f6e6eb49b7bc78a91ae9adfa270a6af` |
| hardware.csv | `78972776c7640ec62e03bffda14caf0fb530a170ca3751109e66a79ac57614de` |

全程科学输入包含 180 条既有回合的 720 个四项误差值与五组冻结配对统计；当前网站只投影公开字段。公开 `data.json`、`episodes.csv`、`comparisons.csv` 的自身摘要、文件大小与生成时间见 [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json)。
