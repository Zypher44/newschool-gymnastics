(() => {
  'use strict';
  const form = document.getElementById('passport-award-form');
  const data = document.getElementById('passport-card-data');
  if (form && data) {
    let cards; try {cards = JSON.parse(data.textContent);} catch (_) {cards = [];}
    const select = form.querySelector('[name=slot]');
    const sync = () => {
      const card = cards.find(c => c.slot === select.value);
      if (!card) return;
      form.querySelector('[name=version]').value = card.version;
      const definitionVersion = form.querySelector('[name=definition_version]');
      if (definitionVersion) definitionVersion.value = card.definition_version || 0;
      document.getElementById('passport-rule').textContent = card.rule + (card.earned ? ' This stamp is already collected.' : card.ready ? ' Ready for your approval.' : ' The saved progress has not reached this target yet.');
      document.getElementById('passport-award-submit').disabled = card.earned || !card.ready;
    };
    select.addEventListener('change', sync);
    document.querySelectorAll('[data-passport-choice]').forEach(link => link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); select.value = link.dataset.passportChoice; sync();
      form.scrollIntoView({block:'center', behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
      select.focus({preventScroll:true});
    }));
    sync();
  }
  const newData = document.getElementById('passport-celebrations');
  const scope = document.getElementById('passport-scope');
  if (!newData || !scope) return;
  let stamps; try {stamps = JSON.parse(newData.textContent);} catch (_) {return;}
  const key = 'practice-passport-seen:' + scope.dataset.scope;
  let seen; try {const saved = JSON.parse(localStorage.getItem(key) || '[]'); seen = new Set(Array.isArray(saved) ? saved : []);} catch (_) {seen = new Set();}
  const waiting = stamps.filter(s => !seen.has(s.id));
  const panel = document.getElementById('passport-new'), button = document.getElementById('passport-open-stamp'), status = document.getElementById('passport-new-message');
  const update = () => {
    panel.hidden = !waiting.length;
    if (waiting.length) {status.textContent = `Your coach awarded ${waiting.length} new stamp${waiting.length === 1 ? '' : 's'}!`; button.textContent = 'Open my new stamp';}
  };
  button.addEventListener('click', () => {
    const stamp = waiting.shift(); if (!stamp) return;
    const card = Array.from(document.querySelectorAll('[data-passport-slot]')).find(c => c.dataset.passportSlot === stamp.slot);
    document.querySelectorAll('.passport-highlight').forEach(c => c.classList.remove('passport-highlight'));
    card?.classList.add('passport-highlight');
    card?.scrollIntoView({block:'center', behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    seen.add(stamp.id); try {localStorage.setItem(key, JSON.stringify([...seen]));} catch (_) {}
    window.TrackerCelebration?.play('wow', button);
    status.textContent = 'You earned ' + stamp.title + '!';
    button.textContent = waiting.length ? 'Open next stamp (' + waiting.length + ')' : 'All new stamps opened';
    button.disabled = !waiting.length;
  });
  update();
})();
