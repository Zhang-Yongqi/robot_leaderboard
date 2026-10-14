# RP1 / G1 Robot Motion Benchmark

RP1 与 G1 固定发布学生策略的离线仿真比较，主比较覆盖 **40个配对动作（N=40）**。公开表格、图表、筛选及 CSV / JSON 导出使用双方共有、条件可配对的数据。网站为 HTML / CSS / JavaScript，无构建步骤或第三方依赖。

## 评测条件

| 条件 / 执行模式 | 配对动作数 | 条件/seed 配对数 | 机器人回合数 |
| --- | ---: | ---: | ---: |
| nominal / native_position | 40 | 40 | 80 |
| explicit_sensitivity / explicit_deploy | 5 | 5 | 10 |
| repeat_nominal / native_position | 5 | 15 | 30 |
| robust_initial_velocity / native_position | 5 | 25 | 50 |

四组分别报告，共 85 个条件/seed 配对、170 条机器人回合及 8 条聚合记录，即 178 个展示行；动作去重后为 40 个。配对依据实际动作、有效条件、模式、seed 和协议身份的交集，保留阈值失败及可配对删失的 null 与原因。历史原始实验数据及旧版本保留在来源项目和 Git 历史中。

## 评测结果与分析

主比较 Progress：RP1 **79.736%**，G1 **77.269%**；RP1−G1 的 95% 配对区间为 **[−0.537, 6.980] 个百分点**，跨零。RP1 body 误差均值较低，G1 wrist 姿态误差均值较低。

统计按动作等权，区间描述固定发布策略与当前动作集。30 条确定性重复保持原独立动作数。身体与手腕误差使用失败前窗口；完整指标定义、评分窗口、训练与 retarget 差异见[评测说明](DATA_PROVENANCE.md)。Phase B 正式重训尚未开始。

## 数据与报告

- [共同动作公开数据](data.json)
- [条件、指标与结果分析](DATA_PROVENANCE.md)
- [版本与 SHA256 清单](RELEASE_MANIFEST.json)
- [新公开视频索引](media.json)：当前 0/40。

共同动作报告版本为 `common_v07_20261014`：[飞书正文](https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb)、[PDF](https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7)、[DOCX](https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce)。附件为版本 3；报告及既有同步视频需要飞书组织访问权限。

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

这些 SHA 对应当前冻结科学版本。脚本核验来源，以字段白名单和精确配对交集生成公开快照；保留行的指标、CI、分母、失败状态及身份保持一致。聚合只在原输入群体完整保留时复用，科学版本变更需同步更新版本契约。

完成静态检查及桌面、手机浏览器 QA 后，提交发布白名单内的公开文件。GitHub Pages 发布源为 `main / (root)`。
