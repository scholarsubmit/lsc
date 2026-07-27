// Scroll-reveal: adds .is-visible to .reveal elements as they enter the viewport.
// Respects prefers-reduced-motion (CSS already no-ops the transition in that case).
(function () {
  var targets = document.querySelectorAll('.reveal');
  if (!targets.length) return;

  if (!('IntersectionObserver' in window)) {
    targets.forEach(function (el) { el.classList.add('is-visible'); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

  targets.forEach(function (el) { io.observe(el); });

  // Safety net: some in-app/embedded mobile browsers throttle or delay
  // IntersectionObserver callbacks. Never leave content permanently hidden —
  // force-reveal anything still waiting after 4s.
  setTimeout(function () {
    targets.forEach(function (el) { el.classList.add('is-visible'); });
  }, 4000);

  // Stagger children of .reveal-stagger containers via an --i custom property
  document.querySelectorAll('.reveal-stagger').forEach(function (group) {
    Array.prototype.forEach.call(group.children, function (child, i) {
      child.style.setProperty('--i', i);
    });
  });
})();
