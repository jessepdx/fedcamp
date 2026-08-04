/* Campdex — JavaScript */

/* Fix Leaflet default marker icon path for CDN usage */
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
});

function toggleFilterDrawer() {
    document.getElementById('filter-drawer').classList.toggle('open');
    document.getElementById('filter-overlay').classList.toggle('open');
}

var lbPhotos = [];
var lbIndex = 0;

function openLightbox(index) {
    lbIndex = index;
    showLightboxPhoto();
    document.getElementById('lightbox').classList.add('open');
}

function showLightboxPhoto() {
    var ph = lbPhotos[lbIndex];
    document.getElementById('lightbox-img').src = ph.url;
    document.getElementById('lightbox-caption').textContent = ph.caption;
    document.getElementById('lightbox-counter').textContent = (lbIndex + 1) + ' / ' + lbPhotos.length;
    document.getElementById('lb-prev').style.display = lbPhotos.length > 1 ? '' : 'none';
    document.getElementById('lb-next').style.display = lbPhotos.length > 1 ? '' : 'none';
}

function closeLightbox() {
    document.getElementById('lightbox').classList.remove('open');
    document.getElementById('lightbox-img').src = '';
}

function lbPrev(e) {
    e.stopPropagation();
    lbIndex = (lbIndex - 1 + lbPhotos.length) % lbPhotos.length;
    showLightboxPhoto();
}

function lbNext(e) {
    e.stopPropagation();
    lbIndex = (lbIndex + 1) % lbPhotos.length;
    showLightboxPhoto();
}

document.addEventListener('keydown', function(e) {
    var lb = document.getElementById('lightbox');
    if (!lb || !lb.classList.contains('open')) return;
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowLeft') lbPrev(e);
    else if (e.key === 'ArrowRight') lbNext(e);
});

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* Geolocation */
function geoLocate() {
    var btn = document.getElementById('geo-btn');
    var status = document.getElementById('geo-status');
    if (!navigator.geolocation) {
        status.textContent = 'Geolocation not supported by your browser';
        status.className = 'geo-status geo-error';
        return;
    }
    btn.setAttribute('aria-busy', 'true');
    btn.disabled = true;
    status.textContent = 'Locating...';
    status.className = 'geo-status';
    navigator.geolocation.getCurrentPosition(
        function(pos) {
            var lat = pos.coords.latitude;
            var lon = pos.coords.longitude;
            document.getElementById('geo-lat').value = lat.toFixed(4);
            document.getElementById('geo-lon').value = lon.toFixed(4);
            status.textContent = 'Searching near ' + lat.toFixed(2) + ', ' + lon.toFixed(2);
            status.className = 'geo-status geo-success';
            btn.textContent = 'Location Set';
            btn.setAttribute('aria-busy', 'false');
            btn.disabled = false;
        },
        function(err) {
            status.textContent = 'Location error: ' + err.message;
            status.className = 'geo-status geo-error';
            btn.setAttribute('aria-busy', 'false');
            btn.disabled = false;
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
}

function validateSearch() {
    var stateMode = document.querySelector('input[name="search_mode"][value="state"]');
    if (stateMode && stateMode.checked) {
        var state = document.querySelector('select[name="state"]');
        if (!state || !state.selectedOptions.length) {
            alert('Please select at least one state.');
            return false;
        }
        return true;
    }
    var lat = document.getElementById('geo-lat');
    var lon = document.getElementById('geo-lon');
    if (!lat || !lat.value || !lon || !lon.value) {
        alert('Please use the "Use My Location" button to set your location first.');
        return false;
    }
    return true;
}

/* ---------------------------------------------------------------
   Tri-state filter chips: neutral -> include -> exclude -> neutral.

   Each chip has a sibling hidden input. Neutral disables it (disabled
   inputs are not submitted); include submits `param`; exclude submits
   `not_param`. The server renders the initial state, so filters survive
   in the URL — only the cycling needs JS.
   --------------------------------------------------------------- */
document.addEventListener('click', function (e) {
    var btn = e.target.closest('.tri-chip');
    if (!btn || btn.classList.contains('tri-demo')) return;
    var input = btn.nextElementSibling;
    if (!input || !input.classList.contains('tri-input')) return;

    var state = (parseInt(btn.dataset.state, 10) + 1) % 3;
    var param = btn.dataset.param;
    btn.dataset.state = state;
    btn.setAttribute('aria-pressed', state === 1 ? 'true' : 'false');
    btn.title = state === 0 ? 'Click to require'
              : state === 1 ? 'Click to exclude'
              : 'Click to clear';
    var sr = btn.querySelector('.tri-sr');
    if (sr) sr.textContent = state === 1 ? '(required)'
                           : state === 2 ? '(excluded)' : '';
    input.disabled = (state === 0);
    input.name = (state === 2) ? 'not_' + param : param;
});
