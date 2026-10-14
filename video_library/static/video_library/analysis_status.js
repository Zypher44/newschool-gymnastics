(() => {
  document.querySelectorAll('[data-video-analysis-panel]').forEach(panel => {
    if (panel.dataset.bound || panel.dataset.finished === 'true') return;
    panel.dataset.bound = 'true';
    const step = panel.querySelector('[data-analysis-step]');
    let stopped = false;
    async function poll() {
      if (stopped) return;
      let delay = 3000;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch(panel.dataset.statusUrl, {
          credentials: 'same-origin', headers: {'Accept': 'application/json'}, signal: controller.signal
        });
        if (response.status === 403 || response.status === 404 || response.redirected) {
          stopped = true;
          step.textContent = 'Sign in again or reopen the video to check its status.';
          return;
        }
        if (!response.ok) throw new Error('Status unavailable');
        const data = await response.json();
        const percentage = Math.max(0, Math.min(100, Number(data.progress_percentage) || 0));
        panel.querySelector('[data-analysis-status]').textContent = data.status_display;
        panel.querySelector('[data-analysis-percent]').textContent = percentage + '%';
        const bar = panel.querySelector('[data-analysis-progress]');
        bar.style.width = percentage + '%';
        bar.setAttribute('aria-valuenow', String(percentage));
        step.textContent = data.current_step;
        if (data.is_finished) {
          stopped = true;
          window.location.reload();
        }
      } catch (_) {
        step.textContent = 'Status temporarily unavailable. Checking again shortly.';
        delay = 10000;
      } finally {
        clearTimeout(timeout);
        if (!stopped) setTimeout(poll, delay);
      }
    }
    setTimeout(poll, 1000);
  });
})();
