# RP1 / G1 Robot Motion Benchmark

固定公开学生权重的离线仿真比较（Phase A）。网站使用原评测界面与经过公开字段白名单投影的数据；HTML / CSS / JavaScript 无构建步骤、无第三方依赖。

40 段共同 LAFAN40 动作在 nominal / native_position 条件下，RP1 Progress 为 79.736%，G1 为 77.269%；RP1−G1 的 95% 配对区间为 [−0.537, 6.980] 个百分点，跨零，不能据此声称 RP1 稳定优胜。RP1 body 误差较低，G1 wrist 姿态误差较低。Phase B 正式重训尚未开始。

## 阅读数据

- [科学方法、证据范围与已知缺失](DATA_PROVENANCE.md)
- [公开字段汇总](data.json)：511 行 = 18 聚合行 + 493 逐回合展示行。
- [版本及 SHA256 清单](RELEASE_MANIFEST.json)

七组双机器人共同配对未齐；单 G1、删失和缺失结果保留状态与分母，不填 0、不混合为总榜。官方 G1 自报结果独立展示，不进入本次实际复跑排名。所有飞书链接均需组织登录/权限，未扩大分享权限。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8080/`。页面只自动加载同目录 CSS、JS 和 data.json；外部来源仅在点击后访问。

## 可重复更新

每次更新使用经过审阅的冻结输入清单。先核验 aggregate 和 data SHA，然后运行标准库脚本：

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

示例 SHA 对应当前冻结版本。换版本必须先审阅科学边界、计数和方法说明并更新版本契约；脚本检查输入未变化、字段投影前后指标/CI/配对/分母完全一致，拒绝未审阅的版本与私有路径。脚本不会复制内部证据、checkpoint、数据包、环境、凭据或服务器配置。

通过检查并完成手机/桌面浏览器 QA 后，只提交此仓库的公开文件。发布源为 GitHub Pages 的 `main / (root)`；使用 `.nojekyll` 直接发布静态文件。无需部署密钥、token、第三方平台或训练环境。

本仓库仅再分发用户授权的网站源码及评测汇总；外部权重、动作原始数据、视频与报告的再分发许可不由本仓库授予。

