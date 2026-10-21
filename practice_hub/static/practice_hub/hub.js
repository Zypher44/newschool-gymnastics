(() => {
  'use strict';
  function prepareClocks() {
    document.querySelectorAll('[data-ph-clock]').forEach(clock => {
      const serverNow = Date.parse(clock.dataset.serverNow);
      clock.phOffset = Number.isFinite(serverNow) ? serverNow - Date.now() : 0;
    });
    tick();
  }
  function tick() {
    document.querySelectorAll('[data-ph-clock]').forEach(clock => {
      const deadline = Date.parse(clock.dataset.deadline);
      const seconds = Number.isFinite(deadline) ? Math.max(0, Math.ceil((deadline - Date.now() - (clock.phOffset || 0)) / 1000)) : Number(clock.dataset.seconds || 0);
      clock.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
      if (seconds === 0 && clock.id === 'ph-clock' && Number.isFinite(deadline)) document.getElementById('ph-clock-status').textContent = 'Time reached';
    });
  }
  // Event choices update that athlete’s trackers and timer together; duration changes require a stopped timer.
  document.addEventListener('change', event => {
    if (!event.target.matches('.ph-child-timer [name="timer_event"], .ph-child-timer [name="timer_minutes"]')) return;
    const form = event.target.closest('.ph-child-timer');
    if (event.target.disabled || form.closest('[aria-busy="true"]')) return;
    const save = form.querySelector(event.target.name === 'timer_event' ? '[data-ph-timer-event-save]' : '[data-ph-timer-save]');
    if (save && form.reportValidity()) form.requestSubmit(save);
  });
  prepareClocks();
  const interval = setInterval(tick, 1000);
  document.addEventListener('live:updated', prepareClocks);
  window.addEventListener('pagehide', () => clearInterval(interval), {once:true});
  const demo = document.getElementById('ph-demo');
  if (demo) {
    let count = 0;
    const status = document.getElementById('ph-demo-status');
    demo.querySelectorAll('[data-demo-result]').forEach(button => button.addEventListener('click', () => {
      count += 1;
      status.textContent = `${button.dataset.demoResult} · ${count} demo tap${count === 1 ? '' : 's'}. No practice results saved.`;
    }));
    demo.querySelector('[data-demo-undo]').addEventListener('click', () => {
      count = Math.max(0, count - 1);
      status.textContent = `Demo undone · ${count} demo tap${count === 1 ? '' : 's'}. No practice results saved.`;
    });
  }
})();
