# RP1 / G1 Robot Motion Benchmark

RP1 与 G1 固定发布学生策略的离线仿真比较，公开结果包含全程身体、手腕与根部的位置、姿态六项误差，以及独立的根部终点位置误差。Common40 覆盖 **40个配对动作（N=40）**，Extreme5 独立报告 **5个配对动作（N=5）** 的空翻／转体测试；motion 跟踪任务完成率依据几何、参考轨迹与有效末端证据单独报告。网站为 HTML / CSS / JavaScript，无构建步骤或第三方依赖。

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

身体与手腕四项误差使用既有轨迹全部 **50 Hz 首次物理子步**评分样本，`motion_t=1..N_common−1`；`N_common` 为共同参考帧数。frame0 用于初始化，200 Hz 末端 hold 不增加评分样本。原四项评分窗口、数值与区间保持不变。

根部两项使用原 200 Hz 物理轨迹中与 **50 Hz 参考时刻同刻**的根状态，完整保留有效参考帧 `1..N_common−1`，包含失控后样本，末后 hold 不计入。首个共同有效同刻样本 **0.02 s** 为固定 XY/yaw 对齐锚点，Z 不平移；随后不逐帧重新拟合。根位置为三维距离的全窗算术均值（mm）；根姿态将实际与参考 wxyz 四元数单位化，用同一固定 yaw 左乘实际姿态，再对相对姿态的最短旋转角取全窗算术均值（rad），保留 roll/pitch 误差，q 与 −q 等价。位置误差按 mm 保留三位小数，姿态按 rad 保留四位；数值越低越好。显示精度下并列仅表示显示值相同，配对差异及其区间按未舍入来源解释，不由显示名次推断。

| 组 / 指标 | RP1 | G1 | RP1−G1 | 95% 配对区间 | 单位 |
| --- | ---: | ---: | ---: | --- | --- |
| Common40 / 身体位置误差 | 121.598 | 156.490 | -34.891 | [-76.304, -3.484] | mm |
| Common40 / 身体姿态误差 | 0.4041 | 0.5477 | -0.1435 | [-0.2675, -0.0391] | rad |
| Common40 / 手腕位置误差 | 128.573 | 166.508 | -37.935 | [-88.584, -0.302] | mm |
| Common40 / 手腕姿态误差 | 0.4276 | 0.5680 | -0.1404 | [-0.2701, -0.0245] | rad |
| Common40 / 根三维位置误差 | 950.378 | 1070.920 | -120.542 | [-310.509, 57.987] | mm |
| Common40 / 根姿态误差 | 0.4332 | 0.5516 | -0.1184 | [-0.2461, -0.0206] | rad |
| Extreme5 / 身体位置误差 | 318.475 | 307.636 | 10.839 | [-5.097, 32.489] | mm |
| Extreme5 / 身体姿态误差 | 0.9061 | 0.9713 | -0.0652 | [-0.1968, 0.1038] | rad |
| Extreme5 / 手腕位置误差 | 322.826 | 307.383 | 15.442 | [-37.720, 68.052] | mm |
| Extreme5 / 手腕姿态误差 | 0.9850 | 1.1266 | -0.1416 | [-0.3103, -0.0098] | rad |
| Extreme5 / 根三维位置误差 | 432.780 | 447.002 | -14.222 | [-98.297, 62.866] | mm |
| Extreme5 / 根姿态误差 | 0.9740 | 1.0937 | -0.1197 | [-0.3059, 0.0489] | rad |

Common40 的身体、手腕四项误差与根姿态误差均值为 RP1 较低，配对差值区间均位于零以下；根位置均值为 RP1 较低，但差值区间跨零。Extreme5 的身体与手腕位置均值为 G1 较低，身体、手腕、根部的姿态误差与根位置误差均值为 RP1 较低；仅手腕姿态差值区间位于零以下，其余五项跨零。三个敏感性组各以 5 个动作为统计单位，身体与手腕四项差值区间均跨零；名义重复、根初态扰动的根姿态区间位于零以下，部署敏感性的根位置区间位于零以上，其余根部区间跨零。

