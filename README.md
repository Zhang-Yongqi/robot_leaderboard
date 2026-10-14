# RP1 / G1 Robot Motion Benchmark

RP1 与 G1 固定发布学生策略的离线仿真比较，以全程身体与手腕的位置、姿态误差为四项主指标。Common40 覆盖 **40个配对动作（N=40）**，Extreme5 独立报告 **5个配对动作（N=5）** 的空翻／转体测试；原评分与首次失败信息作为辅助诊断，并提供冻结硬件模型与控制参数对比。网站为 HTML / CSS / JavaScript，无构建步骤或第三方依赖。

## 评测条件

| 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | ---: | ---: | ---: |
| nominal / native_position | 40 | 40 | 80 |
| explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| repeat_nominal / native_position | 5 | 15 | 30 |
| robust_initial_velocity / native_position | 5 | 25 | 50 |

以上 Common40 四组分别报告，共 85 个条件/seed 配对、170 条机器人回合及 8 条聚合记录，即 178 个展示行；动作去重后为 40 个。其 `data.json` 字节、原评分指标与区间保持原冻结版本。

Extreme5 为 nominal / native_position、seed=0 的独立动作组：5 个配对动作、5 对、10 个机器人回合、2 条聚合记录，10 个回合均触发失败阈值。网页组合展示两套附件后，共 45 个动作、90 对、180 个机器人回合、10 条聚合记录、190 个展示行及 5 个评测组；各组分别计算，硬件表的 29 个槽位另行展示。

全程四项按既有回合身份关联，沿用上述覆盖统计。配对依据实际动作、有效条件、模式、seed 和协议身份的交集，保留阈值失败及可配对删失的 null 与原因。历史原始实验数据及旧版本保留在来源项目和 Git 历史中。

两个主组使用参考初态与零初速；本次主评测未启用观测噪声、域随机化、外力 push 或随机动作延迟。初态扰动组向根节点 vx、vy 及本地 yaw 角速度施加扰动，标准差分别为 0.05 m/s、0.05 m/s、0.05 rad/s。

## 评测结果与分析

四项全程指标使用既有轨迹全部 **50 Hz 首次物理子步**评分样本，`motion_t=1..N_common−1`，包含首次失败及其后样本；`N_common` 为共同参考帧数。frame0 用于初始化，200 Hz 末端 hold 不增加评分样本。位置为 mm，姿态为 rad，均为越低越好。

| 组 / 指标 | RP1 | G1 | RP1−G1 | 95% 配对区间 | 单位 |
| --- | ---: | ---: | ---: | --- | --- |
| Common40 / 身体位置误差 | 121.598 | 156.490 | -34.891 | [-76.304, -3.484] | mm |
| Common40 / 身体姿态误差 | 0.4041 | 0.5477 | -0.1435 | [-0.2675, -0.0391] | rad |
| Common40 / 手腕位置误差 | 128.573 | 166.508 | -37.935 | [-88.584, -0.302] | mm |
| Common40 / 手腕姿态误差 | 0.4276 | 0.5680 | -0.1404 | [-0.2701, -0.0245] | rad |
| Extreme5 / 身体位置误差 | 318.475 | 307.636 | 10.839 | [-5.097, 32.489] | mm |
| Extreme5 / 身体姿态误差 | 0.9061 | 0.9713 | -0.0652 | [-0.1968, 0.1038] | rad |
| Extreme5 / 手腕位置误差 | 322.826 | 307.383 | 15.442 | [-37.720, 68.052] | mm |
| Extreme5 / 手腕姿态误差 | 0.9850 | 1.1266 | -0.1416 | [-0.3103, -0.0098] | rad |

Common40 的四项全程误差均值均为 RP1 较低，配对差值区间均位于零以下。Extreme5 的身体与手腕位置均值为 G1 较低、姿态均值为 RP1 较低；仅手腕姿态差值区间位于零以下，另三项跨零。三个敏感性组各以 5 个动作为统计单位，四项全程差值区间均跨零。

统计先在同动作的完整相同 seed 集内平均，再对动作等权；95% 区间采用 10,000 次配对动作 bootstrap。30 条确定性重复保持原独立动作数。完整均值、区间、逐回合数值与评分窗口见[全程 JSON](fullwindow.json)及[评测说明](DATA_PROVENANCE.md)。

### 辅助：原评分与首次失败诊断

