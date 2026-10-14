# 共同动作数据来源与科学边界

科学版本 `round2-phaseA-036559d03c4a`，冻结比较生成于 `2026-10-13T09:23:01.848935+00:00`。本站由权威来源项目的冻结快照派生共同动作公开子集；原始实验记录保持不变。公开生成时间、文件大小及 SHA 见 [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json)。

## 配对范围

仅纳入 RP1 与 G1 两侧都有记录的精确身份键：`phase / dataset / condition / mode / motion_id / seed`，并核验相同协议与运行口径。`condition` 已是来源适配器的有效条件；修正时钟后的 `aligned_nominal` 归入 `nominal`，使用已选中的替代记录。机器人专属配置和 checkpoint 不要求相等。

身份还与共同动作报告的冻结 run 清单逐条核验：170 条回合均对应真实 run ID，双方记录时钟与条件一致，扰动文件已在来源审计中配对。全局协议 SHA 只是冻结版本身份，不能单独证明逐场景可比。公开 retarget 的源名和完整时长匹配不等于原始 BVH 哈希血缘完全闭合。

| 条件 / 模式 | 共同动作数 | 条件/seed 配对数 | 回合数 |
| --- | ---: | ---: | ---: |
| nominal / native_position | 40 | 40 | 80 |
| explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| repeat_nominal / native_position | 5 | 15 | 30 |
| robust_initial_velocity / native_position | 5 | 25 | 50 |

合计 85 对、170 条回合及 8 条聚合，共 178 展示行，覆盖 40 个独立动作。各条件分别报告。30 条名义重复逐值、逐字节一致，不增加独立动作数或训练 seed 数。

配对不使用成功、Progress、`verified` 或 `strict_pair` 作为入选条件。当前共有范围保留 63 条阈值失败记录，主组未触发失败阈值为 RP1 27/40、G1 26/40。可配对的删失或缺失成绩应保留 null 与原因；当前共有范围没有删失回合。不填零、不强配。原冻结聚合只在其完整动作/seed 群体都保留时复用；本次未重算指标或 CI。

## 指标与统计

| 字段 | 口径与单位 |
| --- | --- |
| body_pos_mm / body_ori_rad | Common14 身体位置 / 姿态误差，首次失败阈值前的局部跟踪均值，mm / rad。使用 ankle-roll 语义映射及 RP1 pelvis/torso 映射，存在存活时间选择效应。 |
| wrist_pos_mm / wrist_ori_rad | 首次失败阈值前的手腕位置 / 姿态误差，mm / rad；不单独证明全回合成功。 |
| root_pos_m | 初始 XY/yaw 对齐、Z 保留；完整 raw rollout 最后 motion_t<N−1 帧的 XYZ root endpoint 误差，m；不按失败截断。 |
| episode_return | 无量纲归一化 tracking return，独立 torso anchor 与 reward 点集合，严格 prefailure 分子及 N−1 分母；与 Common14 误差不同。 |
| progress_pct | 完成进度 0–100%；机器人差值单位为百分点（pp）。 |
| gpu_train_hours | 完整训练 GPU·h 本次未知，保留 null；CPU 推理耗时不替代训练成本。 |

完整相同 seed 集先求每动作均值，再按动作等权聚合。10,000 次 paired motion percentile bootstrap 保存 RP1−G1 差值区间；每机器人均值区间另存。区间限于固定 checkpoint 和当前动作，不是训练 seed 总体区间或本体因果效应。七项描述性 CI 未做多重比较校正。

主组 Progress：RP1 79.735692%，G1 77.268977%；差值 95% CI [−0.536704, 6.980247] pp，跨零。RP1 身体位置/姿态误差较低，G1 手腕姿态误差较低；身体位置差的区间上界接近零，须谨慎解释。Root endpoint、wrist position、return 的配对区间也跨零，各指标分别解读。

组内名次仅在预期参与者齐全、完整状态、协议、配对样本 SHA 和有效指标分母匹配时显示。数值排序不表示显著性，没有跨条件总榜。

## 运行条件与公平性

原生 MuJoCo + CPU ONNX，policy 50 Hz / physics 200 Hz。共同 solver 下保留各机器人的原生 PD、effort、armature 与几何参数。首次单帧高度误差严格 >0.3 m 或重力 Z 差严格 >0.8 记失败；无 recover/rejoin/reset，完整原始 rollout 保留。统计与视频不证明真机性能。

RP1 为 28 DoF 原版 robot-matched ROA student，来源 [Roboparty/MimicLite](https://github.com/Roboparty/MimicLite#released-checkpoints)，ONNX SHA `42e5feea9643bee1adf93a2a3973bfbae022948e76310ffd98325f3b20a7986b`；官方未明确独立 RP1 v1.1 标签。G1 为 29 DoF MimicLite v1.1 发布策略。发布方均声明 8×8192 环境，RP1 静态配置与 checkpoint 记每 rank 8192；独立完整八卡训练 run 日志、GPU 型号和阶段执行证据不足。

RP1 发布包 seed=42，G1 v1.1 配方 seed=0，但本次 G1 权重的历史训练 seed 缺直接证据。训练数据、retarget 和机器人控制参数不同；相同声明规模不能证明全部训练条件公平。Phase B 同配置正式重训尚未开始，暂无成绩。

## 来源与报告

| 冻结来源 | SHA256 |
| --- | --- |
| report/aggregate.json | `036559d03c4a2a3ec8198c6a703b9a09be096c7181eb62d7c0b91ec06bd42210` |
| site/dist/data.json（未公开原输入） | `218518aa397d938fcd84c630c6dc3a1ee65958439d797a9ce1e3f6759bb715bb` |
| site/build_data.py | `a199be0fb34219019a07bc16b8f2f91ad4d7c863f6f22522a7b5b033a5e44f04` |
| 共同动作报告严格配对清单 | `1bf16dffce86358c7cec87aa2d320cc380b48d881a5ebfe57681aa32bcff6367` |

来源 SHA 指接收时冻结字节，公开子集另有自身 SHA；哈希是版本一致性证据，不是签名。行内保留源码、配置、协议、checkpoint 与配对样本 SHA，内部附件不公开。

网站范围对应 `common_v07_20261014` 共同动作报告。[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)和 [DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)均需组织登录/权限。报告任务的最终回执已确认原生正文与统一内容源精确一致，4 张表、4 幅共同动作图及 8 个资料链接核对通过，附件为版本 3，旧版保留。本网站读取该完成回执以对齐范围，没有再次更新飞书。云端原文件字节没有独立下载核验，不把本地上传源 SHA 当作云端字节证明。

只保留来源回合可精确对应共有数据的既有双机器人同步视频链接，需组织权限。视频是个例证据，不增加样本量。[media.json](media.json) 新片索引为空，公开新片为 0/40；新媒体许可待确认，本次未上传任何新媒体。
