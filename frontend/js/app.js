// frontend/js/app.js
(() => {
  "use strict";

  let semesters = [];
  let loadingMeta = false;
  const $ = (id) => document.getElementById(id);
  function message(text) {
    $("semester-message").textContent = text;
    $("semester-message").hidden = !text;
  }
  function updateSemesterSelect() {
    const select = $("meta-semester");
    select.disabled = loadingMeta || window.api.isMutating() || !window.api.getSemester();
    // 실패한 전환은 기존에 조회 중인 학기로 되돌립니다.
    if (!loadingMeta && window.api.getSemester()) select.value = window.api.getSemester();
  }
  function renderSemesterOptions() {
    const select = $("meta-semester");
    select.replaceChildren();
    for (const semester of [...semesters].reverse()) {
      const option = document.createElement("option");
      option.value = semester;
      option.textContent = `${semester}학기 기준`;
      select.append(option);
    }
    select.value = window.api.getSemester();
  }
  async function loadMeta(target = window.api.getSemester()) {
    if (loadingMeta || window.api.isMutating()) return;
    loadingMeta = true;
    updateSemesterSelect();
    $("meta-retry").hidden = true;
    try {
      const meta = await window.api.getMeta(target);
      if (!/^\d{4}-[12]$/.test(meta.semester) || (target && meta.semester !== target)) {
        throw new Error("선택한 학기를 불러오지 못했습니다. 기존 학기를 유지합니다.");
      }
      if (window.api.isMutating()) throw new Error("담기·빼기가 끝난 뒤 학기를 변경해 주세요.");
      const previous = window.api.getSemester();
      window.api.setSemester(meta.semester);
      semesters = Array.isArray(meta.semesters)
        ? [...new Set(meta.semesters.filter(value => typeof value === "string" && /^\d{4}-[12]$/.test(value)))].sort()
        : [];
      if (!semesters.includes(meta.semester)) semesters.push(meta.semester);
      semesters.sort();
      renderSemesterOptions();
      const badge = $("meta-updated");
      badge.hidden = !meta.last_updated;
      badge.textContent = meta.last_updated ? `최신 반영일 ${meta.last_updated.slice(5, 10).replace("-", ".")}` : "";
      message(Array.isArray(meta.semesters) ? "" : "현재는 기본 학기만 조회할 수 있어요.");
      if (previous !== meta.semester) {
        window.dispatchEvent(new Event("semester-change"));
        window.dashboard.resetSemester();
        window.timetable.resetSemester();
        await Promise.all([window.dashboard.refresh(), window.timetable.refresh()]);
      }
    } catch (error) {
      message(error.message);
      if (!window.api.getSemester()) $("meta-semester").options[0].textContent = "학기 정보를 불러오지 못했습니다.";
      $("meta-retry").hidden = false;
    } finally {
      loadingMeta = false;
      updateSemesterSelect();
    }
  }

  // 주소의 해시에 맞춰 탭 표시
  function showTab() {
    let tab = window.location.hash;

    // 첫 접속은 전체 과목 조회. 시간표 화면이 없는 구성도 검색으로 연결합니다.
    if ((!["#timetable", "#search", "#curriculum"].includes(tab)) ||
        (tab === "#timetable" && !window.timetable?.isAvailable()) ||
        (tab === "#curriculum" && !document.getElementById("tab-curriculum"))) {
      tab = "#search";
      window.history.replaceState(null, "", tab);
    }

    document.getElementById("tab-timetable").hidden =
      tab !== "#timetable";

    document.getElementById("tab-search").hidden =
      tab !== "#search";

    const curriculum = document.getElementById("tab-curriculum");
    if (curriculum) curriculum.hidden = tab !== "#curriculum";

    // 선택된 탭의 파란 글자·밑줄 표시
    document.querySelectorAll(".header-tabs__link").forEach((link) => {
      if (link.getAttribute("href") === tab) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    // 선택한 탭의 데이터를 다시 조회하고 화면 갱신
    if (!window.api.getSemester()) return;
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
      .addEventListener("click", () => loadMeta());
    $("meta-semester").addEventListener("change", (event) => {
      const target = event.target.value;
      if (semesters.includes(target) && target !== window.api.getSemester()) loadMeta(target);
    });
    window.addEventListener("api-busy-change", updateSemesterSelect);

    window.addEventListener("hashchange", showTab);

    loadMeta();
    showTab();
  }

  init();
})();
