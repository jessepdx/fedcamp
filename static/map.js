/*
 * map.js — Campdex map homepage.
 *
 * Split view: the map drives a results panel (desktop: beside the map;
 * mobile: a full-screen layer toggled by #view-toggle-btn). Viewport and
 * filter state round-trips through the URL so a copied link reproduces
 * the view.
 */
(function() {
    try {

    // ---------------------------------------------------------------
    // URL state. Grammar on /:
    //   ?ll=<lat>,<lon>&z=<zoom>&ct=<csv>&ag=<csv>&st=<csv>
    //    &rd=<signed csv>&sn=<signed csv>&fr=<signed csv>&rs=1
    //    &rv=<int>&v=list
    // Signed CSV (tri-state groups): bare value = require, leading
    // "-" = exclude — e.g. rd=PAVED,-4WD_REQUIRED. rd/sn/fr map to the
    // road_access / seasonal_status / fire_status params.
    // Parsed BEFORE the map is created so the first pin fetch already
    // uses the restored viewport. Garbage values degrade silently to
    // defaults (CSV values that match no control are simply dropped;
    // unknown keys — e.g. the retired hk= — are ignored).
    // Written with replaceState ONLY — panning must not spam history.
    // ---------------------------------------------------------------

    // Tri-state URL key -> the chips' data-param (also the server param).
    var TRI_PARAMS = { rd: 'road_access', sn: 'seasonal_status', fr: 'fire_status' };

    // #mf-reservable may be the checkbox itself or a wrapper around it —
    // tolerate both, and its absence (markup may not carry it yet).
    function reservableInput() {
        var el = document.getElementById('mf-reservable');
        if (!el) return null;
        return el.tagName === 'INPUT' ? el : el.querySelector('input[type="checkbox"]');
    }

    var urlState = (function() {
        var out = { center: null, zoom: null, list: false };
        var q = new URLSearchParams(window.location.search);
        var ll = (q.get('ll') || '').split(',');
        if (ll.length === 2) {
            var lat = parseFloat(ll[0]), lon = parseFloat(ll[1]);
            if (isFinite(lat) && isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180)
                out.center = [lat, lon];
        }
        var z = parseInt(q.get('z'), 10);
        if (z >= 3 && z <= 18) out.zoom = z;
        out.list = q.get('v') === 'list';
        function csv(key) { return (q.get(key) || '').split(',').filter(Boolean); }
        // Restore control state through the DOM: setting the controls and
        // then reading them back means unknown values can't get into the
        // filter object.
        csv('ct').forEach(function(v) {
            var b = document.querySelector('#mf-type-group .mf-toggle[data-key="' + CSS.escape(v) + '"]');
            if (b) { b.classList.add('active'); b.setAttribute('aria-pressed', 'true'); }
        });
        [['ag', 'mf-agency'], ['st', 'mf-style']].forEach(function(pair) {
            csv(pair[0]).forEach(function(v) {
                var cb = document.querySelector('#' + pair[1] + ' input[value="' + CSS.escape(v) + '"]');
                if (cb) cb.checked = true;
            });
        });
        // Tri-state chips: find the chip and drive it through campdexTriSet
        // (defined in app.js, loaded first). A value with no matching chip
        // (rd=-BOGUS) simply finds nothing and is dropped.
        Object.keys(TRI_PARAMS).forEach(function(key) {
            csv(key).forEach(function(tok) {
                var state = tok.charAt(0) === '-' ? 2 : 1;
                var val = state === 2 ? tok.slice(1) : tok;
                if (!val) return;
                var btn = document.querySelector(
                    '#map-filter-panel .tri-chip[data-param="' + TRI_PARAMS[key] + '"]'
                    + '[data-value="' + CSS.escape(val) + '"]');
                if (btn && window.campdexTriSet) window.campdexTriSet(btn, state);
            });
        });
        if (q.get('rs') === '1') {
            var rsCb = reservableInput();
            if (rsCb) rsCb.checked = true;
        }
        var rv = parseInt(q.get('rv'), 10);
        var rvEl = document.getElementById('mf-rv-input');
        if (rv > 0 && rvEl) rvEl.value = rv;
        return out;
    })();

    if (urlState.list) document.body.classList.add('panel-open');

    var map = L.map('state-map', {
        center: urlState.center || [44.0, -120.5],
        zoom: urlState.zoom || 7,
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
    // Split-view elements
    // ---------------------------------------------------------------
    var resultsList = document.getElementById('results-list');
    var panelEmpty = document.getElementById('panel-empty');
    var panelCount = document.getElementById('panel-count');
    var viewToggleBtn = document.getElementById('view-toggle-btn');
    var viewToggleCount = document.getElementById('view-toggle-count');
    var searchAreaBtn = document.getElementById('search-area-btn');
    var desktopMql = window.matchMedia('(min-width: 1024px)');

    viewToggleBtn.removeAttribute('hidden');
    if (urlState.list) viewToggleBtn.setAttribute('aria-expanded', 'true');

    function panelVisible() {
        return desktopMql.matches || document.body.classList.contains('panel-open');
    }

    // ---------------------------------------------------------------
    // Filters (chip row + panel floating over the map)
    // ---------------------------------------------------------------
    var filters = {
        camping_types: [],
        agencies: [],
        road_access: { include: [], exclude: [] },
        seasonal: { include: [], exclude: [] },
        fire: { include: [], exclude: [] },
        styles: [],
        reservable: false,
        min_rv_length: null
    };

    // Read one tri-state group off the chip BUTTONS (data-state is the
    // source of truth; the sibling hidden inputs exist for the drawer's
    // GET form and are inert here). Absent markup reads as empty.
    function readTri(param) {
        var out = { include: [], exclude: [] };
        document.querySelectorAll('#map-filter-panel .tri-chip[data-param="' + param + '"][data-value]')
            .forEach(function(b) {
                if (b.dataset.state === '1') out.include.push(b.dataset.value);
                else if (b.dataset.state === '2') out.exclude.push(b.dataset.value);
            });
        return out;
    }

    function readFilters() {
        filters.camping_types = [];
        document.querySelectorAll('#mf-type-group .mf-toggle.active').forEach(function(b) {
            filters.camping_types.push(b.dataset.key);
        });
        filters.agencies = [];
        document.querySelectorAll('#mf-agency input:checked').forEach(function(c) { filters.agencies.push(c.value); });
        filters.road_access = readTri('road_access');
        filters.seasonal = readTri('seasonal_status');
        filters.fire = readTri('fire_status');
        filters.styles = [];
        document.querySelectorAll('#mf-style input:checked').forEach(function(c) { filters.styles.push(c.value); });
        var rs = reservableInput();
        filters.reservable = !!(rs && rs.checked);
        var rvEl = document.getElementById('mf-rv-input');
        var val = rvEl ? parseInt(rvEl.value, 10) : NaN;
        filters.min_rv_length = val > 0 ? val : null;
    }
    readFilters();   // pick up state restored from the URL

    // Filter changes apply immediately: pins + panel + URL, and any
    // pending "Search this area" prompt is superseded by the reload.
    function readFiltersAndReload() {
        readFilters();
        requestRefresh();
        writeUrl();
    }

    // Camping type toggles
    document.querySelectorAll('#mf-type-group .mf-toggle').forEach(function(btn) {
        btn.onclick = function() {
            var on = btn.classList.toggle('active');
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
            readFiltersAndReload();
        };
    });

    // Checkbox groups + tri-state chips, delegated on the panel so any
    // checkbox (agency, style, reservable) reloads without per-group
    // wiring. tri:change fires only on user clicks (app.js), never on
    // the programmatic campdexTriSet calls used by URL restore/reset.
    var panelEl = document.getElementById('map-filter-panel');
    if (panelEl) {
        panelEl.addEventListener('change', function(e) {
            if (e.target && e.target.type === 'checkbox') readFiltersAndReload();
        });
        panelEl.addEventListener('tri:change', function() {
            readFiltersAndReload();
            updateFilterCount();
        });
    }

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
        document.querySelectorAll('#map-filter-panel .tri-chip').forEach(function(b) {
            if (window.campdexTriSet) window.campdexTriSet(b, 0);
        });
        var rvEl = document.getElementById('mf-rv-input');
        if (rvEl) rvEl.value = '';
        readFiltersAndReload();
    };

    // ---------------------------------------------------------------
    // URL writing. replaceState only — the back button must not walk
    // back through every pan and filter tweak.
    // ---------------------------------------------------------------
    function writeUrl() {
        var c = map.getCenter();
        // Built by hand so commas stay literal; every value is URL-safe
        // (letters, digits, comma, minus, period, underscore).
        var parts = [
            'll=' + c.lat.toFixed(4) + ',' + c.lng.toFixed(4),
            'z=' + map.getZoom()
        ];
        if (filters.camping_types.length) parts.push('ct=' + filters.camping_types.join(','));
        if (filters.agencies.length) parts.push('ag=' + filters.agencies.join(','));
        // Tri-state groups as signed CSV: bare = require, "-" = exclude.
        function signedCsv(tri) {
            return tri.include.concat(tri.exclude.map(function(v) { return '-' + v; })).join(',');
        }
        [['rd', filters.road_access], ['sn', filters.seasonal], ['fr', filters.fire]]
            .forEach(function(pair) {
                if (pair[1].include.length || pair[1].exclude.length)
                    parts.push(pair[0] + '=' + signedCsv(pair[1]));
            });
        if (filters.styles.length) parts.push('st=' + filters.styles.join(','));
        if (filters.reservable) parts.push('rs=1');
        if (filters.min_rv_length) parts.push('rv=' + filters.min_rv_length);
        if (document.body.classList.contains('panel-open')) parts.push('v=list');
        history.replaceState(null, '', window.location.pathname + '?' + parts.join('&'));
    }

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
    var currentRequest = null;
    var markersById = {};     // facility_id -> marker, rebuilt on every pin load
    var loadedBounds = null;  // bounds of the last pin fetch

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
                className: 'campdex-pin',   // hook for the hover highlight
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

    // rvParam differs per endpoint: /api/pins takes min_rv_length,
    // /search takes rv_length.
    function buildQuery(rvParam) {
        var b = map.getBounds();
        var params = 'south=' + b.getSouth().toFixed(4)
            + '&north=' + b.getNorth().toFixed(4)
            + '&west=' + b.getWest().toFixed(4)
            + '&east=' + b.getEast().toFixed(4);
        filters.camping_types.forEach(function(v) { params += '&camping_type=' + v; });
        filters.agencies.forEach(function(v) { params += '&agency=' + v; });
        // Tri-state: include -> param, exclude -> not_param (the same
        // vocabulary the drawer's GET form submits).
        [['road_access', filters.road_access],
         ['seasonal_status', filters.seasonal],
         ['fire_status', filters.fire]].forEach(function(pair) {
            pair[1].include.forEach(function(v) { params += '&' + pair[0] + '=' + v; });
            pair[1].exclude.forEach(function(v) { params += '&not_' + pair[0] + '=' + v; });
        });
        filters.styles.forEach(function(v) { params += '&style=' + v; });
        if (filters.reservable) params += '&reservable=1';
        if (filters.min_rv_length) params += '&' + rvParam + '=' + filters.min_rv_length;
        return params;
    }

    function loadPins() {
        if (currentRequest) { currentRequest.abort(); currentRequest = null; }

        var query = buildQuery('min_rv_length');
        loadedBounds = map.getBounds();
        status.update('Loading…');

        var controller = new AbortController();
        currentRequest = controller;

        fetch('/api/pins?' + query, {signal: controller.signal})
            .then(function(r) { return r.json(); })
            .then(function(pins) {
                currentRequest = null;
                clearMarkerActive();       // the marker it points at is going away
                pinLayer.clearLayers();
                markersById = {};
                var markers = [];
                pins.forEach(function(p) {
                    var marker = L.marker([p.latitude, p.longitude], {
                        icon: pinIcon(campingColor(p.camping_type, p.seasonal_status)),
                        bubblingMouseEvents: false
                    });
                    markers.push(marker);
                    markersById[p.facility_id] = marker;

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
                    // Pin -> card hover link. setCardActive no-ops when the
                    // facility isn't in the loaded pages (never fetches).
                    marker.on('mouseover', function() { setCardActive(p.facility_id); });
                    marker.on('mouseout', function() { clearCardActive(); });
                });
                // One bulk add is far cheaper than addTo() per marker.
                pinLayer.addLayers(markers);
                var n = pins.length.toLocaleString();
                status.update('<strong>' + n + '</strong> campground' + (pins.length === 1 ? '' : 's') + ' in view');
                document.getElementById('mf-apply-n').textContent = n;
                // Until the panel has fetched (it's lazy on mobile), the pin
                // count is the best number for the List button.
                viewToggleCount.textContent = n;
            })
            .catch(function(err) {
                if (err.name !== 'AbortError') {
                    currentRequest = null;
                    status.update('Couldn’t load campgrounds — try moving the map');
                }
            });
    }

    // ---------------------------------------------------------------
    // Results panel, driven by the same bbox + filters as the pins.
    // htmx fetches the cards partial; the count comes from the
    // X-Total-Count header on every /search response.
    // ---------------------------------------------------------------
    var panelTotal = 0;
    var panelStale = true;   // mobile fetches lazily: only when the list is shown

    function loadPanel() {
        panelStale = false;
        htmx.ajax('GET', '/search?' + buildQuery('rv_length'), {target: '#results-list', swap: 'innerHTML'});
    }

    function renderPanelCount() {
        var shown = resultsList.querySelectorAll('.result-card').length;
        if (shown === 0) {
            panelEmpty.removeAttribute('hidden');
            panelCount.textContent = '0 in view';
        } else {
            panelEmpty.setAttribute('hidden', '');
            panelCount.textContent = shown < panelTotal
                ? panelTotal.toLocaleString() + ' in view — showing ' + shown.toLocaleString()
                : shown.toLocaleString() + ' in view';
        }
        viewToggleCount.textContent = panelTotal.toLocaleString();
    }

    // Only /search responses carry X-Total-Count, so the header's presence
    // is the filter — this also catches the Load More requests htmx issues
    // from inside the swapped-in partial.
    document.body.addEventListener('htmx:afterRequest', function(e) {
        var xhr = e.detail && e.detail.xhr;
        if (!xhr) return;
        var t = xhr.getResponseHeader('X-Total-Count');
        if (t !== null) panelTotal = parseInt(t, 10) || 0;
    });
    // Counting happens after settle, when the new cards are in the DOM
    // (htmx:afterRequest can fire before the swap lands).
    document.body.addEventListener('htmx:afterSettle', function(e) {
        if (e.target === resultsList || resultsList.contains(e.target)) renderPanelCount();
    });
    document.body.addEventListener('htmx:responseError', function() {
        panelCount.textContent = 'Couldn’t load results';
    });

    // ---------------------------------------------------------------
    // Hover-linking: card <-> pin.
    // ---------------------------------------------------------------
    var activeMarker = null;
    var activeCard = null;

    function setMarkerActive(marker) {
        if (marker === activeMarker) return;
        clearMarkerActive();
        if (!marker) return;
        // Pin swallowed by a cluster: no-op. Spiderfying on hover would
        // rearrange the map under the cursor.
        if (pinLayer.getVisibleParent(marker) !== marker) return;
        activeMarker = marker;
        marker.setZIndexOffset(1000);
        if (marker._icon) L.DomUtil.addClass(marker._icon, 'campdex-pin--active');
    }
    function clearMarkerActive() {
        if (!activeMarker) return;
        activeMarker.setZIndexOffset(0);
        if (activeMarker._icon) L.DomUtil.removeClass(activeMarker._icon, 'campdex-pin--active');
        activeMarker = null;
    }
    function setCardActive(fid) {
        clearCardActive();
        var card = resultsList.querySelector('.result-card[data-fid="' + fid + '"]');
        if (!card) return;   // not in the loaded pages — do not fetch
        activeCard = card;
        card.classList.add('is-active');
        card.scrollIntoView({block: 'nearest'});
    }
    function clearCardActive() {
        if (!activeCard) return;
        activeCard.classList.remove('is-active');
        activeCard = null;
    }

    function cardFromEvent(e) {
        return e.target.closest ? e.target.closest('.result-card[data-fid]') : null;
    }
    function onCardEnter(e) {
        var card = cardFromEvent(e);
        if (card) setMarkerActive(markersById[card.dataset.fid]);
    }
    function onCardLeave(e) {
        var card = cardFromEvent(e);
        if (card && !card.contains(e.relatedTarget)) clearMarkerActive();
    }
    resultsList.addEventListener('mouseover', onCardEnter);
    resultsList.addEventListener('mouseout', onCardLeave);
    resultsList.addEventListener('focusin', onCardEnter);
    resultsList.addEventListener('focusout', onCardLeave);

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
    L.DomEvent.disableClickPropagation(searchAreaBtn);
    L.DomEvent.disableClickPropagation(viewToggleBtn);

    // A count on the button so active filters are visible while the panel
    // is closed -- otherwise a filtered map looks identical to an unfiltered
    // one and the result count seems wrong.
    function updateFilterCount() {
        var n = filterPanel.querySelectorAll('input[type="checkbox"]:checked').length;
        n += filterPanel.querySelectorAll('.tri-chip[data-state="1"], .tri-chip[data-state="2"]').length;
        var rvEl = document.getElementById('mf-rv-input');
        if (rvEl && rvEl.value) n++;
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

    // The map is sized by grid/flexbox now, so tell Leaflet when layout moves.
    window.addEventListener('resize', function() { map.invalidateSize(); });

    // ---------------------------------------------------------------
    // Refresh orchestration + "Search this area".
    //
    // Panning no longer refetches. Once the view has moved meaningfully
    // away from the last-fetched bounds the button appears; clicking it
    // refetches pins + panel and updates the URL.
    //
    // Popup hold: a refresh while a popup is open would clearLayers() and
    // destroy the popup the user just opened (popups auto-pan the map, so
    // this is easy to hit). Any refresh requested while a popup is open —
    // including a button-triggered one — is held and runs on popupclose.
    // ---------------------------------------------------------------
    var refreshHeldByPopup = false;
    function popupIsOpen() {
        return !!(map._popup && map._popup.isOpen());
    }
    function requestRefresh() {
        if (popupIsOpen()) { refreshHeldByPopup = true; return; }
        doRefresh();
    }
    function doRefresh() {
        searchAreaBtn.setAttribute('hidden', '');
        loadPins();
        if (panelVisible()) loadPanel();
        else panelStale = true;   // fetch when the list is actually shown
    }

    // "Moved" means any edge shifted by more than ~0.25% of the visible
    // span — effectively any real pan or zoom, while ignoring sub-pixel
    // jitter from invalidateSize().
    function boundsMoved() {
        if (!loadedBounds) return false;
        var b = map.getBounds();
        var latTol = (b.getNorth() - b.getSouth()) * 0.0025;
        var lonTol = (b.getEast() - b.getWest()) * 0.0025;
        return Math.abs(b.getNorth() - loadedBounds.getNorth()) > latTol
            || Math.abs(b.getSouth() - loadedBounds.getSouth()) > latTol
            || Math.abs(b.getEast() - loadedBounds.getEast()) > lonTol
            || Math.abs(b.getWest() - loadedBounds.getWest()) > lonTol;
    }

    map.on('moveend', function() {
        writeUrl();   // replaceState: the URL mirrors the viewport, no history entries
        if (boundsMoved()) searchAreaBtn.removeAttribute('hidden');
        else searchAreaBtn.setAttribute('hidden', '');
    });

    searchAreaBtn.addEventListener('click', function() {
        searchAreaBtn.setAttribute('hidden', '');
        requestRefresh();
        writeUrl();
    });

    map.on('popupclose', function() {
        L.DomUtil.removeClass(map.getContainer(), 'popup-open');
        if (refreshHeldByPopup) {
            refreshHeldByPopup = false;
            // Deferred a tick: during the popupclose event Leaflet hasn't
            // finished tearing the popup down, so popupIsOpen() can still
            // report true and the refresh would re-hold itself forever.
            // (The old moveend debounce re-checked inside its 300ms timer
            // for the same reason.)
            setTimeout(requestRefresh, 0);
        }
    });
    // Leaflet stacks controls above the popup pane, so a popup near a
    // corner slides underneath the legend / count pill. Fade them out
    // while a popup is open instead of letting them cover it.
    map.on('popupopen', function() {
        L.DomUtil.addClass(map.getContainer(), 'popup-open');
    });

    // ---------------------------------------------------------------
    // Mobile list toggle. The map stays mounted underneath the panel so
    // centre/zoom/popups survive the round trip; Leaflet just needs an
    // invalidateSize() when the layout changes around it.
    // ---------------------------------------------------------------
    viewToggleBtn.addEventListener('click', function() {
        var open = document.body.classList.toggle('panel-open');
        viewToggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
        map.invalidateSize();
        if (open) loadPanel();   // always refetch: the list is never stale
        writeUrl();
    });
    document.getElementById('panel-close-btn').addEventListener('click', function() {
        document.body.classList.remove('panel-open');
        viewToggleBtn.setAttribute('aria-expanded', 'false');
        map.invalidateSize();
        writeUrl();
    });
    var onBreakpoint = function() {
        map.invalidateSize();
        if (panelVisible() && panelStale) loadPanel();
    };
    if (desktopMql.addEventListener) desktopMql.addEventListener('change', onBreakpoint);
    else desktopMql.addListener(onBreakpoint);   // older Safari

    // ---------------------------------------------------------------
    // Initial load — the one automatic fetch (no auto-geolocation prompt;
    // default view is the Oregon region unless the URL restored one).
    // Wait for layout to settle before reading bounds: loading immediately
    // fired a request with zero-area bounds, then two more on resize.
    // ---------------------------------------------------------------
    setTimeout(function() {
        map.invalidateSize();
        doRefresh();
        updateChipFade();
    }, 0);

    } catch(e) {
        document.getElementById('state-map').innerHTML =
            '<p style="padding:2rem;text-align:center;">Map failed to load. <a href="/search-form">Use the search form instead</a>.'
            + '<br><small style="color:#999;">' + e.message + '</small></p>';
    }
})();
