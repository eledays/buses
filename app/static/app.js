const reward = document.querySelector(".reward");
const primaryButton = document.querySelector(".primary-button");
const rideForm = document.querySelector(".ride-form");
const formError = document.querySelector("[data-form-error]");
const buttonRecord = document.querySelector(".button-record");
const recentRidesList = document.querySelector("[data-recent-rides]");
const onboarding = document.querySelector("[data-onboarding]");
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
let buttonTimers = [];
let pageGlowTimer = null;

if (onboarding) {
  const startButton = onboarding.querySelector("[data-onboarding-start]");
  const storageKey = "buses_onboarding_done";

  function closeOnboarding() {
    try {
      window.localStorage.setItem(storageKey, "1");
    } catch (_error) {
      // Browsers can disable storage; closing should still work for the current page.
    }
    onboarding.hidden = true;
    document.body.classList.remove("has-onboarding");
  }

  let onboardingDone = false;
  try {
    onboardingDone = window.localStorage.getItem(storageKey) === "1";
  } catch (_error) {
    onboardingDone = false;
  }

  if (!onboardingDone) {
    onboarding.hidden = false;
    document.body.classList.add("has-onboarding");
  }

  startButton?.addEventListener("click", closeOnboarding);
}

if (reward) {
  const record = Number(reward.dataset.record || 0);
  const bursts = record % 100 === 0 ? 42 : record % 10 === 0 ? 22 : 10;

  for (let index = 0; index < bursts; index += 1) {
    const spark = document.createElement("span");
    spark.className = "spark";
    spark.style.setProperty("--x", `${Math.random() * 240 - 120}px`);
    spark.style.setProperty("--y", `${Math.random() * 160 - 80}px`);
    spark.style.setProperty("--delay", `${Math.random() * 0.45}s`);
    reward.appendChild(spark);
  }
}

function clearButtonTimers() {
  buttonTimers.forEach((timer) => window.clearTimeout(timer));
  buttonTimers = [];
}

function setFormError(message) {
  if (!formError) {
    return;
  }

  formError.textContent = message || "";
  formError.hidden = !message;
}

function flashPageGlow() {
  if (pageGlowTimer) {
    window.clearTimeout(pageGlowTimer);
  }

  document.body.classList.remove("page-glow");
  void document.body.offsetWidth;
  document.body.classList.add("page-glow");

  pageGlowTimer = window.setTimeout(() => {
    document.body.classList.remove("page-glow");
  }, 650);
}

function animateRecordButton(recordId) {
  if (!primaryButton || !buttonRecord) {
    return;
  }

  clearButtonTimers();
  primaryButton.classList.remove("is-confirmed", "is-returning");
  primaryButton.dataset.record = recordId;
  buttonRecord.textContent = `#${recordId}`;

  buttonTimers.push(window.setTimeout(() => {
    primaryButton.classList.add("is-confirmed");
    flashPageGlow();
  }, 80));

  buttonTimers.push(window.setTimeout(() => {
    primaryButton.classList.add("is-returning");
    primaryButton.classList.remove("is-confirmed");
  }, 3200));

  buttonTimers.push(window.setTimeout(() => {
    primaryButton.classList.remove("is-returning");
  }, 3900));
}

function formatRecentDate(date) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function prependRecentRide(recordId, formData) {
  if (!recentRidesList) {
    return;
  }

  recentRidesList.querySelector("[data-recent-empty]")?.remove();

  const item = document.createElement("article");
  item.className = "recent-entry-item";

  const routeChip = document.createElement("span");
  routeChip.className = "route-chip";
  routeChip.textContent = formData.get("route_number") || "";

  const main = document.createElement("div");
  const bus = document.createElement("strong");
  bus.textContent = formData.get("bus_number") || "";
  const date = document.createElement("p");
  date.textContent = formatRecentDate(new Date());
  main.append(bus, date);

  const record = document.createElement("span");
  record.className = "ride-id";
  record.textContent = `#${recordId}`;

  item.append(routeChip, main, record);
  recentRidesList.prepend(item);

  while (recentRidesList.querySelectorAll(".recent-entry-item").length > 5) {
    recentRidesList.querySelector(".recent-entry-item:last-of-type")?.remove();
  }
}

if (primaryButton && primaryButton.dataset.record) {
  animateRecordButton(primaryButton.dataset.record);
}

if (rideForm && primaryButton) {
  rideForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError("");
    primaryButton.disabled = true;

    try {
      const formData = new FormData(rideForm);
      const response = await fetch(rideForm.action || window.location.pathname, {
        method: "POST",
        body: formData,
        headers: {
          "Accept": "application/json",
          "X-CSRF-Token": csrfToken,
          "X-Requested-With": "fetch",
        },
      });
      const result = await response.json();

      if (!response.ok || !result.ok) {
        setFormError(result.error || "Не получилось сохранить поездку.");
        return;
      }

      animateRecordButton(result.ride);
      prependRecentRide(result.ride, formData);
      rideForm.reset();
    } catch (_error) {
      setFormError("Связь с сервером пропала. Попробуй еще раз.");
    } finally {
      primaryButton.disabled = false;
    }
  });
}

document.querySelectorAll("[data-collapse-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const targetId = button.dataset.collapseTarget;
    const target = document.getElementById(targetId);
    const label = button.querySelector("[data-more-text]");

    if (!target) {
      return;
    }

    const isOpen = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!isOpen));

    if (label) {
      label.textContent = isOpen ? "Смотреть больше" : "Свернуть";
    }

    if (isOpen) {
      collapseList(target);
    } else {
      expandList(target);
    }
  });
});

