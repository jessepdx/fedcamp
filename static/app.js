/* RV Camping Finder — JavaScript */

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

function initResultsMap(facilities) {
    var mapEl = document.getElementById('results-map');
    if (!mapEl || !facilities.length) return;

    var map = L.map('results-map');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    var bounds = [];

    facilities.forEach(function(f) {
        if (!f.latitude || !f.longitude) return;

        var lat = f.latitude;
        var lng = f.longitude;
        bounds.push([lat, lng]);

        var color = getCampingTypeColor(f.camping_type);

        var marker = L.circleMarker([lat, lng], {
            radius: 8,
            fillColor: color,
            color: '#fff',
            weight: 2,
            fillOpacity: 0.85
        }).addTo(map);

        var popup = '<strong><a href="/facility/' + f.facility_id + '">' +
                    escapeHtml(f.facility_name || 'Unnamed') + '</a></strong><br>';
        if (f.camping_type) {
            popup += f.camping_type.replace(/_/g, ' ') + '<br>';
        }
        if (f.total_campsites) {
            popup += f.total_campsites + ' sites';
        }
        if (f.distance_miles !== undefined && f.distance_miles !== null) {
            popup += ' &middot; ' + f.distance_miles.toFixed(1) + ' mi';
        }

        marker.bindPopup(popup);
    });

    if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [30, 30] });
    }
}

function getCampingTypeColor(type) {
    var colors = {
        'DEVELOPED': '#2d7d46',
        'PRIMITIVE': '#c49f17',
        'DISPERSED': '#6c5ce7'
    };
    return colors[type] || '#95a5a6';
}

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
        if (!state || !state.value) {
            alert('Please select a state.');
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
