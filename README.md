# RP1 / G1 Robot Motion Benchmark

RP1 与 G1 固定发布学生策略的离线仿真比较，公开结果包含全程身体与手腕的位置、姿态四项误差。Common40 覆盖 **40个配对动作（N=40）**，Extreme5 独立报告 **5个配对动作（N=5）** 的空翻／转体测试；motion 跟踪任务完成率正在离线核验。网站为 HTML / CSS / JavaScript，无构建步骤或第三方依赖。

## 评测条件

| 数据组 | 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | --- | ---: | ---: | ---: |
| Common40 主组 | nominal / native_position | 40 | 40 | 80 |
| Extreme5 主组 | nominal / native_position | 5 | 5 | 10 |
| Common40 部署敏感性 | explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| Common40 名义重复 | repeat_nominal / native_position | 5 | 15 | 30 |
| Common40 初态扰动 | robust_initial_velocity / native_position | 5 | 25 | 50 |

共有 **45 个动作、90 个条件/seed 配对、180 个机器人回合和 5 个评测组**。公开 JSON 的 190 条记录由 180 条回合记录与 10 条机器人聚合记录构成；各组独立统计，重复 seed 保持原独立动作数。

配对依据实际动作、有效条件、模式、seed 和协议身份的交集，入选不根据任务结局筛选。缺失或删失成绩保留 null 与原因。历史原始实验数据及旧版本保留在来源项目和 Git 历史中。

两个主组使用参考初态与零初速；本次主评测未启用观测噪声、域随机化、外力 push 或随机动作延迟。初态扰动组向根节点 vx、vy 及本地 yaw 角速度施加扰动，标准差分别为 0.05 m/s、0.05 m/s、0.05 rad/s。

## 全程误差结果与分析

四项误差使用既有轨迹全部 **50 Hz 首次物理子步**评分样本，`motion_t=1..N_common−1`，覆盖完整保存轨迹；`N_common` 为共同参考帧数。frame0 用于初始化，200 Hz 末端 hold 不增加评分样本。位置为 mm，姿态为 rad，均为越低越好。

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

统计先在同动作的完整相同 seed 集内平均，再对动作等权；95% 区间采用 10,000 次配对动作 bootstrap。完整均值、区间、逐回合数值与评分窗口见[公开 JSON](data.json)及[评测说明](DATA_PROVENANCE.md)。

## Motion 跟踪任务完成率

摔倒导致无法继续后续动作跟踪，记为未完成；未发生这类不可继续中断，记为完成。中途摔倒后恢复并跟踪到动作末尾，仍记为完成。核验需对照参考动作，区分参考翻滚、倒地起身与摔倒后无法继续。正式回合标签、判定证据及多 seed 动作统计正在离线核验，完成率保持 `null/pending`，**当前不展示百分比**。

## 硬件模型与控制参数

冻结模型质量为 RP1 **40.726 kg**、G1 **33.741 kg**，驱动轴为 **28 / 29**。29 个解剖槽位包含 28 对同名关节；G1 的 `waist_pitch_joint` 在 RP1 列为 n/a。

表中 force caps 是仿真执行器限制，厂家额定／峰值规格保留未知。速度字段为资产声明，原生运行器未做速度包络限幅。局部轴、安装零位与有符号角端点按各模型坐标解释；RP1 训练软限由配置 factor=0.9 推导，训练 tensor 尚未直接核验，G1 原权重级历史软限未知。当前设计未单独识别硬件因素的因果效应。字段定义与单位见[评测说明](DATA_PROVENANCE.md)。

## 数据与报告

- [公开配对结果 JSON](data.json)：190 条记录，四项全程误差及任务完成率状态。
- [逐回合 CSV](episodes.csv)：180 条机器人回合。
- [聚合比较 CSV](comparisons.csv)：10 条机器人聚合记录。
- 硬件模型与控制参数：[JSON](hardware.json) / [CSV](hardware.csv)。
- [条件、指标与结果分析](DATA_PROVENANCE.md)。
- [版本与 SHA256 清单](RELEASE_MANIFEST.json)。
- [新公开视频索引](media.json)：当前 0/40。

统一报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。原链接正在按“全程误差与跟踪任务完成率”的新口径更新；完成率的正式回合标签、判定证据和多 seed 动作统计待冻结。相关飞书资料需要组织访问权限。Extreme5 的 5 个视频尚未制作。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8080/`。

## 可重复更新

从已冻结的全程科学来源与私有身份映射生成公开字段投影，参数以脚本 `--help` 为准：

```sh
python3 scripts/update_snapshot.py \
  --source-fullwindow /path/to/reviewed/public_fullwindow.json \
  --identity-map /path/to/private/identity-map.json \
  --output-dir /path/to/preview
```

全程科学输入 SHA256 为 `119d981f07983b060b038e860ac0da9b2d5c10c166fc637b83d179cbf6bda5dd`。公开投影保留四项误差、均值、区间、分母与配对身份；输出 `data.json`、`episodes.csv`、`comparisons.csv`，文件摘要见[来源附录](DATA_PROVENANCE.md#附录冻结来源与-sha256)及发布清单。JSON 与 CSV 保留原科学协议、执行协议、配置和来源摘要；原未记录字段为 null。私有身份映射不进入公开目录。

四项全程误差可先独立正式发布，发布前完成静态检查及桌面、手机浏览器 QA。完成率保持 `null/pending`，待正式回合标签、判定证据与多 seed 动作统计冻结后更新。GitHub Pages 发布源为 `main / (root)`。
