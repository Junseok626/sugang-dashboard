// 실제 Flask API 호출 전용. 실패해도 샘플 데이터로 자동 대체하지 않습니다.
(() => {
  "use strict";
  let selectedSemester = null;
  let revision = 0;
  let mutations = 0;
  const validSemester = (value) => /^\d{4}-[12]$/.test(value);
  function setSemester(value) {
    if (!validSemester(value)) throw new Error("학기 형식이 올바르지 않습니다.");
    if (value !== selectedSemester) { selectedSemester = value; revision++; }
  }
  function semesterPath(path, semester = selectedSemester) {
    return semester ? `${path}${path.includes("?") ? "&" : "?"}semester=${encodeURIComponent(semester)}` : path;
  }
  async function request(path, options = {}) {
    const started = revision;
    const writing = options.method && options.method !== "GET";
    if (writing) { mutations++; window.dispatchEvent(new Event("api-busy-change")); }
    try {
      const body = await sendRequest(path, options);
      if (started !== revision) throw new DOMException("학기가 변경되었습니다.", "AbortError");
      return body;
    } catch (error) {
      if (started !== revision) throw new DOMException("학기가 변경되었습니다.", "AbortError");
      throw error;
    } finally {
      if (writing) { mutations--; window.dispatchEvent(new Event("api-busy-change")); }
    }
  }
  async function sendRequest(path, options = {}) {
    let res;
    try {
      res = await fetch(`/api${path}`, options);
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new Error("서버에 연결할 수 없습니다.");
    }
    let body;
    try {
      body = await res.json();
    } catch {
      throw new Error(res.ok ? "서버 응답을 읽을 수 없습니다." : `요청을 처리하지 못했습니다. (${res.status})`);
    }
    if (!res.ok) {
      const error = new Error(typeof body?.error === "string" ? body.error : `요청을 처리하지 못했습니다. (${res.status})`);
      error.status = res.status;
      throw error;
    }
    return body;
  }
  
  function searchCourses(filters = {}) {
    const params = new URLSearchParams();
    const query = (filters.q || "").trim();
    if (query) params.set("q", query);
    for (const key of ["category", "day"]) {
      const value = filters[key];
      const list = value == null ? [] : typeof value === "string" ? [value] : Array.from(value);
      for (const item of list) if (item !== "") params.append(key, item);
    }
    for (const key of ["credit", "min_rating"]) {
      if (filters[key] !== "" && filters[key] != null) params.set(key, filters[key]);
    }
    const queryString = params.toString();
    return request(semesterPath(`/courses${queryString ? `?${queryString}` : ""}`));
  }
  window.api = Object.freeze({
    request,
    setSemester,
    getSemester: () => selectedSemester,
    isMutating: () => mutations > 0,
    getMeta: (semester = selectedSemester) => request(semesterPath("/meta", semester)),
    searchCourses,
    getCourse: (id) => request(`/courses/${encodeURIComponent(id)}`),
    postReview: (id, body) => request(`/courses/${encodeURIComponent(id)}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    getCart: async () => {
      const semester = selectedSemester;
      const cart = await request(semesterPath("/cart", semester));
      if (semester && cart.semester !== semester) throw new Error("선택한 학기의 시간표를 불러오지 못했습니다.");
      return cart;
    },
    addToCart: (id) => request(semesterPath("/cart"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offering_id: id, semester: selectedSemester }),
    }),
    removeFromCart: (id) => request(semesterPath(`/cart/${encodeURIComponent(id)}`), {
      method: "DELETE",
    }),
  });
})();
