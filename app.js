/* Public v3 UI: frozen full-window values, stable episode identities and explicit completion evidence. */
(function () {
  "use strict";
  const METRICS = [
    { key: "full_body_pos_mm", label: "全程身体位置误差", unit: "mm", digits: 2 },
    { key: "full_body_ori_rad", label: "全程身体姿态误差", unit: "rad", digits: 4 },
    { key: "full_wrist_pos_mm", label: "全程手腕位置误差", unit: "mm", digits: 2 },
    { key: "full_wrist_ori_rad", label: "全程手腕姿态误差", unit: "rad", digits: 4 }
  ];
  const FULL_WINDOW = "full_replay_50hz_first_substep";
  const TOP_KEYS = ["schema_version", "publication_state", "fullwindow_source_sha256", "identity_map_sha256", "counts", "metrics", "results", "comparisons", "datasets", "phase", "primary_comparison_ids", "secondary_comparison_ids", "methods", "completion_contract", "report_downloads", "fairness", "stats"];
  const ROW_KEYS = ["id", "label", "phase", "dataset", "condition", "mode", "robot", "motion_id", "seed", "scope", "matched_seed_set", "metrics", "completion", "coverage", "pairing", "fullwindow", "provenance"];
  const PROVENANCE_KEYS = ["protocol_sha256", "execution_protocol_sha256", "config_sha256", "source_sha256"];
  const COMPARISON_KEYS = ["id", "label", "phase", "dataset", "condition", "mode", "role", "metric_window", "n_unique_motions", "paired_cases", "episode_records", "matched_seed_set", "expected_participants", "expected_paired_motions", "sample_set", "sample_set_sha256", "paired_deltas", "paired_motion_values", "completion", "fullwindow_comparison_id"];
  const WINDOW_KEYS = ["run_id", "case_id", "metric_window", "full_recorded_frames", "reference_common_frames", "reference_start_s", "reference_end_s"];
  const COMPLETION_KEYS = ["status", "completed", "rate_pct", "ci95", "reason"];
  const REPORTS = [
    { label: "技术报告正文", url: "https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb" },
    { label: "技术报告 PDF", url: "https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7" },
    { label: "技术报告 DOCX", url: "https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce" }
  ];
  const EMPTY = { schema_version: 3, results: [], comparisons: [], datasets: [], counts: {}, methods: {}, report_downloads: [], fairness: [], stats: {}, primary_comparison_ids: [], secondary_comparison_ids: [] };
  const state = { data: EMPTY, scope: "aggregate", metric: METRICS[0].key, direction: "asc", page: 1, pageSize: 25, loaded: false };
  const $ = id => document.getElementById(id);
  const escape = value => String(value == null ? "" : value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const asArray = value => Array.isArray(value) ? value : [];
  const isNumber = value => typeof value === "number" && Number.isFinite(value);
  const knownCount = value => Number.isInteger(value) && value >= 0;
  const sha256 = value => typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
  const fmt = (value, digits = 2) => isNumber(value) ? value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }) : "n/a";
  const signed = (value, digits) => `${value > 0 ? "+" : ""}${fmt(value, digits)}`;
  const valueOf = (row, key) => isNumber(row?.metrics?.[key]?.value) ? row.metrics[key].value : null;
  const metricDefinition = key => METRICS.find(metric => metric.key === key) || METRICS[0];
  const datasetLabel = id => state.data.datasets.find(item => item.id === id)?.label || id || "待核验";
  const groupKey = row => JSON.stringify([row.phase, row.dataset, row.condition, row.mode]);
  const pairedCaseKey = row => JSON.stringify([row.phase, row.dataset, row.condition, row.mode, row.motion_id, row.seed]);
  const validCI = ci => Array.isArray(ci) && ci.length === 2 && ci.every(isNumber) && ci[0] <= ci[1];
  const pick = (object, keys) => Object.fromEntries(keys.filter(key => Object.hasOwn(object || {}, key)).map(key => [key, object[key]]));
  function assertKeys(object, allowed, label) {
    if (!object || typeof object !== "object" || Array.isArray(object) || Object.keys(object).some(key => !allowed.includes(key))) throw new Error(`${label} 含有接口外字段`);
  }
  function safeURL(value) {
    if (typeof value !== "string" || !value.trim()) return null;
    try { const url = new URL(value, window.location.href); return ["https:", "http:"].includes(url.protocol) ? url.href : null; } catch (_) { return null; }
  }
  function linkHTML(link) {
    const url = safeURL(link?.url);
    return url ? `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(link.label)}${/feishu\.cn/.test(url) ? "（需组织权限）" : ""} ↗</a>` : "";
  }
  const emptyHTML = (title, description) => `<div class="empty-state"><strong>${escape(title)}</strong>${escape(description)}</div>`;
  const coverageText = coverage => `${knownCount(coverage?.numerator) ? coverage.numerator : "?"} / ${knownCount(coverage?.denominator) ? coverage.denominator : "?"} ${coverage?.unit === "motions" ? "动作" : coverage?.unit === "episodes" ? "回合" : escape(coverage?.unit || "样本")}`;
  function validateCompletion(completion, label) {
    assertKeys(completion, COMPLETION_KEYS, label);
    if (typeof completion.status !== "string" || (completion.completed !== null && typeof completion.completed !== "boolean") || (completion.rate_pct !== null && (!isNumber(completion.rate_pct) || completion.rate_pct < 0 || completion.rate_pct > 100)) || (completion.ci95 !== null && !validCI(completion.ci95))) throw new Error(`${label} 数值无效`);
    if (completion.status === "pending" && (completion.completed !== null || completion.rate_pct !== null || completion.ci95 !== null || !completion.reason)) throw new Error(`${label} 未核验状态不能包含成绩`);
  }
  function pairedMotionCases(data) {
    const groups = new Map();
    data.results.filter(row => row.scope === "per_motion").forEach(row => { const key = pairedCaseKey(row); if (!groups.has(key)) groups.set(key, []); groups.get(key).push(row); });
    return [...groups.values()].filter(rows => rows.length === 2 && new Set(rows.map(row => row.robot)).size === 2);
  }
  function normalizeData(input) {
    assertKeys(input, TOP_KEYS, "公开快照");
    if (input.schema_version !== 3) throw new Error("公开数据版本不兼容，需要 schema_version: 3");
    ["results", "comparisons", "datasets", "primary_comparison_ids", "secondary_comparison_ids", "report_downloads", "fairness"].forEach(key => { if (!Array.isArray(input[key])) throw new Error(`缺少公开数组 ${key}`); });
    const counts = { episode_records: 180, paired_cases: 90, unique_motions: 45, comparison_groups: 5, aggregate_rows: 10, result_rows: 190 };
    if (Object.entries(counts).some(([key, count]) => input.counts?.[key] !== count) || input.results.length !== 190 || input.comparisons.length !== 5 || input.datasets.length !== 2) throw new Error("公开配对数量不一致");
    if (Object.keys(input.metrics || {}).length !== 4 || METRICS.some(metric => input.metrics[metric.key]?.unit !== metric.unit || input.metrics[metric.key]?.higher_is_better !== false)) throw new Error("全程四项指标定义不一致");
    assertKeys(input.counts, Object.keys(counts), "公开数量");
    assertKeys(input.methods, ["fullwindow", "units", "weighting", "bootstrap"], "方法");
    assertKeys(input.methods.bootstrap, ["resampling_unit", "generator", "seed", "resamples", "confidence", "quantile_method", "reset_per_group_and_metric", "shared_indices_for_robots", "delta_direction"], "区间方法");
    assertKeys(input.completion_contract, ["status", "rule_version", "source_sha256"], "完成判定版本");
    input.datasets.forEach(dataset => assertKeys(dataset, ["id", "label", "expected_motions"], "数据集"));
    METRICS.forEach(metric => assertKeys(input.metrics[metric.key], ["unit", "label", "higher_is_better"], "指标定义"));
    input.report_downloads.forEach(report => assertKeys(report, ["label", "url", "access"], "报告链接"));
    input.fairness.forEach(item => assertKeys(item, ["item", "rp1", "g1", "status", "evidence", "phase", "condition", "mode"], "公平条件"));
    assertKeys(input.stats, ["report_status", "updated_utc", "notes", "limitations"], "公开说明");
    const ids = new Set(), cases = new Set(), runs = new Map();
    input.results.forEach(row => {
      assertKeys(row, ROW_KEYS, "公开记录");
      if (typeof row.id !== "string" || ids.has(row.id) || row.phase !== "A" || !["rp1", "g1"].includes(row.robot) || !["aggregate", "per_motion"].includes(row.scope)) throw new Error("公开记录身份无效");
      ids.add(row.id); validateCompletion(row.completion, "动作跟踪完成判定");
      assertKeys(row.provenance, PROVENANCE_KEYS, "记录来源身份");
      if (Object.keys(row.provenance).length !== PROVENANCE_KEYS.length || PROVENANCE_KEYS.some(key => row.provenance[key] !== null && !sha256(row.provenance[key]))) throw new Error("记录来源摘要须为 SHA256 或原缺失 null");
      if (!Array.isArray(row.matched_seed_set) || row.matched_seed_set.some(seed => !Number.isSafeInteger(seed) || seed < 0)) throw new Error("seed 集无效");
      assertKeys(row.metrics, METRICS.map(metric => metric.key), "全程指标");
      METRICS.forEach(metric => {
        const cell = row.metrics[metric.key]; assertKeys(cell, ["value", "unit", "ci95", "n_motions"], "指标单元格");
        if (!isNumber(cell.value) || cell.unit !== metric.unit || !knownCount(cell.n_motions) || cell.n_motions < 1 || (row.scope === "aggregate" ? !validCI(cell.ci95) : cell.ci95 !== null || cell.n_motions !== 1)) throw new Error("全程指标数值或区间无效");
      });
      assertKeys(row.coverage, ["numerator", "denominator", "unit"], "覆盖");
      if (!knownCount(row.coverage.numerator) || row.coverage.numerator !== row.coverage.denominator || row.coverage.numerator !== (row.scope === "per_motion" ? 1 : row.metrics[METRICS[0].key].n_motions) || row.coverage.unit !== (row.scope === "per_motion" ? "episodes" : "motions")) throw new Error("覆盖分母无效");
      assertKeys(row.pairing, ["comparison_id", "sample_set_sha256", "case_id"], "配对身份");
      if (!sha256(row.pairing.sample_set_sha256)) throw new Error("配对集合身份无效");
      if (row.scope === "per_motion") {
        assertKeys(row.fullwindow, WINDOW_KEYS, "全程评分窗口");
        if (!Number.isSafeInteger(row.seed) || row.seed < 0 || row.matched_seed_set.length !== 1 || row.matched_seed_set[0] !== row.seed || !row.motion_id || row.fullwindow.metric_window !== FULL_WINDOW || row.fullwindow.full_recorded_frames !== row.fullwindow.reference_common_frames - 1) throw new Error("全程回合窗口或 seed 身份无效");
        if (typeof row.fullwindow.run_id !== "string" || runs.has(row.fullwindow.run_id) || row.fullwindow.case_id !== row.pairing.case_id || !isNumber(row.fullwindow.reference_start_s) || !isNumber(row.fullwindow.reference_end_s) || row.fullwindow.reference_start_s > row.fullwindow.reference_end_s) throw new Error("评分窗口来源身份无效");
        runs.set(row.fullwindow.run_id, row);
        const identity = JSON.stringify([pairedCaseKey(row), row.robot]); if (cases.has(identity)) throw new Error("重复机器人回合"); cases.add(identity);
      } else if (row.seed !== null || row.fullwindow != null) throw new Error("聚合行接口无效");
    });
    const pairs = pairedMotionCases(input), motions = new Set(pairs.map(rows => JSON.stringify([rows[0].dataset, rows[0].motion_id])));
    if (pairs.length !== 90 || motions.size !== 45 || cases.size !== 180 || input.results.filter(row => row.scope === "aggregate").length !== 10) throw new Error("实际回合配对数量不一致");
    const comparisonIds = new Set(), aggregateIds = new Set();
    input.comparisons.forEach(comparison => {
      assertKeys(comparison, COMPARISON_KEYS, "比较组"); validateCompletion(comparison.completion, "比较组完成率");
      if (comparisonIds.has(comparison.id) || comparison.metric_window !== FULL_WINDOW || !sha256(comparison.sample_set_sha256) || comparison.expected_participants?.length !== 2 || comparison.sample_set?.length !== comparison.paired_cases) throw new Error("比较组身份或覆盖无效");
      comparisonIds.add(comparison.id);
      const members = comparison.expected_participants.map(id => input.results.find(row => row.id === id));
      if (members.some(row => !row || row.scope !== "aggregate" || groupKey(row) !== groupKey(comparison) || row.pairing.comparison_id !== comparison.id || row.pairing.sample_set_sha256 !== comparison.sample_set_sha256) || new Set(members.map(row => row.robot)).size !== 2) throw new Error("比较组不能对应原聚合身份");
      members.forEach(row => { if (aggregateIds.has(row.id)) throw new Error("聚合身份重复使用"); aggregateIds.add(row.id); });
      const episodes = input.results.filter(row => row.scope === "per_motion" && groupKey(row) === groupKey(comparison));
      if (episodes.length !== comparison.episode_records || episodes.length !== comparison.paired_cases * 2 || new Set(episodes.map(row => row.motion_id)).size !== comparison.n_unique_motions || members.some(row => METRICS.some(metric => row.metrics[metric.key].n_motions !== comparison.n_unique_motions))) throw new Error("比较组分母不一致");
      const selectedRuns = new Set();
      comparison.sample_set.forEach(sample => {
        assertKeys(sample, ["scientific_selected_case_id", "motion_id", "seed", "participants"], "配对样本");
        assertKeys(sample.participants, ["rp1", "g1"], "配对双方");
        ["rp1", "g1"].forEach(robot => {
          const episode = runs.get(sample.participants[robot]);
          if (!episode || selectedRuns.has(episode.fullwindow.run_id) || episode.robot !== robot || episode.motion_id !== sample.motion_id || episode.seed !== sample.seed || episode.pairing.case_id !== sample.scientific_selected_case_id || episode.pairing.comparison_id !== comparison.id || episode.pairing.sample_set_sha256 !== comparison.sample_set_sha256 || groupKey(episode) !== groupKey(comparison)) throw new Error("配对样本不能一一对应机器人回合");
          selectedRuns.add(episode.fullwindow.run_id);
        });
      });
      if (selectedRuns.size !== episodes.length) throw new Error("配对样本存在缺失回合");
      assertKeys(comparison.paired_motion_values, METRICS.map(metric => metric.key), "动作级统计");
      METRICS.forEach(metric => {
        const values = comparison.paired_motion_values[metric.key];
        if (!Array.isArray(values) || values.length !== comparison.n_unique_motions) throw new Error("动作级统计分母无效");
        values.forEach(value => { assertKeys(value, ["motion_id", "rp1", "g1", "delta_rp1_minus_g1", "seeds", "repeats_per_robot"], "动作级数值"); if (![value.rp1, value.g1, value.delta_rp1_minus_g1].every(isNumber) || !Array.isArray(value.seeds)) throw new Error("动作级数值无效"); });
      });
      assertKeys(comparison.paired_deltas, METRICS.map(metric => metric.key), "全程配对差");
      METRICS.forEach(metric => { const delta = comparison.paired_deltas[metric.key]; assertKeys(delta, ["value", "ci95", "unit", "n_motions"], "配对差值"); if (!isNumber(delta.value) || !validCI(delta.ci95) || delta.unit !== metric.unit || delta.n_motions !== comparison.n_unique_motions) throw new Error("全程配对区间无效"); });
    });
    if (aggregateIds.size !== 10 || input.primary_comparison_ids.length !== 2 || input.secondary_comparison_ids.length !== 3 || [...input.primary_comparison_ids, ...input.secondary_comparison_ids].some(id => !comparisonIds.has(id))) throw new Error("主组与敏感性组身份不一致");
    const output = JSON.parse(JSON.stringify(input));
    output.results = output.results.map(row => ({ ...row, provenance: pick(row.provenance, PROVENANCE_KEYS) }));
    return output;
  }
  function filters() { return Object.fromEntries(["phase", "robot", "dataset", "condition", "mode", "seed", "search"].map(key => [key, $("filter-" + key).value])); }
  function filteredRows(scope = state.scope) {
    const selected = filters(), query = selected.search.trim().toLowerCase();
    return state.data.results.filter(row => row.scope === scope && ["phase", "robot", "dataset", "condition", "mode"].every(key => selected[key] === "all" || String(row[key]) === selected[key]) && (selected.seed === "all" || row.matched_seed_set.map(String).includes(selected.seed)) && (!query || [row.label, row.motion_id, row.id].some(value => String(value || "").toLowerCase().includes(query))));
  }
  function compareRows(a, b) {
    const first = valueOf(a, state.metric), second = valueOf(b, state.metric);
    return (first - second) * (state.direction === "asc" ? 1 : -1) || groupKey(a).localeCompare(groupKey(b)) || a.id.localeCompare(b.id);
  }
  function ranksForMetric(data, key) {
    const output = new Map(data.results.map(row => [row.id, { rank: null, reason: "逐回合不排名", comparison: null }]));
    data.comparisons.forEach(comparison => {
      const members = comparison.expected_participants.map(id => data.results.find(row => row.id === id));
      if (members.length !== 2 || members.some(row => !row || valueOf(row, key) === null || row.pairing.sample_set_sha256 !== comparison.sample_set_sha256)) return;
      members.forEach(row => output.set(row.id, { rank: 1 + members.filter(other => valueOf(other, key) < valueOf(row, key)).length, reason: "同条件配对", comparison: comparison.id }));
    }); return output;
  }
  function fullGroup(dataset) {
    const comparison = state.data.comparisons.find(item => state.data.primary_comparison_ids.includes(item.id) && item.dataset === dataset);
    return comparison ? { comparison, rows: comparison.expected_participants.map(id => state.data.results.find(row => row.id === id)) } : null;
  }
  function completionHTML(row, compact = false) {
    const completion = row.completion;
    if (!completion || completion.status === "pending") return `<span class="completion-pending">待核验</span>${compact ? "" : `<span class="metric-detail">${escape(completion?.reason || "等待正式完成判据和标签冻结")}</span>`}`;
    if (row.scope === "per_motion") return `<span class="completion-result ${completion.completed ? "finished" : "unfinished"}">${completion.completed === true ? "完成" : completion.completed === false ? "未完成" : "判定待核验"}</span>${compact ? "" : `<span class="metric-detail">${escape(completion.reason || "")}</span>`}`;
    return isNumber(completion.rate_pct) ? `<span class="metric-value">${fmt(completion.rate_pct, 2)}%</span>${validCI(completion.ci95) ? `<span class="metric-detail">95% CI [${fmt(completion.ci95[0], 2)}, ${fmt(completion.ci95[1], 2)}]%</span>` : ""}<span class="metric-detail">${escape(completion.reason || "")}</span>` : `<span class="completion-pending">待核验</span>`;
  }
  function completionGroup(group) {
    if (!group) return emptyHTML("Motion 跟踪任务完成率：待核验", "等待正式完成判据和逐动作标签冻结。");
    return `<div class="completion-robots">${["rp1", "g1"].map(robot => { const row = group.rows.find(item => item.robot === robot); return `<div><h4><i class="dot ${robot}"></i>${robot.toUpperCase()}</h4>${completionHTML(row)}<p>${group.comparison.n_unique_motions} 个配对动作${row.completion.status === "pending" ? " · 完成判定待核验" : ""}</p></div>`; }).join("")}</div>`;
  }
  function renderOverview() {
    const counts = state.data.counts;
    $("overview").innerHTML = state.loaded ? `<div class="scope-item"><strong>${counts.unique_motions}</strong><p><b>共同动作</b>两套主数据集分别报告</p></div><div class="scope-item"><strong>${counts.paired_cases}</strong><p><b>条件与 seed 配对</b>${counts.episode_records} 个机器人回合</p></div><div class="scope-item"><strong>${counts.comparison_groups}</strong><p><b>独立评测组</b>重复 seed 不增加动作数</p></div>` : emptyHTML("公开结果待载入", "当前未读取通过版本核验的共同配对数据。");
  }
  function fullFindingCards(group) {
    return METRICS.map(metric => {
      const delta = group.comparison.paired_deltas[metric.key];
      const interpretation = delta.ci95[1] < 0 ? "RP1 全程误差较低，配对区间低于零。" : delta.ci95[0] > 0 ? "G1 全程误差较低，配对区间高于零。" : "配对区间跨零，当前样本未支持明确方向。";
      return `<article class="finding-card"><h3>${metric.label}</h3><p class="metric-caption">越低越好 · ${delta.n_motions} 个配对动作（N=${delta.n_motions}）</p><div class="finding-values">${["rp1", "g1"].map(robot => `<div><span><i class="dot ${robot}"></i>${robot.toUpperCase()}</span><strong>${fmt(valueOf(group.rows.find(row => row.robot === robot), metric.key), metric.digits)}<small>${metric.unit}</small></strong></div>`).join("")}</div><p class="delta-label">全程配对差值 RP1 − G1</p>${pairedIntervalSVG(delta, metric.digits, metric.unit)}<p class="delta-ci">${signed(delta.value, metric.digits)} ${metric.unit} · 95% CI [${fmt(delta.ci95[0], metric.digits)}, ${fmt(delta.ci95[1], metric.digits)}]</p><p class="finding-interpretation">${interpretation}</p></article>`;
    }).join("");
  }
  function pairedIntervalSVG(delta, digits, unit, dark = false) {
    const bound = Math.max(Math.abs(delta.ci95[0]), Math.abs(delta.ci95[1]), Math.abs(delta.value)) * 1.18 || 1;
    const x = (v) => 155 + v / bound * 129;
    const color = dark ? "#bfcee3" : delta.value < 0 ? "#4387f5" : "#159b80";
    return `<svg class="${dark ? "hero-ci" : "ci-svg"}" viewBox="0 0 310 74" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RP1 减 G1 差值 ${escape(signed(delta.value, digits))} ${escape(unit)}，95% 置信区间 ${escape(fmt(delta.ci95[0], digits))} 至 ${escape(fmt(delta.ci95[1], digits))}"><line x1="26" y1="28" x2="284" y2="28" stroke="${dark ? "#46536b" : "#e0e6ef"}"/><line x1="155" y1="7" x2="155" y2="43" stroke="${dark ? "#889bb8" : "#7c8ca3"}" stroke-dasharray="3 3"/><line x1="${x(delta.ci95[0])}" y1="28" x2="${x(delta.ci95[1])}" y2="28" stroke="${color}" stroke-width="4" stroke-linecap="round"/><line x1="${x(delta.ci95[0])}" y1="21" x2="${x(delta.ci95[0])}" y2="35" stroke="${color}"/><line x1="${x(delta.ci95[1])}" y1="21" x2="${x(delta.ci95[1])}" y2="35" stroke="${color}"/><circle cx="${x(delta.value)}" cy="28" r="5" fill="${color}" stroke="${dark ? "#101c30" : "white"}" stroke-width="2"/><text x="26" y="60">−${escape(fmt(bound, digits))}</text><text x="155" y="60" text-anchor="middle">0</text><text x="284" y="60" text-anchor="end">+${escape(fmt(bound, digits))} ${escape(unit)}</text></svg>`;
  }
  function renderPairedSummary() {
    const group = fullGroup("lafan40");
    if (!group) { $("hero-chart").innerHTML = emptyHTML("全程配对摘要暂未载入", "请检查公开快照及载入状态。"); $("paired-summary").innerHTML = emptyHTML("全程指标暂未载入", "没有生成示例成绩。"); return; }
    const key = METRICS[0].key, delta = group.comparison.paired_deltas[key], maximum = Math.max(...group.rows.map(row => valueOf(row, key))) || 1;
    $("hero-chart").innerHTML = `<p class="eyebrow">FULL WINDOW / 40 PAIRED MOTIONS</p><h2>全程身体位置误差</h2><p class="chart-context">全部评分序列 · 越低越好</p>${["rp1", "g1"].map(robot => { const value = valueOf(group.rows.find(row => row.robot === robot), key); return `<div class="bar-row"><div class="bar-label"><span><i class="dot ${robot}"></i>${robot.toUpperCase()}</span><strong>${fmt(value, 2)}<small>mm</small></strong></div><div class="bar-track" aria-hidden="true"><div class="bar-fill ${robot}" style="width:${value / maximum * 100}%"></div></div></div>`; }).join("")}<div class="hero-delta"><p>RP1 − G1 <strong>${signed(delta.value, 2)}<small> mm</small></strong></p><p class="ci-text">95% CI [${fmt(delta.ci95[0], 2)}, ${fmt(delta.ci95[1], 2)}] mm · ${delta.n_motions} 个配对动作（N=${delta.n_motions}）</p>${pairedIntervalSVG(delta, 2, "mm", true)}<p class="hero-conclusion">${delta.ci95[1] < 0 ? "RP1 全程身体位置误差较低。" : "结论以全程配对区间为准。"}</p></div>`;
    $("paired-summary").innerHTML = fullFindingCards(group);
  }
  function renderExtension() {
    const group = fullGroup("extreme5");
    $("extreme-results").innerHTML = `<div class="section-heading compact"><div><p class="eyebrow">EXTREME5 / INDEPENDENT GROUP</p><h3>空翻与转体：5 个配对动作（N=5）</h3><p>踢月转体、侧空翻、后空翻、前空翻与毽子后空翻，共 10 个机器人回合，独立报告。</p></div><span class="scope-label">5 / 5 共同动作</span></div><div class="finding-grid full-finding-grid">${group ? fullFindingCards(group) : emptyHTML("Extreme5 全程指标暂未载入", "请检查公开快照及载入状态。")}</div><p class="result-note">本组视频待制作。</p>`;
  }
  function renderCompletion() {
    $("completion-summary").innerHTML = ["lafan40", "extreme5"].map(dataset => `<article class="completion-card"><h3>${dataset === "lafan40" ? "Common40 · 40 个配对动作" : "Extreme5 · 5 个配对动作"}</h3>${completionGroup(fullGroup(dataset))}</article>`).join("");
    const cases = pairedMotionCases({ results: filteredRows("per_motion") }).slice(0, 30);
    $("completion-chart").innerHTML = cases.length ? `<div class="table-scroll"><table class="completion-table"><thead><tr><th>动作 / 条件 / seed</th><th>RP1</th><th>G1</th></tr></thead><tbody>${cases.map(rows => `<tr><td>${escape(rows[0].motion_id)}<span class="record-meta">${escape(rows[0].condition)} · ${escape(rows[0].mode)} · seed ${rows[0].seed}</span></td>${["rp1", "g1"].map(robot => `<td>${completionHTML(rows.find(row => row.robot === robot))}</td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="chart-note">显示前 ${cases.length} 个双方齐全的条件与 seed 配对；完整判定见逐动作表格及导出。</p>` : emptyHTML("暂无双方齐全的逐动作记录", "调整机器人或动作筛选可查看双方判定。单侧记录仍保留在上方表格。");
  }
  function rowEvidence(row) {
    if (!row.fullwindow) return "";
    const full = row.fullwindow;
    return `<details><summary>评分窗口</summary><div class="record-evidence"><p>${full.full_recorded_frames} 个 50 Hz 首物理子步评分样本；共同参考帧 ${full.reference_common_frames}。</p><p>参考时间 ${fmt(full.reference_start_s, 3)}–${fmt(full.reference_end_s, 3)} s。</p><p>${row.provenance.execution_protocol_sha256 === null ? "此记录原未记录执行版本。" : "原执行版本身份已保留。"}</p></div></details>`;
  }
  function metricHTML(row, metric) {
    const cell = row.metrics[metric.key];
    return `<td class="metric ${state.metric === metric.key ? "highlight" : ""}"><span class="metric-value">${fmt(cell.value, metric.digits)}</span><span class="metric-detail">${row.scope === "aggregate" ? `${cell.n_motions} 个配对动作` : "1 个机器人回合"}</span>${validCI(cell.ci95) ? `<span class="metric-detail">95% CI [${fmt(cell.ci95[0], metric.digits)}, ${fmt(cell.ci95[1], metric.digits)}]</span>` : `<span class="metric-detail">单回合不计算动作区间</span>`}</td>`;
  }
  function renderHeaders() {
    $("results-head").innerHTML = `<tr><th scope="col">组内名次<span class="unit">按所选全程误差</span></th><th scope="col">策略 / 动作<span class="unit">机器人 · 数据集 · 条件</span></th><th scope="col">覆盖<span class="unit">独立动作与配对回合</span></th><th scope="col">Motion 跟踪任务完成<span class="unit">聚合完成率 / 逐动作判定</span></th>${METRICS.map(metric => `<th scope="col" aria-sort="${state.metric === metric.key ? state.direction === "asc" ? "ascending" : "descending" : "none"}"><button type="button" data-sort="${metric.key}">${metric.label} ${state.metric === metric.key ? state.direction === "asc" ? "↑" : "↓" : "↕"}<span class="unit">${metric.unit} · 越低越好 ↓</span></button></th>`).join("")}</tr>`;
  }
  function renderRows(rows, ranks) {
    const pages = Math.max(1, Math.ceil(rows.length / state.pageSize)); state.page = Math.min(state.page, pages);
    const current = rows.slice((state.page - 1) * state.pageSize, state.page * state.pageSize);
    $("results-body").innerHTML = current.length ? current.map(row => { const rank = ranks.get(row.id); return `<tr><td class="rank-cell"><span class="rank-number">${rank?.rank || "—"}</span><span class="rank-note">${escape(rank?.reason || "配对待核验")}</span></td><td class="row-heading"><div class="record-label">${escape(row.label)}</div>${row.scope === "per_motion" ? `<span class="record-meta">${escape(row.motion_id)}</span>` : ""}<span class="record-meta">${escape(datasetLabel(row.dataset))}</span><span class="record-meta">${escape(row.condition)} · ${escape(row.mode)}</span><span class="record-meta">${row.scope === "aggregate" ? "完整匹配 seed 集" : "seed"} ${escape(row.matched_seed_set.join(", "))}</span><div class="record-badges"><span class="badge">${row.robot.toUpperCase()}</span><span class="badge">发布学生策略</span></div>${rowEvidence(row)}</td><td><span class="coverage-primary">${coverageText(row.coverage)}</span><span class="coverage-secondary">${row.scope === "aggregate" ? "同动作 seed 内平均，动作等权" : "已纳入共同配对"}</span></td><td class="completion-cell">${completionHTML(row)}</td>${METRICS.map(metric => metricHTML(row, metric)).join("")}</tr>`; }).join("") : `<tr><td class="empty-cell" colspan="8"><strong>${state.loaded ? "当前筛选没有匹配记录" : "公开结果待载入"}</strong><p>${state.loaded ? "可切换结果粒度或重置筛选。" : "等待通过版本核验的 data.json。"}</p></td></tr>`;
    $("pagination").innerHTML = pages > 1 ? `<span>第 ${state.page} / ${pages} 页 · 每页 ${state.pageSize} 条</span><button type="button" data-page="${state.page - 1}" ${state.page === 1 ? "disabled" : ""}>上一页</button><button type="button" data-page="${state.page + 1}" ${state.page === pages ? "disabled" : ""}>下一页</button>` : "";
    $("result-count").textContent = `${rows.length} 条${state.scope === "aggregate" ? "聚合" : "逐动作"}记录 · ${rows.filter(row => ranks.get(row.id)?.rank != null).length} 条有组内名次${state.scope === "aggregate" ? " · seed 筛选选择包含该 seed 的完整组，均值不重算" : ""}`;
    $("download-csv").disabled = !rows.length; $("download-json").disabled = !state.loaded;
  }
  function renderMotionChart() {
    const metric = metricDefinition(state.metric), source = filteredRows("per_motion"), rows = source.slice().sort(compareRows).slice(0, 36);
    $("motion-chart-description").textContent = `${metric.label} · ${metric.unit} · 越低越好。按当前方向排序，跨组不产生名次。`;
    if (!rows.length) { $("motion-chart").innerHTML = emptyHTML("当前筛选没有逐动作数值", "图表读取真实机器人回合，聚合均值不用于推造分布。"); return; }
    const max = Math.max(...rows.map(row => valueOf(row, state.metric))) || 1, left = 238, right = 658, top = 27, rowHeight = 31, bottom = top + rows.length * rowHeight + 13;
    const x = value => left + value / max * (right - left);
    let svg = `<svg class="motion-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 ${bottom + 32}" role="img" aria-label="当前筛选逐动作${escape(metric.label)}，显示前${rows.length}条">`;
    for (let i = 0; i <= 4; i++) { const position = left + i * (right - left) / 4; svg += `<line x1="${position}" y1="${top - 12}" x2="${position}" y2="${bottom}" stroke="#e3eaf3"/><text x="${position}" y="${bottom + 22}" text-anchor="middle" fill="#697c96" font-size="10">${fmt(i * max / 4, metric.digits)}</text>`; }
    rows.forEach((row, index) => { const y = top + index * rowHeight + 7, value = valueOf(row, state.metric), label = `${row.robot.toUpperCase()} · ${row.motion_id}`, color = row.robot === "rp1" ? "#4387f5" : "#159b80"; svg += `<g><title>${escape(`${label}; ${row.condition}; ${row.mode}; seed ${row.seed}; ${fmt(value, metric.digits)} ${metric.unit}`)}</title><text x="0" y="${y + 4}" font-size="11" fill="#50647f">${escape(label.length > 34 ? label.slice(0, 31) + "…" : label)}</text><line x1="${left}" y1="${y}" x2="${x(value)}" y2="${y}" stroke="${color}" stroke-opacity=".25" stroke-width="5"/><circle cx="${x(value)}" cy="${y}" r="4" fill="${color}"/><text x="752" y="${y + 4}" text-anchor="end" font-size="11" fill="#263e5d">${fmt(value, metric.digits)}</text></g>`; });
    $("motion-chart").innerHTML = `<div class="legend"><span style="--dot:#4387f5">RP1</span><span style="--dot:#159b80">G1</span></div>${svg}</svg><p class="chart-note">显示 ${rows.length} / ${source.length} 个数值。完整记录可在逐动作表格或 CSV 查看。</p>`;
  }
  function renderFairness() {
    const selected = filters();
    const rows = asArray(state.data.fairness).filter(row => ["phase", "condition", "mode"].every(key => !row[key] || row[key] === "all" || selected[key] === "all" || row[key] === selected[key]));
    $("fairness-body").innerHTML = rows.length ? rows.map(row => `<tr><td>${escape(row.item)}</td><td>${escape(row.rp1)}</td><td>${escape(row.g1)}</td><td>${escape(row.status === "matched" ? "已核验一致" : row.status === "disclosed_difference" ? "已披露差异" : "待核验")}</td><td>${escape(row.evidence)}</td></tr>`).join("") : `<tr><td colspan="5">评测条件按上方方法说明；各模型控制参数见逐关节表。</td></tr>`;
  }
  function renderEvidence() {
    $("statistics").innerHTML = `<dt>评分窗口</dt><dd>全部 50 Hz 首物理子步样本，motion_t=1..Ncommon−1，包含失跟后的评分记录。初始化帧与 200 Hz 末端 hold 不增加评分样本。</dd><dt>聚合口径</dt><dd>完整相同 seed 先在动作内平均，再对动作等权；每组独立报告，重复 seed 不增加动作分母。</dd><dt>置信区间</dt><dd>10,000 次配对动作百分位 bootstrap，PCG64 seed 20261013，95% 线性分位数。均值与配对差值区间直接读取冻结统计。</dd><dt>完成判据</dt><dd>动作跟踪时因摔倒而无法继续后续跟踪记为未完成，未发生则完成；中途摔倒后自行恢复并跟踪到末尾算完成。判定结合参考动作及持续状态核验，参考动作中的翻滚与起身单独辨认。逐动作标签、有效分母与多 seed 汇总随冻结结果公布；冻结前显示待核验。</dd><dt>条件覆盖</dt><dd>Common40 主组：40 动作 / 40 对 / 80 回合；Extreme5：5 / 5 / 10。敏感性：5 / 5 / 10；重复：5 / 15 / 30；初态扰动：5 / 25 / 50。共 45 个不同动作、90 对、180 回合。</dd>`;
    const reports = state.data.report_downloads.length ? state.data.report_downloads : REPORTS;
    const reportStatus = state.data.stats.report_status || "正式报告沿用现有链接，正在按全程误差与 Motion 跟踪任务完成率口径更新。";
    $("downloads").innerHTML = `<p>${reports.map(linkHTML).join(" ")}</p><p>${escape(reportStatus)} 资料需飞书组织权限。</p>`;
    const notes = ["区间描述固定发布策略与当前仿真动作。训练数据、重定向和控制参数不同；完整历史训练日志、GPU 训练小时及真机验证待补充。", "Common14 使用 ankle-roll 语义映射。四项全程描述性区间未作多重比较校正。", "公开重定向的动作名与时长已对齐，原始 BVH 输入哈希血缘仍有缺口。", "30 个确定性重复回合逐值一致，独立动作数仍为 5。"];
    $("limitations").innerHTML = notes.map(note => `<li>${escape(note)}</li>`).join("");
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
    const pending=()=>{document.querySelector(".hero-actions .button").textContent="动作回放计划 ↗";$("video-coverage").textContent="0 / 40 新片已发布";$("public-videos").innerHTML=`<div class="video-pending"><strong>共同 40 动作<br>高分辨率回放待交付。</strong><p>新一批 4K 原生渲染与 1080p 网页视频正在制作，公开进度为 0/40。<br>Extreme5 的 5 个视频待制作。</p></div>`;};
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
  async function renderHardware() {
    try {
      const response = await fetch("./hardware.json", { cache: "no-store" });
      if (!response.ok) throw new Error("模型参数读取失败");
      const data = await response.json();
      if (data.schema !== "rp1-g1-public-hardware-comparison-v1" || data.joint_rows.length !== 29 || data.per_robot.rp1.actuated_joint_count !== 28 || data.per_robot.g1.actuated_joint_count !== 29) throw new Error("模型参数契约不兼容");
      const joint = name => data.joint_rows.find(r=>r.joint_name===name);
      $("hardware-overview").innerHTML = `<article class="finding-card"><h3>驱动关节与模型质量</h3><div class="finding-values">${["rp1","g1"].map(robot=>`<div><span><i class="dot ${robot}"></i>${robot.toUpperCase()}</span><strong>${data.per_robot[robot].actuated_joint_count}<small>DoF</small></strong><p>${fmt(data.per_robot[robot].model_mass_kg,2)} kg</p></div>`).join("")}</div><p>质量为模型惯性质量之和。G1 多一个腰部 pitch 轴，RP1 该位置为 n/a。</p></article><article class="finding-card"><h3>模型活动范围（ROM）</h3>${[["waist_roll_joint","腰部 roll"],["left_shoulder_roll_joint","左肩 roll"],["left_wrist_roll_joint","左腕 roll"]].map(([name,label])=>`<p><b>${label}</b><br>RP1 ${fmt(joint(name).rp1.effective_constraint_limits.rom_deg,1)}° / G1 ${fmt(joint(name).g1.effective_constraint_limits.rom_deg,1)}°</p>`).join("")}</article><article class="finding-card"><h3>控制与执行器</h3><p>原生位置 PD：目标角 = 默认角 + action × scale。</p>${["rp1","g1"].map(robot=>{const caps=data.joint_rows.filter(r=>r[robot].present).map(r=>r[robot].policy_control.effort_limit_config_Nm);return `<p><b>${robot.toUpperCase()} 配置力矩上限</b><br>${fmt(Math.min(...caps),1)}–${fmt(Math.max(...caps),1)} N·m（依关节）</p>`;}).join("")}<p>实际 force 限制、PD、armature 与摩擦在逐关节明细中列出。</p></article>`;
      const describe = (name, robot) => {
        const r = name[robot]; if (!r.present) return `<p>${robot.toUpperCase()}：n/a · ${escape(r.reason)}</p>`;
        const l=r.effective_constraint_limits, c=r.policy_control, a=r.effective_actuator, axis=r.coordinate_contract, soft=r.training_soft_limit;
        return `<div class="joint-spec"><h4>${robot.toUpperCase()}</h4><p>模型角范围 [${fmt(l.lower_rad,4)}, ${fmt(l.upper_rad,4)}] rad；ROM ${fmt(l.rom_rad,4)} rad。</p><p>实际 force [${a.actuator_forcerange_Nm.map(x=>fmt(x,3)).join(", ")}] N·m；声明速度 ${fmt(c.velocity_limit_declared_rad_s,3)} rad/s；运行器速度限幅：${c.velocity_limit_runtime_clamp ? "启用" : "未启用"}。</p><p>kp ${fmt(c.kp_Nm_per_rad,3)} N·m/rad；kd ${fmt(c.kd_Nm_s_per_rad,3)} N·m·s/rad；scale ${fmt(c.action_scale_rad_per_unit,4)} rad/action；默认角 ${fmt(c.default_zero_action_target_rad,4)} rad。</p><p>armature ${fmt(a.armature_kg_m2,6)} kg·m²；摩擦 ${fmt(a.frictionloss_Nm,3)} N·m；被动阻尼 ${fmt(a.passive_viscous_damping_Nm_s_rad,3)} N·m·s/rad。</p><p>子 body 轴 [${axis.axis_in_child_body_frame.join(", ")}]，参考角 ${fmt(axis.mjcf_reference_angle_rad,3)} rad，正方向按右手规则；父体 ${escape(r.parent_body)} → 子体 ${escape(r.child_body)}。</p><p>训练惩罚软限：${isNumber(soft.factor) ? `保存配置系数 ${fmt(soft.factor,2)}，推导 [${fmt(soft.derived_lower_rad,4)}, ${fmt(soft.derived_upper_rad,4)}] rad；训练 tensor 未直接核验` : "原权重级历史配置未知"}。模型目标角硬裁剪：${c.target_hard_range_clipped ? "启用" : "未启用"}。</p></div>`;
      };
      const summaryCell=r=>r.present ? `<span>[${fmt(r.effective_constraint_limits.lower_deg,1)}, ${fmt(r.effective_constraint_limits.upper_deg,1)}]°</span><span class="metric-detail">ROM ${fmt(r.effective_constraint_limits.rom_deg,1)}°</span>` : `<span class="metric-na">n/a</span>`;
      $("hardware-table").innerHTML = `<table class="hardware-table"><thead><tr><th>解剖关节 / 轴与控制明细</th><th>RP1 模型限位 / ROM</th><th>G1 模型限位 / ROM</th><th>RP1 配置力矩上限</th><th>G1 配置力矩上限</th></tr></thead><tbody>${data.joint_rows.map(row=>`<tr><td><details><summary>${escape(row.joint_name)}</summary><div class="joint-details">${describe(row,"rp1")}${describe(row,"g1")}</div></details></td><td>${summaryCell(row.rp1)}</td><td>${summaryCell(row.g1)}</td><td>${fmt(row.rp1.policy_control?.effort_limit_config_Nm,1)} N·m</td><td>${fmt(row.g1.policy_control?.effort_limit_config_Nm,1)} N·m</td></tr>`).join("")}</tbody></table>`;
    } catch (error) { $("hardware-overview").innerHTML=emptyHTML("模型参数暂时无法载入",error.message); }
  }
  function render() {
    const rows = filteredRows().sort(compareRows), ranks = ranksForMetric(state.data, state.metric);
    renderHeaders(); renderRows(rows, ranks); renderOverview(); renderPairedSummary(); renderExtension(); renderCompletion(); renderMotionChart(); renderFairness(); renderEvidence();
    $("view-aggregate").setAttribute("aria-pressed", String(state.scope === "aggregate")); $("view-per-motion").setAttribute("aria-pressed", String(state.scope === "per_motion"));
    $("sort-direction").textContent = state.direction === "asc" ? "升序 ↑" : "降序 ↓"; $("sort-metric").value = state.metric;
  }
  function populateFilters() {
    const options = (key, values, label) => { $("filter-" + key).innerHTML = `<option value="all">${label}</option>` + values.map(([value, text]) => `<option value="${escape(value)}">${escape(text)}</option>`).join(""); };
    options("dataset", state.data.datasets.map(dataset => [dataset.id, dataset.label]), "全部数据集");
    ["robot", "condition", "mode"].forEach(key => { const values = [...new Set(state.data.results.map(row => row[key]))].sort(); options(key, values.map(value => [value, key === "robot" ? value.toUpperCase() : value]), { robot: "全部机器人", condition: "全部条件", mode: "全部模式" }[key]); });
    options("seed", [...new Set(state.data.results.flatMap(row => row.matched_seed_set))].sort((a, b) => a - b).map(seed => [seed, seed]), "全部 seed");
    $("sort-metric").innerHTML = METRICS.map(metric => `<option value="${metric.key}">${metric.label} (${metric.unit})</option>`).join("");
  }
  function csvCell(value) { let cell = value == null ? "" : String(value); if (/^[\s]*[=+\-@]/.test(cell) && !isNumber(value)) cell = "'" + cell; return '"' + cell.replace(/"/g, '""') + '"'; }
  function csvExport(rows) {
    const base = ["id", "label", "phase", "dataset", "condition", "mode", "robot", "motion_id", "seed", "scope"];
    const header = [...base, "matched_seed_set_json", "coverage_json", "comparison_id", "sample_set_sha256", "case_id", ...PROVENANCE_KEYS, ...WINDOW_KEYS.map(key => "window_" + key), ...COMPLETION_KEYS.map(key => "completion_" + key), ...METRICS.flatMap(metric => [metric.key, metric.key + "_unit", metric.key + "_ci95_json", metric.key + "_n_motions"])];
    return "\uFEFF" + [header, ...rows.map(row => [...base.map(key => row[key]), JSON.stringify(row.matched_seed_set), JSON.stringify(row.coverage), row.pairing.comparison_id, row.pairing.sample_set_sha256, row.pairing.case_id, ...PROVENANCE_KEYS.map(key => row.provenance[key]), ...WINDOW_KEYS.map(key => row.fullwindow?.[key]), ...COMPLETION_KEYS.map(key => key === "ci95" ? JSON.stringify(row.completion[key]) : row.completion[key]), ...METRICS.flatMap(metric => { const cell = row.metrics[metric.key]; return [cell.value, cell.unit, cell.ci95 === null ? null : JSON.stringify(cell.ci95), cell.n_motions]; })])].map(line => line.map(csvCell).join(",")).join("\r\n") + "\r\n";
  }
  function publicExport(data) { return normalizeData(data); }
  function download(contents, name, type) {
    const url = URL.createObjectURL(new Blob([contents], { type })), anchor = document.createElement("a"); anchor.href = url; anchor.download = name; document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function bindEvents() {
    $("filters").addEventListener("submit", event => event.preventDefault());
    ["input", "change"].forEach(event => $("filters").addEventListener(event, () => { state.page = 1; render(); }));
    $("filters").addEventListener("reset", () => setTimeout(() => { state.page = 1; render(); }, 0));
    ["view-aggregate", "view-per-motion"].forEach(id => $(id).addEventListener("click", () => { state.scope = $(id).dataset.scope; state.page = 1; render(); }));
    $("sort-metric").addEventListener("change", () => { state.metric = $("sort-metric").value; state.direction = "asc"; state.page = 1; render(); });
    $("sort-direction").addEventListener("click", () => { state.direction = state.direction === "asc" ? "desc" : "asc"; state.page = 1; render(); });
    $("results-head").addEventListener("click", event => { const button = event.target.closest("button[data-sort]"); if (!button) return; state.direction = state.metric === button.dataset.sort && state.direction === "asc" ? "desc" : "asc"; state.metric = button.dataset.sort; state.page = 1; render(); });
    $("pagination").addEventListener("click", event => { const button = event.target.closest("button[data-page]"); if (!button || button.disabled) return; state.page = Number(button.dataset.page); render(); $("leaderboard").scrollIntoView({ block: "start" }); });
    $("download-json").addEventListener("click", () => download(JSON.stringify(publicExport(state.data), null, 2) + "\n", "rp1-g1-public-v3.json", "application/json;charset=utf-8"));
    $("download-csv").addEventListener("click", () => download(csvExport(filteredRows().sort(compareRows)), `rp1-g1-${state.scope}.csv`, "text/csv;charset=utf-8"));
  }
  async function init() {
    try {
      const response = await fetch("./data.json", { cache: "no-store", credentials: "same-origin" }); if (!response.ok) throw new Error(`公开快照读取失败（HTTP ${response.status}）`);
      state.data = normalizeData(await response.json()); state.loaded = true;
      $("load-notice").textContent = "已载入四项全程误差：45 个共同动作、90 个配对、180 个既有机器人回合、5 个独立比较组。Motion 跟踪任务完成率等待正式核验。";
      $("report-status").textContent = "全程误差已载入 · 任务完成率待核验";
    } catch (error) { state.data = EMPTY; $("load-notice").textContent = `${error.message}。公开结果保持待载入。`; $("load-notice").classList.add("error"); }
    const updated = state.data.stats.updated_utc;
    $("updated-at").textContent = updated ? new Date(updated).toLocaleDateString("zh-CN", { timeZone: "UTC", year: "numeric", month: "long", day: "numeric" }) : "2026年10月14日";
    populateFilters(); bindEvents(); render(); await Promise.all([renderPublicMedia(), renderHardware()]);
  }
  window.LeaderboardUtils = { normalizeData, publicExport, ranksForMetric, csvExport, valueOf, safeURL, linkHTML, coverageText, pairedCaseKey, pairedMotionCases, validPublicMedia, pairedIntervalSVG, metrics: METRICS, fullMetrics: METRICS };
  init();
})();
