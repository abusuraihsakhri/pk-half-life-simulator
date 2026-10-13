import { simulatePk } from './pk-model.mjs';

const form = document.getElementById('pk-form');
const error = document.getElementById('error');
const csvButton = document.getElementById('csv');
const chart = document.getElementById('chart');
let latest = null;

function read(id, optional = false) {
  const raw = document.getElementById(id).value.trim();
  if (optional && raw === '') return null;
  if (!raw) throw new Error(id + ' is required.');
  const value = Number(raw);
  if (!Number.isFinite(value)) throw new Error(id + ' must be finite.');
  return value;
}
function fmt(x) {
  return x === null || !Number.isFinite(x) ? '—' : Number(x.toPrecision(5)).toLocaleString('en-US', { maximumFractionDigits: 5 });
}
function svg(name, attrs, text) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [key, value] of Object.entries(attrs)) e.setAttribute(key, String(value));
  if (text !== undefined) e.textContent = text;
  return e;
}
function plot(points, duration) {
  chart.replaceChildren();
  const x0 = 66, x1 = 875, y0 = 270, y1 = 20;
  const max = Math.max(1e-10, ...points.map(p => p.concentration)) * 1.1;
  const x = t => x0 + t / duration * (x1 - x0);
  const y = c => y0 - c / max * (y0 - y1);
  for (let i = 0; i <= 4; i++) {
    const yy = y0 - i / 4 * (y0 - y1);
    chart.append(svg('line', {x1:x0,y1:yy,x2:x1,y2:yy,class:'plot-grid'}));
    chart.append(svg('text', {x:x0-12,y:yy+4,'text-anchor':'end',class:'plot-label'},fmt(max*i/4)));
    chart.append(svg('text', {x:x0+(x1-x0)*i/4,y:y0+22,'text-anchor':'middle',class:'plot-label'},fmt(duration*i/4)));
  }
  const d = points.map((p,i) => (i ? 'L' : 'M') + x(p.time).toFixed(3) + ',' + y(p.concentration).toFixed(3)).join(' ');
  chart.append(svg('path',{d,class:'plot-curve'}));
  chart.append(svg('text',{x:470,y:314,'text-anchor':'middle',class:'plot-label'},'Time (hours)'));
  chart.append(svg('text',{transform:'translate(15,148) rotate(-90)','text-anchor':'middle',class:'plot-label'},'Concentration (mg/L)'));
}
function calculate(event) {
  if (event) event.preventDefault();
  try {
    const dose = read('dose'), volume = read('volume');
    const halfLife = read('halfLife'), interval = read('interval', true), horizon = read('horizon');
    latest = simulatePk({dose,volume,halfLife,interval,horizon});
    for (const key of ['c0','clearance','k','aucInf','accumulation','horizonAuc','peak','trough']) {
      document.getElementById(key).textContent = fmt(latest.summary[key]);
    }
    document.getElementById('caption').textContent = latest.summary.doses + ' dose(s) through ' + fmt(horizon) + ' hours · final concentration ' + fmt(latest.summary.endConcentration) + ' mg/L';
    plot(latest.points,horizon);
    error.hidden = true;
    csvButton.disabled = false;
  } catch (exc) {
    latest = null;
    csvButton.disabled = true;
    error.textContent = exc.message || 'Please check the inputs.';
    error.hidden = false;
  }
}
function exportCsv() {
  if (!latest) return;
  const content = 'time_h,concentration_mg_l,auc_mg_h_l\n' + latest.points.map(p => [p.time,p.concentration,p.auc].join(',')).join('\n') + '\n';
  const url = URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'pk-half-life-simulation.csv';
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
form.addEventListener('submit',calculate);
for (const id of ['dose','volume','halfLife','interval','horizon']) {
  document.getElementById(id).addEventListener('input',() => { csvButton.disabled = true; });
}
csvButton.addEventListener('click',exportCsv);
calculate();
