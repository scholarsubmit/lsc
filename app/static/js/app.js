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
});

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
