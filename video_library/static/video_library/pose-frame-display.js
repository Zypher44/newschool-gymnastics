(() => {
  if (window.poseFrameDisplayBound) return;
  window.poseFrameDisplayBound = true;
  let pending = null;
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-pose-frame-seek]');
    if (!button) return;
    const card = button.closest('[data-pose-frame-picture]');
    const status = card.querySelector('[data-pose-frame-status]');
    const player = document.querySelector('video.analysis-video, video.video-player, video.main-video');
    const seconds = Number(button.dataset.poseFrameSeek);
    if (!player || !Number.isFinite(seconds) || seconds < 0) return;
    if (pending) pending.player.removeEventListener('loadedmetadata', pending.handler);
    player.pause();
    const seek = () => {
      player.currentTime = Number.isFinite(player.duration) ? Math.min(seconds, player.duration) : seconds;
      status.textContent = 'Video paused at this frame.';
      player.scrollIntoView({block:'center',behavior:'auto'});
      pending = null;
    };
    if (player.readyState >= 1) seek();
    else { pending = {player,handler:seek}; player.addEventListener('loadedmetadata',seek,{once:true}); player.load(); }
  });
  function images() {
    document.querySelectorAll('[data-pose-frame-image]').forEach(image => {
      if (image.dataset.poseFrameBound) return;
      image.dataset.poseFrameBound = 'true';
      const unavailable = () => {
        const card = image.closest('[data-pose-frame-picture]');
        card.querySelector('[data-pose-frame-seek]').hidden = true;
        card.querySelector('[data-pose-frame-status]').textContent = 'This saved image is unavailable. Run a fresh analysis if the source video is still available.';
      };
      image.addEventListener('error',unavailable);
      if (image.complete && !image.naturalWidth) unavailable();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',images,{once:true});
  else images();
})();
