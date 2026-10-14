(() => {
  function init() {
    const data = document.getElementById('ph-tracker-context');
    if (!data) return;
    let context;
    try { context = JSON.parse(data.textContent); } catch (_) { return; }
    const isSkill = context.kind === 'skill';
    const groupAttr = isSkill ? 'data-st-group' : 'data-routine-group';
    const athleteAttr = isSkill ? 'data-st-athlete' : 'data-routine-athlete';
    const group = [...document.querySelectorAll(`[${groupAttr}]`)].find(b => b.getAttribute(groupAttr) === context.group);
    const athlete = [...document.querySelectorAll(`[${athleteAttr}]`)].find(b => b.getAttribute(athleteAttr) === context.athlete);
    if (group) group.click();
    if (athlete && !athlete.hidden) athlete.click();
    const items = isSkill ? [...document.querySelectorAll('.st-card[data-event]')] :
      [...document.querySelectorAll('.event-box')].map(box => ({
        node: box.parentElement, event: box.querySelector('[data-track][data-event]')?.dataset.event
      }));
    const root = document.querySelector(isSkill ? '#st-tracker' : '.tracker-shell');
    let all = false;
    function filter() {
      if (root) root.classList.toggle('ph-focused-events', !all);
      items.forEach(item => {
        const node = isSkill ? item : item.node;
        const event = isSkill ? item.dataset.event : item.event;
        if (node) node.dataset.phEventHidden = String(!all && event && event !== context.event);
      });
    }
    const toggle = document.getElementById('ph-toggle-events');
    if (toggle) toggle.addEventListener('click', () => {
      all = !all;
      toggle.textContent = all ? 'Show selected event' : 'Show all events';
      toggle.setAttribute('aria-pressed', String(all));
      filter();
    });
    const back = document.getElementById('ph-back-practice');
    document.querySelectorAll(`[${athleteAttr}]`).forEach(button => button.addEventListener('click', () => {
      const id = button.getAttribute(athleteAttr);
      if (!back || !context.allowed_athletes.includes(id)) return;
      const url = new URL(context.back_url, window.location.origin);
      url.searchParams.set('athlete', id);
      back.href = url.pathname + url.search;
    }));
    filter();
  }
  // Both tracker scripts initialize before DOMContentLoaded, including deferred scripts.
  if (document.readyState === 'complete') init();
  else document.addEventListener('DOMContentLoaded', init, {once:true});
})();
