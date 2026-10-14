# RP1 / G1 Robot Motion Benchmark

固定公开学生权重的离线仿真比较。所有公开表格、图表、筛选及 CSV / JSON 导出仅包含 RP1 / G1 共有、条件可配对的数据。页面为 HTML / CSS / JavaScript，无构建步骤或第三方依赖。

当前范围为 **40 个共同动作、85 个条件/seed 配对、170 条回合记录和 8 条聚合记录**。178 行是展示行数，不是独立实验数。主比较 nominal / native_position 有 40 对；执行模式敏感性、重复性、初速扰动分别有 5、15、25 对，独立报告。30 条确定性重复不增加独立动作数。

主比较 Progress：RP1 79.736%，G1 77.269%；RP1−G1 的 95% 配对区间为 [−0.537, 6.980] 个百分点，跨零，不能声称 RP1 稳定优胜。RP1 body 误差较低，G1 wrist 姿态误差较低。Phase B 正式重训尚未开始。

- [共同动作公开数据](data.json)
- [指标、配对规则与科学限制](DATA_PROVENANCE.md)
- [版本与 SHA256 清单](RELEASE_MANIFEST.json)
- [新公开视频索引](media.json)：当前 0/40，本次没有上传新媒体。

配对使用实际动作、有效条件、模式、seed 和协议身份的交集，不按成功筛选。已配对的阈值失败保留；可配对的删失保留 null 和原因。历史原始实验数据及旧版本保留在来源项目和 Git 历史中。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8080/`。既有同步视频和共同动作报告使用飞书组织权限链接；本站不改变权限。

## 可重复更新

冻结来源经过审阅后，运行标准库投影脚本：

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

这些 SHA 对应当前冻结科学版本。脚本先核验来源，再以字段白名单和精确配对交集生成公开快照；保留行的指标、CI、分母、失败状态及身份不变。聚合只在原输入群体完整保留时复用，不强配或重算科学值。改变来源版本需要重新审阅科学契约。

完成静态检查、桌面/手机浏览器 QA 后，只提交公开文件。发布源为 GitHub Pages `main / (root)`，沿用现有 SSH 凭证普通 push。内部审计、原始附件、checkpoint、凭证和训练环境不发布。

新视频素材许可仍待确认；当前新片索引为空。本次只修订已有公开摘要与入口，没有新建凭证、改变访问权限或上传新媒体。
