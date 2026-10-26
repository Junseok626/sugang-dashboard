(() => {
"use strict";
const DAYS = ["월", "화", "수", "목", "금"];
const DAY_START = 9 * 60;
const DAY_END = 19 * 60;
const SLOT = 30;

const state = {
  courses: [],
  cart: [],
  query: "",
  categories: new Set(),
  days: new Set(),
  credit: "",
  minRating: "",
  loading: false,
  error: "",
  cartMessage: "",
};

let latestRequest = 0;
async function loadCourses() {
  const requestId = ++latestRequest;
  state.loading = true;
  state.error = "";
  state.cartMessage = "";
  renderResults();
  try {
    const response = await window.api.searchCourses({
      q: state.query, category: [...state.categories], day: [...state.days],
      credit: state.credit, min_rating: state.minRating,
    });
    if (requestId !== latestRequest) return;
    if (!Array.isArray(response.courses)) throw new Error("과목 목록을 읽을 수 없습니다.");
    state.courses = response.courses;
  } catch (error) {
    if (requestId !== latestRequest) return;
    state.courses = [];
    state.error = error.message;
  } finally {
    if (requestId === latestRequest) {
      state.loading = false;
      renderResults();
    }
  }
}

const toMinutes = (hhmm) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};
// API 시각 문자열은 그대로 보관하고, 계산할 때만 분 단위로 변환합니다.
const numericSlots = (course) => course.slots.map((s) => ({
  day: s.day, start: toMinutes(s.start), end: toMinutes(s.end),
}));

// 같은 시간대는 요일을 묶어서 표시: "화·목 11:00–12:00"
function formatSlots(slots) {
  if (!slots.length) return "시간 미정";
  const groups = new Map();
  for (const s of slots) {
    const range = `${s.start}–${s.end}`;
    groups.set(range, [...(groups.get(range) || []), s.day]);
  }
  return [...groups].map(([range, days]) => `${days.join("·")} ${range}`).join(", ");
}

const overlaps = (a, b) => a.day === b.day && a.start < b.end && b.start < a.end;

function findCourse(id) {
  return state.courses.find((c) => c.offering_id === id);
}

function cartSlots() {
  return state.cart.flatMap(numericSlots);
}

const isInCart = (id) => state.cart.some((course) => course.offering_id === id);
function hasConflict(course) {
  if (isInCart(course.offering_id)) return false;
  const taken = cartSlots();
  return numericSlots(course).some((s) => taken.some((t) => overlaps(s, t)));
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderResults() {
  const rows = document.getElementById("course-rows");
  const visible = state.courses;
  rows.replaceChildren();
  rows.setAttribute("aria-busy", String(state.loading));
  if (state.loading || state.error) {
    document.getElementById("result-count").textContent = state.loading ? "과목을 불러오는 중입니다." : "과목을 불러오지 못했습니다.";
    const status = el("div", "course-table__empty", state.loading ? "잠시만 기다려 주세요." : state.error);
    status.setAttribute("role", state.error ? "alert" : "status");
    if (state.error) {
      const retry = el("button", "btn-add status-retry", "다시 시도");
      retry.type = "button";
      retry.addEventListener("click", loadCourses);
      status.append(retry);
    }
    rows.append(status);
    renderToast([]);
    return;
  }

  document.getElementById("result-count").textContent = `검색결과 ${visible.length}개 과목`;

  if (!visible.length) {
    rows.append(el("p", "course-table__empty", "조건에 맞는 과목이 없습니다."));
  }

  for (const course of visible) {
    const conflict = hasConflict(course);
    const inCart = isInCart(course.offering_id);
    const row = el("div", "course-row");
    row.setAttribute("role", "row");

    const rating = conflict
      ? el("span", "course-row__rating course-row__rating--conflict", "시간 겹침")
      : course.avg_rating === null
        ? el("span", "course-row__rating course-row__rating--empty", "평가 없음")
        : el("span", "course-row__rating", `★ ${course.avg_rating.toFixed(1)}`);

    const btn = el("button", inCart ? "btn-add btn-add--remove" : "btn-add", inCart ? "빼기" : "담기");
    btn.type = "button";
    btn.disabled = conflict;
    btn.setAttribute("aria-label", `${course.course_name} ${inCart ? "빼기" : "담기"}`);
    btn.addEventListener("click", () => (inCart ? handleRemoveFromCart : handleAddToCart)(course.offering_id));

    const name = el("span", "course-row__name", course.course_name);
    name.title = course.course_name;

    row.append(
      name,
      el("span", "", course.professor),
      el("span", "", formatSlots(course.slots)),
      el("span", "", String(course.credit)),
      rating,
      btn,
    );
    // 실제 버튼의 button 역할을 유지합니다.
    for (const cell of row.children) if (cell !== btn) cell.setAttribute("role", "cell");
    rows.append(row);
  }

  renderToast(visible);
}

function renderToast(visible) {
  const toast = document.getElementById("conflict-toast");
  const blocked = visible.find(hasConflict);
  const message = state.cartMessage || (blocked ? `"${blocked.course_name}"는 담긴 과목과 시간이 겹쳐 담을 수 없습니다.` : "");
  toast.hidden = !message;
  document.getElementById("conflict-message").textContent = message;
}

// 09:00~19:00, 30분 단위 행. 시간 라벨은 1시간(2행)씩 차지.
function renderMiniGrid() {
  const grid = document.getElementById("mini-grid");
  const taken = cartSlots();
  const place = (node, row, col, rowSpan = 1) => {
    node.style.gridRow = `${row} / span ${rowSpan}`;
    node.style.gridColumn = String(col);
    if (col === DAYS.length + 1) node.classList.add("mini-grid__cell--last-col");
    grid.append(node);
  };
  grid.replaceChildren();

  place(el("div", "mini-grid__cell mini-grid__cell--head"), 1, 1);
  DAYS.forEach((d, i) => place(el("div", "mini-grid__cell mini-grid__cell--head", d), 1, i + 2));

  const slots = (DAY_END - DAY_START) / SLOT;
  for (let i = 0; i < slots; i++) {
    const start = DAY_START + i * SLOT;
    const row = i + 2;
    const lastRow = i === slots - 1 ? " mini-grid__cell--last-row" : "";
    if (start % 60 === 0) {
      const hourLast = i + 2 >= slots ? " mini-grid__cell--last-row" : "";
      place(el("div", "mini-grid__cell mini-grid__cell--label" + hourLast, String(start / 60)), row, 1, 2);
    }
    DAYS.forEach((d, di) => {
      const slot = { day: d, start, end: start + SLOT };
      const filled = taken.some((t) => overlaps(slot, t)) ? " mini-grid__cell--filled" : "";
      const half = start % 60 === 0 ? " mini-grid__cell--half" : "";
      place(el("div", "mini-grid__cell" + filled + half + lastRow), row, di + 2);
    });
  }
}

function renderCart() {
  const list = document.getElementById("cart-list");
  list.replaceChildren();
  document.getElementById("cart-title").textContent = `내 시간표 (${state.cart.length}과목 담김)`;

  if (!state.cart.length) list.append(el("li", "cart-list__empty", "아직 담은 과목이 없어요."));
  for (const course of state.cart) {
    const card = el("li", "cart-card");
    const text = el("div", "cart-card__text");
    text.append(
      el("span", "cart-card__name", course.course_name),
      el("span", "cart-card__meta", `${formatSlots(course.slots)} · ${course.professor}`),
    );
    text.firstChild.title = course.course_name;
    const remove = el("button", "cart-card__remove", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", `${course.course_name} 빼기`);
    remove.addEventListener("click", () => handleRemoveFromCart(course.offering_id));
    card.append(text, remove);
    list.append(card);
  }
}

function render() {
  renderResults();
  renderMiniGrid();
  renderCart();
}

function handleAddToCart(id) {
  const course = findCourse(id);
  if (!course || isInCart(id)) return;
  if (state.cart.some((item) => item.course_code === course.course_code)) {
    state.cartMessage = "같은 과목의 다른 분반이 이미 담겨 있습니다.";
    renderToast(state.courses);
    return;
  }
  if (hasConflict(course)) return;
  state.cartMessage = "";
  state.cart.push({ ...course, slots: course.slots.map((s) => ({ ...s })) });
  render();
}

function handleRemoveFromCart(id) {
  state.cartMessage = "";
  state.cart = state.cart.filter((course) => course.offering_id !== id);
  render();
}

function bindFilters() {
  const input = document.getElementById("search-input");
  document.getElementById("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    state.query = input.value;
    loadCourses();
  });
  input.addEventListener("input", () => {
    if (input.value === "") {
      state.query = "";
      loadCourses();
    }
  });

  document.querySelectorAll('input[name="category"]').forEach((cb) => {
    cb.addEventListener("change", () => {
      cb.checked ? state.categories.add(cb.value) : state.categories.delete(cb.value);
      loadCourses();
    });
  });

  document.querySelectorAll(".day-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const day = chip.dataset.day;
      const on = !state.days.has(day);
      on ? state.days.add(day) : state.days.delete(day);
      chip.setAttribute("aria-pressed", String(on));
      loadCourses();
    });
  });

  document.getElementById("credit-filter").addEventListener("change", (e) => {
    state.credit = e.target.value;
    loadCourses();
  });
  document.getElementById("rating-filter").addEventListener("change", (e) => {
    state.minRating = e.target.value;
    loadCourses();
  });
}

async function loadMeta() {
  const semester = document.getElementById("meta-semester");
  const badge = document.getElementById("meta-updated");
  const retry = document.getElementById("meta-retry");
  retry.hidden = true;
  try {
    const meta = await window.apiu.getMeta();
    semester.removeAttribute("title");
    semester.textContent = `${meta.semester}학기 기준`;
    badge.hidden = !meta.last_updated;
    badge.textContent = meta.last_updated ? `최신 반영일 ${meta.last_updated.slice(5).replace("-", ".")}` : "";
  } catch (error) {
    semester.textContent = "학기 정보를 불러오지 못했습니다.";
    semester.title = error.message;
    badge.hidden = true;
    retry.hidden = false;
  }
}

function init() {
  bindFilters();
  document.getElementById("meta-retry").addEventListener("click", loadMeta);
  renderMiniGrid();
  renderCart();
  loadMeta();
  loadCourses();
}

init();
})();
