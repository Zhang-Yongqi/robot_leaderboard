/* Four report views reuse the same controls, records and detail nodes. */
(function () {
  "use strict";
  const tabs = [...document.querySelectorAll("[data-panel-target]")];
  const panels = [...document.querySelectorAll("[data-panel]")];
  const anchors = { overview: "top", performance: "results", hardware: "hardware", methods: "data" };
  if (!tabs.length || panels.length !== tabs.length) return;
  function activate(name) {
    const selected = panels.some(panel => panel.dataset.panel === name) ? name : "overview";
    panels.forEach(panel => { panel.hidden = panel.dataset.panel !== selected; });
    tabs.forEach(tab => {
      const active = tab.dataset.panelTarget === selected;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    return selected;
  }
  function followHash(scroll = true) {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { id = "top"; }
    const target = document.getElementById(id || "top");
    const panel = target?.closest("[data-panel]");
    activate(panel?.dataset.panel || "overview");
    if (scroll && target) {
      if (target.tagName === "DETAILS") target.open = true;
      let ancestor = target.parentElement;
      while (ancestor) { if (ancestor.tagName === "DETAILS") ancestor.open = true; ancestor = ancestor.parentElement; }
      requestAnimationFrame(() => window.scrollTo({ top: Math.max(0, target.getBoundingClientRect().top + window.scrollY - (document.querySelector(".site-header")?.offsetHeight || 0) - 16), behavior: "instant" }));
    }
  }
  function choose(tab) {
    const name = activate(tab.dataset.panelTarget);
    const hash = "#" + anchors[name];
    if (location.hash !== hash) history.pushState(null, "", hash);
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => choose(tab));
    tab.addEventListener("keydown", event => {
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : event.key === "ArrowRight" ? (index + 1) % tabs.length : event.key === "ArrowLeft" ? (index - 1 + tabs.length) % tabs.length : null;
      if (next === null) return;
      event.preventDefault();
      choose(tabs[next]);
      tabs[next].focus({ preventScroll: true });
    });
  });
  window.addEventListener("hashchange", () => followHash());
  window.addEventListener("popstate", () => followHash());
  followHash(!!location.hash);
})();
