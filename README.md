# RP1 / G1 Robot Motion Benchmark

RP1 与 G1 固定发布学生策略的离线仿真比较，Common40 主比较覆盖 **40个配对动作（N=40）**；Extreme5 另列 **5个配对动作（N=5）** 的空翻／转体测试，并提供冻结硬件模型与控制参数对比。网站为 HTML / CSS / JavaScript，无构建步骤或第三方依赖。

## 评测条件

| 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | ---: | ---: | ---: |
| nominal / native_position | 40 | 40 | 80 |
| explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| repeat_nominal / native_position | 5 | 15 | 30 |
| robust_initial_velocity / native_position | 5 | 25 | 50 |

以上 Common40 四组分别报告，共 85 个条件/seed 配对、170 条机器人回合及 8 条聚合记录，即 178 个展示行；动作去重后为 40 个。其 `data.json` 字节、指标与区间保持原冻结版本。

Extreme5 为 nominal / native_position、seed=0 的独立动作组：5 个配对动作、5 对、10 个机器人回合、2 条聚合记录，10 个回合均触发失败阈值。网页组合展示两套附件后，共 45 个动作、90 对、180 个机器人回合、10 条聚合记录、190 个展示行及 5 个评测组；各组分别计算，硬件表的 29 个槽位另行展示。

配对依据实际动作、有效条件、模式、seed 和协议身份的交集，保留阈值失败及可配对删失的 null 与原因。历史原始实验数据及旧版本保留在来源项目和 Git 历史中。

## 评测结果与分析

Common40 主比较 Progress：RP1 **79.736%**，G1 **77.269%**；RP1−G1 的 95% 配对区间为 **[−0.537, 6.980] 个百分点**，跨零。RP1 body 误差均值较低，G1 wrist 姿态误差均值较低，原统计保持不变。

Extreme5 的 Progress 为 RP1 **55.167%**、G1 **56.543%**；差值 **−1.376 个百分点**，95% 配对区间 **[−2.202, −0.747] 个百分点**。身体位置误差为 **35.817 / 29.087 mm**，手腕位置误差为 **37.619 / 27.051 mm**（RP1 / G1）。身体与手腕使用各侧首次失败前的窗口，root endpoint 使用共同源窗内完整回放的最后有效同步策略采样帧；七项区间按本组 5 对动作进行 10,000 次配对 bootstrap。

统计按动作等权，区间描述固定发布策略与当前动作集。30 条确定性重复保持原独立动作数。身体与手腕误差使用失败前窗口；完整指标定义、评分窗口、训练与 retarget 差异见[评测说明](DATA_PROVENANCE.md)。Phase B 正式重训尚未开始。

## 硬件模型与控制参数

冻结模型质量为 RP1 **40.726 kg**、G1 **33.741 kg**，驱动轴为 **28 / 29**。29 个解剖槽位包含 28 对同名关节；G1 的 `waist_pitch_joint` 在 RP1 列为 n/a。

表中 force caps 是仿真执行器限制，厂家额定／峰值规格保留未知。速度字段为资产声明，原生运行器未做速度包络限幅。局部轴、安装零位与有符号角端点按各模型坐标解释；RP1 训练软限由配置 factor=0.9 推导，训练 tensor 尚未直接核验，G1 原权重级历史软限未知。字段定义与单位见[评测说明](DATA_PROVENANCE.md)。

## 数据与报告

- [Common40 公开数据](data.json)
- Extreme5：[JSON](extreme5.json) / [CSV](extreme5.csv)
- 硬件模型与控制参数：[JSON](hardware.json) / [CSV](hardware.csv)
- [条件、指标与结果分析](DATA_PROVENANCE.md)
- [版本与 SHA256 清单](RELEASE_MANIFEST.json)
- [新公开视频索引](media.json)：当前 0/40。

统一报告：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。18 页 PDF 与 DOCX 已上传为版本 4，涵盖 Common40、Extreme5 与机器人参数；飞书正文正在同步核对。报告及既有同步视频需要组织访问权限。Extreme5 的 5 个视频尚未制作。

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

已有发布目录中的四个扩展附件会先按固定摘要核验，再保留到新清单。初始化新目录时，增加 `--extensions-manifest /path/to/reviewed/WEBSITE_HANDOFF_MANIFEST.json`，从已冻结交接的白名单复制附件；缺失或不符时在写入前停止。

以上命令和 SHA 对应 Common40 冻结版本。脚本核验来源，以字段白名单和精确配对交集生成其公开快照；保留行的指标、CI、分母、失败状态及身份保持一致。Extreme5 与硬件资料作为独立公开附件载入，文件摘要见[来源附录](DATA_PROVENANCE.md#附录冻结来源与-sha256)。聚合只在原输入群体完整保留时复用，科学版本变更需同步更新版本契约。

完成静态检查及桌面、手机浏览器 QA 后，提交发布白名单内的公开文件。GitHub Pages 发布源为 `main / (root)`。
