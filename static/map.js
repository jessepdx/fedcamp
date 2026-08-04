/*
 * map.js — Campdex map homepage.
 *
 * Extracted verbatim from the inline <script> in templates/map.html so that
 * markup and behaviour live in separate files. No behavioural change in this
 * commit; the code below is byte-identical to what was inline.
 */
(function() {
    try {

    var map = L.map('state-map', {
        center: [44.0, -120.5],
        zoom: 7,
        minZoom: 3,
        maxZoom: 18,
        preferCanvas: true,
        zoomControl: false     // re-added bottom-left, away from the chip row
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        // The page footer is hidden on this layout, so the RIDB credit and
        // the "verify before traveling" caveat live here instead.
        attribution: '&copy; OpenStreetMap | Data: <a href="https://ridb.recreation.gov" target="_blank" rel="noopener">RIDB</a> — verify before traveling',
        maxZoom: 18
    }).addTo(map);

    // Result count pill (bottom-left, stacked above the zoom control so the
    // top corners stay clear for the filter chips).
    var status = L.control({position: 'bottomleft'});
    status.onAdd = function() {
        this._div = L.DomUtil.create('div', 'map-status');
        this._div.setAttribute('aria-live', 'polite');
        this._div.innerHTML = 'Loading…';
        return this._div;
    };
    status.update = function(html) {
        this._div.innerHTML = html;
    };
    status.addTo(map);

    L.control.zoom({position: 'bottomleft'}).addTo(map);

    // Legend control (bottom-right)
    var legend = L.control({position: 'bottomright'});
    legend.onAdd = function() {
        var div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML =
            '<i style="background:#2d7d46"></i>Developed<br>' +
            '<i style="background:#8a6d10"></i>Primitive<br>' +
            '<i style="background:#6c5ce7"></i>Dispersed<br>' +
            '<i style="background:#a85a1e"></i>Seasonal<br>' +
            '<i style="background:#c0392b"></i>Closed';
        return div;
    };
    legend.addTo(map);

    // ---------------------------------------------------------------
    // Filters (bar below map)
    // ---------------------------------------------------------------
    var filters = {
        camping_types: [],
        agencies: [],
        road_access: [],
        styles: [],
        hookups: [],
        min_rv_length: null
    };

    function readFiltersAndReload() {
        filters.camping_types = [];
        document.querySelectorAll('#mf-type-group .mf-toggle.active').forEach(function(b) {
            filters.camping_types.push(b.dataset.key);
        });
        filters.agencies = [];
        document.querySelectorAll('#mf-agency input:checked').forEach(function(c) { filters.agencies.push(c.value); });
        filters.road_access = [];
        document.querySelectorAll('#mf-road input:checked').forEach(function(c) { filters.road_access.push(c.value); });
        filters.styles = [];
        document.querySelectorAll('#mf-style input:checked').forEach(function(c) { filters.styles.push(c.value); });
        filters.hookups = [];
        document.querySelectorAll('#mf-hookups input:checked').forEach(function(c) { filters.hookups.push(c.value); });
        var val = parseInt(document.getElementById('mf-rv-input').value, 10);
        filters.min_rv_length = val > 0 ? val : null;
        loadPins();
    }

    // Camping type toggles
    document.querySelectorAll('#mf-type-group .mf-toggle').forEach(function(btn) {
        btn.onclick = function() {
            var on = btn.classList.toggle('active');
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
            readFiltersAndReload();
        };
    });

    // Checkbox groups
    ['mf-agency', 'mf-road', 'mf-style', 'mf-hookups'].forEach(function(id) {
        document.querySelectorAll('#' + id + ' input').forEach(function(cb) {
            cb.onchange = function() { readFiltersAndReload(); };
        });
    });

    // RV length (debounced)
    var rvDebounce;
    document.getElementById('mf-rv-input').oninput = function() {
        clearTimeout(rvDebounce);
        rvDebounce = setTimeout(readFiltersAndReload, 500);
    };

    // Reset. (The checkbox selector previously pointed at .map-filters-bar,
    // a class that no longer exists in this markup, so reset silently left
    // every checkbox checked.)
    document.getElementById('mf-reset-btn').onclick = function() {
        document.querySelectorAll('#mf-type-group .mf-toggle.active').forEach(function(b) {
            b.classList.remove('active');
            b.setAttribute('aria-pressed', 'false');
        });
        document.querySelectorAll('#map-filter-panel input[type=checkbox]').forEach(function(cb) { cb.checked = false; });
        document.getElementById('mf-rv-input').value = '';
        readFiltersAndReload();
    };

    // ---------------------------------------------------------------
    // Pin layer and loading
    // ---------------------------------------------------------------
    // Cluster markers instead of dropping every pin into the DOM. A
    // zoomed-out view returns 6,000+ campgrounds, and that many divIcon
    // markers is what made the map crawl on phones (preferCanvas does
    // nothing for divIcons). Clusters break apart as you zoom, and below
    // disableClusteringAtZoom every pin is drawn individually.
    var pinLayer = L.markerClusterGroup({
        chunkedLoading: true,          // yield to the UI while adding markers
        showCoverageOnHover: false,    // the convex hull is noise at this density
        maxClusterRadius: 55,
        disableClusteringAtZoom: 11,
        spiderfyOnMaxZoom: true,
        iconCreateFunction: function(cluster) {
            var n = cluster.getChildCount();
            var size = n < 10 ? 'sm' : (n < 100 ? 'md' : 'lg');
            return L.divIcon({
                html: '<div><span>' + n + '</span></div>',
                className: 'campdex-cluster campdex-cluster-' + size,
                iconSize: L.point(40, 40)
            });
        }
    }).addTo(map);
    var loadDebounce;
    var currentRequest = null;

    function campingColor(type, seasonal) {
        if (seasonal === 'PERMANENTLY_CLOSED' || seasonal === 'TEMPORARILY_CLOSED')
            return '#c0392b';
        if (seasonal === 'WINTER_CLOSURE' || seasonal === 'SEASONAL_CLOSURE')
            return '#a85a1e';
        var colors = { 'DEVELOPED': '#2d7d46', 'PRIMITIVE': '#8a6d10', 'DISPERSED': '#6c5ce7' };
        return colors[type] || '#5f6e6f';
    }

    var pinIconCache = {};
    function pinIcon(color) {
        if (!pinIconCache[color]) {
            var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="20" height="30">'
                + '<path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24C24 5.4 18.6 0 12 0z" fill="' + color + '" stroke="#fff" stroke-width="2"/>'
                + '<circle cx="12" cy="12" r="4" fill="#fff" fill-opacity="0.9"/></svg>';
            pinIconCache[color] = L.divIcon({
                html: svg,
                className: '',
                iconSize: [20, 30],
                iconAnchor: [10, 30],
                popupAnchor: [0, -30]
            });
        }
        return pinIconCache[color];
    }

    function escapeHtml(str) {
        if (!str) return '';
        var d = document.createElement('div');
        d.appendChild(document.createTextNode(str));
        return d.innerHTML;
    }

    function buildQuery() {
        var b = map.getBounds();
        var params = 'south=' + b.getSouth().toFixed(4)
            + '&north=' + b.getNorth().toFixed(4)
            + '&west=' + b.getWest().toFixed(4)
            + '&east=' + b.getEast().toFixed(4);
        filters.camping_types.forEach(function(v) { params += '&camping_type=' + v; });
        filters.agencies.forEach(function(v) { params += '&agency=' + v; });
        filters.road_access.forEach(function(v) { params += '&road_access=' + v; });
        filters.styles.forEach(function(v) { params += '&style=' + v; });
        filters.hookups.forEach(function(v) { params += '&hookup=' + v; });
        if (filters.min_rv_length) params += '&min_rv_length=' + filters.min_rv_length;
        return params;
    }

    function loadPins() {
        if (currentRequest) { currentRequest.abort(); currentRequest = null; }

        var query = buildQuery();
        status.update('Loading…');

        var controller = new AbortController();
        currentRequest = controller;

        fetch('/api/pins?' + query, {signal: controller.signal})
            .then(function(r) { return r.json(); })
            .then(function(pins) {
                currentRequest = null;
                pinLayer.clearLayers();
                var markers = [];
                pins.forEach(function(p) {
                    var marker = L.marker([p.latitude, p.longitude], {
                        icon: pinIcon(campingColor(p.camping_type, p.seasonal_status)),
                        bubblingMouseEvents: false
                    });
                    markers.push(marker);

                    var tgt = ('ontouchstart' in window) ? '' : ' target="_blank" rel="noopener"';
                    var html = '<strong><a href="/facility/' + p.facility_id + '"' + tgt + '>'
                        + escapeHtml(p.facility_name) + '</a></strong>';
                    if (p.total_campsites) html += '<br>' + p.total_campsites + ' sites';
                    if (p.org_abbrev) html += ' &middot; ' + p.org_abbrev;
                    if (p.max_rv_length) html += '<br>Max RV: ' + p.max_rv_length + ' ft';
                    if (p.seasonal_status === 'PERMANENTLY_CLOSED') html += '<br><em>Permanently Closed</em>';
                    else if (p.seasonal_status === 'TEMPORARILY_CLOSED') html += '<br><em>Temporarily Closed</em>';
                    else if (p.seasonal_status === 'WINTER_CLOSURE') html += '<br><em>Winter Closure</em>';
                    else if (p.seasonal_status === 'SEASONAL_CLOSURE') html += '<br><em>Seasonal</em>';
                    // Auto-pan clear of the floating chip row (top) and the
                    // status pill / attribution (bottom), which the default
                    // padding knows nothing about.
                    marker.bindPopup(html, {
                        autoPanPaddingTopLeft: L.point(16, 88),
                        autoPanPaddingBottomRight: L.point(16, 48)
                    });
                    marker.bindTooltip(escapeHtml(p.facility_name));
                });
                // One bulk add is far cheaper than addTo() per marker.
                pinLayer.addLayers(markers);
                var n = pins.length.toLocaleString();
                status.update('<strong>' + n + '</strong> campground' + (pins.length === 1 ? '' : 's') + ' in view');
                document.getElementById('mf-apply-n').textContent = n;
            })
            .catch(function(err) {
                if (err.name !== 'AbortError') {
                    currentRequest = null;
                    status.update('Couldn’t load campgrounds — try moving the map');
                }
            });
    }

    // ---------------------------------------------------------------
    // Filter panel (the map fills the viewport, so filters float over it)
    // ---------------------------------------------------------------
    var filtersBtn = document.getElementById('map-filters-btn');
    var filterPanel = document.getElementById('map-filter-panel');
    var filterCount = document.getElementById('map-filter-count');

    function setPanelOpen(open) {
        if (open) { filterPanel.removeAttribute('hidden'); }
        else { filterPanel.setAttribute('hidden', ''); }
        filtersBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    filtersBtn.addEventListener('click', function() {
        setPanelOpen(filterPanel.hasAttribute('hidden'));
    });
    // Mobile sheet's "Show N campgrounds" button: filters apply live, so
    // this just dismisses the sheet.
    document.getElementById('mf-apply-btn').addEventListener('click', function() {
        setPanelOpen(false);
    });

    // Keep map gestures from firing while interacting with the overlay.
    L.DomEvent.disableClickPropagation(document.querySelector('.map-overlay'));
    L.DomEvent.disableScrollPropagation(filterPanel);

    // A count on the button so active filters are visible while the panel
    // is closed -- otherwise a filtered map looks identical to an unfiltered
    // one and the result count seems wrong.
    function updateFilterCount() {
        var n = filterPanel.querySelectorAll('input[type="checkbox"]:checked').length;
        if (document.getElementById('mf-rv-input').value) n++;
        if (n) { filterCount.textContent = n; filterCount.removeAttribute('hidden'); }
        else { filterCount.setAttribute('hidden', ''); }
    }
    filterPanel.addEventListener('change', updateFilterCount);
    document.getElementById('mf-reset-btn').addEventListener('click', function() {
        setTimeout(updateFilterCount, 0);
    });
    updateFilterCount();

    // Fade the right edge of the chip row when it can scroll, so cut-off
    // chips read as "more here" rather than a rendering bug.
    var chiprow = document.querySelector('.map-chiprow');
    function updateChipFade() {
        chiprow.classList.toggle('is-scrollable',
            chiprow.scrollWidth - chiprow.scrollLeft > chiprow.clientWidth + 2);
    }
    chiprow.addEventListener('scroll', updateChipFade);
    window.addEventListener('resize', updateChipFade);
    updateChipFade();

    // The map is sized by flexbox now, so tell Leaflet once layout settles.
    window.addEventListener('resize', function() { map.invalidateSize(); });

    // Debounced load on map move. If a popup is open, hold the reload:
    // opening a popup near the screen edge auto-pans the map, and the
    // moveend reload would clearLayers() and destroy the popup the user
    // just opened. Reload once the popup closes instead.
    var reloadHeldByPopup = false;
    function popupIsOpen() {
        return !!(map._popup && map._popup.isOpen());
    }
    // The popup check runs inside the timeout, not just when scheduling:
    // a popup opened during the 300ms debounce window must also hold the
    // reload, or it gets destroyed the moment the timer fires.
    function scheduleLoad() {
        clearTimeout(loadDebounce);
        loadDebounce = setTimeout(function() {
            if (popupIsOpen()) { reloadHeldByPopup = true; return; }
            loadPins();
        }, 300);
    }
    map.on('moveend', function() {
        clearTimeout(loadDebounce);
        if (popupIsOpen()) {
            reloadHeldByPopup = true;
            return;
        }
        scheduleLoad();
    });
    map.on('popupclose', function() {
        L.DomUtil.removeClass(map.getContainer(), 'popup-open');
        if (reloadHeldByPopup) {
            reloadHeldByPopup = false;
            scheduleLoad();
        }
    });
    // Leaflet stacks controls above the popup pane, so a popup near a
    // corner slides underneath the legend / count pill. Fade them out
    // while a popup is open instead of letting them cover it.
    map.on('popupopen', function() {
        L.DomUtil.addClass(map.getContainer(), 'popup-open');
    });

    // ---------------------------------------------------------------
    // Initial load — default to Oregon region (no auto-geolocation prompt).
    // Wait for layout to settle before reading bounds: loading immediately
    // fired a request with zero-area bounds, then two more on resize.
    // ---------------------------------------------------------------
    setTimeout(function() {
        map.invalidateSize();
        clearTimeout(loadDebounce);   // drop any moveend queued by the resize
        loadPins();
        updateChipFade();
    }, 0);

    } catch(e) {
        document.getElementById('state-map').innerHTML =
            '<p style="padding:2rem;text-align:center;">Map failed to load. <a href="/search-form">Use the search form instead</a>.'
            + '<br><small style="color:#999;">' + e.message + '</small></p>';
    }
})();
