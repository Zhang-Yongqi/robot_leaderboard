# RP1 与 G1 共同动作评测说明

本评测比较两套固定发布学生策略的离线仿真表现，主比较覆盖 **40个配对动作（N=40）**。科学版本为 `round2-phaseA-036559d03c4a`，冻结比较生成于 `2026-10-13T09:23:01.848935+00:00`。公开快照沿用冻结指标与区间，历史原始实验记录保留在来源项目。

## 评测条件

### 动作覆盖与配对

配对按 `phase / dataset / condition / mode / motion_id / seed` 的精确交集建立，并核验相同协议与运行口径。`condition` 为来源适配器的有效条件；修正时钟后的 `aligned_nominal` 归入 `nominal`，使用冻结清单选定的替代记录。机器人专属配置和 checkpoint 各自保留。

170 条机器人回合逐条对应共同动作报告的冻结 run ID，双方时钟、条件及扰动文件一致。全局协议 SHA 用于绑定冻结版本；逐场景配对由这些回合身份与条件记录支持。入选依据为身份交集，包含成功及阈值失败记录，`Progress`、`verified` 和 `strict_pair` 均不作为入选条件。

| 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | ---: | ---: | ---: |
| nominal / native_position | 40 | 40 | 80 |
| explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| repeat_nominal / native_position | 5 | 15 | 30 |
| robust_initial_velocity / native_position | 5 | 25 | 50 |

四组共 85 个条件/seed 配对、170 条机器人回合及 8 条聚合记录，即 178 个展示行；动作去重后为 40 个。各组分别报告，聚合值只在原动作/seed 群体完整保留时沿用冻结版本。可配对的删失或缺失成绩保留 `null` 与原因。

### 策略与运行配置

RP1 为 28 DoF 原版 robot-matched ROA student，来源 [Roboparty/MimicLite](https://github.com/Roboparty/MimicLite#released-checkpoints)；G1 为 29 DoF MimicLite v1.1 发布策略。发布方均声明 8×8192 环境，RP1 静态配置与 checkpoint 记每 rank 8192。两者的训练数据、retarget 和机器人控制参数各自保留。Phase B 同配置正式重训尚未开始。

运行环境为原生 MuJoCo + CPU ONNX，policy 50 Hz / physics 200 Hz。共同 solver 下使用各机器人的原生 PD、effort、armature 与几何参数。首次单帧高度误差严格 >0.3 m 或重力 Z 差严格 >0.8 时记失败；完整原始 rollout 保留，运行中无 recover/rejoin/reset。

### 指标定义

| 字段 | 口径与单位 |
| --- | --- |
| body_pos_mm / body_ori_rad | Common14 身体位置 / 姿态误差，首次失败阈值前的局部跟踪均值，mm / rad；使用 ankle-roll 语义映射及 RP1 pelvis/torso 映射。 |
| wrist_pos_mm / wrist_ori_rad | 首次失败阈值前的手腕位置 / 姿态误差，mm / rad。 |
| root_pos_m | 初始 XY/yaw 对齐、Z 保留；完整 raw rollout 最后 motion_t<参考帧数−1 的帧的 XYZ root endpoint 误差，m，保留失败后的回放窗口。 |
| episode_return | 无量纲归一化 tracking return，使用独立 torso anchor 与 reward 点集合，严格 prefailure 分子及参考帧数−1 分母。 |
| progress_pct | 完成进度 0–100%；机器人差值单位为百分点（pp）。 |
| gpu_train_hours | 完整训练 GPU·h 暂无记录，保留 null；CPU 推理耗时与训练成本分别记录。 |

## 评测结果

主组 Progress 为 RP1 **79.735692%**、G1 **77.268977%**；RP1−G1 差值的 95% CI 为 **[−0.536704, 6.980247] pp**，跨零。RP1 身体位置及姿态误差均值较低，G1 手腕姿态误差均值较低。Root endpoint、wrist position、return 的配对区间也跨零。

全部共有范围保留 63 条阈值失败记录。主组未触发失败阈值为 RP1 27/40、G1 26/40；当前共有范围没有删失回合。

## 结果分析

聚合先对完整相同 seed 集求每动作均值，再按动作等权计算组均值。RP1−G1 差值采用 10,000 次 paired motion percentile bootstrap；每机器人均值区间另存。组内名次依据参与者齐全、完整状态、协议、配对样本及有效指标分母匹配显示，各条件分别报告；配对差异及其不确定性由区间呈现。

实质限制集中如下：

- 结果范围为离线仿真，实机表现待验证。区间描述固定 checkpoint 与当前动作的条件分布，训练 seed 总体和本体形态效应未在本设计中单独分离。七项描述性 CI 未作多重比较校正；身体位置差的区间上界接近零。
- 身体与手腕均值使用首次失败前的窗口，双方存活时长不同会影响误差均值。Common14 的身体点与 Return 的独立 reward 点集合分别定义。
- 30 条名义重复逐值、逐字节一致，独立动作数和训练 seed 数保持原统计单位。
- 公开 retarget 按源动作名和完整时长匹配，原始 BVH 输入哈希血缘尚未完全闭合。
- 发布方尚未明确独立 RP1 v1.1 标签；独立完整八卡训练 run 日志、GPU 型号和阶段执行证据不足。RP1 发布包 seed=42，G1 v1.1 配方 seed=0；本次 G1 权重的历史训练 seed 尚缺直接证据。共同声明的训练规模之外，训练数据、retarget 和控制参数仍有差异。

## 报告与资料

网站范围对应 `common_v07_20261014` 共同动作报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。PDF 与 DOCX 附件为版本 3；相关飞书报告及既有同步视频需要组织访问权限。

既有同步视频的两侧来源回合均对应当前共有数据。新公开视频为 **0/40**，索引见 [media.json](media.json)。

## 附录：冻结来源与 SHA256

| 冻结来源 | SHA256 |
| --- | --- |
| report/aggregate.json | `036559d03c4a2a3ec8198c6a703b9a09be096c7181eb62d7c0b91ec06bd42210` |
| site/dist/data.json（冻结原输入） | `218518aa397d938fcd84c630c6dc3a1ee65958439d797a9ce1e3f6759bb715bb` |
| site/build_data.py | `a199be0fb34219019a07bc16b8f2f91ad4d7c863f6f22522a7b5b033a5e44f04` |
| 共同动作报告严格配对清单 | `1bf16dffce86358c7cec87aa2d320cc380b48d881a5ebfe57681aa32bcff6367` |
| RP1 公开学生 ONNX | `42e5feea9643bee1adf93a2a3973bfbae022948e76310ffd98325f3b20a7986b` |

SHA256 标识接收时的冻结来源字节；行内保留源码、配置、协议、checkpoint 与配对样本摘要。公开子集的生成时间、文件大小及自身摘要见 [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json)。云端报告附件原字节尚未独立下载核验。
