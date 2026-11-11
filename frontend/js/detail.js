// 과목 상세·강의평 작성. 사용자 입력은 모두 textContent로 표시합니다.
(() => {
  "use strict";
  const dialog = document.getElementById("detail-modal");
  const $ = (id) => document.getElementById(id);
  let version = 0;
  let state = {};
  let opener = null;
  const current = (token) => token === version && dialog.open;
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    node.className = className;
    node.textContent = text;
    return node;
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

  function updateControls() {
    const disabled = state.busy || state.loading || !state.course || state.loadError;
    $("detail-cart").disabled = Boolean(disabled);
    $("detail-write").disabled = Boolean(disabled);
    $("detail-retry").disabled = Boolean(state.loading || state.busy);
    $("review-fields").disabled = Boolean(state.busy || state.metaLoading);
    $("review-submit").disabled = Boolean(state.busy || state.metaLoading || !state.metaReady || state.loadError);
    $("review-cancel").disabled = Boolean(state.busy);
    $("review-meta-retry").disabled = Boolean(state.metaLoading || state.busy);
    dialog.setAttribute("aria-busy", String(Boolean(state.loading || state.busy)));
  }

  function setError(message, retry = false) {
    $("detail-error").textContent = message;
    $("detail-error").hidden = !message;
    $("detail-retry").hidden = !retry;
  }

  function renderCourse(course) {
    $("detail-title").textContent = course.course_name;
    $("detail-code").textContent = `${course.course_code} · ${course.department}`;
    $("detail-category").textContent = course.category;
    $("detail-credit").textContent = `${course.credit}학점`;
    $("detail-rating").textContent = course.avg_rating == null ? "평가 없음" : `★ ${course.avg_rating.toFixed(1)} 평균`;
    $("detail-professor").textContent = course.professor;
    $("detail-semester").textContent = course.semester;
    $("detail-time").textContent = formatSlots(course.slots);
    $("detail-room").textContent = course.classroom || "강의실 미정";
    $("detail-review-count").textContent = `강의평 (${course.review_count}개)`;
    const list = $("detail-reviews");
    list.replaceChildren();
    if (!course.reviews.length) {
      list.append(el("p", "detail-empty", "아직 강의평이 없어요. 첫 평가를 남겨 주세요."));
    }
    // API의 최신순 계약을 따르되 같은 시각의 평가는 새 review_id부터 표시합니다.
    const reviews = [...course.reviews].sort((a, b) =>
      String(b.created_at || "").localeCompare(String(a.created_at || "")) || b.review_id - a.review_id);
    for (const review of reviews) {
      const card = el("article", "review-card", "");
      const meta = el("div", "review-card__meta", "");
      const stars = el("span", "review-card__stars", "");
      for (let index = 1; index <= 5; index++) {
        const star = el("span", "review-star__icon", "★");
        star.style.setProperty("--star-fill", `${Math.max(0, Math.min(1, review.rating - index + 1)) * 100}%`);
        star.setAttribute("aria-hidden", "true");
        stars.append(star);
      }
      stars.setAttribute("role", "img");
      stars.setAttribute("aria-label", `5점 만점에 ${review.rating}점`);
      meta.append(stars, el("span", "review-card__term", `${review.taken_semester} 수강`));
      card.append(meta, el("p", "review-card__comment", review.comment));
      list.append(card);
    }
    const cart = $("detail-cart");
    cart.textContent = course.in_cart ? "시간표에서 빼기" : "시간표에 넣기";
    cart.className = `detail-button detail-button--primary${course.in_cart ? " detail-button--remove" : ""}`;
    $("detail-code").hidden = false;
    $("detail-tags").hidden = false;
    $("detail-content").hidden = false;
  }

  async function loadCourse(token) {
    state.loading = true;
    state.loadError = false;
    setError("");
    updateControls();
    try {
      const course = await window.api.getCourse(state.id);
      if (!current(token)) return;
      state.course = course;
      renderCourse(course);
    } catch (error) {
      if (!current(token)) return;
      state.loadError = true;
      if (!state.course) $("detail-title").textContent = "과목 상세";
      setError(error.message, true);
    } finally {
      if (current(token)) {
        state.loading = false;
        updateControls();
      }
    }
  }

  function resetForm() {
    $("review-form").reset();
    state.rating = 0;
    $("review-error").textContent = "";
    $("review-length").textContent = "0 / 500자";
    updateStars();
  }

  function updateStars() {
    dialog.querySelectorAll("[data-rating]").forEach((button) => {
      const rating = Number(button.dataset.rating);

      button.setAttribute("aria-pressed", String(rating === state.rating));
    });
    dialog.querySelectorAll("[data-star]").forEach((star) => {
      const fill = Math.max(0, Math.min(1, state.rating - Number(star.dataset.star) + 1));
      star.style.setProperty("--star-fill", `${fill * 100}%`);
    });
    $("review-rating-value").textContent = state.rating ? `${state.rating}점 선택` : "별점을 선택해 주세요.";
  }

  async function loadSemesters() {
    const token = version;
    state.metaLoading = true;
    state.metaReady = false;
    $("review-meta-error").textContent = "";
    $("review-meta-retry").hidden = true;
    updateControls();
    try {
      const meta = await window.api.getMeta();
      if (!current(token)) return;
      const match = /^(\d{4})-([12])$/.exec(meta.semester);
      if (!match) throw new Error("수강 학기 정보를 읽을 수 없습니다.");
      const select = $("review-semester");
      select.replaceChildren();
      let year = Number(match[1]), term = Number(match[2]);
      for (let index = 0; index < 4; index++) {
        const value = `${year}-${term}`;
        const option = el("option", "", value);
        option.value = value;
        select.append(option);
        if (term === 2) term = 1;
        else { year--; term = 2; }
      }
      select.value = meta.semester;
      state.metaReady = true;
    } catch (error) {
      if (current(token)) {
        $("review-meta-error").textContent = error.message;
        $("review-meta-retry").hidden = false;
      }
    } finally {
      if (current(token)) { state.metaLoading = false; updateControls(); }
    }
  }

  async function refreshBackground() {
    await Promise.all([window.dashboard.refresh(), window.timetable.refresh()]);
  }

  async function toggleCart() {
    if (state.busy || state.loading || state.loadError || !state.course) return;
    const token = version, id = state.id, removing = state.course.in_cart;
    state.busy = true;
    setError("");
    updateControls();
    try {
      await (removing ? window.api.removeFromCart(id) : window.api.addToCart(id));
      const tasks = [refreshBackground()];
      if (current(token)) tasks.push(loadCourse(token));
      await Promise.all(tasks);
    } catch (error) {
      if (current(token)) setError(error.message);
    } finally {
      if (current(token)) { state.busy = false; updateControls(); }
    }
  }

  async function submitReview(event) {
    event.preventDefault();
    if (state.busy || state.loading || state.loadError || !state.metaReady) return;
    const comment = $("review-comment").value.trim();
    const term = $("review-semester").value;
    let error = "";
    if (!Number.isFinite(state.rating) || state.rating < 0.5 || state.rating > 5 || !Number.isInteger(state.rating * 2)) error = "별점은 0.5~5점 사이에서 0.5점 단위로 골라 주세요.";
    else if ([...comment].length < 5 || [...comment].length > 500) error = "강의평은 5자 이상 500자 이하로 적어 주세요.";
    else if (!/^\d{4}-[12]$/.test(term)) error = "수강 학기 형식이 올바르지 않습니다.";
    $("review-error").textContent = error;
    if (error) return;
    const token = version, id = state.id;
    state.busy = true;
    updateControls();
    try {
      await window.api.postReview(id, { rating: state.rating, comment, taken_semester: term });
      const tasks = [refreshBackground()];
      if (current(token)) {
        $("review-form").hidden = true;
        resetForm();
        $("detail-notice").textContent = "강의평이 등록되었습니다.";
        tasks.push(loadCourse(token));
      }
      await Promise.all(tasks);
    } catch (error) {
      if (current(token)) $("review-error").textContent = error.message;
    } finally {
      if (current(token)) { state.busy = false; updateControls(); }
    }
  }

  async function openDetail(offeringId) {
    const token = ++version;
    opener = document.activeElement;
    state = { id: offeringId, course: null, busy: false, loading: false, rating: 0, metaReady: false };
    $("detail-title").textContent = "과목 정보를 불러오는 중…";
    $("detail-code").hidden = true;
    $("detail-tags").hidden = true;
    $("detail-content").hidden = true;
    $("review-form").hidden = true;
    $("detail-notice").textContent = "";
    $("detail-cart").textContent = "시간표에 넣기";
    resetForm();
    if (!dialog.open) dialog.showModal();
    $("detail-close").focus();
    await loadCourse(token);
  }

  $("detail-close").addEventListener("click", () => dialog.close());
  $("detail-close-bottom").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    version++; // 닫힌 뒤 도착하는 요청이 다음 모달을 덮어쓰지 못하게 합니다.
    if (opener?.isConnected) opener.focus();
    else document.querySelector('.header-tabs__link[aria-current="page"]')?.focus();
  });
  const outside = (event) => {
    const rect = dialog.getBoundingClientRect();
    return event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom);
  };
  let startedOutside = false;
  dialog.addEventListener("pointerdown", (event) => { startedOutside = outside(event); });
  dialog.addEventListener("click", (event) => {
    if (startedOutside && outside(event)) dialog.close();
    startedOutside = false;
  });
  $("detail-retry").addEventListener("click", () => loadCourse(version));
  $("detail-cart").addEventListener("click", toggleCart);
  $("detail-write").addEventListener("click", async () => {
    $("review-form").hidden = false;
    if (!state.metaReady && !state.metaLoading) await loadSemesters();
    if (dialog.open && !$("review-form").hidden) $("review-comment").focus();
  });
  $("review-meta-retry").addEventListener("click", loadSemesters);
  $("review-cancel").addEventListener("click", () => {
    $("review-form").hidden = true;
    resetForm();
    $("detail-write").focus();
  });
  const ratingArea = dialog.querySelector(".review-stars");
  const ratingStars = [...dialog.querySelectorAll("[data-star]")];
  let ratingPointer = null;
  function selectRatingAt(clientX) {
    if ($("review-fields").disabled) return;
    let rating = 5;
    for (const star of ratingStars) {
      const rect = star.getBoundingClientRect();
      if (clientX <= rect.right) {
        const value = Number(star.dataset.star);
        // 별 사이의 여백은 직전 별의 점수로 처리합니다.
        rating = clientX < rect.left && value > 1 ? value - 1
          : value - (clientX < rect.left + rect.width / 2 ? 0.5 : 0);
        break;
      }
    }
    state.rating = rating;
    updateStars();
  }
  ratingArea.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.isPrimary === false || ratingPointer !== null || $("review-fields").disabled) return;
    event.preventDefault();
    ratingPointer = event.pointerId;
    ratingArea.setPointerCapture(event.pointerId);
    selectRatingAt(event.clientX);
    dialog.querySelector(`[data-rating="${state.rating}"]`)?.focus();
  });
  ratingArea.addEventListener("pointermove", (event) => {
    if (event.pointerId === ratingPointer) selectRatingAt(event.clientX);
  });
  ratingArea.addEventListener("pointerup", (event) => {
    if (event.pointerId !== ratingPointer) return;
    selectRatingAt(event.clientX);
    ratingPointer = null;
    if (ratingArea.hasPointerCapture(event.pointerId)) ratingArea.releasePointerCapture(event.pointerId);
  });
  const stopRatingDrag = () => {
    const pointer = ratingPointer;
    ratingPointer = null;
    if (pointer !== null && ratingArea.hasPointerCapture(pointer)) ratingArea.releasePointerCapture(pointer);
  };
  ratingArea.addEventListener("pointercancel", stopRatingDrag);
  ratingArea.addEventListener("lostpointercapture", stopRatingDrag);
  dialog.addEventListener("close", stopRatingDrag);
  dialog.querySelectorAll("[data-rating]").forEach((button) => button.addEventListener("click", (event) => {
    // 포인터 선택은 위에서 처리하고, 키보드·보조기기의 클릭은 유지합니다.
    if (event.detail > 0 || $("review-fields").disabled) return;
    state.rating = Number(button.dataset.rating);
    updateStars();
  }));
  // 이모지도 한 글자로 계산합니다. 한글 조합은 끝난 직후 제한합니다.
  let composing = false;
  function limitComment() {
    const input = $("review-comment");
    const characters = [...input.value];
    if (characters.length > 500) {
      const start = input.selectionStart;
      const end = input.selectionEnd;
      input.value = characters.slice(0, 500).join("");
      input.setSelectionRange(Math.min(start, input.value.length), Math.min(end, input.value.length));
    }
    $("review-length").textContent = `${[...input.value].length} / 500자`;
  }
  $("review-comment").addEventListener("compositionstart", () => { composing = true; });
  $("review-comment").addEventListener("compositionend", () => { composing = false; limitComment(); });
  $("review-comment").addEventListener("input", (event) => {
    if (!composing && !event.isComposing) limitComment();
  });
  $("review-form").addEventListener("submit", submitReview);
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-detail-id]");
    if (button) openDetail(Number(button.dataset.detailId));
  });
  window.openDetail = openDetail;
})();
