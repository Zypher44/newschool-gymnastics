(() => {
  'use strict';
  let dirty = false;
  let leaving = false;
  function initialize() {
    const page = document.getElementById('pp-page');
    const form = document.getElementById('pp-plan');
    dirty = form?.dataset.draft === '1';
    leaving = false;
    if (!page || !form) return;
    const status = document.getElementById('pp-save-status');
    function changed(event) {
      if (event.target.matches('[data-pp-search], [data-pp-selected]')) return;
      dirty = true;
      if (status) status.textContent = 'Unsaved changes for this athlete.';
    }
    form.addEventListener('input', changed);
    form.addEventListener('change', changed);
    form.querySelectorAll('.pp-event').forEach(section => {
      const search = section.querySelector('[data-pp-search]');
      const selected = section.querySelector('[data-pp-selected]');
      const rows = Array.from(section.querySelectorAll('[data-pp-skill]'));
      function filter() {
        const query = search.value.trim().toLocaleLowerCase();
        let visible = 0;
        rows.forEach(row => {
          const check = row.querySelector('input[type=checkbox]');
          row.hidden = !row.dataset.name.toLocaleLowerCase().includes(query) || (selected.checked && !check.checked);
          if (!row.hidden) visible += 1;
          row.querySelector('input[type=number]').disabled = !check.checked;
        });
        section.querySelector('.pp-no-match').hidden = visible > 0 || rows.length === 0;
      }
      search.addEventListener('input', filter);
      selected.addEventListener('change', filter);
      rows.forEach(row => row.querySelector('input[type=checkbox]').addEventListener('change', filter));
      filter();
    });
    if (dirty && status) status.textContent = 'Draft or unsaved changes — save this athlete’s plan when ready.';
  }
  document.addEventListener('live:before-navigate', event => {
    if (!document.getElementById('pp-page') || event.detail.source?.id === 'pp-plan') return;
    if (dirty && !window.confirm('Leave this athlete’s unsaved plan changes?')) event.preventDefault();
  });
  document.addEventListener('live:updated', initialize);
  document.addEventListener('submit', event => {
    if (!window.fetch && event.target.id === 'pp-plan') leaving = true;
  });
  window.addEventListener('beforeunload', event => {
    if (dirty && !leaving) { event.preventDefault(); event.returnValue = ''; }
  });
  initialize();
})();
