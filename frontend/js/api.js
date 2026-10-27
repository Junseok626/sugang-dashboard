// 실제 Flask API 호출 전용. 실패해도 샘플 데이터로 자동 대체하지 않습니다.
(() => {
  "use strict";
  async function request(path, options = {}) {
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
    return request(`/courses${queryString ? `?${queryString}` : ""}`);
  }
  window.api = Object.freeze({
    request,
    getMeta: () => request("/meta"),
    searchCourses,
    getCourse: (id) => request(`/courses/${encodeURIComponent(id)}`),
  });
})();