统计先在同动作的完整相同 seed 集内平均，再对动作等权；95% 区间采用 10,000 次配对动作 bootstrap。完整均值、区间、逐回合数值与评分窗口见[公开 JSON](data.json)及[评测说明](DATA_PROVENANCE.md)。

## 根部终点位置误差

`root_endpoint_pos_mm` 使用每回合最后合法参考时刻 **m=N_common−1** 的世界根 XYZ，与参考同刻取样；每回合 **1 个终点样本**。沿用首个共同有效同刻样本 **0.02 s** 的固定 XY/yaw 对齐，Z 保持绝对值，末后 **20 ms hold** 排除。失败后仍保留合法末点，完成标签不用于筛掉或重判终点记录。 此项描述单个末端的空间偏差，与六项全程均值分开报告。

| 数据组 | 动作 N | RP1 均值 [95% 区间] | G1 均值 [95% 区间] | RP1−G1 [95% 配对区间] | 单位 |
| --- | ---: | --- | --- | --- | --- |
| Common40 主组 | 40 | 1384.994 [1015.245, 1799.709] | 1671.610 [1259.900, 2139.424] | -286.616 [-624.173, 39.947] | mm |
| Extreme5 主组 | 5 | 910.962 [665.976, 1240.754] | 1054.553 [750.898, 1527.027] | -143.591 [-313.427, -2.892] | mm |
| 部署敏感性 | 5 | 1439.810 [537.187, 2342.433] | 1149.236 [355.107, 1943.365] | 290.574 [36.770, 544.378] | mm |
| 名义重复 | 5 | 1529.744 [384.028, 3044.259] | 1023.525 [232.239, 1855.871] | 506.219 [-459.103, 1560.896] | mm |
| 根初态扰动 | 5 | 1325.266 [440.389, 2245.413] | 1159.723 [355.828, 1963.618] | 165.543 [-415.809, 709.689] | mm |

Common40 终点误差均值为 RP1 较低，但配对差值区间跨零。Extreme5 区间位于零以下，支持本组 RP1 终点误差较低；双方动作完成率仍为 0%，终点偏差与任务结局分别报告。部署敏感性的区间位于零以上，支持该条件下 G1 较低；名义重复与根初态扰动的区间跨零。

## Motion 跟踪任务完成率

因失控摔倒而无法继续后续跟踪，记为未完成；中途倒地后重新跟上参考并维持到有效动作末端，仍记为完成。核验对照参考动作，区分翻滚、倒地起身与未恢复的失控姿态；完整仿真记录本身不决定完成状态。

| 数据组 | 动作 N | RP1 | G1 |
| --- | ---: | --- | --- |
| Common40 主组 | 40 | 72.5%（29/40） | 65%（26/40） |
| Extreme5 主组 | 5 | 0%（0/5） | 0%（0/5） |
| 部署敏感性 | 5 | 60%（3.0/5 动作当量） | 60%（3.0/5 动作当量） |
| 名义重复 | 5 | 60%（3.0/5 动作当量） | 60%（3.0/5 动作当量） |
| 根初态扰动 | 5 | 60%（3.0/5 动作当量） | 60%（3.0/5 动作当量） |

多 seed 先在动作内平均完成／未完成二元标签，再对动作等权；敏感性组使用“动作等权平均完成比例／完成动作当量”。同动作跨 seed 结局不一致时保留分数比例，不强行归为二分类；15 或 25 个配对回合不扩大独立动作 N=5。

存在 unknown 标签时保留完整分母，点比例为 null，并保留逻辑上下界。完成率描述本组所选动作，不用于推断总体成功概率，未创建完成率 CI。判定依靠几何、参考轨迹与有效末端，接触力未直接记录；两个失败时钟表示最终持续未恢复区间的几何观察起点。完整定义见[评测说明](DATA_PROVENANCE.md)。

## 硬件模型与控制参数

冻结模型质量为 RP1 **40.726 kg**、G1 **33.741 kg**，驱动轴为 **28 / 29**。29 个解剖槽位包含 28 对同名关节；G1 的 `waist_pitch_joint` 在 RP1 列为 n/a。

