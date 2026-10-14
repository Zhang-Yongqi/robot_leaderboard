# RP1 与 G1 共同动作评测说明

本评测比较两套固定发布学生策略的离线仿真表现，以全程身体与手腕的位置、姿态误差为四项主指标。Common40 覆盖 **40个配对动作（N=40）**，Extreme5 独立报告 **5个配对动作（N=5）** 的空翻／转体测试。原评分科学版本为 `round2-phaseA-036559d03c4a`，冻结比较生成于 `2026-10-13T09:23:01.848935+00:00`；其 `data.json` 字节与全部原统计保持不变。全程附件为相同保存轨迹增加误差列，硬件板块描述同一冻结仿真资产与控制设置。历史原始实验记录保留在来源项目。

## 评测条件

### 动作覆盖与配对

配对按 `phase / dataset / condition / mode / motion_id / seed` 的精确交集建立，并核验相同协议与运行口径。`condition` 为来源适配器的有效条件；修正时钟后的 `aligned_nominal` 归入 `nominal`，使用冻结清单选定的替代记录。机器人专属配置和 checkpoint 各自保留。

Common40 的 170 条机器人回合逐条对应共同动作报告的冻结 run ID，双方时钟、条件及扰动文件一致。全局协议 SHA 用于绑定冻结版本；逐场景配对由这些回合身份与条件记录支持。入选依据为身份交集，包含成功及阈值失败记录，`Progress`、`verified` 和 `strict_pair` 均不作为入选条件。

| 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | ---: | ---: | ---: |
| nominal / native_position | 40 | 40 | 80 |
| explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| repeat_nominal / native_position | 5 | 15 | 30 |
| robust_initial_velocity / native_position | 5 | 25 | 50 |

以上 Common40 四组共 85 个条件/seed 配对、170 条机器人回合及 8 条聚合记录，即 178 个展示行；动作去重后为 40 个。各组分别报告，聚合值只在原动作/seed 群体完整保留时沿用冻结版本。可配对的删失或缺失成绩保留 `null` 与原因。

Extreme5 的 5 个预先指定动作均采用 nominal / native_position、seed=0，构成 5 对及 10 个机器人回合，另有 2 条聚合记录。原评分中的身体与手腕误差取各侧首次失败前；root endpoint 取共同源窗内完整回放的最后有效同步策略采样帧。原始 50 Hz 数组及导数保留，初态使用原生参考姿态与零速度，仅初始 XY/yaw 对齐；自然失败后的完整回放保留。

网页载入 Common40 与 Extreme5 后，评测记录合计 **45 个动作、90 个条件/seed 配对、180 个机器人回合、10 条聚合记录、190 个展示行和 5 个评测组**。全程四项与辅助评分共用这些回合身份，各组分别统计；硬件表的 29 个槽位属于模型参数记录。

### 策略与运行配置

