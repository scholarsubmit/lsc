// Lightweight showcase carousel — no dependencies.
// Handles autoplay, dot/arrow navigation, swipe, keyboard, and pause on interaction.
(function () {
  var root = document.querySelector('[data-showcase]');
  if (!root) return;

  var slides = Array.prototype.slice.call(root.querySelectorAll('.showcase-slide'));
  var dotsWrap = root.querySelector('.showcase-dots');
  var prevBtn = root.querySelector('.showcase-nav.prev');
  var nextBtn = root.querySelector('.showcase-nav.next');
  if (!slides.length) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var current = 0;
  var timer = null;
  var AUTOPLAY_MS = 4500;

  var dots = slides.map(function (_, i) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'showcase-dot' + (i === 0 ? ' is-active' : '');
    b.setAttribute('aria-label', 'Go to slide ' + (i + 1));
    b.addEventListener('click', function () { goTo(i); restart(); });
    dotsWrap.appendChild(b);
    return b;
  });

  function show(i) {
    slides.forEach(function (s, idx) { s.classList.toggle('is-active', idx === i); });
    dots.forEach(function (d, idx) { d.classList.toggle('is-active', idx === i); });
    current = i;
  }
  function goTo(i) { show((i + slides.length) % slides.length); }
  function next() { goTo(current + 1); }
  function prev() { goTo(current - 1); }

  function start() {
    if (reduceMotion || slides.length < 2) return;
    stop();
    timer = setInterval(next, AUTOPLAY_MS);
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function restart() { stop(); start(); }

  if (nextBtn) nextBtn.addEventListener('click', function () { next(); restart(); });
  if (prevBtn) prevBtn.addEventListener('click', function () { prev(); restart(); });

  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', start);
  root.addEventListener('focusin', stop);
  root.addEventListener('focusout', start);

  // Swipe support
  var touchStartX = null;
  root.addEventListener('touchstart', function (e) { touchStartX = e.touches[0].clientX; }, { passive: true });
  root.addEventListener('touchend', function (e) {
    if (touchStartX === null) return;
    var dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 40) { dx < 0 ? next() : prev(); restart(); }
    touchStartX = null;
  }, { passive: true });

  // Keyboard (when carousel or its controls are focused)
  root.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { next(); restart(); }
    if (e.key === 'ArrowLeft') { prev(); restart(); }
  });

  show(0);
  start();
})();

// Stat counter: animates numbers up once when the trust strip enters view.
(function () {
  var counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;

  function animate(el) {
    var target = parseInt(el.getAttribute('data-count'), 10) || 0;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.textContent = target; return;
    }
    var start = 0;
    var duration = 900;
    var startTime = null;
    function tick(ts) {
      if (!startTime) startTime = ts;
      var progress = Math.min((ts - startTime) / duration, 1);
      el.textContent = Math.round(start + (target - start) * progress);
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  if (!('IntersectionObserver' in window)) {
    counters.forEach(animate);
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) { animate(entry.target); io.unobserve(entry.target); }
    });
  }, { threshold: 0.6 });
  counters.forEach(function (c) { io.observe(c); });
})();

// Client-side category filter for the homepage "Featured services" grid —
// clicking a category tab filters instantly without a page reload.
(function () {
  var tabs = document.querySelectorAll('[data-cat-tab]');
  var items = document.querySelectorAll('[data-cat-item]');
  if (!tabs.length || !items.length) return;

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function (e) {
      e.preventDefault();
      var cat = tab.getAttribute('data-cat-tab');
      tabs.forEach(function (t) { t.classList.toggle('is-active', t === tab); });
      items.forEach(function (item) {
        var match = cat === 'all' || item.getAttribute('data-cat-item') === cat;
        item.classList.toggle('is-hidden', !match);
      });
    });
  });
})();

// FAQ accordion — click a question to expand its answer; only one open at a time.
(function () {
  var items = document.querySelectorAll('.faq-item');
  if (!items.length) return;

  items.forEach(function (item) {
    var btn = item.querySelector('.faq-q');
    var answer = item.querySelector('.faq-a');
    btn.setAttribute('aria-expanded', 'false');
    btn.addEventListener('click', function () {
      var isOpen = item.classList.contains('is-open');
      items.forEach(function (other) {
        other.classList.remove('is-open');
        other.querySelector('.faq-q').setAttribute('aria-expanded', 'false');
        other.querySelector('.faq-a').style.maxHeight = null;
      });
      if (!isOpen) {
        item.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });
})();
