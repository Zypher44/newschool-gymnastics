(() => {
  'use strict';
  const form = document.getElementById('athlete-journal-form');
  if (!form) return;
  const snapshot = () => JSON.stringify(Array.from(new FormData(form).entries()));
  const initial = snapshot();
  const unsavedDraft = form.dataset.unsaved === 'true';
  let submitting = false;
  form.addEventListener('submit', () => { submitting = true; });
  window.addEventListener('beforeunload', (event) => {
    if (!submitting && (unsavedDraft || snapshot() !== initial)) {
      event.preventDefault();
      event.returnValue = '';
    }
  });
})();
