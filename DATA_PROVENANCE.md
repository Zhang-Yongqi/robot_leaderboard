# 数据来源与科学边界

版本 `round2-phaseA-036559d03c4a`，消费交接 `phaseA503_036559d03c4a_sitehandoff_20261013_v1`，内部交接清单 SHA `57b12a9ebd7b1f6adf451adf0d9fd763654585aac44991d0f3ac540a7021e5fb`（清单本体未公开）。比较快照生成于 `2026-10-13T09:23:01.848935+00:00`。公开生成时间及公开文件 SHA 见 [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json)。原始比较项目的 `analysis/rp1_g1_round2_20261013` 为权威来源，本仓库只读接收公开字段，不修改比较产物。

## 来源一致性

| 来源相对路径 | SHA256 |
| --- | --- |
| report/aggregate.json | `036559d03c4a2a3ec8198c6a703b9a09be096c7181eb62d7c0b91ec06bd42210` |
| site/dist/data.json（未公开的原输入） | `218518aa397d938fcd84c630c6dc3a1ee65958439d797a9ce1e3f6759bb715bb` |
| site/build_data.py | `a199be0fb34219019a07bc16b8f2f91ad4d7c863f6f22522a7b5b033a5e44f04` |
| site/dist/index.html | `f5ede1cbfb46f5691af94ae6ae8b7b329d588109f3f081e0e28f448cddeeb30c` |
| site/dist/app.js | `f2be6d3e897fccd0ef63904cf06c48e2290e6fe9c423a7298ac59dd0fc309a85` |
| site/dist/style.css | `25eeb98522f5a4b56b21524f9ef259ff9e93c3be644771243a502ac79da251c3` |

这些 SHA 指向接收时的来源字节；公开字段投影与页面文案修改后的文件有各自 SHA。哈希用于版本一致性，不是数字签名。行内仍保留源码、配置、协议、checkpoint 与配对样本 SHA；`provenance.evidence_hashes` 保留内部原记录的标签和 SHA，内部附件未公开。原输入、离线 ZIP 与单 HTML 含私有运行信息，因此不直接再分发。

## 统计与分母

正式计划保留 503 条终态记录；10 条旧时钟记录已由预注册修正结果替换，选中 493 个计划结果：488 完整有效回合、5 个删失 smoke。网页包含 493 逐回合行和 18 聚合行，511 行不是独立样本数。额外 2 次基础设施尝试不增加正式计划分母或机器人失败数。

30 条名义重复的确定性状态逐值、逐字节一致，不增加独立动作数或训练 seed 数。来源重复一致性审计使用较早的 aggregate；最终统计采用上表冻结版本，不把较早审计写成最终 aggregate 的独立审计。

完整相同 seed 集先求每动作均值，再按动作等权聚合。10,000 次 paired motion percentile bootstrap，比较组保存 RP1−G1 差值区间；表格保存每机器人均值区间。它们是固定 checkpoint、当前动作的条件区间，不是训练 seed 总体区间或本体因果效应。浏览器不重新生成成绩或 CI。

组内名次只在预期参与者齐全、完整状态、相同协议、配对样本 SHA 和有效指标分母匹配时展示；名次是数值排序，不表示显著性。没有跨数据集总榜，缺失、无效、删失与未配对均保留原因，n/a 不变成零。

## 指标定义

| 字段 | 解释 |
| --- | --- |
| body_pos_mm / body_ori_rad | Common14 身体点位置 / 姿态误差，首次失败阈值前的局部跟踪均值；单位 mm / rad。Common14 将 G1 官方 toe 点改为 ankle-roll，并显式映射 RP1 pelvis/torso。存在存活时间选择效应。 |
| wrist_pos_mm / wrist_ori_rad | 首次失败阈值前的 wrist 位置 / 姿态误差，单位 mm / rad；不单独证明全回合成功。 |
| root_pos_m | 初始 XY/yaw 对齐、Z 保留，完整 raw rollout 最后 motion_t<N−1 帧的 XYZ root endpoint 误差，单位 m；不按失败截断，并保存 endpoint 时间与 progress。 |
| episode_return | 归一化 tracking return，无量纲；采用独立 torso anchor 和 reward 身体点集合；严格 prefailure 分子、N−1 分母，与 Common14 误差不同。 |
| progress_pct | 完成进度，0–100%；配对差值单位为百分点。 |
| gpu_train_hours | 完整训练 GPU·h；本次实测成本未知，保留 null，CPU 推理耗时不替代训练成本。 |

