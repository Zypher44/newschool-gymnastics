(() => {
  function bind() {
    document.querySelectorAll('[data-keyframe-image]').forEach(image => {
      if (image.dataset.keyframeBound) return;
      image.dataset.keyframeBound = 'true';
      const unavailable = () => {
        const picture = image.closest('[data-keyframe-picture]');
        if (!picture) return;
        picture.querySelector('[data-keyframe-unavailable]').hidden = false;
        picture.querySelector('[data-keyframe-jump]').hidden = true;
        picture.querySelector('[data-keyframe-open]').hidden = true;
      };
      image.addEventListener('error', unavailable);
      if (image.complete && !image.naturalWidth) unavailable();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true });
  else bind();
})();
