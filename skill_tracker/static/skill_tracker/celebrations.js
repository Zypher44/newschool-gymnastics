/* Shared, local celebrations for accepted Skill and Routine Tracker results. */
(() => {
  'use strict';
  if (window.TrackerCelebration) return;
  const colors = ['#ffce32', '#33b98b', '#458eff', '#ed6faa', '#9876ef'];
  let canvas, context, particles = [], frame = 0, lastTime = 0;
  let audio, brassWave, master, banner, bannerTimer, lastSound = -Infinity;
  const reducedMotion = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clearConfetti() {
    if (frame) window.cancelAnimationFrame(frame);
    frame = 0; lastTime = 0; particles = [];
    if (canvas) { canvas.remove(); canvas = null; context = null; }
  }
  function draw(time) {
    const dt = Math.min((time - (lastTime || time)) / 1000, .04);
    lastTime = time;
    context.clearRect(0, 0, window.innerWidth, window.innerHeight);
    particles = particles.filter(p => p.life > 0);
    for (const p of particles) {
      p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt;
      p.vy += 440 * dt; p.angle += p.spin * dt;
      context.save(); context.translate(p.x, p.y); context.rotate(p.angle);
      context.globalAlpha = Math.min(1, Math.max(0, p.life / .45));
      context.fillStyle = p.color;
      context.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * .55);
      context.restore();
    }
    if (particles.length) frame = window.requestAnimationFrame(draw);
    else clearConfetti();
  }
  function confetti(kind, button) {
    if (reducedMotion() || !window.requestAnimationFrame) return;
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.setAttribute('aria-hidden', 'true');
      canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:10001;';
      context = canvas.getContext('2d');
      if (!context) { canvas = null; return; }
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = window.innerWidth * ratio; canvas.height = window.innerHeight * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      document.body.appendChild(canvas);
    }
    const wow = kind === 'wow', count = wow ? 240 : 55;
    const rect = button && button.getBoundingClientRect();
    const localX = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
    const localY = rect ? rect.top + rect.height / 2 : window.innerHeight * .6;
    for (let i = 0; i < count; i++) {
      const left = i % 2 === 0;
      particles.push({
        x: wow ? window.innerWidth * (left ? .15 : .85) : localX,
        y: wow ? window.innerHeight * .7 : localY,
        vx: wow ? (left ? 1 : -1) * (70 + Math.random() * 330) : (Math.random() - .5) * 300,
        vy: -(wow ? 370 + Math.random() * 330 : 180 + Math.random() * 220),
        life: wow ? 2.6 + Math.random() * .6 : 1.3 + Math.random() * .4,
        size: wow ? 6 + Math.random() * 6 : 4 + Math.random() * 5,
        angle: Math.random() * Math.PI, spin: (Math.random() - .5) * 12,
        color: colors[i % colors.length],
      });
    }
    particles = particles.slice(-480);
    if (!frame) frame = window.requestAnimationFrame(draw);
  }
  function sound(kind) {
    const now = performance.now();
    // Rate limiting keeps quick taps from building up loud overlapping audio.
    if (now - lastSound < (kind === 'wow' ? 550 : 280)) return;
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return;
    if (!audio || audio.state === 'closed') {
      audio = new Audio();
      master = audio.createGain(); master.gain.value = .16;
      const compressor = audio.createDynamicsCompressor();
      master.connect(compressor); compressor.connect(audio.destination);
      const real = new Float32Array(17), imaginary = new Float32Array(17);
      // Strong upper harmonics and a bright attack produce a trumpet-like brass tone.
      for (let h = 1; h < imaginary.length; h++) imaginary[h] = (h < 5 ? 1 : .65) / Math.pow(h, .8);
      brassWave = audio.createPeriodicWave(real, imaginary);
    }
    if (audio.state === 'suspended') {
      const resume = audio.resume(); if (resume && resume.catch) resume.catch(() => {});
    }
    lastSound = now;
    const notes = kind === 'wow'
      ? [[523.25, 0, .15], [659.25, .16, .15], [783.99, .32, .22], [1046.5, .57, .67], [659.25, .57, .67], [783.99, .57, .67]]
      : [[783.99, 0, .1], [1046.5, .12, .25]];
    for (const [frequency, delay, duration] of notes) {
      const start = audio.currentTime + delay, end = start + duration;
      const osc = audio.createOscillator(), envelope = audio.createGain(), filter = audio.createBiquadFilter();
      osc.setPeriodicWave(brassWave);
      osc.frequency.setValueAtTime(frequency * .985, start);
      osc.frequency.exponentialRampToValueAtTime(frequency, start + .035);
      filter.type = 'lowpass'; filter.Q.value = .6;
      filter.frequency.setValueAtTime(1800, start);
      filter.frequency.linearRampToValueAtTime(6500, start + .04);
      filter.frequency.linearRampToValueAtTime(2700, end);
      const volume = kind === 'wow' ? .38 : .22;
      envelope.gain.setValueAtTime(.0001, start);
      envelope.gain.exponentialRampToValueAtTime(volume, start + .025);
      envelope.gain.exponentialRampToValueAtTime(volume * .7, end - .045);
      envelope.gain.exponentialRampToValueAtTime(.0001, end);
      osc.connect(filter); filter.connect(envelope); envelope.connect(master);
      osc.onended = () => { osc.disconnect(); filter.disconnect(); envelope.disconnect(); };
      osc.start(start); osc.stop(end + .015);
    }
  }
  function notification(kind) {
    if (!banner) {
      banner = document.createElement('div'); banner.setAttribute('aria-hidden', 'true');
      document.body.appendChild(banner);
    }
    const wow = kind === 'wow';
    banner.textContent = wow ? 'WOW!' : 'Nice hit!';
    banner.style.cssText = `position:fixed;top:max(18px,env(safe-area-inset-top));left:50%;transform:translateX(-50%);z-index:10002;pointer-events:none;padding:12px 24px;border-radius:18px;background:${wow ? '#ffce32' : '#d8f6e6'};color:#163047;font:bold ${wow ? '36' : '24'}px/1.2 system-ui,sans-serif;box-shadow:0 6px 25px #16304726;white-space:nowrap;`;
    window.clearTimeout(bannerTimer);
    bannerTimer = window.setTimeout(() => { banner.remove(); banner = null; }, wow ? 1600 : 1000);
  }
  window.TrackerCelebration = {
    play(kind, button) {
      if (kind !== 'wow' && kind !== 'hit') return;
      // Each effect is independent: a blocked sound or canvas never interrupts scoring.
      try { confetti(kind, button); } catch (_) { clearConfetti(); }
      try { sound(kind); } catch (_) { /* Device may not support audio. */ }
      try { notification(kind); } catch (_) { /* Existing result status remains available. */ }
    },
  };
  window.addEventListener('resize', clearConfetti);
  document.addEventListener('visibilitychange', () => { if (document.hidden) clearConfetti(); });
})();
