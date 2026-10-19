/* Presentation-only localization. Scientific records and export data remain untouched. */
(function () {
  "use strict";
  const STORAGE_KEY = "roboparty-language";
  const dictionary = Object.assign({}, window.ROBO_I18N_UI, window.ROBO_I18N_DATA);
  const catalogReady = [window.ROBO_I18N_UI, window.ROBO_I18N_DATA].every(catalog => catalog && typeof catalog === "object" && Object.keys(catalog).length > 0 && Object.values(catalog).every(value => typeof value === "string"));
  const hasHan = /[\u3400-\u9fff]/;
  const keys = Object.keys(dictionary).filter(key => hasHan.test(key)).sort((a, b) => b.length - a.length);
  const escapeRegex = text => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const phrases = keys.length ? new RegExp(keys.map(escapeRegex).join("|"), "g") : null;
  const textSources = new WeakMap(), attributeSources = new WeakMap();
  const attributes = ["aria-label", "aria-description", "title", "placeholder", "alt"];
  let language = "zh", observer;
  try { if (catalogReady && localStorage.getItem(STORAGE_KEY) === "en") language = "en"; } catch (_) { /* Storage may be disabled. */ }

  function english(source) {
    if (!phrases || !hasHan.test(source)) return source;
    const trimmed = source.trim();
    if (Object.hasOwn(dictionary, trimmed)) return source.replace(trimmed, dictionary[trimmed]);
    return source
      .replace(/已载入(.+?)：([\d,]+) 个共同动作、([\d,]+) 个配对、([\d,]+) 个既有机器人回合、([\d,]+) 个独立比较组。Motion 跟踪任务完成率及逐动作判定已核验。/g, (_, scope, motions, pairs, episodes, groups) => `Loaded ${english(scope).toLowerCase()}: ${motions} shared motions, ${pairs} pairs, ${episodes} existing robot episodes and ${groups} independent comparison groups. Motion completion rates and per-motion adjudications are verified.`)
      .replace(/([\d,]+) 个 (50 Hz 参考同刻评分样本|旧版身体缓存评分样本)；共同参考帧 ([\d,]+)。/g, (_, count, scope, frames) => `${count} ${english(scope).replace(/^Legacy/, "legacy")}; ${frames} shared reference frames.`)
      .replace(/([\d,]+) 个配对 LAFAN 动作（N=([\d,]+)），使用各自发布学生策略。全程误差覆盖完整评分序列，包含失跟后的记录；(.*?)位置为 mm，姿态为 rad。/g, (_, count, n, endpoint) => `${count} paired LAFAN motions (N=${n}), using each robot's released student policy. Full-window errors cover the entire scoring sequence, including records after tracking is lost. ${endpoint ? english(endpoint) + " " : ""}Position errors are in mm; orientation errors are in rad.`)
      .replace(/显式执行敏感性组（N=([\d,]+)）的根位置配对差值 RP1 − G1 的 95% CI 为 \[([^\]]+)\] mm。/g, (_, n, interval) => `In the explicit-execution sensitivity group (N=${n}), the 95% CI for the paired root position difference, RP1 − G1, is [${interval}] mm. `)
      .replace(/(六项全程误差、根部终点位置误差|六项全程误差|四项全程误差)、任务完成状态与五组统计；共 ([\d,]+) 个机器人回合。/g, (_, scope, count) => `${english(scope)}, completion status and statistics for five groups; ${count} robot episodes in total.`)
      .replace(/每项均值、双方区间及 RP1 减 G1 配对差。/g, "means, intervals for both robots and paired RP1 − G1 differences.")
      .replace(/([\d,]+) 条(聚合|逐动作)记录 · ([\d,]+) 条有组内名次/g, (_, count, scope, ranked) => `${count} ${scope === "聚合" ? "aggregate" : "per-motion"} ${count === "1" ? "record" : "records"} · ${ranked} ranked within their group`)
      .replace(/第 (\d+) \/ (\d+) 页 · 每页 (\d+) 条/g, "Page $1 / $2 · $3 per page")
      .replace(/当前筛选逐动作([^，]+)，显示前(\d+)条/g, (_, metric, count) => `Per-motion ${english(metric).toLowerCase()} under the current filters; first ${count} records`)
      .replace(/显示 (\d+) \/ (\d+) 个数值。完整记录可在逐动作表格或 CSV 查看。/g, "Showing $1 / $2 values. Complete records are available in the per-motion table or CSV.")
      .replace(/(\d+) 个配对动作/g, "$1 paired motions")
      .replace(/(\d+) 个机器人回合/g, "$1 robot episodes")
      .replace(phrases, phrase => dictionary[phrase])
      .replace(/(\d{4})年(\d{1,2})月(\d{1,2})日/g, (_, year, month, day) => `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`)
      .replace(/（/g, " (").replace(/）/g, ")").replace(/，/g, ", ").replace(/；/g, "; ").replace(/。/g, ".").replace(/：/g, ": ").replace(/／/g, " / ").replace(/、/g, ", ");
  }
  window.RoboI18n = Object.freeze({ searchText: source => catalogReady ? english(String(source || "")) : String(source || "") });
  function excluded(element) { return !element || !!element.closest("script,style,noscript,textarea,[translate=no]"); }
  function updateText(node) {
    if (excluded(node.parentElement)) return;
    const old = textSources.get(node);
    const source = old && node.nodeValue === old.output ? old.source : node.nodeValue;
    if (!hasHan.test(source) && !old) return;
    const output = language === "en" ? english(source) : source;
    textSources.set(node, { source, output });
    if (node.nodeValue !== output) node.nodeValue = output;
  }
  function updateAttributes(element) {
    if (excluded(element)) return;
    let saved = attributeSources.get(element);
    if (!saved) { saved = {}; attributeSources.set(element, saved); }
    const names = element.matches('meta[name="description"]') ? [...attributes, "content"] : attributes;
    names.forEach(name => {
      if (!element.hasAttribute(name)) return;
      const current = element.getAttribute(name), old = saved[name];
      const source = old && current === old.output ? old.source : current;
      const output = language === "en" ? english(source) : source;
      saved[name] = { source, output };
      if (current !== output) element.setAttribute(name, output);
    });
  }
  function translateTree(root) {
    if (root.nodeType === Node.TEXT_NODE) { updateText(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
    if (root.nodeType === Node.ELEMENT_NODE) updateAttributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      if (walker.currentNode.nodeType === Node.TEXT_NODE) updateText(walker.currentNode);
      else updateAttributes(walker.currentNode);
    }
  }
  function observe() {
    observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...attributes, "content"] });
  }
  function setLanguage(next, remember = true) {
    language = catalogReady && next === "en" ? "en" : "zh";
    document.documentElement.lang = language === "en" ? "en" : "zh-CN";
    if (remember) { try { localStorage.setItem(STORAGE_KEY, language); } catch (_) { /* The current page still works. */ } }
    observer.disconnect();
    translateTree(document.documentElement);
    document.querySelectorAll("[data-language]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.language === language)));
    observe();
  }
  observer = new MutationObserver(records => {
    observer.disconnect();
    const roots = new Set();
    records.forEach(record => {
      if (record.type === "childList") record.addedNodes.forEach(node => roots.add(node));
      else roots.add(record.target);
    });
    roots.forEach(translateTree);
    observe();
  });
  document.querySelectorAll("[data-language]").forEach(button => button.addEventListener("click", () => setLanguage(button.dataset.language)));
  if (!catalogReady) {
    const englishButton = document.querySelector('[data-language="en"]');
    englishButton.disabled = true;
    englishButton.title = "English unavailable / 英文暂时不可用，请刷新重试";
  }
  setLanguage(language, false);
})();
