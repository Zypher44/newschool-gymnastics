(() => {
  function bind() {
    document.querySelectorAll('[data-skill-timing]').forEach(card => {
      if (card.dataset.timingBound) return;
      card.dataset.timingBound = 'true';
      const a = card.querySelector('[data-skill-start-a]'), b = card.querySelector('[data-skill-start-b]');
      if (!a || !b) return;
      const rows = [...card.querySelectorAll('[data-timing-row]')];
      const status = card.querySelector('[data-timing-status]');
      const basis = card.querySelector('[data-timing-basis]');
      const parse = value => value.trim() !== '' && Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : null;
      function clear(message) {
        rows.forEach(row => row.querySelectorAll('[data-elapsed-a], [data-elapsed-b], [data-elapsed-difference]').forEach(cell => cell.textContent = '—'));
        status.textContent = message;
      }
      function render(manual) {
        const starts = [parse(a.value), parse(b.value)];
        if (starts.includes(null)) { clear('Set both skill starts to compare elapsed time.'); return; }
        const players = [document.getElementById('compare-video-a'), document.getElementById('compare-video-b')];
        if (players.some((player, i) => player && Number.isFinite(player.duration) && starts[i] > player.duration)) {
          clear('A skill start is beyond the end of its video.'); return;
        }
        let previous = starts;
        const results = [];
        for (const row of rows) {
          const times = [parse(row.dataset.firstTime), parse(row.dataset.secondTime)];
          if (times.includes(null) || times.some((time, i) => time <= previous[i] || (players[i] && Number.isFinite(players[i].duration) && time > players[i].duration))) {
            clear('Skill starts must precede the sampled phases, and phase timestamps must stay in order.'); return;
          }
          results.push(times.map((time, i) => time - starts[i]));
          previous = times;
        }
        results.forEach(([first, second], i) => {
          const row = rows[i], delta = second - first;
          row.querySelector('[data-elapsed-a]').textContent = first.toFixed(2) + 's';
          row.querySelector('[data-elapsed-b]').textContent = second.toFixed(2) + 's';
          row.querySelector('[data-elapsed-difference]').textContent = Math.abs(delta) < .005 ? 'Same elapsed time' : 'B ' + Math.abs(delta).toFixed(2) + 's ' + (delta > 0 ? 'later' : 'earlier');
        });
        basis.textContent = manual ? 'Elapsed time from the coach-set skill starts in each clip. Phase frames are still estimates.' : 'Elapsed time from the estimated Entry frame in each clip. Confirm the actual starts below; estimated phases are review points.';
        status.textContent = manual ? 'Skill starts applied to this page. Review the timing against the videos.' : 'Estimated timing ready. Confirm the starts before using it as feedback.';
      }
      card.querySelector('[data-timing-apply]').addEventListener('click', () => render(true));
      card.querySelector('[data-timing-reset]').addEventListener('click', () => { a.value = a.dataset.estimatedStart; b.value = b.dataset.estimatedStart; render(false); });
      card.querySelector('[data-timing-current]').addEventListener('click', () => {
        const first = document.getElementById('compare-video-a'), second = document.getElementById('compare-video-b');
        if (!first || !second || first.readyState < 1 || second.readyState < 1) { status.textContent = 'Wait for both videos to load before selecting their current positions.'; return; }
        first.pause(); second.pause();
        a.value = first.currentTime.toFixed(2); b.value = second.currentTime.toFixed(2);
        render(true);
      });
      [a, b].forEach(input => input.addEventListener('input', () => clear('Start values changed. Click Apply Starts to update the timing table.')));
      render(false);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, {once:true});
  else bind();
})();
