// General site interactions: mobile nav, flash auto-dismiss, AJAX add-to-cart, quantity steppers.
document.addEventListener("DOMContentLoaded", function () {
  // Mobile nav toggle
  const navToggle = document.getElementById("nav-toggle");
  const mobileNav = document.getElementById("mobile-nav");
  if (navToggle && mobileNav) {
    navToggle.addEventListener("click", () => mobileNav.classList.toggle("open"));
  }

  // Flash message dismiss + auto-hide
  document.querySelectorAll(".flash").forEach((flash) => {
    const closeBtn = flash.querySelector(".flash-close");
    if (closeBtn) closeBtn.addEventListener("click", () => flash.remove());
    setTimeout(() => flash.remove(), 6000);
  });

  // AJAX "Add to cart" forms (progressively enhances normal form POSTs)
  document.querySelectorAll("form.add-to-cart-form").forEach((form) => {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const submitBtn = form.querySelector("button[type=submit]");
      const originalLabel = submitBtn ? submitBtn.textContent : "";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Adding…";
      }

      try {
        const res = await fetch(form.action, {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          body: new FormData(form),
        });
        const data = await res.json();

        const cartBadge = document.querySelector(".cart-link .badge");
        if (data.cart_count) {
          if (cartBadge) {
            cartBadge.textContent = data.cart_count;
          } else {
            const cartLink = document.querySelector(".cart-link");
            const span = document.createElement("span");
            span.className = "badge";
            span.textContent = data.cart_count;
            cartLink.appendChild(span);
          }
        }
        showToast(data.message || "Added to cart.");
      } catch (err) {
        // Fall back to normal form submission if fetch fails (e.g. offline)
        form.submit();
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalLabel;
        }
      }
    });
  });

  // Quantity steppers
  document.querySelectorAll(".qty-stepper").forEach((stepper) => {
    const input = stepper.querySelector("input[type=number]");
    stepper.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const delta = parseInt(btn.dataset.delta, 10);
        const newVal = Math.max(1, (parseInt(input.value, 10) || 1) + delta);
        input.value = newVal;
      });
    });
  });

  // Password show/hide toggle (eye icon)
  document.querySelectorAll(".password-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.classList.toggle("is-showing", !showing);
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });

  // Mobile category filter (select-based) mirrors the desktop chip row
  const mobileCategorySelect = document.getElementById("mobile-category-select");
  if (mobileCategorySelect) {
    mobileCategorySelect.addEventListener("change", () => {
      window.location.href = mobileCategorySelect.value;
    });
  }

  // Little celebratory confetti burst — used after a booking/order success flash
  if (document.querySelector(".flash-success")) {
    burstConfetti();
  }
});

function burstConfetti() {
  const colors = ["#5B21B6", "#8B5CF6", "#C4B5FD", "#1E9E6B"];
  const container = document.createElement("div");
  container.className = "confetti-layer";
  document.body.appendChild(container);

  for (let i = 0; i < 24; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "vw";
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = Math.random() * 0.4 + "s";
    piece.style.animationDuration = 1.6 + Math.random() * 1.2 + "s";
    container.appendChild(piece);
  }
  setTimeout(() => container.remove(), 3200);
}

function showToast(message) {
  const stack = document.getElementById("flash-stack") || (function () {
    const el = document.createElement("div");
    el.id = "flash-stack";
    el.className = "flash-stack";
    document.body.appendChild(el);
    return el;
  })();

  const toast = document.createElement("div");
  toast.className = "flash flash-success";
  toast.innerHTML = `<span>${message}</span><button class="flash-close" aria-label="Dismiss">&times;</button>`;
  toast.querySelector(".flash-close").addEventListener("click", () => toast.remove());
  stack.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ── Header currency switcher ──
document.addEventListener("DOMContentLoaded", function () {
  const headerCurrencySelect = document.getElementById("header-currency-select");
  if (headerCurrencySelect) {
    headerCurrencySelect.addEventListener("change", function () {
      fetch(`/set-currency/${this.value}`, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      }).then(function () { window.location.reload(); });
    });
  }
});
