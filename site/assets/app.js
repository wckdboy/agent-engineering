/* global document, fetch, localStorage, navigator, IntersectionObserver */
(() => {
  "use strict";

  const state = {
    data: null,
    skillPhase: "all",
    skillQuery: "",
    toolCat: "all",
    toolQuery: "",
    pathId: null,
    lastFocus: null,
    toastTimer: null,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
  const titleCase = (value) => String(value).replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const phaseName = (id) => {
    const phase = state.data?.phases.find((p) => p.id === id);
    return phase ? phase.title : titleCase(id);
  };

  function toast(message) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => { el.hidden = true; }, 1800);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to clipboard");
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      try { document.execCommand("copy"); toast("Copied to clipboard"); }
      catch { toast("Copy failed — select the text"); }
      area.remove();
    }
  }

  function renderStats() {
    const s = state.data.stats;
    $("#hero-stats").innerHTML = [
      [s.skills, "skills"],
      [s.tools, "tools + connectors"],
      [s.paths, "build paths"],
      [s.adopted, "adopted"],
    ].map(([n, label]) => `<div class="stat"><strong>${n}</strong><span>${esc(label)}</span></div>`).join("");
    $("#source-meta").textContent = `source ${state.data.source.commit} · schema ${state.data.source.content_sha256.slice(0, 12)}${state.data.source.dirty ? " · working tree" : ""}`;
    $("#footer-version").textContent = `v${state.data.version}`;
  }

  function renderPhases() {
    $("#phase-grid").innerHTML = state.data.phases.map((p) => `
      <article class="phase-card">
        <div class="phase-number">${esc(p.number)} / ${esc(p.id)}</div>
        <h3>${esc(p.title)}</h3>
        <p class="phase-question">${esc(p.question)}</p>
        <p class="phase-body">${esc(p.body)}</p>
        <div class="phase-skills">${p.skills.map((s) => `<span>${esc(s)}</span>`).join("")}</div>
      </article>`).join("");
  }

  function renderPrinciples() {
    $("#principle-grid").innerHTML = state.data.principles.map((p, i) => `
      <article class="principle-card">
        <span class="principle-index">${String(i + 1).padStart(2, "0")} / ${esc(p.id)}</span>
        <h3>${esc(p.title)}</h3>
        <p>${esc(p.lead)}</p>
        <ul>${p.points.map((point) => `<li>${esc(point)}</li>`).join("")}</ul>
      </article>`).join("");
  }

  function skillMatches(skill) {
    if (state.skillPhase !== "all" && skill.phase !== state.skillPhase) return false;
    const q = state.skillQuery.trim().toLowerCase();
    if (!q) return true;
    return [skill.id, skill.name, skill.description, skill.activate, skill.phase, ...(skill.tags || [])]
      .join(" ").toLowerCase().includes(q);
  }

  function renderSkillFilters() {
    const phases = [{ id: "all", title: "All" }, ...state.data.phases];
    $("#skill-filters").innerHTML = phases.map((p) => `
      <button class="chip ${state.skillPhase === p.id ? "active" : ""}" type="button"
        data-skill-phase="${esc(p.id)}" aria-pressed="${state.skillPhase === p.id}">${esc(p.title)}</button>`).join("");
  }

  function renderSkills() {
    const visible = state.data.skills.filter(skillMatches);
    $("#skill-count").textContent = `${visible.length} / ${state.data.skills.length}`;
    $("#skill-empty").hidden = visible.length > 0;
    $("#skill-grid").innerHTML = visible.map((skill) => `
      <article class="skill-card" role="button" tabindex="0" data-skill="${esc(skill.id)}"
        aria-label="Open ${esc(skill.name)}">
        <div class="skill-top">
          <span class="skill-phase">${esc(phaseName(skill.phase))}</span>
          <span class="skill-phase"><span class="risk-dot risk-${esc(skill.risk)}"></span>${esc(skill.risk)} risk</span>
        </div>
        <h3>${esc(skill.name)}</h3>
        <p>${esc(skill.description)}</p>
        <p class="skill-activate">${esc(skill.activate.replace(/^-\s*/, ""))}</p>
        <div class="skill-foot">
          <div class="skill-tags">${(skill.tags || []).slice(0, 3).map((t) => `<span>#${esc(t)}</span>`).join("")}</div>
          <span class="skill-open">Open →</span>
        </div>
      </article>`).join("");
  }

  function openSkill(id) {
    const skill = state.data.skills.find((s) => s.id === id);
    if (!skill) return;
    state.lastFocus = document.activeElement;
    $("#drawer-kicker").textContent = `${phaseName(skill.phase)} · ${skill.risk} risk`;
    $("#drawer-title").textContent = skill.name;
    $("#drawer-meta").innerHTML = [
      `<span class="status-chip adopted">${esc(skill.phase)}</span>`,
      `<span class="status-chip ${skill.risk === "high" ? "blocked" : "conditional"}">${esc(skill.risk)} risk</span>`,
      ...(skill.tags || []).map((t) => `<span class="status-chip skipped">#${esc(t)}</span>`),
    ].join("");
    $("#drawer-body").innerHTML = skill.body_html;
    $("#drawer-source").textContent = skill.source_path;
    $("#drawer-copy").dataset.copy = skill.raw_markdown || `---\nname: ${skill.id}\ndescription: ${skill.description}\n---\n\n${skill.body_markdown}`;
    $("#skill-drawer").hidden = false;
    $("#drawer-backdrop").hidden = false;
    document.body.style.overflow = "hidden";
    $("#drawer-close").focus();
  }

  function closeSkill() {
    $("#skill-drawer").hidden = true;
    $("#drawer-backdrop").hidden = true;
    document.body.style.overflow = "";
    if (state.lastFocus && typeof state.lastFocus.focus === "function") state.lastFocus.focus();
  }

  function renderToolFilters() {
    const cats = [{ id: "all", title: "All" }];
    const seen = new Set();
    state.data.tools.forEach((t) => { if (!seen.has(t.category)) { seen.add(t.category); cats.push({ id: t.category, title: titleCase(t.category) }); } });
    $("#tool-filters").innerHTML = cats.map((c) => `
      <button class="chip ${state.toolCat === c.id ? "active" : ""}" type="button"
        data-tool-cat="${esc(c.id)}" aria-pressed="${state.toolCat === c.id}">${esc(c.title)}</button>`).join("");
  }

  function toolMatches(tool) {
    if (state.toolCat !== "all" && tool.category !== state.toolCat) return false;
    const q = state.toolQuery.trim().toLowerCase();
    if (!q) return true;
    return [tool.id, tool.name, tool.category, tool.status, tool.summary, tool.why, tool.command, ...(tool.tags || [])]
      .join(" ").toLowerCase().includes(q);
  }

  function renderTools() {
    const visible = state.data.tools.filter(toolMatches);
    $("#tool-count").textContent = `${visible.length} / ${state.data.tools.length}`;
    $("#tool-empty").hidden = visible.length > 0;
    $("#tool-grid").innerHTML = visible.map((tool) => `
      <article class="tool-card">
        <div class="tool-head">
          <div><h3>${esc(tool.name)}</h3><div class="tool-cat">${esc(titleCase(tool.category))}</div></div>
          <span class="status-chip ${esc(tool.status)}">${esc(tool.status)}</span>
        </div>
        <p class="tool-summary">${esc(tool.summary)}</p>
        <p class="tool-why">${esc(tool.why)}</p>
        <div class="tool-foot">
          <span class="tool-command">${esc(tool.command)}</span>
          <a class="tool-link" href="${esc(tool.docs)}" target="_blank" rel="noreferrer">docs ↗</a>
        </div>
      </article>`).join("");
  }

  function renderPaths() {
    $("#path-menu").innerHTML = state.data.paths.map((p) => `
      <button class="path-button ${state.pathId === p.id ? "active" : ""}" type="button"
        role="tab" aria-selected="${state.pathId === p.id}" data-path="${esc(p.id)}">
        <span>${esc(p.glyph)}</span>${esc(p.title)}
      </button>`).join("");
    const path = state.data.paths.find((p) => p.id === state.pathId) || state.data.paths[0];
    if (!path) return;
    $("#path-detail").innerHTML = `
      <p class="section-kicker">Build path</p>
      <h3>${esc(path.title)}</h3>
      <p class="path-summary">${esc(path.summary)}</p>
      <p class="path-when">Use when: ${esc(path.when)}</p>
      <div class="path-steps">
        ${path.steps.map((step, i) => `
          <div class="path-step">
            <div class="step-index">${String(i + 1).padStart(2, "0")}</div>
            <div>
              <h4>${esc(step.title)}</h4>
              <p>${esc(step.body)}</p>
              <div class="step-meta">
                ${step.commands.map((cmd) => `<span class="command-pill"><code>${esc(cmd)}</code><button type="button" data-copy="${esc(cmd)}" aria-label="Copy command">⧉</button></span>`).join("")}
                ${step.skills.map((s) => `<button class="skill-link" type="button" data-skill="${esc(s)}">${esc(s)}</button>`).join("")}
              </div>
              <div class="step-done">${esc(step.done)}</div>
            </div>
          </div>`).join("")}
      </div>`;
  }

  function observedDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000")) return null;
    const date = new Date(`${value}T00:00:00Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value ? value : null;
  }

  function safeEvidenceLink(link) {
    if (!link || typeof link.label !== "string" || !link.label.trim() || typeof link.url !== "string") return false;
    if (!link.url.startsWith("https://") || /[\s\x00-\x1f\x7f\\<>"`]/.test(link.url)) return false;
    const authority = link.url.slice(8).split(/[/?#]/)[0];
    if (!/^[A-Za-z0-9.\[\]:-]+$/.test(authority) || authority.endsWith(":")) return false;
    try {
      const url = new URL(link.url);
      return !!url.hostname && (!url.port || Number(url.port) > 0);
    } catch { return false; }
  }

  function renderRepos() {
    $("#repo-grid").innerHTML = state.data.repos.map((repo) => {
      const observed = observedDate(repo.last_observed);
      const links = Array.isArray(repo.evidence_links) ? repo.evidence_links.filter(safeEvidenceLink) : [];
      return `
      <article class="repo-card">
        <div class="repo-head">
          <div><h3>${esc(repo.name)}</h3><p class="repo-role">${esc(repo.role)}</p></div>
          <span class="status-chip ${esc(repo.status)}">${repo.status === "template" ? "" : "recorded "}${esc(repo.status)}</span>
        </div>
        <p class="repo-provenance">Recorded observation · not live CI<br>Last observed: ${observed ? `<time datetime="${observed}">${observed}</time>` : "not recorded"}</p>
        <p class="repo-body">${esc(repo.evidence)}</p>
        <p class="repo-links">${links.length ? links.map((link) => `<a href="${esc(link.url)}" target="_blank" rel="noopener noreferrer">${esc(link.label)} ↗</a>`).join(" · ") : "No linked evidence recorded"}</p>
        <div class="repo-meta">
          <span>branch ${esc(repo.branch)}</span>
          <span>${esc(repo.gate)}</span>
          ${repo.remote ? `<span>${esc(repo.remote)}</span>` : ""}
        </div>
        <p class="repo-note">${esc(repo.notes)}</p>
      </article>`;
    }).join("");
  }

  function renderLimits() {
    $("#limit-list").innerHTML = state.data.limits.map((limit) => `<li>${esc(limit)}</li>`).join("");
  }

  function renderAll() {
    renderStats();
    renderPhases();
    renderPrinciples();
    renderSkillFilters();
    renderSkills();
    renderToolFilters();
    renderTools();
    renderPaths();
    renderRepos();
    renderLimits();
    observeSections();
  }

  function observeSections() {
    const links = $$('a[href^="#"]');
    const sections = state.data ? $$("main section[id]") : [];
    if (!("IntersectionObserver" in window) || !sections.length) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const id = entry.target.id;
        links.forEach((a) => {
          if (a.getAttribute("href") === `#${id}` && (a.closest(".topnav") || a.closest(".side-nav"))) {
            a.classList.add("active");
          } else if (a.closest(".topnav") || a.closest(".side-nav")) {
            a.classList.remove("active");
          }
        });
      });
    }, { rootMargin: "-20% 0px -70% 0px", threshold: 0 });
    sections.forEach((section) => observer.observe(section));
  }

  function initTheme() {
    const stored = localStorage.getItem("agenteng-theme");
    const theme = stored || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.dataset.theme = theme;
    updateThemeLabel();
    $("#theme-toggle").addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("agenteng-theme", next);
      updateThemeLabel();
    });
  }

  function updateThemeLabel() {
    const dark = document.documentElement.dataset.theme !== "light";
    const button = $("#theme-toggle");
    button.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    button.querySelector(".theme-icon").textContent = dark ? "☼" : "◐";
  }

  function initNav() {
    const menu = $("#menu-toggle");
    const sidebar = $("#sidebar");
    menu.addEventListener("click", () => {
      const open = sidebar.classList.toggle("open");
      menu.setAttribute("aria-expanded", String(open));
    });
    $$(".side-nav a, .topnav a").forEach((a) => a.addEventListener("click", () => {
      sidebar.classList.remove("open");
      menu.setAttribute("aria-expanded", "false");
    }));
    $("#search-trigger").addEventListener("click", () => {
      $("#skills").scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(() => $("#skill-search").focus(), 250);
    });
  }

  function initEvents() {
    $("#skill-search").addEventListener("input", (event) => {
      state.skillQuery = event.target.value;
      renderSkills();
    });
    $("#skill-filters").addEventListener("click", (event) => {
      const button = event.target.closest("[data-skill-phase]");
      if (!button) return;
      state.skillPhase = button.dataset.skillPhase;
      renderSkillFilters();
      renderSkills();
    });
    $("#tool-search").addEventListener("input", (event) => {
      state.toolQuery = event.target.value;
      renderTools();
    });
    $("#tool-filters").addEventListener("click", (event) => {
      const button = event.target.closest("[data-tool-cat]");
      if (!button) return;
      state.toolCat = button.dataset.toolCat;
      renderToolFilters();
      renderTools();
    });
    $("#path-menu").addEventListener("click", (event) => {
      const button = event.target.closest("[data-path]");
      if (!button) return;
      state.pathId = button.dataset.path;
      renderPaths();
    });
    document.addEventListener("click", (event) => {
      const skill = event.target.closest("[data-skill]");
      if (skill) { openSkill(skill.dataset.skill); return; }
      const copy = event.target.closest("[data-copy]");
      if (copy) { copyText(copy.dataset.copy); return; }
    });
    document.addEventListener("keydown", (event) => {
      const tag = (document.activeElement?.tagName || "").toLowerCase();
      const typing = tag === "input" || tag === "textarea" || document.activeElement?.isContentEditable;
      if (event.key === "/" && !typing) {
        event.preventDefault();
        $("#skills").scrollIntoView({ behavior: "smooth", block: "start" });
        setTimeout(() => $("#skill-search").focus(), 200);
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        $("#skills").scrollIntoView({ behavior: "smooth", block: "start" });
        setTimeout(() => $("#skill-search").focus(), 200);
      }
      if (event.key === "Escape" && !$("#skill-drawer").hidden) closeSkill();
      if (event.key === "Tab" && !$("#skill-drawer").hidden) {
        const focusables = $$("button, a[href], [tabindex]:not([tabindex='-1'])", $("#skill-drawer"))
          .filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    $("#drawer-close").addEventListener("click", closeSkill);
    $("#drawer-backdrop").addEventListener("click", closeSkill);
    $("#drawer-copy").addEventListener("click", (event) => copyText(event.currentTarget.dataset.copy || ""));
  }

  async function boot() {
    initTheme();
    initNav();
    initEvents();
    try {
      const response = await fetch("./data/site.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.data = await response.json();
      state.pathId = state.data.paths.some((p) => p.id === "fix-bug") ? "fix-bug" : state.data.paths[0]?.id;
      renderAll();
    } catch (error) {
      $("#main").insertAdjacentHTML("afterbegin",
        `<div class="noscript">The generated catalog could not load (${esc(error.message)}). Serve this directory over HTTP: <code>cd site && python3 -m http.server 8080</code>. The machine-readable files still work: <a href="./agents.json">agents.json</a>, <a href="./llms.txt">llms.txt</a>.</div>`);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