原生 MuJoCo + CPU ONNX，policy 50 Hz / physics 200 Hz。共同 solver 下保留各机器人原生 PD、effort、armature 与几何参数。首次单帧高度误差严格 >0.3 m 或重力 Z 差严格 >0.8 记失败，无 recover/rejoin/reset；完整原始 rollout 保留。公开 retarget 按源名、完整时长对齐；原始 BVH 输入哈希血缘未完全闭合。同名配对不等于原始血缘完全一致。七项描述性 CI 未做多重比较校正。

40/40 LAFAN40 nominal / native_position 动作的 Progress：RP1 79.735692%，G1 77.268977%，RP1−G1 95% CI [−0.536704, 6.980247] pp。区间跨零，不能声称 RP1 稳定优胜。Body position / orientation 在该条件下 RP1 较低；wrist orientation 为 G1 较低。Root endpoint、wrist position、return 的配对区间也跨零，各指标分别解释。

RP1 当前只具备公开 LAFAN40 覆盖，非 LAFAN 的 348 段缺失；G1 单机补充共 318 段没有 RP1 配对，PHUMA30 缺有效 FPS 元信息，Root90 的 90 段为推断元信息。Dance / Ground 的 root、wrist 不报告，Manipulation 的 root 不报告，均保留 n/a。七组目标数据集共同覆盖尚未齐全。Phase A 比较发布权重；Phase B 同配置正式重训尚未开始，没有 Phase B held-out 成绩。

## 发布权重来源与训练证据

RP1 来自 [Roboparty/MimicLite Released Checkpoints](https://github.com/Roboparty/MimicLite#released-checkpoints) 的 robot-matched 原始 ROA student。实际下载对应 Drive ID `10nzo4O9ZFJTLf0283RKns_Xmm4YxhjL1`；RP1 ONNX SHA `42e5feea9643bee1adf93a2a3973bfbae022948e76310ffd98325f3b20a7986b` 与 bundle manifest 一致。官方对本份权重明确声明 8×8192 环境，配置及 checkpoint 静态元数据均记每 rank 8192，训练代码支持 per-rank 口径。没有独立 run 日志证明完整实际八卡训练历史、GPU 型号和完整阶段执行，不能称完全审计训练。官方未明确独立 RP1 v1.1 release 标签。

G1 v1.1 README 声明 8×8192 环境，配方记 seed=0，但本次 G1 权重的历史训练 seed 缺少直接证据；RP1 发布配置与 checkpoint 保存 seed=42，训练数据不同。相同声明规模不能证明全部条件公平。官方 G1 历史表采用 toe14，与本轮 Common14 和执行器背景不同，单列为外部参考。约 50.106 GPU·h 为同一 G1 checkpoint 的 train/adapt/finetune 整链自报成本，跨数据集重复展示不可相加。

## 报告、视频与云端限制

[技术报告 PDF v2（10 页）](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX v2（10 页）](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)、[专业改写版原生正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)与[附录/35 个视频](https://roboparty.feishu.cn/drive/folder/JReufYd5al9Sfzd2GEkcLGjYnJf)均需飞书组织登录与相应权限；公开网站不会改变这些权限。PDF/DOCX 已升级为专业改写版并预览核验；数据源窗口已确认原生正文在原链接完成替换，刷新全文与审阅版一致，五张表、四幅图及八个资料链接齐全，组织阅读权限保持。本次文字与图注修订不改变冻结评测数据；旧交接清单中的报告文件 SHA 仍指向接收时的旧报告字节。35 个视频已在线预览核验；其 SHA 为本地原视频，未下载云端原文件核验字节一致性。单例视频与仿真统计不证明真机性能。

原始附录本地 42 数据分卷 + 5 控制文件已验收；飞书仅确认 34/42 分卷、0/5 控制文件，余 13 项终态未知，不能称原始云附录完整。本仓库不再分发动作大包、checkpoint、完整内部运行附件、聊天、凭据、SSH 或服务器信息。
# 展示页面与新媒体

展示页面以共同 40 动作的主要配对结果为入口，三项精度图和完成度图直接读取冻结的均值及配对差值区间；浏览器不重新计算统计量。完整七项配对指标、条件差异及全记录筛选保留在可展开区域。展示更新不改变科学 data.json 的任何字节。

media.json 是单独的新公开视频索引。目前新渲染尚未交付，索引为空，公开新片为 0/40；既有飞书素材保留在历史区域并注明组织权限。计划中的新片从共同主选择的保存状态做 FK 重渲染，保留失败后的完整回放，不重跑策略或物理。接收范围为获准公开的 1080p web 和真实共同帧封面；原生 4K master 留在数据源。新媒体验收和托管状态不能由既有 35 段视频推断。