function expandList(target) {
  target.hidden = false;
  target.classList.add("is-animating");
  target.style.height = "0px";
  target.style.opacity = "0";
  void target.offsetHeight;
  target.style.height = `${target.scrollHeight}px`;
  target.style.opacity = "1";

  window.setTimeout(() => {
    target.classList.remove("is-animating");
    target.style.height = "";
    target.style.opacity = "";
  }, 300);
}

const rideModal = document.querySelector("[data-ride-modal]");
const rideEditForm = document.querySelector("[data-ride-edit-form]");
const editError = document.querySelector("[data-edit-error]");
let activeRideCard = null;
let modalCloseTimer = null;

function setEditError(message) {
  if (!editError) {
    return;
  }

  editError.textContent = message || "";
  editError.hidden = !message;
}

function openRideModal(card) {
  if (!rideModal || !rideEditForm) {
    return;
  }

  activeRideCard = card;
  setEditError("");
  rideEditForm.querySelector("[data-edit-id]").value = card.dataset.id;
  rideEditForm.querySelector("[data-edit-route]").value = card.dataset.route || "";
  rideEditForm.querySelector("[data-edit-bus]").value = card.dataset.bus || "";
  rideEditForm.querySelector("[data-edit-note]").value = card.dataset.note || "";
  rideEditForm.querySelector("[data-edit-ridden-at]").value = card.dataset.riddenAt || "";
  rideModal.showModal();
  window.clearTimeout(modalCloseTimer);
  window.requestAnimationFrame(() => {
    rideModal.classList.add("is-open");
  });
}

function closeRideModal() {
  if (rideModal?.open) {
    rideModal.classList.remove("is-open");
    modalCloseTimer = window.setTimeout(() => {
      rideModal.close();
      activeRideCard = null;
    }, 220);
  } else {
    activeRideCard = null;
  }
}

function forceCloseRideModal() {
  if (rideModal?.open) {
    window.clearTimeout(modalCloseTimer);
    rideModal.classList.remove("is-open");
    rideModal.close();
  }
  activeRideCard = null;
}

function formatRideDate(value) {
  return value ? value.replace("T", " ") : "";
}

function updateRideCard(card, ride) {
  card.dataset.route = ride.route_number;
  card.dataset.bus = ride.bus_number;
  card.dataset.note = ride.note || "";
  card.dataset.riddenAt = ride.ridden_at_input || ride.ridden_at.slice(0, 16);
  card.querySelector(".route-chip").textContent = ride.route_number;
  card.querySelector("[data-ride-bus]").textContent = ride.bus_number;
  card.querySelector("[data-ride-date]").textContent = ride.ridden_at_display || formatRideDate(ride.ridden_at);

  const noteElement = card.querySelector("[data-ride-note]");
  if (noteElement) {
    noteElement.textContent = ride.note || "";
    noteElement.hidden = !ride.note;
  }
}

document.querySelectorAll("[data-edit-ride]").forEach((button) => {
  button.addEventListener("click", () => {
    const card = button.closest("[data-ride-card]");
    if (card) {
      openRideModal(card);
    }
  });
});

document.querySelector("[data-close-modal]")?.addEventListener("click", closeRideModal);

rideModal?.addEventListener("click", (event) => {
  if (event.target === rideModal) {
    closeRideModal();
  }
});

rideModal?.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeRideModal();
});

rideEditForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!activeRideCard) {
    return;
  }

  setEditError("");
  const rideId = rideEditForm.querySelector("[data-edit-id]").value;

  try {
    const response = await fetch(`/rides/${rideId}`, {
      method: "PUT",
      body: new FormData(rideEditForm),
      headers: {
        "Accept": "application/json",
        "X-CSRF-Token": csrfToken,
        "X-Requested-With": "fetch",
      },
    });
    const result = await response.json();

    if (!response.ok || !result.ok) {
      setEditError(result.error || "Не получилось сохранить запись.");
      return;
    }

    updateRideCard(activeRideCard, result.ride);
    forceCloseRideModal();
  } catch (_error) {
    setEditError("Связь с сервером пропала. Попробуй еще раз.");
  }
});

document.querySelector("[data-delete-ride]")?.addEventListener("click", async () => {
  if (!activeRideCard) {
    return;
  }

  const rideId = activeRideCard.dataset.id;
  const confirmed = window.confirm(`Удалить запись #${rideId}?`);
  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(`/rides/${rideId}`, {
      method: "DELETE",
      headers: {
        "Accept": "application/json",
        "X-CSRF-Token": csrfToken,
        "X-Requested-With": "fetch",
      },
    });
    const result = await response.json();

    if (!response.ok || !result.ok) {
      setEditError(result.error || "Не получилось удалить запись.");
      return;
    }

    activeRideCard.remove();
    forceCloseRideModal();
  } catch (_error) {
    setEditError("Связь с сервером пропала. Попробуй еще раз.");
  }
});

function collapseList(target) {
  target.classList.add("is-animating");
  target.style.height = `${target.scrollHeight}px`;
  target.style.opacity = "1";
  void target.offsetHeight;
  target.style.height = "0px";
  target.style.opacity = "0";

  window.setTimeout(() => {
    target.hidden = true;
    target.classList.remove("is-animating");
    target.style.height = "";
    target.style.opacity = "";
  }, 300);
}
