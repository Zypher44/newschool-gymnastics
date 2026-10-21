/* Free comparison controls: retain each clip's own movement timestamp. */
(() => {
  function bind() {
    const a = document.getElementById('compare-video-a');
    const b = document.getElementById('compare-video-b');
    if (!a || !b || a.dataset.freeComparisonBound) return;
    a.dataset.freeComparisonBound = 'true';
    const videos = [a, b];
    const status = document.getElementById('comparison-status');
    const restart = document.getElementById('restart-both');
    let anchors = [0, 0];
    let operation = 0;
    let linked = false;
    let offset = 0;
    let rate = 1;
    const waiters = new Set();
    const say = (message) => { if (status) status.textContent = message; };
    const finiteTime = (value) => typeof value === 'number' && Number.isFinite(value) && value >= 0;
    const current = (video) => finiteTime(video.currentTime) ? video.currentTime : 0;
    const duration = (video) => finiteTime(video.duration) ? video.duration : Infinity;
    const pause = () => { linked = false; videos.forEach(video => video.pause()); };
    function cancel() {
      operation += 1;
      for (const done of [...waiters]) done(false);
      pause();
      return operation;
    }
    function times() {
      ['time-a', 'time-b'].forEach((id, index) => {
        const label = document.getElementById(id);
        if (label) label.textContent = current(videos[index]).toFixed(2) + 's';
      });
    }
    function clearPhase() {
      document.querySelectorAll('.phase-sync-button').forEach(button => {
        button.classList.remove('active-phase');
        button.setAttribute('aria-pressed', 'false');
      });
    }
    function ready(video, ticket) {
      if (video.readyState >= 1) return Promise.resolve(ticket === operation);
      return new Promise(resolve => {
        const loaded = () => finish(ticket === operation);
        const failed = () => finish(false);
        const finish = (ok) => {
          video.removeEventListener('loadedmetadata', loaded);
          video.removeEventListener('error', failed);
          window.clearTimeout(timer);
          waiters.delete(finish);
          resolve(ok);
        };
        const timer = window.setTimeout(failed, 10000);
        waiters.add(finish);
        video.addEventListener('loadedmetadata', loaded, { once: true });
        video.addEventListener('error', failed, { once: true });
        video.load();
      });
    }
    async function bothReady(ticket) {
      const results = await Promise.all(videos.map(video => ready(video, ticket)));
      if (ticket !== operation) return false;
      if (!results.every(Boolean)) { say('A video is unavailable. Check playback, then try again.'); return false; }
      return true;
    }
    async function seekPair(targets, { remember = false, label = '' } = {}) {
      const ticket = cancel();
      if (!targets.every(finiteTime)) { say('No valid review timestamps are available for this point.'); return; }
      if (!await bothReady(ticket)) return;
      if (targets.some((value, index) => value > duration(videos[index]))) {
        say('A review timestamp is outside its video. Find the matching movement manually.'); return;
      }
      videos.forEach((video, index) => { video.currentTime = targets[index]; });
      if (remember) {
        anchors = [...targets];
        if (restart) restart.textContent = 'Restart at Review Point';
      }
      clearPhase();
      if (label) document.querySelectorAll('.phase-sync-button').forEach(button => {
        if (button.dataset.phase === label) {
          button.classList.add('active-phase');
          button.setAttribute('aria-pressed', 'true');
        }
      });
      times();
      say('Review point: A ' + targets[0].toFixed(2) + 's · B ' + targets[1].toFixed(2) + 's. Play Both keeps these separate positions.');
    }
    async function playBoth() {
      const ticket = cancel();
      if (!await bothReady(ticket)) return;
      if (videos.some(video => current(video) >= duration(video))) {
        say('A video is at its end. Restart at the review point before playing.'); return;
      }
      // Never move both videos to a shared clock time: phase positions differ.
      offset = current(b) - current(a);
      videos.forEach(video => { video.playbackRate = rate; });
      linked = true;
      try {
        await Promise.all(videos.map(video => video.play()));
        if (ticket !== operation) { if (!linked) pause(); return; }
        if (!linked || videos.some(video => video.paused)) return;
        say('Playing both from their own positions at ' + rate + '× speed.');
      } catch {
        if (ticket === operation) {
          pause();
          say('Both videos were paused because playback could not start. Try Play Both again.');
        }
      }
    }
    async function step(amount) {
      const ticket = cancel();
      if (!await bothReady(ticket)) return;
      const positions = videos.map(current);
      const lower = Math.max(...positions.map(value => -value));
      const upper = Math.min(...videos.map((video, index) => duration(video) - positions[index]));
      const delta = Math.max(lower, Math.min(amount, upper));
      videos.forEach((video, index) => { video.currentTime = positions[index] + delta; });
      times();
      say('Both videos moved ' + delta.toFixed(2) + 's. Their alignment is preserved.');
    }
    function on(id, action) { const node = document.getElementById(id); if (node) node.addEventListener('click', action); }
    on('play-both', playBoth);
    on('pause-both', () => { cancel(); say('Both videos paused.'); });
    on('restart-both', () => seekPair(anchors));
    on('back-both', () => step(-0.25));
    on('forward-both', () => step(0.25));
    on('align-current', async () => {
      const ticket = cancel();
      if (!await bothReady(ticket)) return;
      seekPair(videos.map(current), { remember: true });
    });
    on('clear-alignment', () => {
      anchors = [0, 0];
      if (restart) restart.textContent = 'Restart Both';
      seekPair([0, 0]);
    });
    document.querySelectorAll('[data-comparison-speed]').forEach(button => button.addEventListener('click', () => {
      const selected = Number(button.dataset.comparisonSpeed);
      if (![0.25, 0.5, 1].includes(selected)) return;
      rate = selected;
      videos.forEach(video => { video.playbackRate = rate; });
      document.querySelectorAll('[data-comparison-speed]').forEach(item => {
        const active = Number(item.dataset.comparisonSpeed) === rate;
        item.setAttribute('aria-pressed', String(active));
        item.classList.toggle('active', active);
      });
      say('Both videos set to ' + rate + '× speed.');
    }));
    document.querySelectorAll('.phase-sync-button').forEach(button => button.addEventListener('click', () => {
      const raw = [button.dataset.firstTime, button.dataset.secondTime];
      if (raw.some(value => typeof value !== 'string' || !value.trim())) {
        say('No paired timestamps are available. Align the movement manually.'); return;
      }
      seekPair(raw.map(Number), { remember: true, label: button.dataset.phase });
    }));
    videos.forEach(video => {
      video.addEventListener('timeupdate', times);
      video.addEventListener('seeked', times);
      video.addEventListener('ended', () => { cancel(); say('A video ended. Both videos paused.'); });
      video.addEventListener('error', () => { cancel(); say('A video is unavailable. Check playback, then try again.'); });
      // Native controls are independent, so coaches can locate each movement.
      video.addEventListener('pause', () => { if (linked) { pause(); say('Both videos paused.'); } });
      video.addEventListener('waiting', () => { if (linked) { pause(); say('A video is buffering. Press Play Both when it is ready.'); } });
    });
    a.addEventListener('timeupdate', () => {
      if (!linked || a.paused || b.paused || a.seeking || b.seeking) return;
      const target = current(a) + offset;
      if (target < 0 || target > duration(b)) { pause(); return; }
      if (Math.abs(current(b) - target) > 0.15) b.currentTime = target;
    });
    times();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true });
  else bind();
})();
