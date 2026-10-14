(() => {
  if (window.videoCoachingReviewBound) return;
  window.videoCoachingReviewBound = true;
  const player = () => document.querySelector('video.analysis-video, video.video-player, video.main-video');
  let pendingSeek = null;
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-coach-seek], [data-coach-speed], [data-coach-use-draft]');
    if (!button) return;
    const card = button.closest('.video-coach-brief');
    if (!card) return;
    const message = card.querySelector('[data-coach-message]');
    if (button.hasAttribute('data-coach-use-draft')) {
      const targetPath = new URL(card.dataset.coachReviewUrl, document.baseURI).pathname;
      const form = [...document.forms].find((item) => new URL(item.action, document.baseURI).pathname === targetPath);
      const notes = form && form.querySelector('textarea[name="coach_review_notes"]');
      const draft = card.querySelector('[data-coach-draft]').value;
      if (!notes) { message.textContent = 'Open the video detail page to add this draft to Coach Notes.'; return; }
      if (!notes.value.includes(draft)) notes.value = notes.value.trim() ? notes.value.trimEnd() + '\n\n' + draft : draft;
      notes.dispatchEvent(new Event('input', { bubbles: true }));
      notes.focus();
      message.textContent = 'Draft added. Edit it, choose a review decision, then click Save Coach Review.';
      return;
    }
    const video = player();
    if (!video) { message.textContent = 'Video player unavailable on this page.'; return; }
    if (button.hasAttribute('data-coach-speed')) {
      const rate = Number(button.dataset.coachSpeed);
      if (![0.5, 1].includes(rate)) return;
      video.playbackRate = rate;
      card.querySelectorAll('[data-coach-speed]').forEach((item) => item.setAttribute('aria-pressed', String(Number(item.dataset.coachSpeed) === rate)));
      message.textContent = 'Playback speed set to ' + (rate === 1 ? 'normal.' : 'half speed.');
      return;
    }
    const seconds = Number(button.dataset.coachSeek);
    if (!Number.isFinite(seconds) || seconds < 0) return;
    if (pendingSeek) pendingSeek.video.removeEventListener('loadedmetadata', pendingSeek.handler);
    const seek = () => {
      video.pause();
      video.currentTime = Number.isFinite(video.duration) ? Math.min(seconds, video.duration) : seconds;
      const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      video.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
      message.textContent = 'Video paused at the selected review point. Press play to watch the movement.';
      pendingSeek = null;
    };
    if (video.readyState >= 1) seek();
    else { pendingSeek = { video, handler: seek }; video.addEventListener('loadedmetadata', seek, { once: true }); video.load(); }
  });
})();
