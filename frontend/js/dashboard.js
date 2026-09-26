const DAYS = ["월", "화", "수", "목", "금"];

const state = {
  courses: [],
  cart: [],
  query: "",
  categories: new Set(),
  days: new Set(),
  credit: "",
  minRating: "",
};

// 백엔드 연결 시 fetch("/api/...")로 교체
async function loadCourses() {
  return SAMPLE_COURSES;
}

// "화3,목3" → [{ day: "화", period: 3 }, { day: "목", period: 3 }]
function parseSlots(dayTime) {
  return dayTime.split(",").map((s) => {
    const t = s.trim();
    return { day: t[0], period: Number(t.slice(1)) };
  });
}

function formatSlots(dayTime) {
  return dayTime.split(",").map((s) => s.trim()).join(", ");
}

function findCourse(id) {
  return state.courses.find((c) => c.offering_id === id);
}

function cartSlots() {
  return state.cart.flatMap((id) => parseSlots(findCourse(id).day_time));
}

function hasConflict(course) {
  if (state.cart.includes(course.offering_id)) return false;
  const taken = cartSlots();
  return parseSlots(course.day_time).some((s) => taken.some((t) => t.day === s.day && t.period === s.period));
}

function matchesFilters(course) {
  const q = state.query.trim().toLowerCase();
  if (q && !course.course_name.toLowerCase().includes(q) && !course.professor.toLowerCase().includes(q)) return false;
  if (state.categories.size && !state.categories.has(course.category)) return false;
  if (state.days.size && !parseSlots(course.day_time).some((s) => state.days.has(s.day))) return false;
  if (state.credit && course.credit !== Number(state.credit)) return false;
  if (state.minRating && course.rating < Number(state.minRating)) return false;
  return true;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderResults() {
  const rows = document.getElementById("course-rows");
  const visible = state.courses.filter(matchesFilters);
  rows.replaceChildren();

  document.getElementById("result-count").textContent = `검색결과 ${visible.length}개 과목`;

  if (!visible.length) {
    rows.append(el("p", "course-table__empty", "조건에 맞는 과목이 없습니다."));
  }

  for (const course of visible) {
    const conflict = hasConflict(course);
    const inCart = state.cart.includes(course.offering_id);
    const row = el("div", "course-row");
    row.setAttribute("role", "row");

    const rating = conflict
      ? el("span", "course-row__rating course-row__rating--conflict", "시간 겹침")
      : el("span", "course-row__rating", `★ ${course.rating.toFixed(1)}`);

    const btn = el("button", "btn-add", inCart ? "담김" : "담기");
    btn.type = "button";
    btn.disabled = conflict || inCart;
    btn.addEventListener("click", () => addToCart(course.offering_id));

    row.append(
      el("span", "", course.course_name),
      el("span", "", course.professor),
      el("span", "", formatSlots(course.day_time)),
      el("span", "", String(course.credit)),
      rating,
      btn,
    );
    for (const cell of row.children) cell.setAttribute("role", "cell");
    rows.append(row);
  }

  renderToast(visible);
}

function renderToast(visible) {
  const toast = document.getElementById("conflict-toast");
  const blocked = visible.find(hasConflict);
  toast.hidden = !blocked;
  if (blocked) {
    document.getElementById("conflict-message").textContent =
      `"${blocked.course_name}"는 담긴 과목과 시간이 겹쳐 담을 수 없습니다.`;
  }
}

function renderMiniGrid() {
  const grid = document.getElementById("mini-grid");
  const periods = state.courses.flatMap((c) => parseSlots(c.day_time).map((s) => s.period));
  const first = Math.min(...periods);
  const last = Math.max(...periods);
  const taken = cartSlots();
  grid.replaceChildren();

  grid.append(el("div", "mini-grid__cell mini-grid__cell--head"));
  for (const d of DAYS) grid.append(el("div", "mini-grid__cell mini-grid__cell--head", d));

  for (let p = first; p <= last; p++) {
    const lastRow = p === last ? " mini-grid__cell--last-row" : "";
    grid.append(el("div", "mini-grid__cell mini-grid__cell--label" + lastRow, String(p)));
    for (const d of DAYS) {
      const filled = taken.some((t) => t.day === d && t.period === p) ? " mini-grid__cell--filled" : "";
      grid.append(el("div", "mini-grid__cell" + filled + lastRow));
    }
  }
}

function renderCart() {
  const list = document.getElementById("cart-list");
  list.replaceChildren();
  document.getElementById("cart-title").textContent = `내 시간표 (${state.cart.length}과목 담김)`;

  for (const id of state.cart) {
    const course = findCourse(id);
    const card = el("li", "cart-card");
    const text = el("div", "cart-card__text");
    text.append(
      el("span", "cart-card__name", course.course_name),
      el("span", "cart-card__meta", `${formatSlots(course.day_time)} · ${course.professor}`),
    );
    const remove = el("button", "cart-card__remove", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", `${course.course_name} 빼기`);
    remove.addEventListener("click", () => removeFromCart(id));
    card.append(text, remove);
    list.append(card);
  }
}

function render() {
  renderResults();
  renderMiniGrid();
  renderCart();
}

function addToCart(id) {
  const course = findCourse(id);
  if (state.cart.includes(id) || hasConflict(course)) return;
  state.cart.push(id);
  render();
}

function removeFromCart(id) {
  state.cart = state.cart.filter((x) => x !== id);
  render();
}

function bindFilters() {
  const input = document.getElementById("search-input");
  document.getElementById("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    state.query = input.value;
    renderResults();
  });
  input.addEventListener("input", () => {
    if (input.value === "") {
      state.query = "";
      renderResults();
    }
  });

  document.querySelectorAll('input[name="category"]').forEach((cb) => {
    cb.addEventListener("change", () => {
      cb.checked ? state.categories.add(cb.value) : state.categories.delete(cb.value);
      renderResults();
    });
  });

  document.querySelectorAll(".day-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const day = chip.dataset.day;
      const on = !state.days.has(day);
      on ? state.days.add(day) : state.days.delete(day);
      chip.setAttribute("aria-pressed", String(on));
      renderResults();
    });
  });

  document.getElementById("credit-filter").addEventListener("change", (e) => {
    state.credit = e.target.value;
    renderResults();
  });
  document.getElementById("rating-filter").addEventListener("change", (e) => {
    state.minRating = e.target.value;
    renderResults();
  });
}

async function init() {
  state.courses = await loadCourses();
  state.cart = [...SAMPLE_CART];
  bindFilters();
  render();
}

init();
