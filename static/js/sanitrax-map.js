/* Carte Leaflet d'incidence régionale — partagée par la vue d'ensemble et la carte. */
function initCarteSN(containerId, dataId) {
  if (typeof L === 'undefined') return;
  var el = document.getElementById(containerId);
  var src = document.getElementById(dataId);
  if (!el || !src) return;
  var data = JSON.parse(src.textContent);

  var map = L.map(el, { zoomControl: true, attributionControl: false, scrollWheelZoom: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    { maxZoom: 12, minZoom: 5, subdomains: 'abcd' }).addTo(map);

  var SN = [[12.25, -17.55], [16.72, -11.34]];
  map.fitBounds(SN, { padding: [8, 8] });

  var maxC = Math.max.apply(null, data.map(function (d) { return d.cases; })) || 1;
  data.forEach(function (d) {
    var diam = Math.round(2 * (8 + Math.sqrt(d.cases / maxC) * 20));
    var ring = d.sel ? '#0E2C49' : '#fff';
    var bw = d.sel ? 3 : 1.5;
    var crit = d.niveau >= 2;
    var html = '<div style="position:relative;width:' + diam + 'px;height:' + diam + 'px">'
      + (crit ? '<span style="position:absolute;inset:0;border-radius:50%;background:' + d.fill + ';opacity:.35;animation:mkPulse 1.8s ease-out infinite"></span>' : '')
      + '<span style="position:absolute;inset:0;border-radius:50%;background:' + d.fill + ';border:' + bw + 'px solid ' + ring + ';box-shadow:0 2px 6px rgba(16,44,73,.35)"></span></div>';
    var icon = L.divIcon({ html: html, className: 'sn-div', iconSize: [diam, diam], iconAnchor: [diam / 2, diam / 2] });
    var mk = L.marker([d.lat, d.lng], { icon: icon, riseOnHover: true });
    mk.bindTooltip(d.nom + ' · ' + d.inc + ' /100k', { direction: 'top', offset: [0, -diam / 2] });
    mk.bindPopup('<b style="font-family:Spectral,serif;color:#0E2C49">' + d.nom + '</b><br>'
      + 'Cas <b>' + d.cases + '</b> · Inc. <b>' + d.inc + '</b> /100k<br>'
      + '<span style="font-weight:700;color:' + d.fill + '">' + d.label + '</span>');
    mk.addTo(map);
  });

  setTimeout(function () { map.invalidateSize(); }, 200);
  setTimeout(function () { map.invalidateSize(); map.fitBounds(SN, { padding: [8, 8] }); }, 500);
}
