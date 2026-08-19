(function () {
  const toggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-nav]');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = open ? '×' : '☰';
    });
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.textContent = '☰';
      }
    });
  }
  document.querySelectorAll('[data-year]').forEach(function (node) {
    node.textContent = String(new Date().getFullYear());
  });
}());
