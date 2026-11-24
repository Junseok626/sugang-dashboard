// 이수 체크는 이 브라우저에만 누적 저장합니다. API/수강 담기와 독립적입니다.
(() => {
  "use strict";
  const data = window.curriculumData;
  const STORAGE_KEY = "sugang.curriculum.ict-data.v1";
  const validIds = new Set(data.courses.map(course => course.id));
  const byId = new Map(data.courses.map(course => [course.id, course]));
  let completed = new Set();
  let initialized = false;
  let previousSelection = null;
  const buttons = new Map();
  const edges = [];
  const modules = [];
  const $ = id => document.getElementById(id);
  function el(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function position(node, x, y, width, height) {
    Object.assign(node.style, {left: `${x}px`, top: `${y}px`});
    if (width !== undefined) node.style.width = `${width}px`;
    if (height !== undefined) node.style.height = `${height}px`;
    return node;
  }
  function decode(value) {
    if (value === null) return new Set();
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) throw new Error("Invalid stored selection");
    return new Set(parsed.filter(id => typeof id === "string" && validIds.has(id)));
  }
  function storageMessage(text) {
    $("curriculum-storage-message").textContent = text;
    $("curriculum-storage-message").hidden = !text;
  }
  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...completed]));
      storageMessage("");
    } catch {
      storageMessage("이수 표시를 저장하지 못했어요. 현재 화면에서는 사용할 수 있지만 새로고침하면 유지되지 않을 수 있어요.");
    }
  }
  function buildBoard() {
    const board = $("curriculum-board");
    board.replaceChildren();
    data.modules.forEach((module, index) => {
      const zone = position(el("div", `curriculum-zone curriculum-tone--${module.tone}`), module.x, index === 3 ? 48 : 268, module.width, index === 3 ? 804 : 584);
      zone.setAttribute("aria-hidden", "true");
      board.append(zone);
      const heading = position(el("div", `curriculum-column curriculum-tone--${module.tone}`), module.x, 0, module.width);
      heading.append(el("span", "curriculum-column__label", module.label), el("strong", "", module.name));
      board.append(heading);
      const courseIds = module.courseIds || data.courses.filter(course => course.x >= module.x && course.x < module.x + module.width && (index >= 3 || course.y >= 268)).map(course => course.id);
      let summary = null;
      if (index < 3) {
        const card = el("article", `curriculum-module-card curriculum-tone--${module.tone}`);
        const status = el("strong", "curriculum-module-status");
        const progress = el("progress", "");
        progress.max = courseIds.length;
        progress.setAttribute("aria-label", `${module.name} 이수 진행률`);
        const count = el("span", "curriculum-module-count");
        const remaining = el("p", "curriculum-module-remaining");
        card.append(el("span", "curriculum-column__label", `모듈(트랙) ${index+1}`), el("h4", "", module.name), status, progress, count, remaining);
        $("curriculum-module-list").append(card);
        summary = {card, status, progress, count, remaining};
      }
      modules.push({zone, heading, courseIds, summary});
    });
    [48,272,450,704].forEach(y => board.append(position(el("div", "curriculum-rule"), 0, y, 1176)));
    [124,378,556,776].forEach(y => board.append(position(el("div", "curriculum-rule curriculum-rule--term"), 44, y, 1132)));
    [[1,160],[2,361],[3,577],[4,773]].forEach(([year,y]) => board.append(position(el("strong", "curriculum-year", `${year}학년`),0,y,40)));
    [[1,66,14],[2,176,15],[1,303,21],[2,392,21],[1,481,19],[2,608,25],[1,718,13],[2,790,10]].forEach(([term,y,credit]) => {
      const label = position(el("div", "curriculum-term"),44,y,45);
      label.append(el("span", "", `${term}학기`),el("small", "", `${credit}학점`));
      board.append(label);
    });
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.classList.add("curriculum-connections");
    svg.setAttribute("viewBox", "0 0 1176 852");
    svg.setAttribute("width", "1176");
    svg.setAttribute("height", "852");
    svg.setAttribute("aria-hidden", "true");
    // Keep the Figma first-year grouping line separate from prerequisite progress.
    const grouping = document.createElementNS(ns, "path");
    grouping.setAttribute("d", "M204 88 H816");
    grouping.classList.add("curriculum-grouping");
    svg.append(grouping);
    for (const edge of data.edges) {
      const from = byId.get(edge.from), to = byId.get(edge.to);
      const x1 = from.x + from.width / 2, y1 = from.y + from.height;
      const x2 = to.x + to.width / 2, y2 = to.y;
      const path = document.createElementNS(ns, "path");
      // Long links use the open gutter so intervening course cards stay unobstructed.
      const longLink = y2 - y1 > 100;
      const gutter = Math.min(from.x, to.x) - 10;
      const mid = (y1 + y2) / 2;
      const route = longLink
        ? `M${x1} ${y1} V${y1+12} H${gutter} V${y2-14} H${x2} V${y2}`
        : `M${x1} ${y1} V${mid} H${x2} V${y2}`;
      path.setAttribute("d", `${route} M${x2-4} ${y2-5} L${x2} ${y2} L${x2+4} ${y2-5}`);
      path.classList.add("curriculum-path");
      path.dataset.from = edge.from;
      path.dataset.to = edge.to;
      svg.append(path);
      edges.push({path, ...edge});
    }
    board.append(svg);
    for (const course of data.courses) {
      const category = {"기초":"basic", "핵심":"core", "심화":"advanced"}[course.category];
      const button = position(el("button", `curriculum-course curriculum-course--${category}${course.intro ? " curriculum-course--intro" : ""}${course.height === 36 ? " curriculum-course--compact" : ""}`),course.x,course.y,course.width,course.height);
      button.type = "button";
      button.dataset.courseId = course.id;
      button.append(el("span", "curriculum-course__name", `${course.name} (${course.credit})`));
      const check = el("span", "curriculum-course__check", "✓");
      check.setAttribute("aria-hidden", "true");
      button.append(check);
      button.addEventListener("click", () => toggle(course));
      buttons.set(course.id, button);
      board.append(button);
    }
    for (const badge of data.badges) {
      const node = position(el("span", `curriculum-skill curriculum-skill--${badge.skill}`,badge.skill),badge.x,badge.y,16,16);
      node.setAttribute("aria-hidden", "true");
      board.append(node);
    }
  }
  function render() {
    let credit = 0;
    for (const course of data.courses) {
      const done = completed.has(course.id);
      const button = buttons.get(course.id);
      button.classList.toggle("is-completed", done);
      button.setAttribute("aria-pressed", String(done));
      const name = course.name.replace(/\n/g, " ");
      button.setAttribute("aria-label", `${name}, ${course.credit}학점, 전공${course.category}, ${done ? "이수 완료, 클릭하면 취소" : "미이수, 클릭하면 이수 완료"}`);
      const prerequisites = data.edges.filter(edge => edge.to === course.id).map(edge => byId.get(edge.from).name.replace(/\n/g," "));
      button.title = `${name} · 전공${course.category}${prerequisites.length ? `\n연결된 선수 과목: ${prerequisites.join(", ")}` : ""}`;
      if (done) credit += course.credit;
    }
    let connected = 0;
    edges.forEach(edge => {
      const done = completed.has(edge.from) && completed.has(edge.to);
      edge.path.classList.toggle("is-completed", done);
      if (done) connected++;
    });
    let completedModules = 0;
    modules.forEach(module => {
      const done = module.courseIds.every(id => completed.has(id));
      module.zone.classList.toggle("is-completed",done);
      module.heading.classList.toggle("is-completed",done);
      if (module.summary) {
        const {card, status, progress, count, remaining} = module.summary;
        const missing = module.courseIds.filter(id => !completed.has(id));
        const checked = module.courseIds.length - missing.length;
        if (done) completedModules++;
        card.classList.toggle("is-completed", done);
        status.textContent = done ? "✓ 모듈 완성" : "○ 이수 중";
        progress.value = checked;
        count.textContent = `${checked} / ${module.courseIds.length}과목 이수`;
        remaining.textContent = done ? "모든 과목을 이수했어요!" : `남은 과목: ${missing.map(id => byId.get(id).name.replace(/\n/g, " ")).join(", ")}`;
      }
    });
    $("curriculum-module-total").textContent = completedModules === 3 ? "✓ 세 모듈을 모두 완성했어요!" : `모듈 ${completedModules} / 3개 완성`;
    $("curriculum-progress").max = data.courses.length;
    $("curriculum-progress").value = completed.size;
    $("curriculum-progress-text").textContent = `${completed.size} / ${data.courses.length}과목 · ${credit}학점 표시 · ${Math.round(completed.size/data.courses.length*100)}%`;
    $("curriculum-path-count").textContent = `연결된 경로 ${connected} / ${edges.length}`;
    $("curriculum-reset").disabled = completed.size === 0;
    $("curriculum-undo").hidden = previousSelection === null;
  }
  function toggle(course) {
    if (completed.has(course.id)) completed.delete(course.id); else completed.add(course.id);
    previousSelection = null;
    save(); render();
    $("curriculum-announcement").textContent = `${course.name.replace(/\n/g," ")} ${completed.has(course.id) ? "이수 완료로 표시" : "이수 표시 취소"}`;
  }
  function init() {
    if (initialized || !$("curriculum-board")) return;
    initialized = true;
    buildBoard();
    try { completed = decode(localStorage.getItem(STORAGE_KEY)); }
    catch { storageMessage("저장된 이수 표시를 읽지 못했어요. 새로 선택해 주세요."); }
    $("curriculum-reset").addEventListener("click", () => {
      previousSelection = new Set(completed);
      completed.clear(); save(); render();
      $("curriculum-announcement").textContent = "이수 표시를 초기화했어요. 되돌리기로 복원할 수 있어요.";
      $("curriculum-undo").focus();
    });
    $("curriculum-undo").addEventListener("click", () => {
      completed = previousSelection || completed;
      previousSelection = null; save(); render();
      $("curriculum-reset").focus();
      $("curriculum-announcement").textContent = "초기화 전 이수 표시를 복원했어요.";
    });
    window.addEventListener("storage", event => {
      if (event.key !== STORAGE_KEY && event.key !== null) return;
      try { completed = decode(event.newValue); previousSelection = null; render(); }
      catch { storageMessage("다른 탭의 이수 표시를 읽지 못했어요."); }
    });
    render();
  }
  window.curriculum = Object.freeze({init, refresh: () => {init(); render();}});
})();
