(() => {
const form = document.getElementById('daily-checkin'); if (!form) return;
const value = name => new FormData(form).get(name);
function update() {
 const body = value('body_feeling');
 const visible = {area:['sore','pain'].includes(body), told:['pain','sick'].includes(body),
 worry:value('practice_feeling')==='nervous', help:!!value('help_skill') || (!!value('help_event') && value('help_event')!=='none')};
 form.querySelectorAll('[data-followup]').forEach(panel => {
  panel.hidden = !visible[panel.dataset.followup];
  panel.querySelectorAll('input,select').forEach(input => { input.disabled = panel.hidden; });
 });
}
form.addEventListener('change',update);update();
})();
