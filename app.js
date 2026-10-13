/* Buildless, dependency-free report UI. Values and CIs always come from the data producer. */
(function () {
  "use strict";

  const METRICS = [
    { key: "body_pos_mm", label: "Body position", unit: "mm", direction: "asc", digits: 2 },
    { key: "body_ori_rad", label: "Body orientation", unit: "rad", direction: "asc", digits: 4 },
    { key: "root_pos_m", label: "Root endpoint error", unit: "m", direction: "asc", digits: 4 },
    { key: "gpu_train_hours", label: "GPU train hours", unit: "GPU·h", direction: "asc", digits: 3 },
    { key: "wrist_pos_mm", label: "Wrist position", unit: "mm", direction: "asc", digits: 2 },
    { key: "wrist_ori_rad", label: "Wrist orientation", unit: "rad", direction: "asc", digits: 4 },
    { key: "episode_return", label: "Normalized tracking return", unit: "无量纲", direction: "desc", digits: 2 },
    { key: "progress_pct", label: "Progress", unit: "%", direction: "desc", digits: 2 }
  ];
  const DATASETS = [
    ["locomotion", "MotionDecode Locomotion-80"], ["manipulation", "MotionDecode Manipulation-48"],
    ["ground", "MotionDecode Ground-60"], ["dance", "MotionDecode Dance-40"],
    ["lafan40", "Legacy LAFAN-40"], ["phuma30", "Legacy PHUMA-30"], ["root90", "Legacy Root-90"]
  ];
  const STATUS = { complete: "已记录", partial: "部分记录", pending: "待完成", blocked: "受阻", invalid: "无效", matched: "已核验一致", disclosed_difference: "已披露差异", unknown: "未知" };
  const EMPTY = {
    schema_version: 1, status: "pending", updated_utc: null,
    status_message: "等待导入经过核验的第二轮结果。当前页面不含实验结果。",
    datasets: DATASETS.map(([id, label]) => ({ id, label, expected_motions: null })),
    results: [], comparisons: [], official_references: [], fairness: [], downloads: [], notes: [],
    phases: {
      A: { label: "Phase A · 发布权重", status: "pending", description: "公开 checkpoint 的固定协议复跑。" },
      B: { label: "Phase B · 独立重训", status: "pending", description: "同配置独立重训尚未正式启动，尚无正式评测结果。" }
    },
    statistics: {
      aggregation: "展示数据生成端冻结的聚合值；浏览器不合并跨数据集、条件或 seed 的均值。",
      ci_method: "pending：等待实际协议的重采样单位、次数与样本量。",
      ci_scope: "动作条件区间与训练 seed 总体区间必须明确区分。",
      missing_policy: "缺失、无效与删失保留原因和分母；n/a 不视为零。",
      rank_policy: "仅在相同协议、指标有效样本身份、共同覆盖且预期参与者齐全的组内排名。",
      limitations: []
    }
  };
  const state = { data: EMPTY, scope: "aggregate", metric: METRICS[0].key, direction: "asc", page: 1, pageSize: 25, origin: "pending", issues: [] };
  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const isNumber = (value) => typeof value === "number" && Number.isFinite(value);
  const asArray = (value) => Array.isArray(value) ? value : [];
  const showText = (value, fallback = "pending") => value == null || value === "" ? fallback : String(value);
  const metricDefinition = (key) => METRICS.find((metric) => metric.key === key) || METRICS[0];
  const valueOf = (row, key) => row.metrics && row.metrics[key] && isNumber(row.metrics[key].value) ? row.metrics[key].value : null;
  const sha256 = (value) => typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
  const fmt = (value, digits = 2) => isNumber(value) ? value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }) : "n/a";
  const knownCount = (value) => Number.isInteger(value) && value >= 0;
  const coverageText = (coverage) => {
    const c = coverage || {};
    return `${knownCount(c.numerator) ? c.numerator.toLocaleString("en-US") : "?"} / ${knownCount(c.denominator) ? c.denominator.toLocaleString("en-US") : "?"} ${showText(c.unit, "样本")}`;
  };
  const statusBadge = (status) => `<span class="badge ${Object.hasOwn(STATUS, status) ? escape(status) : "unknown"}">${escape(STATUS[status] || status || "pending")}</span>`;
  const datasetLabel = (id) => ((state.data.datasets || []).find((item) => item.id === id) || {}).label || id || "pending";
  const phaseLabel = (phase) => phase === "A" ? "原版发布策略" : phase === "B" ? "同配置重训" : "来源未知";
  function safeURL(value) {
    if (typeof value !== "string" || !value.trim()) return null;
    try {
      const url = new URL(value, window.location.href);
      return ["https:", "http:", "file:"].includes(url.protocol) ? url.href : null;
    } catch (_) { return null; }
  }
  function linkHTML(link, fallback = "原始记录") {
    if (!link) return "";
    const url = safeURL(link.url);
    const requiresPermission = url && /(^|\.)feishu\.cn$/i.test(new URL(url).hostname);
    const permissionLabel = requiresPermission ? "（需组织权限）" : "";
    const label = String(link.label || fallback).replace(/版本与文件 SHA256 清单/g, "发布版本清单");
    const displayLabel = label + (requiresPermission && !label.includes("需组织权限") ? permissionLabel : "");
    const permissionTitle = requiresPermission ? ' title="需组织登录及已有访问权限；本站不改变文件分享权限"' : "";
    // Only the packager's closed registry can issue attachment URLs. safeURL
    // keeps rejecting arbitrary blob:/data: values supplied by page data.
    const registry = window.LeaderboardAttachments;
    const attachment = registry && typeof registry.get === "function" ? registry.get(link.url, link.sha256) : null;
    if (attachment && attachment.original_url === link.url && attachment.sha256 === link.sha256 &&
        typeof registry.isTrusted === "function" && registry.isTrusted(attachment)) {
      const source = attachment.external && safeURL(link.url);
      return `<a href="${escape(attachment.href)}" download="${escape(attachment.download_name)}" data-original-url="${escape(link.url)}" data-source-sha256="${escape(attachment.sha256)}" title="离线附件">${escape(label)} ↓</a>${source ? ` <a href="${escape(source)}" target="_blank" rel="noopener noreferrer"${permissionTitle}>在线来源${permissionLabel} ↗</a>` : ""}`;
    }
    return url ? `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer"${permissionTitle}>${escape(displayLabel)} ↗</a>` : `<span class="metric-detail">${escape(label)}：链接不可用</span>`;
  }
  function emptyHTML(title, description) {
    return `<div class="empty-state"><strong>${escape(title)}</strong>${escape(description)}</div>`;
  }
  function normalizeData(input) {
    if (!input || typeof input !== "object" || Array.isArray(input) || input.schema_version !== 1) throw new Error("数据格式不兼容；需要 schema_version: 1。");
    ["results", "comparisons", "official_references", "fairness", "datasets"].forEach((key) => {
      if (!Array.isArray(input[key])) throw new Error(`缺少数组 ${key}，请按 DATA_SCHEMA.json 生成快照。`);
    });
    const issues = [];
    const seen = new Set();
    input.results.forEach((row, index) => {
      if (!row || typeof row !== "object" || typeof row.id !== "string" || seen.has(row.id)) throw new Error(`results[${index}] 缺少唯一 id；拒绝展示不确定的重复记录。`);
      seen.add(row.id);
      if (!["A", "B"].includes(row.phase) || !["aggregate", "per_motion"].includes(row.scope)) throw new Error(`记录 ${row.id} 的 phase 或 scope 不符合接口。`);
      METRICS.forEach(({ key }) => {
        const cell = (row.metrics || {})[key];
        if (!cell || (!isNumber(cell.value) && !cell.reason)) issues.push(`${row.id}/${key}：缺失数值或 n/a 原因`);
        if (cell && cell.value != null && !isNumber(cell.value)) issues.push(`${row.id}/${key}：非有限数值被显示为 n/a`);
      });
    });
    state.issues = issues;
    return Object.assign({}, EMPTY, input, { phases: Object.assign({}, EMPTY.phases, input.phases || {}), statistics: Object.assign({}, EMPTY.statistics, input.statistics || {}) });
  }
  function filters() {
    return Object.fromEntries(["phase", "robot", "dataset", "condition", "mode", "seed", "search"].map((key) => [key, $("filter-" + key).value]));
  }
  function filteredRows(scope = state.scope) {
    const selected = filters();
    const query = selected.search.trim().toLowerCase();
    return state.data.results.filter((row) => {
      if (row.scope !== scope) return false;
      if (["phase", "robot", "dataset", "condition", "mode", "seed"].some((key) => selected[key] !== "all" && String(row[key]) !== selected[key])) return false;
      return !query || [row.label, row.motion_id, row.id, (row.checkpoint || {}).name].some((value) => String(value || "").toLowerCase().includes(query));
    });
  }
  function compareRows(a, b) {
    const aValue = valueOf(a, state.metric), bValue = valueOf(b, state.metric);
    if (aValue === null && bValue !== null) return 1;
    if (bValue === null && aValue !== null) return -1;
    const difference = aValue === null ? 0 : (aValue - bValue) * (state.direction === "asc" ? 1 : -1);
    return difference || String(a.dataset).localeCompare(String(b.dataset)) || String(a.id).localeCompare(String(b.id));
  }
  /* Compute rank only within an explicitly declared complete paired group. Never infer pairing from names. */
  function ranksForMetric(data, key) {
    const output = new Map();
    const definition = metricDefinition(key);
    data.results.forEach((row) => output.set(row.id, { rank: null, reason: "未核验共同配对" }));
    asArray(data.comparisons).forEach((comparison) => {
      const ids = asArray(comparison.expected_participants);
      const members = ids.map((id) => data.results.find((row) => row.id === id)).filter(Boolean);
      let reason = "";
      if (!comparison.verified || !sha256(comparison.sample_set_sha256)) reason = comparison.reason || "配对身份待核验";
      else if (ids.length < 2 || new Set(ids).size !== ids.length || members.length !== ids.length) reason = "预期对照记录未齐全";
      else {
        const first = members[0];
        const signature = (row) => JSON.stringify([row.phase, row.scope, row.dataset, row.condition, row.mode, String(row.seed), row.motion_id || null]);
        if (members.some((row) => signature(row) !== signature(first))) reason = "阶段 / 协议粒度不一致";
        else if (members.some((row) => row.status !== "complete")) reason = "对照包含未完成记录";
        else if (members.some((row) => !row.pairing || !row.pairing.verified || row.pairing.comparison_id !== comparison.id || row.pairing.sample_set_sha256 !== comparison.sample_set_sha256)) reason = "配对样本 SHA256 不一致";
        else if (members.some((row) => valueOf(row, key) === null)) reason = "对照指标存在 n/a";
        else if (members.some((row) => row.metrics[key].sample_set_sha256 !== comparison.sample_set_sha256)) reason = "指标有效样本未证实配对";
        else {
          const paired = first.paired_coverage || {}, metricCoverage = first.metrics[key].coverage || {};
          if (!knownCount(paired.numerator) || paired.numerator < 1 || !knownCount(paired.denominator) || paired.denominator < paired.numerator) reason = "共同覆盖分母待核验";
          else if (!knownCount(metricCoverage.numerator) || metricCoverage.numerator < 1 || metricCoverage.numerator !== metricCoverage.denominator) reason = "指标共同覆盖不完整";
          else if (members.some((row) => {
            const p = row.paired_coverage || {}, m = row.metrics[key].coverage || {};
            return p.numerator !== paired.numerator || p.denominator !== paired.denominator || p.unit !== paired.unit || m.numerator !== metricCoverage.numerator || m.denominator !== metricCoverage.denominator || m.unit !== metricCoverage.unit;
          })) reason = "有效覆盖分子 / 分母不一致";
        }
      }
      members.forEach((row) => {
        const rank = reason ? null : 1 + members.filter((other) => definition.direction === "asc" ? valueOf(other, key) < valueOf(row, key) : valueOf(other, key) > valueOf(row, key)).length;
        output.set(row.id, { rank, reason: reason || comparison.label || comparison.id, comparison: comparison.id });
      });
    });
    return output;
  }
  function metricHTML(row, metric) {
    const cell = (row.metrics || {})[metric.key] || {};
    const value = valueOf(row, metric.key);
    const ci = cell.ci || {};
    const ciValid = isNumber(ci.low) && isNumber(ci.high) && ci.low <= ci.high;
    let ciLabel = ciValid ? `${isNumber(ci.level) ? fmt(ci.level * 100, 0) + "% " : ""}CI [${fmt(ci.low, metric.digits)}, ${fmt(ci.high, metric.digits)}]` : `CI n/a · ${ci.reason || "未提供有效区间"}`;
    const ciTitle = [ci.method, ci.resampling_unit && `重采样单位 ${ci.resampling_unit}`, knownCount(ci.n_clusters) && `${ci.n_clusters} clusters`, knownCount(ci.n_seeds) && `${ci.n_seeds} seeds`].filter(Boolean).join("；");
    return `<td class="metric ${state.metric === metric.key ? "highlight" : ""}">${value === null ? `<span class="metric-na">n/a</span><span class="metric-detail reason">${escape(cell.reason || "未提供数值与原因")}</span>` : `<span class="metric-value">${fmt(value, metric.digits)}</span>${cell.reason ? `<span class="metric-detail">${escape(cell.reason)}</span>` : ""}`}<span class="metric-detail">有效 ${escape(coverageText(cell.coverage))}</span><span class="metric-detail" title="${escape(ciTitle)}">${escape(ciLabel)}</span></td>`;
  }
  function rowEvidence(row) {
    const provenance = row.provenance || {}, checkpoint = row.checkpoint || {};
    const notes = asArray(row.notes).map(readerNote).filter(Boolean);
    return `<details><summary>策略、条件与视频</summary><div class="record-evidence"><p>${escape(checkpoint.name || "策略身份待提供")}</p><p>评测环境：${escape(provenance.runtime || "待提供")}</p>${notes.map((note) => `<p>${escape(note)}</p>`).join("")}${asArray(row.videos).map((video) => `${linkHTML(video, "视频")}<p>${video.synchronized ? "共同时间轴对比" : "单机示例"} · ${escape(String(video.description || "视频仅为个例证据").replace(/SHA 为本地原视频；云端原文件未下载做字节哈希。\s*/g, ""))}</p>`).join("")}</div></details>`;
  }
  function readerNote(note) {
    const text = String(note);
    if (text.startsWith("源数据注记")) {
      try {
        const metadata = JSON.parse(text.slice(text.indexOf("{")));
        const status = metadata.metadata_status;
        return status === "metadata_inferred" || asArray(status).includes("metadata_inferred") ? "此数据集使用补推元信息，非原生 metadata。" : "";
      } catch (_) { return ""; }
    }
    if (/SHA|sha256|manifest|comparisons\[|字段白名单|内部附件|原始附录|云端仅确认/.test(text)) return "";
    if (text.includes("飞书完整报告")) return "飞书报告与视频需组织登录及已有访问权限。";
    return text.replace(/aligned_nominal/g, "对齐名义条件").replace(/逐字节确定性一致/g, "结果完全一致");
  }
  function renderHeaders() {
    $("results-head").innerHTML = `<tr><th scope="col">组内名次<span class="unit">按所选指标</span></th><th scope="col">策略 / 动作<span class="unit">阶段 · 机器人 · 条件</span></th><th scope="col">覆盖<span class="unit">已评 / 计划；共同 / 母集</span></th>${METRICS.map((metric) => `<th scope="col" aria-sort="${state.metric === metric.key ? (state.direction === "asc" ? "ascending" : "descending") : "none"}"><button type="button" data-sort="${metric.key}" title="按 ${escape(metric.label)} 排序">${metric.label} ${state.metric === metric.key ? state.direction === "asc" ? "↑" : "↓" : "↕"}<span class="unit">${metric.unit} · ${metric.direction === "asc" ? "越低越好 ↓" : "越高越好 ↑"}</span></button></th>`).join("")}</tr>`;
    $("reference-head").innerHTML = `<tr><th scope="col">官方来源 / 条件</th><th scope="col">来源覆盖</th>${METRICS.map((metric) => `<th scope="col">${metric.label}<span class="unit">${metric.unit}</span></th>`).join("")}</tr>`;
  }
  function renderRows(rows, ranks) {
    const pages = Math.max(1, Math.ceil(rows.length / state.pageSize));
    state.page = Math.min(state.page, pages);
    const current = rows.slice((state.page - 1) * state.pageSize, state.page * state.pageSize);
    $("results-body").innerHTML = current.length ? current.map((row) => {
      const ranking = ranks.get(row.id) || { rank: null, reason: "未核验共同配对" };
      const rankDescription = String(ranking.reason).replace(/SHA256/g, "身份");
      return `<tr><td class="rank-cell"><span class="rank-number">${ranking.rank === null ? "—" : ranking.rank}</span><span class="rank-note" title="${escape(rankDescription)}">${escape(ranking.rank === null ? rankDescription : "同条件配对")}</span></td><td class="row-heading"><div class="record-label">${escape(row.label)}</div>${row.scope === "per_motion" ? `<span class="record-meta">${escape(row.motion_id || "动作 ID 待提供")}</span>` : ""}<span class="record-meta">${escape(datasetLabel(row.dataset))}</span><span class="record-meta">${escape(row.condition)} · ${escape(row.mode)} · seed ${escape(row.seed)}</span><div class="record-badges"><span class="badge">${escape(String(row.robot).toUpperCase())}</span><span class="badge">${escape(phaseLabel(row.phase))}</span>${statusBadge(row.status)}</div>${row.status_reason ? `<span class="record-meta">${escape(row.status_reason)}</span>` : ""}${rowEvidence(row)}</td><td><span class="coverage-primary">${escape(coverageText(row.coverage))}</span><span class="coverage-secondary">共同 ${escape(coverageText(row.paired_coverage))}</span><span class="coverage-secondary">${escape((row.coverage || {}).reason || "")}</span><span class="coverage-secondary">${escape((row.paired_coverage || {}).reason || "")}</span></td>${METRICS.map((metric) => metricHTML(row, metric)).join("")}</tr>`;
    }).join("") : `<tr><td class="empty-cell" colspan="11"><strong>${state.data.results.length ? "当前筛选没有匹配记录" : "PENDING · 等待实测结果"}</strong><p>${state.data.results.length ? "可切换结果粒度或重置筛选；界面不会从其他条件补入数值。" : "导入带有 checkpoint、有效配置、原始记录和分母的 data.json 后显示。当前未生成任何示例成绩。"}</p></td></tr>`;
    $("pagination").innerHTML = pages > 1 ? `<span>第 ${state.page} / ${pages} 页 · 每页 ${state.pageSize} 条</span><button type="button" data-page="${state.page - 1}" ${state.page === 1 ? "disabled" : ""}>上一页</button><button type="button" data-page="${state.page + 1}" ${state.page === pages ? "disabled" : ""}>下一页</button>` : "";
    const ranked = rows.filter((row) => (ranks.get(row.id) || {}).rank != null).length;
    $("result-count").textContent = `${rows.length} 条${state.scope === "aggregate" ? "聚合" : "逐动作"}记录 · ${ranked} 条可作组内排名 · n/a 始终排在末尾 · 名次按完整配对组计算，筛选单个机器人不会重排名次`;
    $("download-csv").disabled = !rows.length;
  }
  function renderOverview() {
    const summary = pairedSummaryFor(state.data);
    $("overview").innerHTML = summary ? `<div class="scope-item"><strong>40</strong><p><b>共同动作</b>RP1 与 G1 的主要配对范围</p></div><div class="scope-item"><strong>318</strong><p><b>G1 补充动作</b>单系统覆盖，不做双机器人排名</p></div><div class="scope-item"><strong>27 / 26</strong><p><b>未触发失败阈值</b>RP1 / G1，各以 40 动作为分母</p></div>` : emptyHTML("配对结果待核验", "尚未读取可支持结论的完整共同动作组。");
  }
  function pairedSummaryFor(data) {
    const keys = ["progress_pct", "body_pos_mm", "body_ori_rad", "wrist_ori_rad"];
    const ranks = keys.map((key) => ranksForMetric(data, key));
    for (const comparison of asArray(data.comparisons)) {
      const members = asArray(comparison.expected_participants).map((id) => data.results.find((row) => row.id === id));
      if (members.length !== 2 || members.some((row) => !row || row.phase !== "A" || row.scope !== "aggregate" || row.dataset !== "lafan40" || row.condition !== "nominal" || row.mode !== "native_position")) continue;
      const rp1 = members.find((row) => String(row.robot).toLowerCase() === "rp1");
      const g1 = members.find((row) => String(row.robot).toLowerCase() === "g1");
      if (!rp1 || !g1 || members.some((row) => (row.paired_coverage || {}).numerator !== 40 || (row.paired_coverage || {}).denominator !== 40)) continue;
      if (ranks.some((ranking) => members.some((row) => !(ranking.get(row.id) || {}).rank || ranking.get(row.id).comparison !== comparison.id))) continue;
      const delta = (comparison.paired_deltas || {}).progress_pct || {};
      if (!isNumber(delta.value) || delta.n_motions !== 40 || !Array.isArray(delta.ci95) || delta.ci95.length !== 2 || !delta.ci95.every(isNumber) || delta.ci95[0] > delta.ci95[1]) continue;
      return { rp1, g1, comparison, delta, crossesZero: delta.ci95[0] <= 0 && delta.ci95[1] >= 0 };
    }
    return null;
  }
  const CN_METRICS = { body_pos_mm: "身体位置误差", body_ori_rad: "身体姿态误差", wrist_ori_rad: "手腕姿态误差", wrist_pos_mm: "手腕位置误差", root_pos_m: "根节点端点误差", episode_return: "归一化跟踪回报", progress_pct: "动作完成度" };
  const signed = (value, digits) => `${value > 0 ? "+" : ""}${fmt(value, digits)}`;
  function pairedIntervalSVG(delta, digits, unit, dark = false) {
    const bound = Math.max(Math.abs(delta.ci95[0]), Math.abs(delta.ci95[1]), Math.abs(delta.value)) * 1.18 || 1;
    const x = (v) => 155 + v / bound * 129;
    const color = dark ? "#bfcee3" : delta.value < 0 ? "#4387f5" : "#159b80";
    return `<svg class="${dark ? "hero-ci" : "ci-svg"}" viewBox="0 0 310 74" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RP1 减 G1 差值 ${escape(signed(delta.value, digits))} ${escape(unit)}，95% 置信区间 ${escape(fmt(delta.ci95[0], digits))} 至 ${escape(fmt(delta.ci95[1], digits))}"><line x1="26" y1="28" x2="284" y2="28" stroke="${dark ? "#46536b" : "#e0e6ef"}"/><line x1="155" y1="7" x2="155" y2="43" stroke="${dark ? "#889bb8" : "#7c8ca3"}" stroke-dasharray="3 3"/><line x1="${x(delta.ci95[0])}" y1="28" x2="${x(delta.ci95[1])}" y2="28" stroke="${color}" stroke-width="4" stroke-linecap="round"/><line x1="${x(delta.ci95[0])}" y1="21" x2="${x(delta.ci95[0])}" y2="35" stroke="${color}"/><line x1="${x(delta.ci95[1])}" y1="21" x2="${x(delta.ci95[1])}" y2="35" stroke="${color}"/><circle cx="${x(delta.value)}" cy="28" r="5" fill="${color}" stroke="${dark ? "#101c30" : "white"}" stroke-width="2"/><text x="26" y="60">−${escape(fmt(bound, digits))}</text><text x="155" y="60" text-anchor="middle">0</text><text x="284" y="60" text-anchor="end">+${escape(fmt(bound, digits))} ${escape(unit)}</text></svg>`;
  }
  function renderPairedSummary() {
    const summary = pairedSummaryFor(state.data);
    if (!summary) {
      $("hero-chart").innerHTML = emptyHTML("配对摘要待核验", "尚未读取完整共同动作组。");
      $("paired-summary").innerHTML = ""; $("paired-all-metrics").innerHTML = ""; return;
    }
    const { rp1, g1, comparison, delta, crossesZero } = summary;
    $("hero-chart").innerHTML = `<p class="eyebrow">COMPLETION / 40 PAIRED MOTIONS</p><h2>完成度接近，差值仍跨零。</h2><p class="chart-context">平均动作推进比例 · 数值越高越好</p>${[rp1,g1].map((row) => `<div class="progress-row"><div class="progress-label"><span><i class="dot ${row.robot}"></i>${String(row.robot).toUpperCase()}</span><strong>${fmt(valueOf(row,"progress_pct"),2)}<small>%</small></strong></div><div class="progress-track" aria-hidden="true"><div class="progress-fill ${row.robot}" style="width:${valueOf(row,"progress_pct")}%"></div></div></div>`).join("")}<div class="hero-delta"><p>RP1 − G1 <strong>${signed(delta.value,2)}<small> pp</small></strong></p><p class="ci-text">95% CI [${fmt(delta.ci95[0],2)}, ${fmt(delta.ci95[1],2)}] pp · N = 40</p>${pairedIntervalSVG(delta,2,"pp",true)}<p class="hero-conclusion">${crossesZero ? "区间跨零，无法据此认定完成度稳定优胜。" : "推断范围限于当前固定策略与共同动作。"}</p></div>`;
    const conclusions = {body_pos_mm:"RP1 均值较低 · 区间上界接近零",body_ori_rad:"RP1 身体姿态误差较低",wrist_ori_rad:"G1 手腕姿态误差较低"};
    $("paired-summary").innerHTML = ["body_pos_mm","body_ori_rad","wrist_ori_rad"].map((key) => {
      const m=metricDefinition(key), d=comparison.paired_deltas[key];
      return `<article class="finding-card"><h3>${CN_METRICS[key]}</h3><p class="metric-caption">${m.label} · 越低越好 · N = ${d.n_motions}</p><div class="finding-values">${[rp1,g1].map(row=>`<div><span><i class="dot ${row.robot}"></i>${String(row.robot).toUpperCase()}</span><strong>${fmt(valueOf(row,key),m.digits)}<small>${m.unit}</small></strong></div>`).join("")}</div><p class="delta-label">配对差值 RP1 − G1</p>${pairedIntervalSVG(d,m.digits,m.unit)}<p class="delta-ci">${signed(d.value,m.digits)} ${m.unit} · 95% CI [${fmt(d.ci95[0],m.digits)}, ${fmt(d.ci95[1],m.digits)}]</p><p class="finding-interpretation">${conclusions[key]}</p></article>`;
    }).join("");
    $("paired-all-metrics").innerHTML = `<table class="paired-table"><caption class="sr-only">共同 40 动作，RP1 减 G1 配对差值及 95% 置信区间</caption><thead><tr><th>指标</th><th>单位</th><th>RP1 均值</th><th>G1 均值</th><th>RP1 − G1</th><th>95% CI</th><th>N</th></tr></thead><tbody>${METRICS.filter(m=>comparison.paired_deltas[m.key]).map(m=>{const d=comparison.paired_deltas[m.key];return `<tr><td>${CN_METRICS[m.key]}</td><td>${m.unit}</td><td class="number">${fmt(valueOf(rp1,m.key),m.digits)}</td><td class="number">${fmt(valueOf(g1,m.key),m.digits)}</td><td class="number">${signed(d.value,m.digits)} ${d.unit==="pp"?"pp":""}</td><td class="number">[${fmt(d.ci95[0],m.digits)}, ${fmt(d.ci95[1],m.digits)}] ${d.unit==="pp"?"pp":m.unit}</td><td>${d.n_motions}</td></tr>`}).join("")}</tbody></table>`;
  }
  function renderMotionChart() {
    const metric = metricDefinition(state.metric);
    const source = filteredRows("per_motion"), valid = source.filter((row) => valueOf(row, state.metric) !== null).sort(compareRows);
    $("motion-chart-description").textContent = `${metric.label} · ${metric.unit} · ${metric.direction === "asc" ? "越低越好" : "越高越好"}。图按当前列表方向排序，跨组不产生名次。`;
    if (!valid.length) {
      $("motion-chart").innerHTML = emptyHTML("逐动作记录待提供", source.length ? "该指标没有有效值；具体原因保留在逐动作表格。" : "图表只读取 per_motion 记录，不从聚合均值推造分布。");
      return;
    }
    const rows = valid.slice(0, 36), values = rows.map((row) => valueOf(row, state.metric));
    const min = Math.min(0, ...values), max = Math.max(0, ...values), range = max - min || 1;
    const left = 238, right = 658, top = 27, rowHeight = 31, bottom = top + rows.length * rowHeight + 13;
    const x = (value) => left + (value - min) / range * (right - left);
    const color = (row) => String(row.robot).toLowerCase() === "rp1" ? "#4387f5" : "#159b80";
    let svg = `<svg class="motion-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 ${bottom + 32}" role="img" aria-labelledby="motion-svg-title motion-svg-description"><title id="motion-svg-title">逐动作 ${escape(metric.label)}</title><desc id="motion-svg-description">当前筛选 ${valid.length} 个有效值，显示排序后的前 ${rows.length} 条。完整数值和原始分母见逐动作表格。</desc>`;
    for (let i = 0; i <= 4; i += 1) {
      const position = left + i * (right - left) / 4, value = min + i * range / 4;
      svg += `<line x1="${position}" y1="${top - 12}" x2="${position}" y2="${bottom}" stroke="#e3eaf3"/><text x="${position}" y="${bottom + 22}" text-anchor="middle" fill="#697c96" font-size="10">${escape(fmt(value, metric.digits))}</text>`;
    }
    rows.forEach((row, index) => {
      const y = top + index * rowHeight + 7, value = valueOf(row, state.metric), label = `${String(row.robot).toUpperCase()} · ${row.motion_id || row.id}`, short = label.length > 34 ? label.slice(0, 31) + "…" : label;
      svg += `<g><title>${escape(`${label}; ${row.condition}; ${row.mode}; seed ${row.seed}; ${fmt(value, metric.digits)} ${metric.unit}; ${coverageText((row.metrics[state.metric] || {}).coverage)}`)}</title><text x="0" y="${y + 4}" font-size="11" fill="#50647f">${escape(short)}</text><line x1="${x(0)}" y1="${y}" x2="${x(value)}" y2="${y}" stroke="${color(row)}" stroke-opacity=".25" stroke-width="5"/><circle cx="${x(value)}" cy="${y}" r="4" fill="${color(row)}"/><text x="752" y="${y + 4}" text-anchor="end" font-size="11" fill="#263e5d">${escape(fmt(value, metric.digits))}</text></g>`;
    });
    svg += "</svg>";
    $("motion-chart").innerHTML = `<div class="legend"><span style="--dot:#4387f5">RP1</span><span style="--dot:#159b80">G1 / 其他</span></div>${svg}<p class="chart-note">显示 ${rows.length} / ${valid.length} 个有效值；另有 ${source.length - valid.length} 条 n/a。${valid.length > rows.length ? "图表截取前 36 条，完整记录可在逐动作表格或 CSV 中查看。" : "悬停点查看动作、条件、模式、seed 和分母；键盘用户可访问上方数据表。"}</p>`;
  }
  function renderFailures(rows) {
    const available = rows.filter((row) => asArray(row.failures).length);
    if (!available.length) {
      $("failure-chart").innerHTML = emptyHTML("失败分布待提供", "未提供失败记录不等于零失败；缺失、无效和删失应保留在原始分母中。");
      return;
    }
    $("failure-chart").innerHTML = available.slice(0, 8).map((row) => `<div class="failure-record"><p class="failure-title">${escape(row.label)}<small>${escape([datasetLabel(row.dataset), row.motion_id, row.condition, row.mode, "seed " + row.seed].filter(Boolean).join(" · "))}</small></p>${row.failures.map((failure) => {
      const valid = knownCount(failure.count) && knownCount(failure.denominator) && failure.count <= failure.denominator;
      const ratio = valid && failure.denominator > 0 ? failure.count / failure.denominator : 0;
      return `<div class="failure-line"><span>${escape(failure.reason)}</span><div class="failure-track" aria-hidden="true"><div class="failure-fill" style="width:${100 * ratio}%"></div></div><span class="failure-count">${valid ? `${failure.count} / ${failure.denominator}` : "n/a"}<span class="metric-detail">${escape(failure.unit || "样本")}</span></span></div>`;
    }).join("")}</div>`).join("") + `<p class="chart-note">显示 ${Math.min(8, available.length)} / ${available.length} 条有失败分类的记录。分类是否互斥以协议为准；不将不同分类求和解释为总失败率。</p>`;
  }
  function renderReferences() {
    const dataset = $("filter-dataset").value;
    const rows = state.data.official_references.filter((row) => dataset === "all" || row.dataset === dataset);
    $("reference-body").innerHTML = rows.length ? rows.map((row) => `<tr><td class="row-heading"><div class="record-label">${escape(row.label)}</div><span class="record-meta">${escape(String(row.robot).toUpperCase())} · ${escape(datasetLabel(row.dataset))}</span>${linkHTML(row.source, "官方原始来源")}<p class="reference-context">${escape(row.context || "来源条件待提供")}</p></td><td><span class="coverage-primary">${escape(coverageText(row.coverage))}</span><span class="coverage-secondary">${escape((row.coverage || {}).reason || "")}</span><span class="badge">不参与复跑排名</span></td>${METRICS.map((metric) => metricHTML(row, metric)).join("")}</tr>`).join("") : `<tr><td class="empty-cell" colspan="10"><strong>官方来源待核验</strong><p>外部官方值在独立区展示。没有来源、条件与覆盖信息时，不填入参考数字。</p></td></tr>`;
  }
  function renderFairness() {
    const selected = filters();
    const rows = state.data.fairness.filter((row) => ["phase", "condition", "mode"].every((key) => !row[key] || row[key] === "all" || selected[key] === "all" || row[key] === selected[key]));
    $("fairness-body").innerHTML = rows.length ? rows.map((row) => `<tr><td>${escape(row.item)}${row.phase && row.phase !== "all" ? `<span class="record-meta">${escape(phaseLabel(row.phase))}</span>` : ""}</td><td>${escape(row.rp1)}</td><td>${escape(row.g1)}</td><td>${statusBadge(row.status)}</td><td>${escape(String(row.evidence || "待提供").replace(/每回合 manifest；/g, ""))}</td></tr>`).join("") : `<tr><td colspan="5" class="empty-cell"><strong>公平条件核验待导入</strong><p>应逐项提供 runtime、执行器、控制 / 物理步长、初态、终止、seed、训练预算、归一化器及 retarget 身份。</p></td></tr>`;
  }
  function renderEvidence() {
    const statistics = state.data.statistics;
    $("statistics").innerHTML = [["聚合口径", "aggregation"], ["CI 方法", "ci_method"], ["推断范围", "ci_scope"], ["缺失处理", "missing_policy"], ["排名条件", "rank_policy"]].map(([label, key]) => `<dt>${label}</dt><dd>${escape(statistics[key] || "待提供")}</dd>`).join("");
    const all=asArray(state.data.downloads), reports=all.filter(d=>/feishu\.cn\/(docx|file)\//.test(d.url)&&/技术报告/.test(d.label));
    $("downloads").innerHTML = `<p>${reports.map(linkHTML).join(" ")}</p><p>专业改写版正文、PDF / DOCX v2（10 页）均已核验更新；飞书链接需组织权限。</p>`;
    const historical=all.filter(d=>!reports.includes(d)&&/feishu\.cn/.test(d.url));
    $("historical-links").innerHTML = `<p>以下为既有组织内报告附录与历史素材，不是本次新增的公开高分辨率视频。原始云端附录尚未全部验收。</p>${historical.map(d=>`<div class="historical-item">${linkHTML(d)}</div>`).join("")}`;
    const notes = [...asArray(statistics.limitations), ...asArray(state.data.notes)].map(readerNote).filter(Boolean);
    $("limitations").innerHTML = notes.map((note) => `<li>${escape(note)}</li>`).join("");
  }
  function validPublicMedia(input) {
    if (!input || input.schema !== "rp1-g1-public-media-v1" || input.expected_common_motions !== 40 || !Array.isArray(input.items)) throw new Error("媒体索引格式待核验");
    const common = new Set(state.data.results.filter(r=>r.scope==="per_motion"&&r.robot==="rp1"&&r.dataset==="lafan40"&&r.condition==="nominal"&&r.mode==="native_position"&&r.seed===0).map(r=>r.motion_id));
    const seen=new Set();
    input.items.forEach(item=>{
      if(!common.has(item.motion_id)||seen.has(item.motion_id)||item.public_release_approved!==true||item.is_new_render!==true||item.full_episode!==true||item.width!==1920||item.height!==1080||!isNumber(item.duration_s)||item.duration_s<=0||!isNumber(item.fps)||!sha256(item.sha256)) throw new Error("媒体身份、授权或完整回放待核验");
      seen.add(item.motion_id);
      const url=new URL(item.url,window.location.href), poster=new URL(item.poster,window.location.href);
      if(url.protocol!=="https:"||url.hostname!=="github.com"||!url.pathname.startsWith("/Zhang-Yongqi/robot_leaderboard/releases/download/")||poster.origin!==window.location.origin||!poster.pathname.includes("/media/posters/")||!item.poster.match(/^\.\/media\/posters\/[a-zA-Z0-9_.-]+\.(?:jpg|webp|png)$/)) throw new Error("媒体公开地址待核验");
      if(typeof item.label!=="string"||typeof item.credits!=="string"||typeof item.restrictions!=="string"||!Array.isArray(item.source_result_ids)||item.source_result_ids.length!==2)throw new Error("媒体来源或署名待核验");
      const rows=item.source_result_ids.map(id=>state.data.results.find(r=>r.id===id));
      if(rows.some(r=>!r||r.motion_id!==item.motion_id||r.scope!=="per_motion"||r.dataset!=="lafan40"||r.mode!=="native_position"||!["nominal","aligned_nominal"].includes(r.condition)||r.seed!==0)||new Set(rows.map(r=>r.robot)).size!==2)throw new Error("媒体源回合不属于共同主选择");
    });return input;
  }
  function selectPublicVideo(item) {
    const time=`${Math.floor(item.duration_s/60)}:${String(Math.round(item.duration_s%60)).padStart(2,"0")}`;
    $("video-feature").innerHTML = `<video id="paired-video" class="video-player" controls preload="none" playsinline poster="${escape(item.poster)}"><source src="${escape(item.url)}" type="video/mp4">此浏览器无法播放视频。请使用下方 MP4 下载。</video><div class="video-info"><p class="eyebrow">RP1 / G1 · FULL EPISODE</p><h3>${escape(item.label)}</h3><p class="video-meta">1920 × 1080 · ${escape(fmt(item.fps,0))} fps · ${time} · 1×</p><p>${escape(item.description||"左 RP1 / 右 G1；共同时间轴的完整状态回放。")}</p><a href="${escape(item.url)}">下载完整 MP4 ↗</a><p class="video-credits">${escape(item.credits)} ${escape(item.restrictions)}</p><p id="media-error" class="media-error" role="status"></p></div>`;
    $("paired-video").addEventListener("error",()=>{$("media-error").textContent="视频暂时无法加载，可尝试下载 MP4。";});
    document.querySelectorAll(".video-choice").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.motion===item.motion_id)));
  }
  async function renderPublicMedia() {
    const pending=()=>{document.querySelector(".hero-actions .button").textContent="动作回放计划 ↗";$("video-coverage").textContent="0 / 40 新片已发布";$("public-videos").innerHTML=`<div class="video-pending"><strong>共同 40 动作<br>高分辨率回放待交付。</strong><p>新一批 4K 原生渲染与 1080p 网页视频尚未完成。当前没有可公开播放的新片。<br>组织内历史素材可在下方“历史报告与视频”查看。</p></div>`;};
    pending();
    try {
      const response=await fetch("./media.json",{cache:"no-store",credentials:"same-origin"});
      if(!response.ok)throw new Error("媒体索引读取失败");
      const media=validPublicMedia(await response.json()); if(!media.items.length)return;
      $("video-coverage").textContent=`${media.items.length} / 40 新片已发布`;document.querySelector(".hero-actions .button").textContent="查看同步动作 ↗";$("video-intro").textContent="左侧 RP1，右侧 G1。同一动作、共同时间轴与相机尺度；完整回放保留真实失败后的过程。";
      $("public-videos").innerHTML=`<div id="video-feature" class="video-main"></div><form class="video-filter" id="video-filter"><label>查找共同动作<input id="video-search" type="search" placeholder="输入动作名称" autocomplete="off"></label></form><div id="video-grid" class="video-grid"></div><p class="video-credits">${escape(media.credits||"")}</p>`;
      const gallery=()=>{const q=$("video-search").value.trim().toLowerCase();const items=media.items.filter(i=>(i.label+" "+i.motion_id).toLowerCase().includes(q));$("video-grid").innerHTML=items.map(i=>`<button type="button" class="video-choice" data-motion="${escape(i.motion_id)}" aria-pressed="false"><img src="${escape(i.poster)}" alt="${escape(i.label)}，RP1 与 G1 同时刻画面" loading="lazy" width="1920" height="1080"><span>${escape(i.label)}<small>${Math.floor(i.duration_s/60)} 分 ${Math.round(i.duration_s%60)} 秒</small></span></button>`).join("")||"<p>没有匹配动作。</p>";};
      gallery();selectPublicVideo(media.items[0]);
      $("video-filter").addEventListener("submit",e=>e.preventDefault());$("video-search").addEventListener("input",gallery);
      $("video-grid").addEventListener("click",e=>{const b=e.target.closest("button[data-motion]");if(b)selectPublicVideo(media.items.find(i=>i.motion_id===b.dataset.motion));});
    } catch(error) {pending();console.warn("公共视频尚未通过索引核验：",error.message);}
  }
  function render() {
    const rows = filteredRows().sort(compareRows), ranks = ranksForMetric(state.data, state.metric);
    renderHeaders(); renderRows(rows, ranks); renderOverview(); renderPairedSummary(); renderMotionChart(); renderFailures(rows); renderReferences(); renderFairness(); renderEvidence();
    $("view-aggregate").setAttribute("aria-pressed", String(state.scope === "aggregate"));
    $("view-per-motion").setAttribute("aria-pressed", String(state.scope === "per_motion"));
    $("sort-direction").textContent = state.direction === "asc" ? "升序 ↑" : "降序 ↓";
    $("sort-metric").value = state.metric;
  }
  function populateFilters() {
    const selectOptions = (key, options, label) => {
      $("filter-" + key).innerHTML = `<option value="all">${escape(label)}</option>` + options.map(([value, text]) => `<option value="${escape(value)}">${escape(text)}</option>`).join("");
    };
    selectOptions("dataset", state.data.datasets.map((dataset) => [dataset.id, dataset.label]), `全部 ${state.data.datasets.length} 组`);
    ["robot", "condition", "mode", "seed"].forEach((key) => {
      const values = [...new Set(state.data.results.map((row) => row[key]).filter((value) => value != null).map(String))].sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
      selectOptions(key, values.map((value) => [value, key === "robot" ? value.toUpperCase() : value]), { robot: "全部机器人", condition: "全部条件", mode: "全部模式", seed: "全部 seed" }[key]);
    });
    $("sort-metric").innerHTML = METRICS.map((metric) => `<option value="${metric.key}">${metric.label} (${metric.unit})</option>`).join("");
  }
  function csvCell(value) {
    let cell = value == null ? "" : String(value);
    if (/^[\s]*[=+\-@]/.test(cell) && !isNumber(value)) cell = "'" + cell;
    return '"' + cell.replace(/"/g, '""') + '"';
  }
  function csvExport(rows) {
    const base = ["id", "label", "phase", "robot", "dataset", "condition", "mode", "seed", "scope", "motion_id", "status", "status_reason"];
    const fields = ["coverage_numerator", "coverage_denominator", "coverage_unit", "coverage_reason", "paired_numerator", "paired_denominator", "paired_unit", "paired_reason", "comparison_id", "paired_sample_set_sha256", "checkpoint_sha256", "source_sha256", "config_sha256", "protocol_sha256", "raw_links_json", "videos_json", "failures_json"];
    const metricFields = ["value", "reason", "coverage_numerator", "coverage_denominator", "coverage_unit", "ci_low", "ci_high", "ci_level", "ci_method", "ci_resampling_unit", "ci_n_clusters", "ci_n_seeds", "ci_reason", "sample_set_sha256"];
    const header = [...base, ...fields, ...METRICS.flatMap((metric) => metricFields.map((field) => metric.key + "_" + field))];
    return "\uFEFF" + [header, ...rows.map((row) => {
      const c = row.coverage || {}, p = row.paired_coverage || {}, pairing = row.pairing || {}, provenance = row.provenance || {};
      return [...base.map((key) => row[key]), c.numerator, c.denominator, c.unit, c.reason, p.numerator, p.denominator, p.unit, p.reason, pairing.comparison_id, pairing.sample_set_sha256, (row.checkpoint || {}).sha256, provenance.source_sha256, provenance.config_sha256, provenance.protocol_sha256, JSON.stringify(asArray(provenance.raw_links)), JSON.stringify(asArray(row.videos)), JSON.stringify(asArray(row.failures)), ...METRICS.flatMap(({ key }) => {
        const m = (row.metrics || {})[key] || {}, mc = m.coverage || {}, ci = m.ci || {};
        return [valueOf(row, key), m.reason, mc.numerator, mc.denominator, mc.unit, ci.low, ci.high, ci.level, ci.method, ci.resampling_unit, ci.n_clusters, ci.n_seeds, ci.reason, m.sample_set_sha256];
      })];
    })].map((line) => line.map(csvCell).join(",")).join("\r\n") + "\r\n";
  }
  function download(contents, name, type) {
    const blob = new Blob([contents], { type }), url = URL.createObjectURL(blob), anchor = document.createElement("a");
    anchor.href = url; anchor.download = name; document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function bindEvents() {
    $("filters").addEventListener("submit", (event) => event.preventDefault());
    $("filters").addEventListener("input", () => { state.page = 1; render(); });
    $("filters").addEventListener("change", () => { state.page = 1; render(); });
    $("filters").addEventListener("reset", () => { setTimeout(() => { state.page = 1; render(); }, 0); });
    ["view-aggregate", "view-per-motion"].forEach((id) => $(id).addEventListener("click", () => { state.scope = $(id).dataset.scope; state.page = 1; render(); }));
    $("sort-metric").addEventListener("change", () => { state.metric = $("sort-metric").value; state.direction = metricDefinition(state.metric).direction; state.page = 1; render(); });
    $("sort-direction").addEventListener("click", () => { state.direction = state.direction === "asc" ? "desc" : "asc"; state.page = 1; render(); });
    $("results-head").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-sort]");
      if (!button) return;
      const metric = button.dataset.sort;
      state.direction = state.metric === metric ? state.direction === "asc" ? "desc" : "asc" : metricDefinition(metric).direction;
      state.metric = metric; state.page = 1; render();
    });
    $("pagination").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-page]");
      if (!button || button.disabled) return;
      state.page = Number(button.dataset.page); render(); $("leaderboard").scrollIntoView({ block: "start" });
    });
    $("download-json").addEventListener("click", () => download(JSON.stringify(state.data, null, 2) + "\n", "rp1-g1-snapshot.json", "application/json;charset=utf-8"));
    $("download-csv").addEventListener("click", () => download(csvExport(filteredRows().sort(compareRows)), `rp1-g1-${state.scope}.csv`, "text/csv;charset=utf-8"));
  }
  async function init() {
    let notice = "";
    try {
      if (window.LEADERBOARD_DATA != null) {
        state.data = normalizeData(window.LEADERBOARD_DATA); state.origin = "embedded";
      } else if (window.location.protocol === "file:") {
        notice = "当前为本地文件模式，未附带内嵌结果。等待封装时提供 window.LEADERBOARD_DATA，或通过本地 HTTP 服务读取同目录 data.json。";
      } else {
        const response = await fetch("./data.json", { cache: "no-store", credentials: "same-origin" });
        if (!response.ok) throw new Error(`data.json 读取失败（HTTP ${response.status}）`);
        state.data = normalizeData(await response.json()); state.origin = "data.json";
      }
    } catch (error) {
      notice = `${error.message} 页面保持 pending，不以空值替代实验成绩。`;
      $("load-notice").classList.add("error");
    }
    // Public presentation title is independent of the frozen scientific snapshot title.
    $("report-status").textContent = String(state.data.status || "pending").toUpperCase();
    $("updated-at").textContent = state.data.updated_utc ? new Date(state.data.updated_utc).toLocaleDateString("zh-CN", {timeZone:"UTC", year:"numeric",month:"long",day:"numeric"}) : "待导入";
    if (state.data.updated_utc) $("updated-at").setAttribute("datetime", state.data.updated_utc);
    const issues = state.issues.length ? ` 有 ${state.issues.length} 处字段缺失或非有限值，已显式标为 n/a；请检查数据生成端。` : "";
    $("load-notice").textContent = notice || `${state.data.status_message || "快照已载入；结论范围以各记录的协议、覆盖与来源为准。"} 数据来源：${state.origin}。${issues}`;
    populateFilters(); bindEvents(); render(); await renderPublicMedia();
  }
  /* Pure helpers exposed for offline contract checks; no scores or fixtures are bundled. */
  window.LeaderboardUtils = { ranksForMetric, csvExport, normalizeData, coverageText, valueOf, safeURL, linkHTML, pairedSummaryFor, validPublicMedia, pairedIntervalSVG, metrics: METRICS };
  init();
})();
