(() => {
  document.querySelectorAll('[data-guide-dismiss]').forEach(form => {
    form.addEventListener('submit', async event => {
      if (!window.fetch) return;
      event.preventDefault();
      const banner = form.closest('.ph-banner');
      const button = form.querySelector('button');
      const error = banner.querySelector('[data-guide-error]');
      button.disabled = true;
      error.hidden = true;
      try {
        const response = await fetch(form.action, {
          method: 'POST', body: new FormData(form), credentials: 'same-origin',
          headers: {'Accept': 'application/json'}
        });
        if (!response.ok || !(await response.json()).dismissed) throw new Error('Dismiss failed');
        const main = document.querySelector('main');
        if (main) { main.setAttribute('tabindex', '-1'); main.focus({preventScroll: true}); }
        banner.remove();
      } catch (failure) {
        error.textContent = 'Could not hide the reminder. Please try again.';
        error.hidden = false;
        button.disabled = false;
      }
    });
  });
})();
