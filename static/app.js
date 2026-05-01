const reward = document.querySelector(".reward");
const primaryButton = document.querySelector(".primary-button");
const rideForm = document.querySelector(".ride-form");
const formError = document.querySelector("[data-form-error]");
const buttonRecord = document.querySelector(".button-record");
let buttonTimers = [];
let pageGlowTimer = null;

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

if (primaryButton && primaryButton.dataset.record) {
  animateRecordButton(primaryButton.dataset.record);
}

if (rideForm && primaryButton) {
  rideForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError("");
    primaryButton.disabled = true;

    try {
      const response = await fetch(rideForm.action || window.location.pathname, {
        method: "POST",
        body: new FormData(rideForm),
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "fetch",
        },
      });
      const result = await response.json();

      if (!response.ok || !result.ok) {
        setFormError(result.error || "Не получилось сохранить поездку.");
        return;
      }

      animateRecordButton(result.ride.id);
      rideForm.reset();
      rideForm.querySelector("input")?.focus();
    } catch (_error) {
      setFormError("Связь с сервером пропала. Попробуй еще раз.");
    } finally {
      primaryButton.disabled = false;
    }
  });
}

document.querySelectorAll("input").forEach((input) => {
  input.addEventListener("input", () => {
    input.value = input.value.toUpperCase();
  });
});

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