RP1 为 28 DoF 原版 robot-matched ROA student，来源 [Roboparty/MimicLite](https://github.com/Roboparty/MimicLite#released-checkpoints)；G1 为 29 DoF MimicLite v1.1 发布策略。发布方均声明 8×8192 环境，RP1 静态配置与 checkpoint 记每 rank 8192。两者的训练数据、retarget 和机器人控制参数各自保留。Phase B 同配置正式重训尚未开始。

运行环境为原生 MuJoCo + CPU ONNX，policy 50 Hz / physics 200 Hz。共同 solver 下使用各机器人的原生 PD、effort、armature 与几何参数。首次单帧高度误差严格 >0.3 m 或重力 Z 差严格 >0.8 时记失败；完整原始 rollout 保留，运行中无 recover/rejoin/reset。

Common40 nominal 与 Extreme5 主组使用参考姿态和零初速；本次主评测未启用观测噪声、域随机化、外力 push 或随机动作延迟。`robust_initial_velocity` 实际扰动自由根节点的 vx、vy 与本地 yaw 角速度，标准差分别为 **0.05 m/s、0.05 m/s、0.05 rad/s**，属于根速度扰动。

### 全程主指标

| 字段 | 口径与单位 |
| --- | --- |
| full_body_pos_mm / full_body_ori_rad | 全程 Common14 身体位置 / 姿态误差，mm / rad；沿用 ankle-roll 语义映射及 RP1 pelvis/torso 映射。 |
| full_wrist_pos_mm / full_wrist_ori_rad | 全程手腕位置 / 姿态误差，mm / rad。 |

窗口为 `full_replay_50hz_first_substep`：每个既有回合的全部 **50 Hz 首次物理子步**误差样本，`motion_t=1..N_common−1`，包含首次失败及其后全部样本。这里的 `N_common` 为共同参考帧数，与统计单位 N=40 / N=5 分开使用；frame0 是初始化，200 Hz 末端 hold 不新增评分。每回合样本等权，同一配对两侧的评分帧数与参考窗口一致。

全程位置字段已经是 mm，可直接显示；姿态为 rad。附件中旧 `local_body_tracking_error` / `wrist_tracking_error` 诊断原值为 m，转换为 mm 时乘 1000。

### 辅助指标：原评分与首次失败诊断

| 字段 | 口径与单位 |
| --- | --- |
| body_pos_mm / body_ori_rad | Common14 身体位置 / 姿态误差，首次失败阈值前的局部跟踪均值，mm / rad；使用 ankle-roll 语义映射及 RP1 pelvis/torso 映射。 |
| wrist_pos_mm / wrist_ori_rad | 首次失败阈值前的手腕位置 / 姿态误差，mm / rad。 |
| root_pos_m | Common40：初始 XY/yaw 对齐、Z 保留；原评分最后有效策略帧（motion_t<参考帧数−1）的 XYZ root endpoint 误差，m，保留失败后的回放窗口。 |
| episode_return | 无量纲归一化 tracking return，使用独立 torso anchor 与 reward 点集合，严格 prefailure 分子及参考帧数−1 分母。 |
| progress_pct | 首次阈值位置 0–100%；未触发时取参考末端。机器人差值单位为百分点（pp）；原始 progress 以 fraction 保存。 |
| gpu_train_hours | 完整训练 GPU·h 暂无记录，保留 null；CPU 推理耗时与训练成本分别记录。 |

Extreme5 的原 root 指标取共同源窗内完整回放的最后有效同步策略采样帧，初始 XY/yaw 对齐、Z 保留，单位为 m；原身体与手腕指标使用各侧首次失败前窗口。Progress 是首次阈值诊断，完整回放不将其改写为成功率。原 Return 与 root endpoint 数值保留；新增全程评分仅含四项身体／手腕误差。

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

## 评测结果

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

身体与手腕位置误差均值为 G1 较低，姿态误差均值为 RP1 较低；仅手腕姿态差值区间位于零以下，其余三项跨零。两个动作组独立报告，不合并为 N=45 的主估计。完整精度、每机器人均值区间及逐回合记录见 [fullwindow.json](fullwindow.json) 和 [fullwindow.csv](fullwindow.csv)。

### 辅助：Common40 原评分与首次失败诊断

原主组 Progress 为 RP1 **79.735692%**、G1 **77.268977%**；RP1−G1 差值的 95% CI 为 **[−0.536704, 6.980247] pp**，跨零。原前缀窗口中 RP1 身体位置及姿态误差均值较低，G1 手腕姿态误差均值较低。原 root endpoint、wrist position、return 的配对区间也跨零，原统计保持不变。

Common40 共有范围保留 63 条阈值失败记录。主组未触发失败阈值为 RP1 27/40、G1 26/40；当前 Common40 范围没有删失回合。

### 辅助：Extreme5 原评分与首次失败诊断

10 个机器人回合均触发失败阈值，两侧未触发失败阈值均为 0/5。Progress 表示首次失败发生在动作进度中的位置。

| 指标 | RP1 | G1 | RP1−G1 | 95% 配对区间 | 单位 |
| --- | ---: | ---: | ---: | --- | --- |
| Progress | 55.167 | 56.543 | −1.376 | [−2.202, −0.747] | 均值 %，差值及区间 pp |
| 身体位置误差 | 35.817 | 29.087 | 6.730 | [−0.658, 14.117] | mm |
| 身体姿态误差 | 0.1117 | 0.0979 | 0.0137 | [−0.0029, 0.0292] | rad |
| root endpoint 误差 | 0.9101 | 1.0556 | −0.1455 | [−0.3140, −0.0065] | m |
| 手腕位置误差 | 37.619 | 27.051 | 10.568 | [3.436, 16.649] | mm |
| 手腕姿态误差 | 0.1284 | 0.1014 | 0.0270 | [−0.0034, 0.0573] | rad |
| 归一化 tracking return | 1.0105 | 1.0533 | −0.0428 | [−0.0604, −0.0245] | 无量纲 |

原诊断中 G1 的首次阈值 Progress 较高，前缀身体与手腕位置误差均值较低；RP1 的原 root endpoint 误差均值较低。完整精度与逐回合结果见 [extreme5.json](extreme5.json) 和 [extreme5.csv](extreme5.csv)。

## 结果分析

聚合先对完整相同 seed 集求每动作均值，再按动作等权计算组均值。全程四项的 95% 区间采用 10,000 次 paired motion percentile bootstrap，PCG64 随机种子 20261013、线性分位数，每组和指标重置；两侧共享重采样索引。每机器人均值区间与 RP1−G1 配对差值区间分别保存。组内名次依据参与者齐全、完整状态、协议、配对样本及有效指标分母匹配显示，各条件分别报告；配对差异及其不确定性由区间呈现。

Common40 全程主组以 **40 对动作**、Extreme5 以 **5 对动作**为重采样单位。名义重复、初态扰动与显式部署敏感性三组均为 **N=5**，各自四项全程配对区间均跨零；seed 重复不扩大独立动作分母。原七项及首次失败诊断的均值、分母与区间保持原冻结版本。

实质限制集中如下：

- 结果范围为离线仿真，实机表现待验证。区间描述固定 checkpoint 与当前动作的条件分布，训练 seed 总体和本体形态效应未在本设计中单独分离。各项描述性 CI 未作多重比较校正；原 Common40 前缀身体位置差的区间上界接近零。
- 全程均值包含失败后的误差与持续时长；辅助前缀均值受双方存活时长差异影响。Common14 的身体点与 Return 的独立 reward 点集合分别定义，记录完整不等于跟踪成功。
- 30 条名义重复逐值、逐字节一致，独立动作数和训练 seed 数保持原统计单位。
- 公开 retarget 按源动作名和完整时长匹配，原始 BVH 输入哈希血缘尚未完全闭合。
- 发布方尚未明确独立 RP1 v1.1 标签；独立完整八卡训练 run 日志、GPU 型号和阶段执行证据不足。RP1 发布包 seed=42，G1 v1.1 配方 seed=0；本次 G1 权重的历史训练 seed 尚缺直接证据。共同声明的训练规模之外，训练数据、retarget 和控制参数仍有差异。
- Extreme5 区间来自本组 5 对动作；历史人类源哈希与完整训练暴露信息暂无记录，已核验的对应关系包括共同动作身份、时序和根部运动。
- 硬件表按同名解剖关节映射；局部轴、安装零位及有符号角端点需要坐标转换后比较。单关节 ROM 描述该轴跨度，全身可达性还涉及串联几何与碰撞条件。固定策略、训练数据、retarget、本体与控制参数共同影响结果，当前设计未单独识别硬件因素的因果效应。

## 报告与资料

统一报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。飞书正文与 18 页 PDF / DOCX 当前均为 **版本 4**，涵盖 Common40、Extreme5 与机器人参数；新增全程四项的版本 5 尚待云端更新。全程数值以 [fullwindow.json](fullwindow.json) / [fullwindow.csv](fullwindow.csv) 为准；原评分与硬件资料保留既有冻结附件。相关飞书资料需要组织访问权限。

既有同步视频的两侧来源回合均对应 Common40 共有数据。新公开视频为 **0/40**，索引见 [media.json](media.json)；Extreme5 的 5 个视频尚未制作。

## 附录：冻结来源与 SHA256

| 冻结来源 | SHA256 |
| --- | --- |
| report/aggregate.json | `036559d03c4a2a3ec8198c6a703b9a09be096c7181eb62d7c0b91ec06bd42210` |
| site/dist/data.json（冻结原输入） | `218518aa397d938fcd84c630c6dc3a1ee65958439d797a9ce1e3f6759bb715bb` |
| site/build_data.py | `a199be0fb34219019a07bc16b8f2f91ad4d7c863f6f22522a7b5b033a5e44f04` |
| 共同动作报告严格配对清单 | `1bf16dffce86358c7cec87aa2d320cc380b48d881a5ebfe57681aa32bcff6367` |
| RP1 公开学生 ONNX | `42e5feea9643bee1adf93a2a3973bfbae022948e76310ffd98325f3b20a7986b` |
| extreme5.json | `a2d3e11f3f05737b89d4332fc384a95d93eefd819f3ff76eb203a2b4c5b3803e` |
| extreme5.csv | `34fc4c3e1d08b3c8f30757f21efa8675e4e090ba050221e5a5d7d219c04473c1` |
| hardware.json | `5815d8d7e1a28305124849990dc682c85f6e6eb49b7bc78a91ae9adfa270a6af` |
| hardware.csv | `78972776c7640ec62e03bffda14caf0fb530a170ca3751109e66a79ac57614de` |
| [fullwindow.json](fullwindow.json)（源 public_fullwindow.json） | `119d981f07983b060b038e860ac0da9b2d5c10c166fc637b83d179cbf6bda5dd` |
| [fullwindow.csv](fullwindow.csv)（源 public_episodes_fullwindow.csv） | `894a5b836fb1473202c3c3da08b11f9280fe3b572f589279dd00e444ea7e2ff4` |

全程 JSON 为 407,473 bytes，CSV 为 88,651 bytes、180 条回合记录；网站短文件名与来源文件字节相同。

SHA256 标识接收时的冻结来源字节；行内保留源码、配置、协议、checkpoint 与配对样本摘要。公开子集的生成时间、文件大小及自身摘要见 [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json)。云端报告附件原字节尚未独立下载核验。
