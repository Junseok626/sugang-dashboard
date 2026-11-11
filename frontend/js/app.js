// frontend/js/app.js
(() => {
  "use strict";

  // 헤더의 학기·최신 반영일 조회
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
      badge.textContent = meta.last_updated
        ? `최신 반영일 ${meta.last_updated.slice(5, 10).replace("-", ".")}`
        : "";
    } catch (error) {
      semester.textContent = "학기 정보를 불러오지 못했습니다.";
      semester.title = error.message;
      badge.hidden = true;
      retry.hidden = false;
    }
  }

  // 주소의 해시에 맞춰 탭 표시
  function showTab() {
    let tab = window.location.hash;

    // 첫 접속은 전체 과목 조회. 시간표 화면이 없는 구성도 검색으로 연결합니다.
    if ((!["#timetable", "#search", "#curriculum"].includes(tab)) ||
        (tab === "#timetable" && !window.timetable?.isAvailable())) {
      tab = "#search";
      window.history.replaceState(null, "", tab);
    }

    document.getElementById("tab-timetable").hidden =
      tab !== "#timetable";

    document.getElementById("tab-search").hidden =
      tab !== "#search";

    document.getElementById("tab-curriculum").hidden = tab !== "#curriculum";

    // 선택된 탭의 파란 글자·밑줄 표시
    document.querySelectorAll(".header-tabs__link").forEach((link) => {
      if (link.getAttribute("href") === tab) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    // 선택한 탭의 데이터를 다시 조회하고 화면 갱신
    if (tab === "#search") {
      window.dashboard.refresh();
    } else if (tab === "#timetable") {
      window.timetable?.refresh();
    }
  }

  function init() {
    window.dashboard.init();
    window.timetable.init();

    document
      .getElementById("meta-retry")
      .addEventListener("click", loadMeta);

    window.addEventListener("hashchange", showTab);

    loadMeta();
    showTab();
  }

  init();
})();