Common40 原 Progress 为 RP1 **79.736%**、G1 **77.269%**；RP1−G1 的 95% 配对区间为 **[−0.537, 6.980] pp**。原前缀窗口中 RP1 身体误差均值较低，G1 手腕姿态误差均值较低。

Extreme5 原 Progress 为 **55.167% / 56.543%**；差值 **−1.376 pp**，95% 区间 **[−2.202, −0.747] pp**。原前缀身体位置误差为 **35.817 / 29.087 mm**，手腕位置为 **37.619 / 27.051 mm**（RP1 / G1）。两侧各 5 个动作均触发失败阈值。

Progress 记录首次阈值位置，未触发时取参考末端；完整回放与该诊断分别呈现。原身体／手腕前缀指标、Return 和最后有效策略帧 root endpoint 保持既有评分口径；新增全程指标为上述四项误差。Phase B 正式重训尚未开始。

## 硬件模型与控制参数

冻结模型质量为 RP1 **40.726 kg**、G1 **33.741 kg**，驱动轴为 **28 / 29**。29 个解剖槽位包含 28 对同名关节；G1 的 `waist_pitch_joint` 在 RP1 列为 n/a。

表中 force caps 是仿真执行器限制，厂家额定／峰值规格保留未知。速度字段为资产声明，原生运行器未做速度包络限幅。局部轴、安装零位与有符号角端点按各模型坐标解释；RP1 训练软限由配置 factor=0.9 推导，训练 tensor 尚未直接核验，G1 原权重级历史软限未知。当前设计未单独识别硬件因素的因果效应。字段定义与单位见[评测说明](DATA_PROVENANCE.md)。

## 数据与报告

- 全程四项主指标：[JSON](fullwindow.json) / [180 回合 CSV](fullwindow.csv)
- [Common40 原评分数据](data.json)
- Extreme5：[JSON](extreme5.json) / [CSV](extreme5.csv)
- 硬件模型与控制参数：[JSON](hardware.json) / [CSV](hardware.csv)
- [条件、指标与结果分析](DATA_PROVENANCE.md)
- [版本与 SHA256 清单](RELEASE_MANIFEST.json)
- [新公开视频索引](media.json)：当前 0/40。

统一报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。18 页全程报告的飞书正文、PDF / DOCX 已在原链接同步为 **版本 5（V5 已同步）**；正文 15 表、888 单元格完整回读通过，4 张原版诊断图和 8 个来源链接保留。当前数值见全程 JSON / CSV。报告及既有同步视频需要组织访问权限。Extreme5 的 5 个视频尚未制作。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8080/`。

## 可重复更新

从冻结来源运行标准库投影脚本：

```sh
python3 scripts/update_snapshot.py \
  --source-data /path/to/reviewed/site/dist/data.json \
  --expected-source-sha 218518aa397d938fcd84c630c6dc3a1ee65958439d797a9ce1e3f6759bb715bb \
  --expected-aggregate-sha 036559d03c4a2a3ec8198c6a703b9a09be096c7181eb62d7c0b91ec06bd42210 \
  --handoff /path/to/reviewed/MANIFEST.json \
  --expected-handoff-sha 57b12a9ebd7b1f6adf451adf0d9fd763654585aac44991d0f3ac540a7021e5fb \
  --output-dir .
python3 scripts/verify_public.py
node --check app.js
```

已有发布目录中的冻结扩展附件会先按固定摘要核验，再保留到新清单。初始化新目录时，增加 `--extensions-manifest /path/to/reviewed/WEBSITE_HANDOFF_MANIFEST.json`，从已冻结交接的白名单复制原四附件，同时增加 `--fullwindow-receipt /path/to/reviewed/PUBLIC_FULLWINDOW_FINAL_RECEIPT.json`，从正式终态白名单复制全程两附件；缺失或不符时在写入前停止。

以上命令和 SHA 对应 Common40 冻结版本。脚本核验来源，以字段白名单和精确配对交集生成其公开快照；保留行的指标、CI、分母、失败状态及身份保持一致。Extreme5、硬件与全程资料作为冻结扩展附件载入，文件摘要见[来源附录](DATA_PROVENANCE.md#附录冻结来源与-sha256)。聚合只在原输入群体完整保留时复用，科学版本变更需同步更新版本契约。

完成静态检查及桌面、手机浏览器 QA 后，提交发布白名单内的公开文件。GitHub Pages 发布源为 `main / (root)`。
