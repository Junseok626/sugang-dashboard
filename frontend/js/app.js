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

    // 주소에 탭이 없거나 잘못된 값이면 내 시간표로
    if (tab !== "#timetable" && tab !== "#search") {
      tab = "#timetable";
      window.history.replaceState(null, "", tab);
    }

    document.getElementById("tab-timetable").hidden =
      tab !== "#timetable";

    document.getElementById("tab-search").hidden =
      tab !== "#search";

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
    } else {
      // 다음 단계에서 timetable.js가 공개할 함수.
      // 아직 파일이 없을 때는 실행하지 않음.
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
