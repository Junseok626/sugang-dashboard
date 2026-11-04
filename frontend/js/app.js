// 공통 헤더와 주소(#timetable / #search)에 따른 탭 전환을 담당합니다.
(() => {
  "use strict";
  async function loadMeta() {
    const semester = document.getElementById("meta-semester");
    const badge = document.getElementById("meta-updated");
    const retry = document.getElementById("meta-retry");
    retry.hidden = true;
    try {
      const meta = await window.api.getMeta();
      semester.textContent = `${meta.semester}학기 기준`;
      semester.removeAttribute("title");
      badge.hidden = !meta.last_updated;
      badge.textContent = meta.last_updated ? `최신 반영일 ${meta.last_updated.slice(5, 10).replace("-", ".")}` : "";
    } catch (error) {
      semester.textContent = "학기 정보를 불러오지 못했습니다.";
      semester.title = error.message;
      badge.hidden = true;
      retry.hidden = false;
    }
  }

  function showTab() {
    let tab = window.location.hash;
    if (tab !== "#timetable" && tab !== "#search") {
      tab = "#timetable";
      window.history.replaceState(null, "", tab);
    }
    document.getElementById("tab-timetable").hidden = tab !== "#timetable";
    document.getElementById("tab-search").hidden = tab !== "#search";
    document.querySelectorAll(".header-tabs__link").forEach((link) => {
      if (link.getAttribute("href") === tab) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    if (tab === "#search") window.dashboard.refresh();
    else window.timetable.refresh();
  }

  function init() {
    window.dashboard.init();
    window.timetable.init();
    document.getElementById("meta-retry").addEventListener("click", loadMeta);
    window.addEventListener("hashchange", showTab);
    loadMeta();
    showTab();
  }
  init();
})();
