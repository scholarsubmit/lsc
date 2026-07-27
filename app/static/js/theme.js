// Theme switcher: light / dark, persisted to localStorage, respects system preference.
// Supports multiple toggle buttons on the same page (top nav + sidebar) via a shared
// class, so moving the control into a dashboard sidebar doesn't break the header one.
(function () {
  const root = document.documentElement;
  const toggleBtns = document.querySelectorAll(".theme-toggle-btn, #theme-toggle");

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    localStorage.setItem("pc-theme", theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#120E1A" : "#5B21B6");
  }

  toggleBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  });

  // Keep in sync if the user changes their OS-level preference and hasn't set a manual choice.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem("pc-theme")) {
      applyTheme(e.matches ? "dark" : "light");
    }
  });
})();
