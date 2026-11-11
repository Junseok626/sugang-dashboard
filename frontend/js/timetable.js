// 내 시간표: 서버의 getCart() 결과로 격자·목록·학점을 함께 갱신.
(() => {
  "use strict";
  const DAYS = ["월", "화", "수", "목", "금"];
  const START = 9 * 60;
  const END = 19 * 60;
  const STEP = 30;
  const state = { cart: null, loading: false, removing: false, error: "" };
  let latestRequest = 0;
  let initialized = false;

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const minutes = (time) => {
    const [hour, minute] = time.split(":").map(Number);
    return hour * 60 + minute;
  };

  function formatSlots(slots) {
    if (!slots.length) return "시간 미정";
    const groups = new Map();
    for (const slot of slots) {
      const range = `${slot.start}–${slot.end}`;
      groups.set(range, [...(groups.get(range) || []), slot.day]);
    }
    return [...groups].map(([range, days]) => `${days.join("·")} ${range}`).join(", ");
  }

  function buildGrid() {
    const cells = document.getElementById("week-grid-cells");
    cells.replaceChildren();
    const place = (node, row, col, span = 1) => {
      node.style.gridRow = `${row} / span ${span}`;
      node.style.gridColumn = String(col);
      cells.append(node);
    };
    place(el("div", "week-grid__head"), 1, 1);
    DAYS.forEach((day, index) => place(el("div", "week-grid__head", day), 1, index + 2));
    for (let index = 0; index < (END - START) / STEP; index++) {
      const start = START + index * STEP;
      if (index % 2 === 0) {
        place(el("div", "week-grid__time", `${String(start / 60).padStart(2, "0")}:00`), index + 2, 1, 2);
      }
      DAYS.forEach((_, day) => place(el("div", "week-grid__cell"), index + 2, day + 2));
    }
  }

  function render() {
    const cart = state.cart;
    const items = cart?.items || [];
    const busy = state.loading || state.removing;
    document.getElementById("tab-timetable").setAttribute("aria-busy", String(busy));
    document.getElementById("timetable-summary").textContent = cart
      ? `${cart.semester}학기 · ${items.length}과목 ${cart.total_credit}학점`
      : state.loading ? "시간표를 불러오는 중…" : "시간표를 불러오지 못했습니다.";
    document.getElementById("timetable-cart-title").textContent = cart ? `담은 과목 (${items.length})` : "담은 과목";
    document.getElementById("timetable-total").textContent = cart ? `${cart.total_credit}학점` : "—";
    document.getElementById("timetable-empty").hidden = !cart || items.length > 0;

    const status = document.getElementById("timetable-status");
    status.hidden = !state.error;
    document.getElementById("timetable-error").textContent = state.error;
    document.getElementById("timetable-retry").disabled = busy;

    const blocks = document.getElementById("week-grid-blocks");
    const list = document.getElementById("timetable-cart-list");
    blocks.replaceChildren();
    list.replaceChildren();
    if (!items.length) {
      list.append(el("li", "timetable-list__empty", cart
        ? "아직 담은 과목이 없어요"
        : state.loading ? "불러오는 중…" : "목록을 불러오지 못했습니다."));
    }

    items.forEach((course, index) => {
      // 시간 미정 과목도 담은 순서에는 포함하고, 블록만 생략.
      for (const slot of course.slots) {
        const day = DAYS.indexOf(slot.day);
        const start = Math.max(START, minutes(slot.start));
        const end = Math.min(END, minutes(slot.end));
        if (day < 0 || !Number.isFinite(start) || !Number.isFinite(end) || end <= start) continue;
        const block = el("button", "timetable-block");
        block.type = "button";
        block.dataset.detailId = course.offering_id;
        block.style.left = `calc(var(--time-label-width) + (100% - var(--time-label-width)) * ${day} / 5)`;
        block.style.top = `calc(var(--day-header-height) + var(--half-hour-height) * ${(start - START) / STEP})`;
        block.style.height = `calc(var(--half-hour-height) * ${(end - start) / STEP})`;
        block.style.backgroundColor = `var(--block-${index % 6 + 1})`;
        block.title = `${course.course_name} · ${slot.day} ${slot.start}–${slot.end} · ${course.classroom || "강의실 미정"}`;
        block.append(el("strong", "timetable-block__name", course.course_name),
          el("span", "timetable-block__room", course.classroom || "강의실 미정"));
        blocks.append(block);
      }
      const card = el("li", "cart-card");
      const text = el("button", "cart-card__text detail-trigger");
      text.type = "button";
      text.dataset.detailId = course.offering_id;
      const name = el("span", "cart-card__name", course.course_name);
      name.title = course.course_name;
      text.append(name, el("span", "cart-card__meta", `${formatSlots(course.slots)} · ${course.professor}`));
      const remove = el("button", "cart-card__remove", "×");
      remove.type = "button";
      remove.disabled = busy;
      remove.setAttribute("aria-label", `${course.course_name} 빼기`);
      remove.addEventListener("click", () => removeCourse(course.offering_id));
      card.append(text, remove);
      list.append(card);
    });
  }

  async function refresh() {
    if (!isAvailable()) return;
    const requestId = ++latestRequest;
    state.loading = true;
    state.error = "";
    render();
    try {
      const cart = await window.api.getCart();
      if (requestId !== latestRequest) return;
      if (!Array.isArray(cart.items)) throw new Error("시간표 목록을 읽을 수 없습니다.");
      state.cart = cart;
    } catch (error) {
      if (requestId === latestRequest) state.error = error.message;
    } finally {
      if (requestId === latestRequest) {
        state.loading = false;
        render();
      }
    }
  }

  async function removeCourse(id) {
    if (state.loading || state.removing) return;
    state.removing = true;
    state.error = "";
    render();
    try {
      await window.api.removeFromCart(id);
      // 서버에 저장된 최신 목록과 검색 결과를 모두 다시 조회.
      await Promise.all([refresh(), window.dashboard.refresh()]);
    } catch (error) {
      state.error = error.message;
    } finally {
      state.removing = false;
      render();
    }
  }

  function init() {
    if (initialized || !isAvailable()) return;
    initialized = true;
    buildGrid();
    document.getElementById("timetable-retry").addEventListener("click", refresh);
  }

  // 현재 HTML에 큰 시간표가 없는 경우 초기화·갱신을 건너뜁니다.
  function isAvailable() {
    return ["tab-timetable", "week-grid-cells", "week-grid-blocks", "timetable-summary",
      "timetable-cart-title", "timetable-total", "timetable-empty", "timetable-status",
      "timetable-error", "timetable-retry", "timetable-cart-list"]
      .every((id) => document.getElementById(id));
  }

  window.timetable = Object.freeze({ init, refresh, isAvailable });
})();
