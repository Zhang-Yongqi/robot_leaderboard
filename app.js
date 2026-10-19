/* Verified schema4/schema5/schema6/schema7 UI: independent body/wrist, synchronized root, and single endpoint definitions. */
(function () {
  "use strict";
  const BASE_METRICS = [
    { key: "full_body_pos_mm", label: "全程身体位置误差", unit: "mm", digits: 2 },
    { key: "full_body_ori_rad", label: "全程身体姿态误差", unit: "rad", digits: 4 },
    { key: "full_wrist_pos_mm", label: "全程手腕位置误差", unit: "mm", digits: 2 },
    { key: "full_wrist_ori_rad", label: "全程手腕姿态误差", unit: "rad", digits: 4 }
  ];
  const ROOT_METRICS = [
    { key: "full_root_pos_mm", label: "全程根三维位置误差", unit: "mm", digits: 2 },
    { key: "full_root_ori_rad", label: "全程根姿态误差", unit: "rad", digits: 4 }
  ];
  const METRIC_SPECS = [...BASE_METRICS, ...ROOT_METRICS];
  const ENDPOINT_METRICS = [{ key: "root_endpoint_pos_mm", label: "根部终点位置误差", unit: "mm", digits: 2 }];
  const ENDPOINT_SOURCE_SHA = "f932d85e4583544eeb942cd8eecf9804fda26dc849cc96d7d713f481044604f2";
  const ENDPOINT_METRIC_WINDOW = "last_valid_same_time_reference_root_endpoint";
  const ENDPOINT_CONTRACT_KEYS = ["status", "source_sha256", "metrics", "definition"];
  const ENDPOINT_DEFINITION = {"unit": "mm", "label": "根部终点位置误差", "role": "endpoint_position_error", "higher_is_better": false, "sample_count": 1, "window": "last_valid_same_time_reference_root_endpoint"};
  const ENDPOINT_METHOD_DEFINITION = {"window": "last_valid_same_time_reference_root_endpoint", "sample_count_per_episode": 1, "definition": "每回合最后一个合法参考时刻的根三维位置距离，mm；不是全程误差均值", "actual_reference_clock": "同一批既有200Hz物理轨迹在最后合法参考时刻取已有同刻根XYZ；所有参考末帧Ncommon−1合法，末后20ms停留排除", "fixed_anchor": "首个共同有效同刻帧0.02秒固定XY/yaw对齐，绝对Z不移；不使用reset/frame0锚点，不逐帧重拟合", "statistic": "每回合一个终点值；完整固定seed先动作内等权平均，再五个条件组各自动作等权；主数据集不合并", "CI": "沿用PCG64/20261013/10000次配对动作bootstrap，每组重新设seed，linear quantile；CI未作多重比较校正", "not_success_proxy": "完成率独立保留，不由终点位置误差重新判断；失败后末帧仍计入", "existing_six_errors_and_completion_unchanged": true, "new_physical_episodes": 0};
  const DEFAULT_METRIC = "full_body_pos_mm";
  const ROOT_SOURCE_SHA = "ac5a4a25fd0235c2472746135de43c66eb1a091e21be72016a7c8e5bf34ace4e";
  const ROOT_METRIC_WINDOW = "full_replay_50hz_same_time_raw_state_at_reference";
  const ROOT_WINDOW_LABEL = "50 Hz 参考时刻对应的同刻根状态（来自原 200 Hz 轨迹）";
  const ROOT_CONTRACT_KEYS = ["status", "source_sha256", "metrics", "window_label"];
  const ROOT_METHOD_KEYS = ["window", "source", "sampling", "alignment", "position", "orientation", "weighting_and_CI", "old_four_window_unchanged", "completion_unchanged", "completion_does_not_filter_errors", "new_physical_episodes"];
  const ROOT_METHOD_DEFINITION = {"window": "full_replay_50hz_same_time_raw_state_at_reference", "source": "同一批既有物理回放轨迹，不增加物理实验", "sampling": "在原200Hz物理轨迹中按50Hz参考时刻取已有同刻根姿态；有效参考帧1..Ncommon−1完整保留，包含失控后样本，末后停留不计入", "alignment": "第一个共同有效同刻帧0.02秒作固定XY/yaw对齐锚点；Z保持绝对值。不是reset/frame0对齐；不逐帧重拟合", "position": "全窗三维根位置距离的算术均值，mm", "orientation": "实际与参考wxyz四元数单位化，同一固定yaw左乘实际姿态；相对姿态最短旋转角的全窗算术均值，rad；保留roll/pitch误差，q与−q等价", "weighting_and_CI": "完整固定seed先动作内等权，再动作等权；每组独立沿用配对动作PCG64/20261013/10000次/linear quantile", "old_four_window_unchanged": true, "completion_unchanged": true, "completion_does_not_filter_errors": true, "new_physical_episodes": 0};
  const ROOT_WINDOW_KEYS = ["metric_window", "recorded_frames", "reference_start_s", "reference_end_s", "physics_start_s", "physics_end_s"];
  const FULL_WINDOW = "full_replay_50hz_first_substep";
  const CLOCK_WINDOW = "full_replay_50hz_same_time_raw_body_fk_at_reference";
  const CLOCK_SOURCE_SHA = "8531f0cb539d6e713334efcbc6211ae3896f42bd000cd793cb896933a65b061f";
  const CLOCK_CSV_SHA = "ee64fb6c35d368fd6913f29baecb9f63c8b19e8252fe0f81a7207e0b2af2162c";
  const CLOCK_EXTENSION_KEYS = ["status", "source_sha256", "source_csv_sha256", "baseline_source_sha256", "baseline_schema_version", "metrics", "window", "old_root_endpoint_method_flags_scope", "new_physical_episodes"];
  const CLOCK_METHOD_KEYS = ["window", "source", "new_physical_episodes", "sampling", "reference_window", "alignment", "position", "orientation", "precision", "weighting_and_CI", "completion_does_not_filter_errors", "root_endpoint_completion_unchanged", "old_four_cache_timing", "reference_unchanged", "historical_preservation_flags_scope"];
  const TOP_KEYS = ["schema_version", "publication_state", "fullwindow_source_sha256", "identity_map_sha256", "counts", "metrics", "results", "comparisons", "datasets", "phase", "primary_comparison_ids", "secondary_comparison_ids", "methods", "completion_contract", "report_downloads", "fairness", "stats"];
  const ROW_KEYS = ["id", "label", "phase", "dataset", "condition", "mode", "robot", "motion_id", "seed", "scope", "matched_seed_set", "metrics", "completion", "coverage", "pairing", "fullwindow", "provenance"];
  const PROVENANCE_KEYS = ["protocol_sha256", "execution_protocol_sha256", "config_sha256", "source_sha256"];
  const COMPARISON_KEYS = ["id", "label", "phase", "dataset", "condition", "mode", "role", "metric_window", "n_unique_motions", "paired_cases", "episode_records", "matched_seed_set", "expected_participants", "expected_paired_motions", "sample_set", "sample_set_sha256", "paired_deltas", "paired_motion_values", "completion", "fullwindow_comparison_id"];
  const WINDOW_KEYS = ["run_id", "case_id", "metric_window", "full_recorded_frames", "reference_common_frames", "reference_start_s", "reference_end_s"];
  const COMPLETION_KEYS = ["status", "completed", "rate_pct", "ci95", "reason", "evidence_level", "reason_code", "failure_reference_time_s", "failure_physics_time_s", "summary"];
  const COMPLETION_SUMMARY_KEYS = ["seed_counts", "motion_completion_equivalents", "expected_motion_denominator", "expected_seeds_per_motion", "effective_adjudicated_motions", "n_unknown_motions", "integer_completed_motions", "completion_rate", "possible_rate_bounds", "completion_percent", "possible_percent_bounds", "completion_summary_label", "completion_CI_created", "per_motion_rates"];
  const MOTION_RATE_KEYS = ["motion_id", "seed_counts", "expected_seed_denominator", "completion_fraction", "possible_fraction_bounds", "completion_percent", "possible_percent_bounds"];
  const COMPLETION_GROUP_KEYS = ["aggregation_rule", "ratio_unit", "display_unit", "range_type", "completion_CI_created", "interpretation", "robots"];
  const COMPLETION_DEFINITION_KEYS = ["label", "criterion_id", "definition", "statuses", "evidence_levels", "reason_codes", "recovered_midmotion_falls_can_complete", "precision_errors_do_not_define_completion", "point_rate_when_unknown"];
  const COMPLETION_COUNT_KEYS = ["completed", "not_completed", "unknown"];
  const COMPLETION_SOURCE_SHA = "8607a1403d9fbc846a741cb141cd65b07ce7805c7fb0df11cf1f22ecb119905f";
  const REPORTS = [
    { label: "V8 技术报告正文", url: "https://roboparty.feishu.cn/docx/KRsrdYUJXo16iuxPtMpc1JoznOb" },
    { label: "V8 技术报告 PDF", url: "https://roboparty.feishu.cn/file/DzWzbyTyho37zKxYdT5cDZgjnC7" },
    { label: "V8 技术报告 DOCX", url: "https://roboparty.feishu.cn/file/SihQbYLFJoUKyuxkmJ2cQ0dLnce" }
  ];
  const EMPTY = { schema_version: 4, results: [], comparisons: [], datasets: [], counts: {}, methods: {}, report_downloads: [], fairness: [], stats: {}, primary_comparison_ids: [], secondary_comparison_ids: [] };
  const state = { data: EMPTY, scope: "aggregate", metric: DEFAULT_METRIC, direction: "asc", page: 1, pageSize: 25, comparisonCondition: null, loaded: false, overviewDataset: "lafan40", overviewMetric: DEFAULT_METRIC };
  const $ = id => document.getElementById(id);
  const escape = value => String(value == null ? "" : value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const asArray = value => Array.isArray(value) ? value : [];
  const isNumber = value => typeof value === "number" && Number.isFinite(value);
  const knownCount = value => Number.isInteger(value) && value >= 0;
  const sha256 = value => typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
  const fmt = (value, digits = 2) => isNumber(value) ? value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }) : "n/a";
  const signed = (value, digits) => `${value > 0 ? "+" : ""}${fmt(value, digits)}`;
  const valueOf = (row, key) => isNumber(row?.metrics?.[key]?.value) ? row.metrics[key].value : null;
  const metricsFor = data => ([6, 7].includes(data.schema_version) ? [...METRIC_SPECS, ...ENDPOINT_METRICS] : data.schema_version === 5 ? METRIC_SPECS : BASE_METRICS).map(spec => ({ ...spec, label: data.metrics?.[spec.key]?.label || spec.label }));
  const activeMetrics = () => metricsFor(state.data);
  const metricDefinition = key => activeMetrics().find(metric => metric.key === key) || activeMetrics().find(metric => metric.key === DEFAULT_METRIC);
  const datasetLabel = id => state.data.datasets.find(item => item.id === id)?.label || id || "待核验";
  const groupKey = row => JSON.stringify([row.phase, row.dataset, row.condition, row.mode]);
  const REVIEWED_COHORTS = new Map([
    [JSON.stringify(["A", "lafan40", "nominal", "native_position"]), { n: 40, pairs: 40, seeds: [0], role: "primary" }],
    [JSON.stringify(["A", "extreme5", "nominal", "native_position"]), { n: 5, pairs: 5, seeds: [0], role: "primary" }],
    [JSON.stringify(["A", "lafan40", "repeat_nominal", "native_position"]), { n: 5, pairs: 15, seeds: [0, 1, 42], role: "secondary" }],
    [JSON.stringify(["A", "lafan40", "robust_initial_velocity", "native_position"]), { n: 5, pairs: 25, seeds: [0, 1, 2, 3, 4], role: "secondary" }],
    [JSON.stringify(["A", "lafan40", "explicit_sensitivity", "explicit_deploy"]), { n: 5, pairs: 5, seeds: [0], role: "secondary" }]
  ]);
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
  function assertExactKeys(object, keys, label) {
    assertKeys(object, keys, label);
    if (Object.keys(object).length !== keys.length) throw new Error(`${label} 缺少规定字段`);
  }
  const validRange = (values, maximum) => validCI(values) && values[0] >= 0 && values[1] <= maximum;
  const validNullableRate = (value, maximum) => value === null || isNumber(value) && value >= 0 && value <= maximum;
  function validateCompletionSummary(summary) {
    assertExactKeys(summary, COMPLETION_SUMMARY_KEYS, "完成比例汇总");
    assertExactKeys(summary.seed_counts, COMPLETION_COUNT_KEYS, "完成判定 seed 计数");
    assertExactKeys(summary.motion_completion_equivalents, COMPLETION_COUNT_KEYS, "完成动作当量");
    const n = summary.expected_motion_denominator, seeds = summary.expected_seeds_per_motion;
    if (!knownCount(n) || n < 1 || !knownCount(seeds) || seeds < 1 || COMPLETION_COUNT_KEYS.some(key => !knownCount(summary.seed_counts[key]) || !validNullableRate(summary.motion_completion_equivalents[key], n) || summary.motion_completion_equivalents[key] === null) || !validNullableRate(summary.effective_adjudicated_motions, n) || summary.effective_adjudicated_motions === null || !knownCount(summary.n_unknown_motions) || summary.n_unknown_motions > n || (summary.integer_completed_motions !== null && (!knownCount(summary.integer_completed_motions) || summary.integer_completed_motions > n)) || !validNullableRate(summary.completion_rate, 1) || !validNullableRate(summary.completion_percent, 100) || !validRange(summary.possible_rate_bounds, 1) || !validRange(summary.possible_percent_bounds, 100) || summary.completion_CI_created !== false || typeof summary.completion_summary_label !== "string" || !Array.isArray(summary.per_motion_rates) || summary.per_motion_rates.length !== n) throw new Error("完成比例、动作分母或逻辑范围无效");
    if (summary.n_unknown_motions > 0 && (summary.completion_rate !== null || summary.completion_percent !== null)) throw new Error("有未知标签时不得填造完成比例");
    if (seeds > 1 && summary.integer_completed_motions !== null) throw new Error("多 seed 汇总不能宣称整数完成动作数");
    const motions = new Set();
    summary.per_motion_rates.forEach(motion => {
      assertExactKeys(motion, MOTION_RATE_KEYS, "逐动作完成比例");
      assertExactKeys(motion.seed_counts, COMPLETION_COUNT_KEYS, "逐动作 seed 计数");
      if (typeof motion.motion_id !== "string" || motions.has(motion.motion_id) || motion.expected_seed_denominator !== seeds || COMPLETION_COUNT_KEYS.some(key => !knownCount(motion.seed_counts[key])) || !validNullableRate(motion.completion_fraction, 1) || !validNullableRate(motion.completion_percent, 100) || !validRange(motion.possible_fraction_bounds, 1) || !validRange(motion.possible_percent_bounds, 100) || motion.seed_counts.unknown > 0 && (motion.completion_fraction !== null || motion.completion_percent !== null)) throw new Error("逐动作完成比例无效");
      motions.add(motion.motion_id);
    });
  }
  function validateCompletion(completion, scope) {
    assertExactKeys(completion, COMPLETION_KEYS, "动作完成判定");
    if (completion.ci95 !== null || typeof completion.reason !== "string") throw new Error("完成率不提供置信区间");
    if (scope === "aggregate") {
      if (completion.status !== "summarized" || ["completed", "evidence_level", "reason_code", "failure_reference_time_s", "failure_physics_time_s"].some(key => completion[key] !== null)) throw new Error("聚合完成率接口无效");
      validateCompletionSummary(completion.summary);
      if (completion.rate_pct !== completion.summary.completion_percent || completion.reason !== completion.summary.completion_summary_label) throw new Error("完成率须使用来源汇总值");
      return;
    }
    const expected = { completed: [true, "terminal_tracking_complete", "verified_geometry_reference_and_valid_endpoint"], not_completed: [false, "persistent_fall_unable_to_resume", "verified_geometry_reference_and_valid_endpoint"], unknown: [null, "unknown_evidence", "unknown_insufficient_evidence"] }[completion.status];
    if (!expected || completion.completed !== expected[0] || completion.reason_code !== expected[1] || completion.evidence_level !== expected[2] || completion.summary !== null || completion.rate_pct !== null || [completion.failure_reference_time_s, completion.failure_physics_time_s].some(value => value !== null && (!isNumber(value) || value < 0))) throw new Error("逐动作完成判定或证据无效");
    if (completion.status !== "not_completed" && (completion.failure_reference_time_s !== null || completion.failure_physics_time_s !== null)) throw new Error("完成或未知判定不能宣称未恢复时刻");
  }
  function validateCompletionGroup(completion) {
    assertExactKeys(completion, COMPLETION_GROUP_KEYS, "比较组完成汇总");
    assertExactKeys(completion.robots, ["rp1", "g1"], "完成汇总双方");
    if (completion.aggregation_rule !== "seed_binary_mean_within_motion_then_equal_motion_mean" || completion.ratio_unit !== "fraction" || completion.display_unit !== "%" || completion.range_type !== "unknown_label_logical_bounds_not_statistical_CI" || completion.completion_CI_created !== false || typeof completion.interpretation !== "string") throw new Error("完成率统计单位或范围类型无效");
    ["rp1", "g1"].forEach(robot => validateCompletionSummary(completion.robots[robot]));
  }
  function pairedMotionCases(data) {
    const groups = new Map();
    data.results.filter(row => row.scope === "per_motion").forEach(row => { const key = pairedCaseKey(row); if (!groups.has(key)) groups.set(key, []); groups.get(key).push(row); });
    return [...groups.values()].filter(rows => rows.length === 2 && new Set(rows.map(row => row.robot)).size === 2);
  }
  function normalizeData(input) {
    const clockEnabled = input?.schema_version === 7;
    const endpointEnabled = [6, 7].includes(input?.schema_version);
    const fullWindow = clockEnabled ? CLOCK_WINDOW : FULL_WINDOW;
    const rootEnabled = input?.schema_version === 5 || endpointEnabled;
    const metricSpecs = endpointEnabled ? [...METRIC_SPECS, ...ENDPOINT_METRICS] : rootEnabled ? METRIC_SPECS : BASE_METRICS;
    const metricKeys = metricSpecs.map(metric => metric.key);
    assertExactKeys(input, [...TOP_KEYS, ...(rootEnabled ? ["root_extension"] : []), ...(endpointEnabled ? ["endpoint_extension"] : []), ...(clockEnabled ? ["clock_extension"] : [])], "公开快照");
    if (![4, 5, 6, 7].includes(input.schema_version)) throw new Error("公开数据版本不兼容，需要 schema_version: 4、5、6 或 7");
    if (clockEnabled) {
      const extension = input.clock_extension;
      assertExactKeys(extension, CLOCK_EXTENSION_KEYS, "同刻重评分来源合同");
      if (extension.status !== "verified" || extension.source_sha256 !== CLOCK_SOURCE_SHA || extension.source_csv_sha256 !== CLOCK_CSV_SHA || extension.baseline_source_sha256 !== ENDPOINT_SOURCE_SHA || extension.baseline_schema_version !== 6 || extension.window !== CLOCK_WINDOW || extension.new_physical_episodes !== 0 || !Array.isArray(extension.metrics) || extension.metrics.length !== 4 || BASE_METRICS.some(metric => !extension.metrics.includes(metric.key)) || typeof extension.old_root_endpoint_method_flags_scope !== "string") throw new Error("同刻重评分来源或旧轨迹范围未核验");
    }
    if (endpointEnabled) {
      const extension = input.endpoint_extension;
      assertExactKeys(extension, ENDPOINT_CONTRACT_KEYS, "根部终点来源合同");
      assertExactKeys(extension.definition, Object.keys(ENDPOINT_DEFINITION), "根部终点定义");
      if (extension.status !== "verified" || extension.source_sha256 !== ENDPOINT_SOURCE_SHA || !Array.isArray(extension.metrics) || extension.metrics.length !== 1 || extension.metrics[0] !== "root_endpoint_pos_mm" || Object.keys(ENDPOINT_DEFINITION).some(key => extension.definition[key] !== ENDPOINT_DEFINITION[key])) throw new Error("根部终点来源、末帧定义或单样本合同未核验");
    }
    if (rootEnabled) {
      assertExactKeys(input.root_extension, ROOT_CONTRACT_KEYS, "root 来源合同");
      if (input.root_extension.status !== "verified" || !sha256(input.root_extension.source_sha256) || input.root_extension.source_sha256 !== ROOT_SOURCE_SHA || !Array.isArray(input.root_extension.metrics) || input.root_extension.metrics.length !== 2 || ROOT_METRICS.some(metric => !input.root_extension.metrics.includes(metric.key)) || input.root_extension.window_label !== ROOT_WINDOW_LABEL) throw new Error("root 来源、指标或独立采样窗未核验");
    }
    if (input.phase !== "A" || input.publication_state !== (clockEnabled ? "fullwindow_semantic_completion_root_endpoint_clock_corrected_published" : endpointEnabled ? "fullwindow_semantic_completion_root_endpoint_published" : rootEnabled ? "fullwindow_semantic_completion_root_metrics_published" : "fullwindow_semantic_completion_published") || input.fullwindow_source_sha256 !== COMPLETION_SOURCE_SHA || !sha256(input.identity_map_sha256)) throw new Error("公开结果身份或科学来源版本不兼容");
    ["results", "comparisons", "datasets", "primary_comparison_ids", "secondary_comparison_ids", "report_downloads", "fairness"].forEach(key => { if (!Array.isArray(input[key])) throw new Error(`缺少公开数组 ${key}`); });
    const counts = { episode_records: 180, paired_cases: 90, unique_motions: 45, comparison_groups: 5, aggregate_rows: 10, result_rows: 190 };
    if (Object.entries(counts).some(([key, count]) => input.counts?.[key] !== count) || input.results.length !== 190 || input.comparisons.length !== 5 || input.datasets.length !== 2) throw new Error("公开配对数量不一致");
    if (Object.keys(input.metrics || {}).length !== metricSpecs.length || metricSpecs.some(metric => input.metrics[metric.key]?.unit !== metric.unit || input.metrics[metric.key]?.higher_is_better !== false)) throw new Error("误差指标白名单、单位或方向不一致");
    assertKeys(input.counts, Object.keys(counts), "公开数量");
    assertExactKeys(input.methods, ["fullwindow", "units", "weighting", "bootstrap", "completion", ...(rootEnabled ? ["root"] : []), ...(endpointEnabled ? ["root_endpoint"] : []), ...(clockEnabled ? ["clock_rescore"] : [])], "方法");
    if (clockEnabled) {
      const method = input.methods.clock_rescore;
      assertExactKeys(method, CLOCK_METHOD_KEYS, "同刻重评分方法");
      if (method.window !== CLOCK_WINDOW || method.new_physical_episodes !== 0 || method.completion_does_not_filter_errors !== true || method.root_endpoint_completion_unchanged !== true || method.reference_unchanged !== true || CLOCK_METHOD_KEYS.filter(key => !["completion_does_not_filter_errors", "root_endpoint_completion_unchanged", "reference_unchanged", "new_physical_episodes"].includes(key)).some(key => typeof method[key] !== "string" || !method[key])) throw new Error("同刻重评分方法或不变量未核验");
    }
    if (rootEnabled) {
      assertExactKeys(input.methods.root, ROOT_METHOD_KEYS, "root 独立方法");
      if (ROOT_METHOD_KEYS.some(key => input.methods.root[key] !== ROOT_METHOD_DEFINITION[key])) throw new Error("root 定义与采样窗未提供");
    }
    if (endpointEnabled) {
      assertExactKeys(input.methods.root_endpoint, Object.keys(ENDPOINT_METHOD_DEFINITION), "根部终点独立方法");
      if (Object.keys(ENDPOINT_METHOD_DEFINITION).some(key => input.methods.root_endpoint[key] !== ENDPOINT_METHOD_DEFINITION[key])) throw new Error("根部终点须使用最后合法同刻帧与固定对齐");
    }
    assertExactKeys(input.methods.completion, COMPLETION_DEFINITION_KEYS, "任务完成定义");
    assertExactKeys(input.methods.completion.statuses, ["completed", "not_completed", "unknown"], "任务完成状态定义");
    assertExactKeys(input.methods.completion.reason_codes, ["terminal_tracking_complete", "persistent_fall_unable_to_resume", "unknown_evidence"], "任务完成依据定义");
    if (input.methods.completion.criterion_id !== "fall_recovery_terminal_tracking_v2" || input.methods.completion.recovered_midmotion_falls_can_complete !== true || input.methods.completion.precision_errors_do_not_define_completion !== true) throw new Error("任务完成判据版本不兼容");
    assertKeys(input.methods.bootstrap, ["resampling_unit", "generator", "seed", "resamples", "confidence", "quantile_method", "reset_per_group_and_metric", "shared_indices_for_robots", "delta_direction"], "区间方法");
    assertExactKeys(input.completion_contract, ["status", "rule_version", "source_sha256"], "完成判定版本");
    if (input.completion_contract.status !== "verified" || input.completion_contract.rule_version !== input.methods.completion.criterion_id || input.completion_contract.source_sha256 !== COMPLETION_SOURCE_SHA) throw new Error("完成判定来源或版本不匹配");
    input.datasets.forEach(dataset => assertKeys(dataset, ["id", "label", "expected_motions"], "数据集"));
    metricSpecs.forEach(metric => {
      assertExactKeys(input.metrics[metric.key], ["unit", "label", "higher_is_better"], "指标定义");
      if (typeof input.metrics[metric.key].label !== "string" || !input.metrics[metric.key].label.trim()) throw new Error("指标名称未提供");
    });
    input.report_downloads.forEach(report => assertKeys(report, ["label", "url", "access"], "报告链接"));
    input.fairness.forEach(item => assertKeys(item, ["item", "rp1", "g1", "status", "evidence", "phase", "condition", "mode"], "公平条件"));
    assertKeys(input.stats, ["report_status", "updated_utc", "notes", "limitations"], "公开说明");
    const ids = new Set(), cases = new Set(), runs = new Map();
    input.results.forEach(row => {
      assertKeys(row, rootEnabled ? [...ROW_KEYS, "rootwindow"] : ROW_KEYS, "公开记录");
      if (typeof row.id !== "string" || ids.has(row.id) || row.phase !== "A" || !["rp1", "g1"].includes(row.robot) || !["aggregate", "per_motion"].includes(row.scope)) throw new Error("公开记录身份无效");
      ids.add(row.id); validateCompletion(row.completion, row.scope);
      if (row.scope === "per_motion" && row.completion.reason !== input.methods.completion.reason_codes[row.completion.reason_code]) throw new Error("判定依据文字须保持来源定义");
      assertKeys(row.provenance, PROVENANCE_KEYS, "记录来源身份");
      if (Object.keys(row.provenance).length !== PROVENANCE_KEYS.length || PROVENANCE_KEYS.some(key => row.provenance[key] !== null && !sha256(row.provenance[key]))) throw new Error("记录来源摘要须为 SHA256 或原缺失 null");
      if (!Array.isArray(row.matched_seed_set) || row.matched_seed_set.some(seed => !Number.isSafeInteger(seed) || seed < 0)) throw new Error("seed 集无效");
      assertKeys(row.metrics, metricKeys, "误差指标");
      metricSpecs.forEach(metric => {
        const cell = row.metrics[metric.key]; assertKeys(cell, ["value", "unit", "ci95", "n_motions"], "指标单元格");
        if (!isNumber(cell.value) || metric.key === "root_endpoint_pos_mm" && cell.value < 0 || cell.unit !== metric.unit || !knownCount(cell.n_motions) || cell.n_motions < 1 || (row.scope === "aggregate" ? !validCI(cell.ci95) : cell.ci95 !== null || cell.n_motions !== 1)) throw new Error("误差指标数值或区间无效");
      });
      assertKeys(row.coverage, ["numerator", "denominator", "unit"], "覆盖");
      if (!knownCount(row.coverage.numerator) || row.coverage.numerator !== row.coverage.denominator || row.coverage.numerator !== (row.scope === "per_motion" ? 1 : row.metrics[DEFAULT_METRIC].n_motions) || row.coverage.unit !== (row.scope === "per_motion" ? "episodes" : "motions")) throw new Error("覆盖分母无效");
      assertKeys(row.pairing, ["comparison_id", "sample_set_sha256", "case_id"], "配对身份");
      if (!sha256(row.pairing.sample_set_sha256)) throw new Error("配对集合身份无效");
      if (row.scope === "per_motion") {
        assertKeys(row.fullwindow, WINDOW_KEYS, "全程评分窗口");
        if (!Number.isSafeInteger(row.seed) || row.seed < 0 || row.matched_seed_set.length !== 1 || row.matched_seed_set[0] !== row.seed || !row.motion_id || row.fullwindow.metric_window !== fullWindow || row.fullwindow.full_recorded_frames !== row.fullwindow.reference_common_frames - 1) throw new Error("全程回合窗口或 seed 身份无效");
        if (typeof row.fullwindow.run_id !== "string" || runs.has(row.fullwindow.run_id) || row.fullwindow.case_id !== row.pairing.case_id || !isNumber(row.fullwindow.reference_start_s) || !isNumber(row.fullwindow.reference_end_s) || row.fullwindow.reference_start_s > row.fullwindow.reference_end_s) throw new Error("评分窗口来源身份无效");
        if (rootEnabled) {
          assertExactKeys(row.rootwindow, ROOT_WINDOW_KEYS, "root 独立回合窗口");
          if (row.rootwindow.metric_window !== ROOT_METRIC_WINDOW || !Number.isInteger(row.rootwindow.recorded_frames) || row.rootwindow.recorded_frames !== row.fullwindow.full_recorded_frames || ROOT_WINDOW_KEYS.filter(key => key.endsWith("_s")).some(key => !isNumber(row.rootwindow[key])) || row.rootwindow.reference_start_s !== row.fullwindow.reference_start_s || row.rootwindow.reference_end_s !== row.fullwindow.reference_end_s || row.rootwindow.reference_start_s > row.rootwindow.reference_end_s || row.rootwindow.physics_start_s > row.rootwindow.physics_end_s || row.rootwindow.physics_start_s !== row.rootwindow.reference_start_s || row.rootwindow.physics_end_s !== row.rootwindow.reference_end_s) throw new Error("root 独立回合采样窗无效");
        }
        runs.set(row.fullwindow.run_id, row);
        const identity = JSON.stringify([pairedCaseKey(row), row.robot]); if (cases.has(identity)) throw new Error("重复机器人回合"); cases.add(identity);
      } else if (row.seed !== null || row.fullwindow != null || row.rootwindow != null) throw new Error("聚合行接口无效");
    });
    const pairs = pairedMotionCases(input), motions = new Set(pairs.map(rows => JSON.stringify([rows[0].dataset, rows[0].motion_id])));
    if (pairs.length !== 90 || motions.size !== 45 || cases.size !== 180 || input.results.filter(row => row.scope === "aggregate").length !== 10) throw new Error("实际回合配对数量不一致");
    const comparisonIds = new Set(), aggregateIds = new Set(), cohortKeys = new Set();
    input.comparisons.forEach(comparison => {
      assertKeys(comparison, COMPARISON_KEYS, "比较组"); validateCompletionGroup(comparison.completion);
      if (comparisonIds.has(comparison.id) || comparison.metric_window !== fullWindow || !sha256(comparison.sample_set_sha256) || comparison.expected_participants?.length !== 2 || comparison.sample_set?.length !== comparison.paired_cases) throw new Error("比较组身份或覆盖无效");
      const cohort = REVIEWED_COHORTS.get(groupKey(comparison));
      if (!cohort || cohortKeys.has(groupKey(comparison)) || comparison.n_unique_motions !== cohort.n || comparison.expected_paired_motions !== cohort.n || comparison.paired_cases !== cohort.pairs || comparison.role !== cohort.role || JSON.stringify(comparison.matched_seed_set) !== JSON.stringify(cohort.seeds)) throw new Error("比较组分母不一致");
      cohortKeys.add(groupKey(comparison));
      comparisonIds.add(comparison.id);
      const members = comparison.expected_participants.map(id => input.results.find(row => row.id === id));
      if (members.some(row => !row || row.scope !== "aggregate" || groupKey(row) !== groupKey(comparison) || row.pairing.comparison_id !== comparison.id || row.pairing.sample_set_sha256 !== comparison.sample_set_sha256 || JSON.stringify(row.matched_seed_set) !== JSON.stringify(cohort.seeds)) || new Set(members.map(row => row.robot)).size !== 2) throw new Error("比较组不能对应原聚合身份");
      members.forEach(row => { if (aggregateIds.has(row.id)) throw new Error("聚合身份重复使用"); aggregateIds.add(row.id); });
      members.forEach(row => {
        const summary = comparison.completion.robots[row.robot];
        if (JSON.stringify(row.completion.summary) !== JSON.stringify(summary) || summary.expected_motion_denominator !== comparison.n_unique_motions || summary.expected_seeds_per_motion !== comparison.matched_seed_set.length) throw new Error("聚合完成率须保持比较组原汇总");
      });
      const episodes = input.results.filter(row => row.scope === "per_motion" && groupKey(row) === groupKey(comparison));
      if (episodes.length !== comparison.episode_records || episodes.length !== comparison.paired_cases * 2 || new Set(episodes.map(row => row.motion_id)).size !== comparison.n_unique_motions || members.some(row => metricSpecs.some(metric => row.metrics[metric.key].n_motions !== comparison.n_unique_motions))) throw new Error("比较组分母不一致");
      const motionIds = new Set(episodes.map(row => row.motion_id));
      motionIds.forEach(motion => ["rp1", "g1"].forEach(robot => {
        const seeds = episodes.filter(row => row.motion_id === motion && row.robot === robot).map(row => row.seed).sort((left, right) => left - right);
        if (JSON.stringify(seeds) !== JSON.stringify(cohort.seeds)) throw new Error("比较组分母不一致");
      }));
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
      assertKeys(comparison.paired_motion_values, metricKeys, "动作级统计");
      metricSpecs.forEach(metric => {
        const values = comparison.paired_motion_values[metric.key];
        if (!Array.isArray(values) || values.length !== comparison.n_unique_motions || new Set(values.map(value => value.motion_id)).size !== comparison.n_unique_motions) throw new Error("动作级统计分母无效");
        values.forEach(value => { assertKeys(value, ["motion_id", "rp1", "g1", "delta_rp1_minus_g1", "seeds", "repeats_per_robot"], "动作级数值"); if (![value.rp1, value.g1, value.delta_rp1_minus_g1].every(isNumber) || !motionIds.has(value.motion_id) || JSON.stringify(value.seeds) !== JSON.stringify(cohort.seeds) || value.repeats_per_robot !== cohort.seeds.length) throw new Error("动作级数值无效"); });
      });
      assertKeys(comparison.paired_deltas, metricKeys, "误差配对差");
      metricSpecs.forEach(metric => { const delta = comparison.paired_deltas[metric.key]; assertKeys(delta, ["value", "ci95", "unit", "n_motions"], "配对差值"); if (!isNumber(delta.value) || !validCI(delta.ci95) || delta.unit !== metric.unit || delta.n_motions !== comparison.n_unique_motions) throw new Error("误差配对区间无效"); });
    });
    if (aggregateIds.size !== 10 || input.primary_comparison_ids.length !== 2 || input.secondary_comparison_ids.length !== 3 || new Set([...input.primary_comparison_ids, ...input.secondary_comparison_ids]).size !== 5 || input.primary_comparison_ids.some(id => input.comparisons.find(group => group.id === id)?.role !== "primary") || input.secondary_comparison_ids.some(id => input.comparisons.find(group => group.id === id)?.role !== "secondary")) throw new Error("主组与敏感性组身份不一致");
    const output = JSON.parse(JSON.stringify(input));
    output.results = output.results.map(row => ({ ...row, provenance: pick(row.provenance, PROVENANCE_KEYS) }));
    return output;
  }
  function filters() { return Object.fromEntries(["phase", "robot", "dataset", "condition", "mode", "seed", "completion", "search"].map(key => [key, $("filter-" + key).value])); }
  function filteredRows(scope = state.scope) {
    const selected = filters(), query = selected.search.trim().toLowerCase();
    return state.data.results.filter(row => row.scope === scope && ["phase", "robot", "dataset", "condition", "mode"].every(key => selected[key] === "all" || String(row[key]) === selected[key]) && (selected.seed === "all" || row.matched_seed_set.map(String).includes(selected.seed)) && (selected.completion === "all" || row.scope === "aggregate" || row.completion.status === selected.completion) && (!query || [row.label, row.motion_id, row.id, window.RoboI18n?.searchText(row.label)].some(value => String(value || "").toLowerCase().includes(query))));
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
  const conditionLabel = condition => ({ aligned_nominal: "主基线", nominal: "主基线", repeat_nominal: "重复名义条件", robust_initial_velocity: "初态速度扰动", explicit_sensitivity: "显式执行敏感性" }[condition] || condition);
  function comparisonBestStates(values, digits, higherIsBetter = false) {
    const comparable = ["rp1", "g1"].every(robot => isNumber(values[robot]));
    if (!comparable) return { rp1: null, g1: null };
    if (fmt(values.rp1, digits) === fmt(values.g1, digits)) return { rp1: "tie", g1: "tie" };
    const best = higherIsBetter === (values.rp1 > values.g1) ? "rp1" : "g1";
    return { rp1: best === "rp1" ? "best" : null, g1: best === "g1" ? "best" : null };
  }
  function comparisonValueHTML(value, digits, unit, advantage, detail = "") {
    const badge = advantage ? `<span class="comparison-best-label">${advantage === "tie" ? "并列" : "较优"}</span>` : "";
    return `<td class="comparison-number${advantage ? ` numeric-${advantage}` : ""}">${isNumber(value) ? `<strong class="comparison-value">${fmt(value, digits)}<small>${escape(unit)}</small></strong>` : '<span class="comparison-missing">n/a</span>'}${badge}${detail}</td>`;
  }
  function comparisonTableHTML(data, comparison) {
    const members = comparison.expected_participants.map(id => data.results.find(row => row.id === id));
    const byRobot = Object.fromEntries(members.filter(Boolean).map(row => [row.robot, row]));
    const errorRows = metricsFor(data).map(metric => {
      const values = Object.fromEntries(["rp1", "g1"].map(robot => [robot, valueOf(byRobot[robot], metric.key)]));
      const best = comparisonBestStates(values, metric.digits);
      const delta = comparison.paired_deltas[metric.key];
      return `<tr data-metric="${escape(metric.key)}"><th scope="row">${escape(metric.label)}<span class="comparison-direction">${escape(metric.unit)} · 越低越好 ↓</span></th>${["rp1", "g1"].map(robot => { const cell = byRobot[robot]?.metrics?.[metric.key]; return comparisonValueHTML(values[robot], metric.digits, metric.unit, best[robot], validCI(cell?.ci95) ? `<span class="comparison-ci">95% CI [${fmt(cell.ci95[0], metric.digits)}, ${fmt(cell.ci95[1], metric.digits)}]</span>` : ""); }).join("")}<td class="comparison-delta">${isNumber(delta?.value) ? `<strong>${signed(delta.value, metric.digits)} <small>${escape(metric.unit)}</small></strong>` : '<span class="comparison-missing">n/a</span>'}${validCI(delta?.ci95) ? `<span class="comparison-ci">95% CI [${fmt(delta.ci95[0], metric.digits)}, ${fmt(delta.ci95[1], metric.digits)}]</span>` : ""}</td></tr>`;
    }).join("");
    const completionValues = Object.fromEntries(["rp1", "g1"].map(robot => [robot, byRobot[robot]?.completion?.rate_pct]));
    const completionDigits = ["rp1", "g1"].every(robot => !isNumber(completionValues[robot]) || Number.isInteger(completionValues[robot])) ? 0 : 1;
    const completionBest = comparisonBestStates(completionValues, completionDigits, true);
    const completionRow = `<tr data-metric="completion"><th scope="row">Motion 跟踪任务完成率<span class="comparison-direction">% · 越高越好 ↑</span></th>${["rp1", "g1"].map(robot => { const summary = byRobot[robot]?.completion?.summary; const detail = summary ? summary.integer_completed_motions !== null ? `${summary.integer_completed_motions} / ${summary.expected_motion_denominator} 个动作完成` : `完成动作当量 ${fmt(summary.motion_completion_equivalents.completed, 2)} / ${summary.expected_motion_denominator}<br>动作等权平均比例` : ""; return comparisonValueHTML(completionValues[robot], completionDigits, "%", completionBest[robot], detail ? `<span class="comparison-ci">${detail}</span>` : ""); }).join("")}<td class="comparison-delta"><span class="comparison-ci">${comparison.matched_seed_set.length > 1 ? "先动作内平均 seed，再动作等权" : "按固定动作分母"}</span></td></tr>`;
    return `<div class="table-scroll comparison-scroll" tabindex="0" role="region" aria-label="${escape(comparison.label)}数值对比"><table class="comparison-table" data-comparison-id="${escape(comparison.id)}"><caption class="sr-only">${escape(comparison.label)}，${comparison.n_unique_motions} 个配对动作；每项均值、双方区间及 RP1 减 G1 配对差。</caption><thead><tr><th scope="col">指标 / 单位 / 方向</th><th scope="col"><i class="dot rp1" aria-hidden="true"></i> RP1</th><th scope="col"><i class="dot g1" aria-hidden="true"></i> G1</th><th scope="col">配对差 RP1 − G1</th></tr></thead><tbody>${errorRows}${completionRow}</tbody></table></div>`;
  }
  function comparisonPanelHTML(data, comparison, heading) {
    const title = heading || conditionLabel(comparison.condition);
    return `<article class="comparison-panel"><div class="comparison-panel-heading"><h4>${escape(title)}</h4><p>${comparison.n_unique_motions} 个配对动作（N=${comparison.n_unique_motions}） · ${comparison.episode_records} 回合</p><span>${escape(conditionLabel(comparison.condition))} · ${escape(comparison.mode)} · seeds ${comparison.matched_seed_set.join(", ")}</span></div>${comparisonTableHTML(data, comparison)}</article>`;
  }
  function renderComparisonTables() {
    const primary = state.data.primary_comparison_ids.map(id => state.data.comparisons.find(item => item.id === id)).filter(Boolean);
    $("comparison-primary").innerHTML = primary.length ? primary.map(comparison => comparisonPanelHTML(state.data, comparison, comparison.dataset === "lafan40" ? "Common40" : "Extreme5")).join("") : emptyHTML("配对数值表暂未载入", "等待正式公开结果。");
    const secondary = state.data.secondary_comparison_ids.map(id => state.data.comparisons.find(item => item.id === id)).filter(Boolean);
    $("comparison-secondary-section").hidden = !secondary.length;
    if (!secondary.length) { $("comparison-secondary").innerHTML = ""; $("comparison-condition").innerHTML = ""; return; }
    if (!secondary.some(comparison => comparison.id === state.comparisonCondition)) state.comparisonCondition = secondary[0].id;
    $("comparison-condition").innerHTML = secondary.map(comparison => `<option value="${escape(comparison.id)}">${escape(conditionLabel(comparison.condition))}</option>`).join("");
    $("comparison-condition").value = state.comparisonCondition;
    $("comparison-secondary").innerHTML = comparisonPanelHTML(state.data, secondary.find(comparison => comparison.id === state.comparisonCondition));
  }
  const completionPercent = value => `${fmt(value, Number.isInteger(value) ? 0 : 1)}%`;
  function completionEvidenceHTML(completion) {
    const level = completion.evidence_level === "verified_geometry_reference_and_valid_endpoint" ? "参考几何与有效动作末端已核验" : "现有证据不足";
    const hasTime = isNumber(completion.failure_reference_time_s) || isNumber(completion.failure_physics_time_s);
    return `<details class="completion-evidence"><summary>判定依据</summary><p>${escape(completion.reason)}</p><p>${level}</p>${hasTime ? `<p>最终持续未恢复区间起点（几何观察）<br>参考时间 ${fmt(completion.failure_reference_time_s, 3)} s<br>物理时间 ${fmt(completion.failure_physics_time_s, 3)} s</p>` : ""}</details>`;
  }
  function completionHTML(row, compact = false) {
    const completion = row.completion;
    if (row.scope === "per_motion") {
      const label = { completed: "完成", not_completed: "未完成", unknown: "待判定" }[completion.status];
      return `<span class="completion-result ${completion.completed === true ? "finished" : completion.completed === false ? "unfinished" : "undetermined"}">${label}</span>${compact ? "" : completionEvidenceHTML(completion)}`;
    }
    const summary = completion.summary;
    const amount = summary.integer_completed_motions !== null ? `${summary.integer_completed_motions} / ${summary.expected_motion_denominator} 个动作完成` : `完成动作当量 ${fmt(summary.motion_completion_equivalents.completed, 2)} / ${summary.expected_motion_denominator}`;
    const unknown = summary.n_unknown_motions > 0 ? `<span class="metric-detail">${summary.n_unknown_motions} 个动作含未知标签；逻辑范围 [${fmt(summary.possible_percent_bounds[0], 1)}, ${fmt(summary.possible_percent_bounds[1], 1)}]%</span>` : "";
    return `${isNumber(completion.rate_pct) ? `<span class="metric-value">${completionPercent(completion.rate_pct)}</span>` : '<span class="completion-pending">待判定</span>'}<span class="metric-detail">${escape(amount)}</span>${summary.integer_completed_motions === null ? '<span class="metric-detail">动作等权平均完成比例</span>' : ""}${unknown}`;
  }
  function completionGroup(group) {
    if (!group) return emptyHTML("Motion 跟踪任务完成率暂未载入", "请检查正式公开快照。");
    return `<div class="completion-robots">${["rp1", "g1"].map(robot => { const row = group.rows.find(item => item.robot === robot); return `<div><h4><i class="dot ${robot}"></i>${robot.toUpperCase()}</h4>${completionHTML(row)}<p>${group.comparison.n_unique_motions} 个配对动作</p></div>`; }).join("")}</div>`;
  }
  function renderOverview() {
    const counts = state.data.counts;
    $("overview").innerHTML = state.loaded ? `<div class="scope-item"><strong>${counts.unique_motions}</strong><p><b>共同动作</b>两套主数据集分别报告</p></div><div class="scope-item"><strong>${counts.paired_cases}</strong><p><b>条件与 seed 配对</b>${counts.episode_records} 个机器人回合</p></div><div class="scope-item"><strong>${counts.comparison_groups}</strong><p><b>独立评测组</b>重复 seed 不增加动作数</p></div>` : emptyHTML("公开结果待载入", "当前未读取通过版本核验的共同配对数据。");
  }
  function fullFindingCards(group) {
    return activeMetrics().map(metric => {
      const delta = group.comparison.paired_deltas[metric.key];
      const interpretation = delta.ci95[1] < 0 ? "RP1 误差较低，配对区间低于零。" : delta.ci95[0] > 0 ? "G1 误差较低，配对区间高于零。" : "配对区间跨零，当前样本未支持明确方向。";
      return `<article class="finding-card"><h3>${metric.label}</h3><p class="metric-caption">${metric.key === "root_endpoint_pos_mm" ? "最后合法同刻参考末帧 · " : ""}越低越好 · ${delta.n_motions} 个配对动作（N=${delta.n_motions}）</p><div class="finding-values">${["rp1", "g1"].map(robot => `<div><span><i class="dot ${robot}"></i>${robot.toUpperCase()}</span><strong>${fmt(valueOf(group.rows.find(row => row.robot === robot), metric.key), metric.digits)}<small>${metric.unit}</small></strong></div>`).join("")}</div><p class="delta-label">配对差值 RP1 − G1</p>${pairedIntervalSVG(delta, metric.digits, metric.unit)}<p class="delta-ci">${signed(delta.value, metric.digits)} ${metric.unit} · 95% CI [${fmt(delta.ci95[0], metric.digits)}, ${fmt(delta.ci95[1], metric.digits)}]</p><p class="finding-interpretation">${interpretation}</p></article>`;
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
    $("paired-summary").innerHTML = group ? fullFindingCards(group) : emptyHTML("全程指标暂未载入", "等待正式指标数据。");
    renderOverviewChart();
  }
  function renderOverviewChart() {
    const group = fullGroup(state.overviewDataset), metric = metricDefinition(state.overviewMetric);
    if (!group) { $("hero-chart").innerHTML = emptyHTML("全程配对摘要暂未载入", "请检查公开快照及载入状态。"); return; }
    const key = metric.key, delta = group.comparison.paired_deltas[key], maximum = Math.max(...group.rows.map(row => valueOf(row, key))) || 1;
    const context = key === "root_endpoint_pos_mm" ? "每回合一个合法末帧 · 越低越好" : key.startsWith("full_root_") ? "参考同刻根误差的全窗均值 · 越低越好" : "全部评分序列 · 越低越好";
    const interpretation = delta.ci95[1] < 0 ? "RP1 误差较低，配对区间低于零。" : delta.ci95[0] > 0 ? "G1 误差较低，配对区间高于零。" : "配对区间跨零，当前样本未支持明确方向。";
    $("hero-chart").innerHTML = `<p class="eyebrow">${group.comparison.dataset === "lafan40" ? "COMMON40" : "EXTREME5"} / ${key === "root_endpoint_pos_mm" ? "ENDPOINT" : "FULL WINDOW"} / ${delta.n_motions} PAIRED MOTIONS</p><h2>${escape(metric.label)}</h2><p class="chart-context">${context}</p>${["rp1", "g1"].map(robot => { const value = valueOf(group.rows.find(row => row.robot === robot), key); return `<div class="bar-row"><div class="bar-label"><span><i class="dot ${robot}"></i>${robot.toUpperCase()}</span><strong>${fmt(value, metric.digits)}<small>${metric.unit}</small></strong></div><div class="bar-track" aria-hidden="true"><div class="bar-fill ${robot}" style="width:${value / maximum * 100}%"></div></div></div>`; }).join("")}<div class="hero-delta"><p>RP1 − G1 <strong>${signed(delta.value, metric.digits)}<small> ${metric.unit}</small></strong></p><p class="ci-text">95% CI [${fmt(delta.ci95[0], metric.digits)}, ${fmt(delta.ci95[1], metric.digits)}] ${metric.unit} · ${delta.n_motions} 个配对动作（N=${delta.n_motions}）</p>${pairedIntervalSVG(delta, metric.digits, metric.unit, true)}<p class="hero-conclusion">${interpretation}</p></div>`;
  }
  function renderExtension() {
    const group = fullGroup("extreme5");
    $("extreme-results").innerHTML = `<div class="section-heading compact"><div><p class="eyebrow">EXTREME5 / INDEPENDENT GROUP</p><h3>空翻与转体：5 个配对动作（N=5）</h3><p>踢月转体、侧空翻、后空翻、前空翻与毽子后空翻，共 10 个机器人回合，独立报告。</p></div><span class="scope-label">5 / 5 共同动作</span></div><div class="finding-grid full-finding-grid">${group ? fullFindingCards(group) : emptyHTML("Extreme5 全程指标暂未载入", "请检查公开快照及载入状态。")}</div><p class="result-note">本组视频待制作。</p>`;
  }
  function renderCompletion() {
    $("completion-summary").innerHTML = ["lafan40", "extreme5"].map(dataset => `<article class="completion-card"><h3>${dataset === "lafan40" ? "Common40 · 40 个配对动作" : "Extreme5 · 5 个配对动作"}</h3>${completionGroup(fullGroup(dataset))}</article>`).join("");
    const secondary = state.data.comparisons.filter(item => state.data.secondary_comparison_ids.includes(item.id));
    const conditionLabels = { repeat_nominal: "重复名义条件", robust_initial_velocity: "初态速度扰动", explicit_sensitivity: "显式执行敏感性" };
    $("completion-secondary").innerHTML = secondary.length ? `<details class="disclosure"><summary>三个敏感性组的完成比例<span>各 5 个动作 · 动作等权</span></summary><div class="detail-content"><div class="table-scroll"><table class="completion-secondary-table"><thead><tr><th>条件 / 完整 seed 集</th><th>动作数</th><th>RP1</th><th>G1</th></tr></thead><tbody>${secondary.map(comparison => `<tr><td>${escape(conditionLabels[comparison.condition] || comparison.condition)}<span class="record-meta">${escape(comparison.mode)} · seeds ${comparison.matched_seed_set.join(", ")}</span></td><td>${comparison.n_unique_motions}</td>${["rp1", "g1"].map(robot => `<td>${completionHTML(state.data.results.find(row => row.id === comparison.expected_participants.find(id => state.data.results.find(item => item.id === id)?.robot === robot)))}</td>`).join("")}</tr>`).join("")}</tbody></table></div><p>同动作的 seed 判定先平均，再对动作等权；此处按完成动作当量报告，重复 seed 不扩增动作分母。</p></div></details>` : "";
    const selectedCases = new Set(filteredRows("per_motion").map(pairedCaseKey));
    const matchedCases = pairedMotionCases(state.data).filter(rows => selectedCases.has(pairedCaseKey(rows[0])));
    const cases = matchedCases.slice(0, 30);
    $("completion-chart").innerHTML = cases.length ? `<div class="table-scroll"><table class="completion-table"><thead><tr><th>动作 / 条件 / seed</th><th>RP1</th><th>G1</th></tr></thead><tbody>${cases.map(rows => `<tr><td>${escape(rows[0].motion_id)}<span class="record-meta">${escape(rows[0].condition)} · ${escape(rows[0].mode)} · seed ${rows[0].seed}</span></td>${["rp1", "g1"].map(robot => `<td>${completionHTML(rows.find(row => row.robot === robot))}</td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="chart-note">按筛选匹配的动作选择配对，展示双方判定。显示前 ${cases.length} / ${matchedCases.length} 对；完整记录见逐动作表格及导出。</p>` : emptyHTML("没有匹配的逐动作配对", "调整筛选可查看双方判定。");
  }
  function rowEvidence(row) {
    if (!row.fullwindow) return "";
    const full = row.fullwindow;
    const rootWindow = row.rootwindow;
    const rootText = rootWindow ? `<p>root 窗口合同；${rootWindow.recorded_frames} 个名义有效参考帧。</p><p>名义参考窗界 ${fmt(rootWindow.reference_start_s, 3)}–${fmt(rootWindow.reference_end_s, 3)} s；同刻物理对应窗界 ${fmt(rootWindow.physics_start_s, 3)}–${fmt(rootWindow.physics_end_s, 3)} s（合同投影）。</p>` : "";
    return `<details><summary>评分窗口</summary><div class="record-evidence"><p>${full.full_recorded_frames} 个 ${row.fullwindow.metric_window === CLOCK_WINDOW ? "50 Hz 参考同刻评分样本" : "旧版身体缓存评分样本"}；共同参考帧 ${full.reference_common_frames}。</p><p>参考时间 ${fmt(full.reference_start_s, 3)}–${fmt(full.reference_end_s, 3)} s。</p>${rootText}${row.metrics.root_endpoint_pos_mm ? "<p>根部终点位置误差：最后合法参考时刻的同刻根 XYZ 距离，每回合一个末帧值；排除参考后的 hold。</p>" : ""}<p>${row.provenance.execution_protocol_sha256 === null ? "此记录原未记录执行版本。" : "原执行版本身份已保留。"}</p></div></details>`;
  }
  function metricHTML(row, metric) {
    const cell = row.metrics[metric.key];
    return `<td class="metric ${state.metric === metric.key ? "highlight" : ""}"><span class="metric-value">${fmt(cell.value, metric.digits)}</span><span class="metric-detail">${row.scope === "aggregate" ? `${cell.n_motions} 个配对动作` : "1 个机器人回合"}</span>${validCI(cell.ci95) ? `<span class="metric-detail">95% CI [${fmt(cell.ci95[0], metric.digits)}, ${fmt(cell.ci95[1], metric.digits)}]</span>` : `<span class="metric-detail">单回合不计算动作区间</span>`}</td>`;
  }
  function renderHeaders() {
    $("results-table").setAttribute("data-metric-count", String(activeMetrics().length));
    $("results-head").innerHTML = `<tr><th scope="col">组内名次<span class="unit">按所选误差</span></th><th scope="col">策略 / 动作<span class="unit">机器人 · 数据集 · 条件</span></th><th scope="col">覆盖<span class="unit">独立动作与配对回合</span></th><th scope="col">Motion 跟踪任务完成<span class="unit">聚合完成率 / 逐动作判定</span></th>${activeMetrics().map(metric => `<th scope="col" aria-sort="${state.metric === metric.key ? state.direction === "asc" ? "ascending" : "descending" : "none"}"><button type="button" data-sort="${metric.key}">${metric.label} ${state.metric === metric.key ? state.direction === "asc" ? "↑" : "↓" : "↕"}<span class="unit">${metric.unit} · 越低越好 ↓</span></button></th>`).join("")}</tr>`;
  }
  function renderRows(rows, ranks) {
    const pages = Math.max(1, Math.ceil(rows.length / state.pageSize)); state.page = Math.min(state.page, pages);
    const current = rows.slice((state.page - 1) * state.pageSize, state.page * state.pageSize);
    $("results-body").innerHTML = current.length ? current.map(row => { const rank = ranks.get(row.id); return `<tr><td class="rank-cell"><span class="rank-number">${rank?.rank || "—"}</span><span class="rank-note">${escape(rank?.reason || "配对待核验")}</span></td><td class="row-heading"><div class="record-label">${escape(row.label)}</div>${row.scope === "per_motion" ? `<span class="record-meta">${escape(row.motion_id)}</span>` : ""}<span class="record-meta">${escape(datasetLabel(row.dataset))}</span><span class="record-meta">${escape(row.condition)} · ${escape(row.mode)}</span><span class="record-meta">${row.scope === "aggregate" ? "完整匹配 seed 集" : "seed"} ${escape(row.matched_seed_set.join(", "))}</span><div class="record-badges"><span class="badge">${row.robot.toUpperCase()}</span><span class="badge">发布学生策略</span></div>${rowEvidence(row)}</td><td><span class="coverage-primary">${coverageText(row.coverage)}</span><span class="coverage-secondary">${row.scope === "aggregate" ? "同动作 seed 内平均，动作等权" : "已纳入共同配对"}</span></td><td class="completion-cell">${completionHTML(row)}</td>${activeMetrics().map(metric => metricHTML(row, metric)).join("")}</tr>`; }).join("") : `<tr><td class="empty-cell" colspan="${4 + activeMetrics().length}"><strong>${state.loaded ? "当前筛选没有匹配记录" : "公开结果待载入"}</strong><p>${state.loaded ? "可切换结果粒度或重置筛选。" : "等待通过版本核验的 data.json。"}</p></td></tr>`;
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
    $("statistics").innerHTML = `<dt>身体／手腕窗口</dt><dd>${state.data.schema_version === 7 ? "原200 Hz状态重建的50 Hz参考同刻身体姿态，motion_t=1..Ncommon−1；修正旧版早20 ms身体缓存。" : "旧版身体缓存评分样本，motion_t=1..Ncommon−1。"}包含失跟后的评分记录，初始化帧与末端hold不计入。</dd><dt>误差聚合</dt><dd>完整相同 seed 先在动作内平均，再对动作等权；每组独立报告。</dd><dt>误差置信区间</dt><dd>10,000 次配对动作百分位 bootstrap，PCG64 seed 20261013，95% 线性分位数。已载入误差指标的均值与配对差值区间直接读取冻结统计。</dd><dt>完成判据</dt><dd>${escape(state.data.methods.completion?.definition || "任务完成定义暂未载入。")}</dd><dt>完成比例</dt><dd>单 seed 主组按完成动作数 / 动作数报告；三个敏感性组按同动作 seed 判定平均，再对动作等权，报告完成比例与完成动作当量。未知标签保留原动作分母，点估计为 null，另示逻辑上下界；完成率不提供统计置信区间。</dd><dt>判定证据</dt><dd>判定来自参考几何、完整轨迹及有效末端；接触力未直接记录。两条失败时间轴表示最终持续未恢复区间的几何观察起点，参考动作中的翻滚和起身已区别处理。</dd><dt>条件覆盖</dt><dd>Common40 主组：40 动作 / 40 对 / 80 回合；Extreme5：5 / 5 / 10。敏感性：5 / 5 / 10；重复：5 / 15 / 30；初态扰动：5 / 25 / 50。共 45 个不同动作、90 对、180 回合。</dd>`;
    if ([5, 6, 7].includes(state.data.schema_version)) {
      const root = state.data.methods.root;
      $("statistics").innerHTML += `<dt>root 独立窗口</dt><dd>${escape(root.sampling)}</dd><dt>root 定义</dt><dd>${escape(root.alignment)} ${escape(root.position)} ${escape(root.orientation)}</dd><dt>root 窗界说明</dt><dd>逐回合窗界为名义参考时刻的合同投影；公开包未提供逐样本 raw 时间戳数组。</dd>`;
    }
    if ([6, 7].includes(state.data.schema_version)) {
      const endpoint = state.data.methods.root_endpoint;
      $("statistics").innerHTML += `<dt>根部终点</dt><dd>${escape(endpoint.definition)} ${escape(endpoint.actual_reference_clock)}</dd><dt>终点对齐与判定</dt><dd>${escape(endpoint.fixed_anchor)} ${escape(endpoint.not_success_proxy)}</dd>`;
    }
    if (state.data.schema_version === 7) {
      const clock = state.data.methods.clock_rescore;
      $("statistics").innerHTML += `<dt>同刻重评分</dt><dd>${escape(clock.source)} ${escape(clock.sampling)} ${escape(clock.reference_window)}</dd><dt>身体／手腕对齐</dt><dd>${escape(clock.alignment)} ${escape(clock.position)} ${escape(clock.orientation)} ${escape(clock.precision)}</dd><dt>历史窗口说明</dt><dd>${escape(clock.old_four_cache_timing)} ${escape(clock.historical_preservation_flags_scope)}</dd>`;
    }
    const reports = state.data.report_downloads.length ? state.data.report_downloads : REPORTS;
    const reportStatus = state.data.stats.report_status || "V8 已同步：正文、PDF 和 DOCX 已更新至原地址。";
    $("downloads").innerHTML = `<p>${reports.map(linkHTML).join(" ")}</p><p>${escape(reportStatus)} 资料需飞书组织权限。</p>`;
    const notes = ["区间描述固定发布策略与当前仿真动作。训练数据、重定向和控制参数不同；完整历史训练日志、GPU 训练小时及真机验证待补充。", "Common14 使用 ankle-roll 语义映射。误差描述性区间未作多重比较校正。", "公开重定向的动作名与时长已对齐，原始 BVH 输入哈希血缘仍有缺口。", "30 个确定性重复回合逐值一致，独立动作数仍为 5。"];
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
  function renderMetricScope() {
    const endpointEnabled = [6, 7].includes(state.data.schema_version);
    const rootEnabled = state.data.schema_version === 5 || endpointEnabled;
    $("report-subtitle").textContent = "统一测试条件下的动作跟踪与运动表现对比，依据本页公开的仿真评测协议。";
    const sensitivity = state.data.comparisons.find(item => item.condition === "explicit_sensitivity");
    const rootDelta = rootEnabled && sensitivity?.paired_deltas.full_root_pos_mm;
    $("root-sensitivity-note").textContent = rootDelta ? `显式执行敏感性组（N=${rootDelta.n_motions}）的根位置配对差值 RP1 − G1 的 95% CI 为 [${fmt(rootDelta.ci95[0], 2)}, ${fmt(rootDelta.ci95[1], 2)}] mm。${rootDelta.ci95[0] > 0 ? "支持 G1 误差较低。" : rootDelta.ci95[1] < 0 ? "支持 RP1 误差较低。" : "区间跨零。"}各条件组独立解释。` : "";
    $("root-sensitivity-note").hidden = !rootDelta;
    $("results-title").textContent = endpointEnabled ? "六项全程误差与根部终点位置误差。" : rootEnabled ? "全程身体、手腕与根节点跟踪误差。" : "全程身体与手腕跟踪误差。";
    $("results-description").textContent = `40 个配对 LAFAN 动作（N=40），使用各自发布学生策略。全程误差覆盖完整评分序列，包含失跟后的记录；${endpointEnabled ? "根部终点另取最后合法同刻参考末帧。" : ""}位置为 mm，姿态为 rad。`;
    $("metric-result-note").textContent = `${endpointEnabled ? "六项全程误差与根部终点位置误差的" : rootEnabled ? "六项全程误差的" : "四项全程误差的"}均值与配对区间直接来自冻结统计，各条件组分别报告。`;
    $("metric-method-description").textContent = state.data.schema_version === 7 ? "本版对既有180回合做同刻离线重评分，没有新增策略推理或物理回放。身体与手腕由原200 Hz状态重建50 Hz参考同刻姿态，替换旧版早20 ms的身体缓存；保留完整有效参考窗及失控后的记录。根部两项、独立终点与任务完成判定保持原口径。" : rootEnabled ? "身体与手腕四项保留全部 50 Hz 首物理子步评分窗；根节点位置与姿态从原 200 Hz 轨迹选取与参考同刻的状态，完整有效窗包含失控后记录，排除参考末后的 hold。中途摔倒后自行恢复并跟踪到末尾算完成。" : "四项误差取全部 50 Hz 首物理子步评分记录。任务完成判定检查是否因摔倒无法继续后续跟踪；中途摔倒后自行恢复并跟踪到末尾算完成。参考动作中的翻滚和起身须一并核验。";
    $("endpoint-method-description").hidden = !endpointEnabled;
    $("endpoint-method-description").textContent = endpointEnabled ? "根部终点位置误差取最后合法参考末帧（Ncommon−1）的同刻根 XYZ 距离，单位 mm；沿用首个共同有效同刻帧 0.02 s 的固定 XY/yaw 对齐，绝对 Z 不平移。排除参考后的 hold，失败后末帧仍保留；任务完成率独立判定。" : "";
    $("metric-data-description").textContent = `${endpointEnabled ? "六项全程误差、根部终点位置误差" : rootEnabled ? "六项全程误差" : "四项全程误差"}与任务完成判定共用既有 180 回合、90 个条件／seed 配对和 45 个不同动作 ID，分为 5 个独立条件组。详细报告需原有访问权限。`;
    $("metric-download-description").textContent = `${endpointEnabled ? "六项全程误差、根部终点位置误差" : rootEnabled ? "六项全程误差" : "四项全程误差"}、任务完成状态与五组统计；共 180 个机器人回合。`;
  }
  function render() {
    const rows = filteredRows().sort(compareRows), ranks = ranksForMetric(state.data, state.metric);
    renderMetricScope(); renderHeaders(); renderRows(rows, ranks); renderOverview(); renderComparisonTables(); renderPairedSummary(); renderExtension(); renderCompletion(); renderMotionChart(); renderFairness(); renderEvidence();
    $("view-aggregate").setAttribute("aria-pressed", String(state.scope === "aggregate")); $("view-per-motion").setAttribute("aria-pressed", String(state.scope === "per_motion"));
    $("sort-direction").textContent = state.direction === "asc" ? "升序 ↑" : "降序 ↓"; $("sort-metric").value = state.metric;
  }
  function populateFilters() {
    const options = (key, values, label) => { $("filter-" + key).innerHTML = `<option value="all">${label}</option>` + values.map(([value, text]) => `<option value="${escape(value)}">${escape(text)}</option>`).join(""); };
    options("dataset", state.data.datasets.map(dataset => [dataset.id, dataset.label]), "全部数据集");
    ["robot", "condition", "mode"].forEach(key => { const values = [...new Set(state.data.results.map(row => row[key]))].sort(); options(key, values.map(value => [value, key === "robot" ? value.toUpperCase() : value]), { robot: "全部机器人", condition: "全部条件", mode: "全部模式" }[key]); });
    options("seed", [...new Set(state.data.results.flatMap(row => row.matched_seed_set))].sort((a, b) => a - b).map(seed => [seed, seed]), "全部 seed");
    $("sort-metric").innerHTML = activeMetrics().map(metric => `<option value="${metric.key}">${metric.label} (${metric.unit})</option>`).join("");
    $("overview-metric").innerHTML = activeMetrics().map(metric => `<option value="${metric.key}">${metric.label} (${metric.unit})</option>`).join("");
    $("overview-metric").value = state.overviewMetric;
  }
  function csvCell(value) { let cell = value == null ? "" : String(value); if (/^[\s]*[=+\-@]/.test(cell) && !isNumber(value)) cell = "'" + cell; return '"' + cell.replace(/"/g, '""') + '"'; }
  function csvExport(rows, data = state.data) {
    const metrics = metricsFor(data);
    const rootFields = [5, 6, 7].includes(data.schema_version) ? ["root_window_metadata_json"] : [];
    const endpointFields = [6, 7].includes(data.schema_version) ? ["endpoint_metric_window", "endpoint_sample_count"] : [];
    const base = ["id", "label", "phase", "dataset", "condition", "mode", "robot", "motion_id", "seed", "scope"];
    const header = [...base, "matched_seed_set_json", "coverage_json", "comparison_id", "sample_set_sha256", "case_id", ...PROVENANCE_KEYS, ...WINDOW_KEYS.map(key => "window_" + key), ...COMPLETION_KEYS.map(key => "completion_" + key), ...rootFields, ...endpointFields, ...metrics.flatMap(metric => [metric.key, metric.key + "_unit", metric.key + "_ci95_json", metric.key + "_n_motions"])];
    return "\uFEFF" + [header, ...rows.map(row => [...base.map(key => row[key]), JSON.stringify(row.matched_seed_set), JSON.stringify(row.coverage), row.pairing.comparison_id, row.pairing.sample_set_sha256, row.pairing.case_id, ...PROVENANCE_KEYS.map(key => row.provenance[key]), ...WINDOW_KEYS.map(key => row.fullwindow?.[key]), ...COMPLETION_KEYS.map(key => ["ci95", "summary"].includes(key) ? JSON.stringify(row.completion[key]) : row.completion[key]), ...rootFields.map(() => JSON.stringify(row.rootwindow || null)), ...endpointFields.map(key => key === "endpoint_metric_window" ? ENDPOINT_METRIC_WINDOW : 1), ...metrics.flatMap(metric => { const cell = row.metrics[metric.key]; return [cell.value, cell.unit, cell.ci95 === null ? null : JSON.stringify(cell.ci95), cell.n_motions]; })])].map(line => line.map(csvCell).join(",")).join("\r\n") + "\r\n";
  }
  function publicExport(data) { return normalizeData(data); }
  function download(contents, name, type) {
    const url = URL.createObjectURL(new Blob([contents], { type })), anchor = document.createElement("a"); anchor.href = url; anchor.download = name; document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function bindEvents() {
    $("overview-dataset").addEventListener("change", () => { state.overviewDataset = $("overview-dataset").value; renderOverviewChart(); });
    $("overview-metric").addEventListener("change", () => { state.overviewMetric = $("overview-metric").value; renderOverviewChart(); });
    $("comparison-condition").addEventListener("change", () => { state.comparisonCondition = $("comparison-condition").value; renderComparisonTables(); });
    $("filters").addEventListener("submit", event => event.preventDefault());
    ["input", "change"].forEach(event => $("filters").addEventListener(event, eventObject => { if (eventObject.target.id === "filter-completion" && $("filter-completion").value !== "all") state.scope = "per_motion"; state.page = 1; render(); }));
    $("filters").addEventListener("reset", () => setTimeout(() => { state.page = 1; render(); }, 0));
    ["view-aggregate", "view-per-motion"].forEach(id => $(id).addEventListener("click", () => { state.scope = $(id).dataset.scope; if (state.scope === "aggregate") $("filter-completion").value = "all"; state.page = 1; render(); }));
    $("sort-metric").addEventListener("change", () => { state.metric = $("sort-metric").value; state.direction = "asc"; state.page = 1; render(); });
    $("sort-direction").addEventListener("click", () => { state.direction = state.direction === "asc" ? "desc" : "asc"; state.page = 1; render(); });
    $("results-head").addEventListener("click", event => { const button = event.target.closest("button[data-sort]"); if (!button) return; state.direction = state.metric === button.dataset.sort && state.direction === "asc" ? "desc" : "asc"; state.metric = button.dataset.sort; state.page = 1; render(); });
    $("pagination").addEventListener("click", event => { const button = event.target.closest("button[data-page]"); if (!button || button.disabled) return; state.page = Number(button.dataset.page); render(); $("leaderboard").scrollIntoView({ block: "start" }); });
    $("download-json").addEventListener("click", () => download(JSON.stringify(publicExport(state.data), null, 2) + "\n", state.data.schema_version === 7 ? "rp1-g1-sametime-rescore-v9.json" : `rp1-g1-public-v${state.data.schema_version}.json`, "application/json;charset=utf-8"));
    $("download-csv").addEventListener("click", () => download(csvExport(filteredRows().sort(compareRows)), `rp1-g1-${state.data.schema_version === 7 ? "sametime-v9-" : ""}${state.scope}.csv`, "text/csv;charset=utf-8"));
  }
  async function init() {
    try {
      const response = await fetch("./data.json", { cache: "no-store", credentials: "same-origin" }); if (!response.ok) throw new Error(`公开快照读取失败（HTTP ${response.status}）`);
      state.data = normalizeData(await response.json()); state.loaded = true;
      $("load-notice").textContent = `已载入${[6, 7].includes(state.data.schema_version) ? "六项全程误差与根部终点位置误差" : activeMetrics().length === 6 ? "六项全程误差" : "四项全程误差"}：45 个共同动作、90 个配对、180 个既有机器人回合、5 个独立比较组。Motion 跟踪任务完成率及逐动作判定已核验。`;
      $("report-status").textContent = state.data.schema_version === 7 ? "既有轨迹同刻重评分 · 无新物理回放" : "误差指标已载入 · 任务完成率已核验";
    } catch (error) { state.data = EMPTY; $("load-notice").textContent = `${error.message}。公开结果保持待载入。`; $("load-notice").classList.add("error"); }
    const updated = state.data.stats.updated_utc;
    $("updated-at").textContent = updated ? new Date(updated).toLocaleDateString("zh-CN", { timeZone: "UTC", year: "numeric", month: "long", day: "numeric" }) : "2026年10月14日";
    populateFilters(); bindEvents(); render(); await Promise.all([renderPublicMedia(), renderHardware()]);
  }
  window.LeaderboardUtils = { normalizeData, publicExport, ranksForMetric, csvExport, valueOf, safeURL, linkHTML, coverageText, pairedCaseKey, pairedMotionCases, validPublicMedia, pairedIntervalSVG, comparisonBestStates, comparisonTableHTML, comparisonPanelHTML, get metrics() { return activeMetrics(); }, get fullMetrics() { return activeMetrics(); }, metricsFor, rootMetrics: ROOT_METRICS, endpointMetrics: ENDPOINT_METRICS, completionHTML, validateCompletion, validateCompletionSummary };
  init();
})();
