/* Progressive enhancement: the entire research list remains readable without JS. */
document.querySelectorAll('.list-controls').forEach(controls => {
  const table = controls.nextElementSibling.querySelector('tbody');
  const rows = Array.from(table.rows), pageSize = 15;
  const pager = controls.parentElement.querySelector('.pagination');
  const empty = controls.parentElement.querySelector('.no-results');
  let page = 0;
  const draw = () => {
    const query = controls.querySelector('[data-search]').value.trim().toLocaleLowerCase();
    const kind = controls.querySelector('[data-kind-filter]').value;
    const action = controls.querySelector('[data-action-filter]').value;
    const sort = controls.querySelector('[data-sort]').value;
    const selected = rows.filter(r => (!query || r.textContent.toLocaleLowerCase().includes(query)) &&
      (!kind || r.dataset.kind === kind) && (!action || r.dataset.action === action));
    selected.sort((a,b) => sort === 'name' ? a.dataset.name.localeCompare(b.dataset.name, 'zh-Hant') : b.dataset.date.localeCompare(a.dataset.date));
    page = Math.max(0, Math.min(page, Math.ceil(selected.length/pageSize)-1));
    rows.forEach(r => {r.hidden = true;});
    selected.forEach((r,i) => {table.appendChild(r); r.hidden = i < page*pageSize || i >= (page+1)*pageSize;});
    empty.hidden = selected.length > 0;
    pager.querySelector('[data-count]').textContent = selected.length ? `${page*pageSize+1}–${Math.min((page+1)*pageSize,selected.length)} / ${selected.length}` : '0';
    pager.querySelector('[data-prev]').disabled = page === 0;
    pager.querySelector('[data-next]').disabled = (page+1)*pageSize >= selected.length;
  };
  controls.addEventListener('input', () => {page=0; draw();});
  pager.querySelector('[data-prev]').addEventListener('click', () => {page--;draw();});
  pager.querySelector('[data-next]').addEventListener('click', () => {page++;draw();});
  draw();
});
document.querySelectorAll('.chain-map').forEach(map => {
  const scope = map.parentElement;
  const reset = () => {
    map.querySelectorAll('[data-node]').forEach(n => n.setAttribute('aria-pressed','false'));
    scope.querySelectorAll('.chain-edges li').forEach(e => {e.hidden=false;});
  };
  map.querySelectorAll('[data-node]').forEach(node => node.addEventListener('click', () => {
    const wasSelected=node.getAttribute('aria-pressed')==='true'; reset();
    if(wasSelected) return;
    node.setAttribute('aria-pressed','true');
    scope.querySelectorAll('.chain-edges li').forEach(e => {e.hidden=e.dataset.from!==node.dataset.node && e.dataset.to!==node.dataset.node;});
  }));
  scope.querySelector('.chain-reset').addEventListener('click',reset);
});