表中 force caps 是仿真执行器限制，厂家额定／峰值规格保留未知。速度字段为资产声明，原生运行器未做速度包络限幅。局部轴、安装零位与有符号角端点按各模型坐标解释；RP1 训练软限由配置 factor=0.9 推导，训练 tensor 尚未直接核验，G1 原权重级历史软限未知。当前设计未单独识别硬件因素的因果效应。字段定义与单位见[评测说明](DATA_PROVENANCE.md)。

## 数据与报告

- [公开配对结果 JSON](data.json)：190 条记录，六项全程误差、根部终点位置误差及语义任务完成率。
- [逐回合 CSV](episodes.csv)：180 条机器人回合、46 列。
- [聚合比较 CSV](comparisons.csv)：10 条机器人聚合记录、55 列。
- 硬件模型与控制参数：[JSON](hardware.json) / [CSV](hardware.csv)。
- [条件、指标与结果分析](DATA_PROVENANCE.md)。
- [版本与 SHA256 清单](RELEASE_MANIFEST.json)。
- [新公开视频索引](media.json)：当前 0/40。

统一报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。《RP1与G1全程跟踪精度与动作完成率》**V8 已同步**，正文、PDF 与 DOCX 均已更新到原地址，包含六项全程误差、独立根部终点位置误差与任务完成率。相关飞书资料需要组织访问权限。Extreme5 的 5 个视频尚未制作。

共同失败动作与 Extreme5 已列为后续复测重录范围；本版继续采用当前冻结结果。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8080/`。

## 可重复更新

从冻结的六项全程误差、根部终点位置误差与任务完成率公共科学输入、私有身份映射生成公开字段投影，调用参数以发布脚本 `--help` 为准。

```sh
python3 scripts/update_snapshot.py \
  --fullwindow-source /path/to/archived/public_fullwindow.json \
  --source-completion /path/to/reviewed/public_completion_fullwindow.json \
  --source-root /path/to/reviewed/public_sixerror_completion.json \
  --source-endpoint /path/to/reviewed/public_sevenerror_completion.json \
  --identity-map /path/to/private/identity-map.json \
  --output-dir .private/publication_staging \
  --publication

python3 scripts/verify_public.py \
  --repo-root .private/publication_candidate \
  --source-fullwindow /path/to/archived/public_fullwindow.json \
  --source-completion /path/to/reviewed/public_completion_fullwindow.json \
  --source-root /path/to/reviewed/public_sixerror_completion.json \
  --source-endpoint /path/to/reviewed/public_sevenerror_completion.json \
  --identity-map /path/to/private/identity-map.json
```

当前正式复合科学来源为 `public_sevenerror_completion.json` 与 `public_sevenerror_episodes.csv`；文件包含六项全程误差、独立终点值、每机器人均值与区间、配对差值区间及完成率。终点每回合一个样本，原六项全程窗口、数值、CI 与完成率保持冻结来源。各输入的冻结 SHA256 见[来源附录](DATA_PROVENANCE.md#附录冻结来源与-sha256)。schema 6 公开输出为 `data.json`、`episodes.csv`、`comparisons.csv`，自身摘要见发布清单。JSON 与 CSV 保留科学协议、执行协议、配置和来源摘要；原未记录字段为 null。私有身份映射不进入公开目录。

`--source-completion`、`--source-root` 与 `--source-endpoint` 的 JSON 同目录分别须包含 `public_completion_episodes.csv`、`public_sixerror_episodes.csv` 与 `public_sevenerror_episodes.csv`，各自按冻结 SHA256 核验。历史全程、完成率及根部输入保留原有回归锚，终点独立接入。`--endpoint-adapter` 可省略，默认使用已注册的 `public_root_endpoint_completion_v8`。

生成目录包含三份公开数据文件。验证与发布的完整候选须包含 **18 个白名单公开文件**及更新后的 `RELEASE_MANIFEST.json`，包括 `scripts/source_contract.py`；三份生成数据本身不构成完整发布包。

公开投影经独立核验及静态、桌面和手机浏览器 QA 后发布。科学来源与公开投影的摘要分别记录，报告云端更新单独核验。GitHub Pages 发布源为 `main / (root)`。
