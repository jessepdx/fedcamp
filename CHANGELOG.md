# Changelog

All notable changes to the Campdex (formerly RV Camping Finder) project.

## [0.16.1] — 2026-08-03

### Fixed
- **`robots.txt` was blocking `/api/`** — flatly contradicting a site that documents a free public API and invites AI assistants to use it. The API is now explicitly allowed. That disallow was added to protect crawl budget and shouldn't have covered the API.
- Removed the blanket `Allow: /`, which competed with `Disallow: /search?`. Google resolves that by longest-match so the disallow wins there, but simpler parsers take the first match and would have crawled the infinite filter permutation space. Anything not disallowed is allowed by default, so the blanket rule bought nothing and cost correctness.

### Added
- `robots.txt` now names 17 AI crawlers and assistants explicitly — OpenAI, Anthropic, Perplexity, Google-Extended, Applebot-Extended, Common Crawl and others — each granted the site and the API. Relying on the wildcard would have worked, but naming them makes the invitation unambiguous.
- Content signals declaring `search=yes, ai-input=yes, ai-train=yes` — all three granted. The underlying data is public federal information, the entire database is already a free download, and the site's purpose is getting campground facts in front of people; an assistant that has learned this data is that purpose being served.
- **`/llms.txt`** (llmstxt.org convention) — a machine-readable orientation for language models: what the site covers, how to call the API, the rate limit, the bulk download, and prominently the one thing an assistant must not get wrong, that `UNKNOWN` means "the agency never recorded this" rather than "no restriction". Linked from `robots.txt`.

## [0.16.0] — 2026-08-03

### Changed
- **API rate limit raised from 60 to 300 requests per minute.** The limit is per IP, but the API's documented use case is AI assistants, and those call from a platform's shared egress — every user of a ChatGPT custom GPT or a Claude integration lands on the same handful of addresses, so a few concurrent people would 429 each other. Measured cost says this was far too conservative: `/api/states` is 0.9ms and `/api/search` 23ms, so 300/min sustained is roughly 12% of one core. The limiter is there to stop accidental hammering, not to guard the data — the entire database is a public download, and bulk users should take that instead.
- **Rewrote the AI assistant prompt on the About page.** The previous version described the three endpoints and nothing else. The new one leads with the thing that actually matters: `UNKNOWN` means "the agency never recorded this", not "no restriction", and an assistant that treats it as "fine" will tell someone a road is passable when nobody knows. It explains when to use exclusion filters versus positive ones (Oregon: 283 results versus 581), covers the RV-length `OR IS NULL` semantics, tells the assistant to link back to facility pages, to say this is federal land only rather than inventing state parks, and to advise verifying with the agency before a long drive.

### Fixed
- The API parameter table said `camping_type` defaults to `DEVELOPED`. That stopped being true when the default became all three types, so anyone following the docs would have silently searched a third of the data.
- The parameter table was missing `style`, `hookup`, `reservable` and the `not_*` exclusion filters entirely — the exclusion filters being the most distinctive thing the API offers.

## [0.15.2] — 2026-08-03

### Fixed
- **Deploys served stale CSS and JavaScript for up to four hours.** Static assets carry `max-age=14400` and their URLs were unversioned, so a returning visitor got new HTML with the previous `style.css` and `map.js`. The result was real, confusing breakage that looked like layout bugs: an unstyled page heading, result cards that ignored the panel's densification, and a "Map" button wired to a handler the cached script didn't contain — so it appeared to do nothing. Asset URLs now carry `?v=<mtime>`, read once per process; gunicorn restarts on every deploy, so the version always matches what shipped.
- The split view now holds down to 760px instead of 1024px. At 1024px an ordinary 900px-wide laptop window got the phone treatment — the results list swallowed the entire browser, hiding the map, the nav and the filters, on a screen with room for all three. Between 760 and 1024 the split still fits with a narrower panel.
- On phones, the "List" button floated on top of the filter sheet's own "Show N campgrounds" button (both ending at the same y on a 375×812 screen), making taps in that zone ambiguous. It steps aside while the sheet is open.

### Changed
- Result cards now show "Road / Season / Campfires not recorded" pills, matching the facility pages. About 78% of Oregon's cards carry at least one, so a campground with no road data no longer scans the same as one with an easy road. The pills are muted and wrap into the existing pill row; median card height moved 131px → 133px.

## [0.15.1] — 2026-08-03

### Changed
- **Missing conditions now say "Not recorded" and look like a gap, not a value.** About half of campable facilities have no road access published, 40% no season, 57% no campfire status — RIDB simply doesn't carry it. These previously rendered as a solid grey "Unknown" pill, indistinguishable at a glance from a real value. They now render as a muted dashed outline, because a solid pill reads as something the agency published. Not overclaiming is the whole point of this site.
- Facility pages with gaps carry a line naming exactly what's missing and pointing at the description and directions, which is usually where the answer lives — plus the advice to call the agency before a long drive.
- `tag_display` no longer mangles the acronyms this vocabulary is full of: `4WD_REQUIRED` rendered as "4Wd Required".

### Fixed
- `tag_display` raised `AttributeError` on `None`. Several condition columns are genuinely NULL rather than the literal `'UNKNOWN'`, so any template reaching one would have 500'd.

### Notes
- Checked whether the classifier discards description-derived signals it had already parsed, since descriptions often mention road and season detail. For road access and campfires the answer is **0%** — every signal the pipeline extracts is already used. For season, 351 facilities have a signal but stay `UNKNOWN`, and all 351 are "mentions snow" with no explicit closure language. That is correct: plenty of year-round campgrounds mention snow. No recoverable signal is being thrown away, so the honest fix was to surface the gap rather than guess at a value.

## [0.15.0] — 2026-08-03

### Added
- **A crawlable path to the campground pages.** A search engine could previously reach exactly four pages: the homepage links only to `/`, `/about`, `/search-form` and `/stats`, the map is JavaScript, and the state picker is a `<select>` rather than links. Meanwhile ~6,900 facility pages carrying several hundred words each of road access, seasonal, campsite and directions detail sat entirely undiscoverable. New `/campgrounds` (state index) and `/campgrounds/<state>` (full facility list) pages, linked from the footer of every page, connect them: **656+ pages are now reachable from the homepage with JavaScript disabled, against 4 before**, and every facility is two clicks from the front door.
- `sitemap.xml` — 6,927 URLs (6,873 facilities, 50 states, static pages), built from the database and cached for 24 hours so a 2-vCPU box isn't rebuilding 800KB of XML per crawler request.
- `robots.txt` is now served by the app so it can carry a `Sitemap:` directive. Cloudflare had been serving a default file that never mentioned the sitemap. Filtered `/search?…` permutations are disallowed — they're effectively infinite and duplicate the canonical facility pages, so they'd burn crawl budget that should go to real content.
- `schema.org/Campground` JSON-LD on facility pages, with coordinates, address and managing agency. Only fields the agency actually recorded are emitted — claiming an amenity we have no data for would be exactly the overclaiming this site exists to avoid.
- `rel="canonical"` on every page, overridable per template.

### Fixed
- The map homepage had no `<h1>` at all — the map-first rebuild replaced the heading block with a strap line, leaving the site's most important page with no heading for the document outline or for search engines. Restored as a heading sized to the layout rather than to a display scale.

## [0.14.0] — 2026-08-03

### Changed
- **One filter vocabulary across the whole site.** The map and the results list had drifted into different languages: the map offered Style and Hookups but could not express exclusion; the drawer offered Season, Campfires and require/exclude chips but no Style. The map now carries require/exclude chips for Road, Season and Campfires, so it can finally express "paved, not 4WD, not permanently closed" — the query this product exists to answer. The drawer gains Style and Reservable.
- Mode was chosen per field by how often the data is unknown, not for uniformity. Require/exclude only earns its complexity where `UNKNOWN` is common — excluding keeps unknowns, requiring discards them. Road (51% unknown), Season (40%), Campfires (57%) are tri-state. Camping type (0% unknown) and Agency (4.5%) stay simple checkboxes, because at that coverage "exclude BLM" is just "include the other five". **Agency exclusion is therefore removed from the UI**; existing `not_agency=` URLs keep working.
- **Reservable** is promoted out of Amenities into a first-class filter, as a single positive checkbox. It is deliberately not require/exclude: the column has zero NULLs, so RIDB conflates "not reservable" with "not recorded", and a "first-come, first-served" option would claim knowledge the data does not contain.
- **Hookups removed from the map panel.** Only 13.5% of campable facilities have an electric hookup recorded — too thin to hold prime space, and Amenities already covers it. The `hookup=` parameter still works for API callers.
- Map URL grammar extends to signed CSV: `rd=PAVED,-4WD_REQUIRED` (bare requires, leading `-` excludes), plus `sn=`, `fr=` and `rs=1`. Old URLs still load; `hk=` is silently ignored.
- Filter option lists are exposed to every template through a context processor. The map page previously rendered with no context, so its panel hardcoded its options in markup while the drawer looped over the constants — which is precisely how the two vocabularies drifted apart.

### Fixed
- `/search` in bbox mode silently discarded `seasonal_status`, `fire_status` and `tag` filters: the bbox branch built its own kwargs dict and never passed them. All three search paths now share one filter vocabulary.
- The results drawer preserved state and lat/lon context but not the bounding box, so applying a filter on a map-derived URL silently threw the map area away.
- `db.py` had the same filter logic copy-pasted across six query functions, two of them byte-identical. That duplication is *how* the two vocabularies came to exist — each copy grew filters the others never got. One `_filter_sql()` builder now serves all six, ~170 lines lighter, verified behaviour-neutral against a 23-case matrix across every query path.

## [0.13.0] — 2026-08-03

### Added
- **The map and the results list are one screen.** On desktop the homepage is now a split view — a results panel beside the map, both driven by the map's viewport and one shared set of filters. Previously the map and `/search` were separate worlds with no shared state, which is the single biggest thing recreation.gov does badly and every product in this category (AllTrails, The Dyrt, Zillow) solves the same way. Below 1024px it's a map with a List toggle; the map stays mounted so centre, zoom and open popups survive the switch, and the list is fetched lazily — a phone showing the map never pays for it.
- **"Search this area".** Panning no longer refetches silently on every movement. The button appears once the view has actually moved and the user decides when to reload, so a deliberate pan costs nothing.
- **Shareable URLs.** Map centre, zoom, and every active filter live in the query string (`?ll=44.06,-121.32&z=11&ct=DEVELOPED&ag=FS`), written with `replaceState` so panning doesn't fill the back button. Pasting a URL reproduces the exact view, filters, and list. Unrecognised values degrade silently to defaults.
- **Hover-linking.** Hovering a result highlights its pin; hovering a pin highlights and scrolls to its card. Pins inside a cluster deliberately do nothing rather than spiderfying, which would be noise.
- `GET /search` accepts a bounding box (`south`/`north`/`west`/`east`) plus `style` and `hookup`, and returns `X-Total-Count` with the unpaginated total. `db.search_by_bounds` and `db.get_bounds_count` share one WHERE clause with the pins query, so the map count, the panel count, and pagination cannot disagree.

### Changed
- `/search?view=map` is retired and 302s to `/` — the split view supersedes it. `initResultsMap` removed.
- The map's JavaScript moved out of a `<script>` block in `map.html` into `static/map.js`. 357 lines of behaviour lived inside the template, so markup and behaviour could not be edited independently.
- Panel cards are densified by CSS scope, not a separate template: photos, tag rows and link rows are hidden, the condition pills and stats row stay. Conditions are the differentiator, so they lead.

### Fixed
- `search_by_bounds` orders by `total_campsites DESC, facility_id`. The existing queries order on `total_campsites` alone, which is unstable across `OFFSET` pages and can silently duplicate or drop rows between them; the new query does not inherit that.
- Resuming a deferred pin reload inside Leaflet's `popupclose` re-held forever, because Leaflet still reports the popup open mid-teardown. The resume is now deferred a tick. The previous 300ms debounce had been masking it.
- Condition pills overflowed the results panel by up to 160px, clipping "Seasonal Closure — Likely Open" mid-word: the base card row is `title | pills` with `flex-shrink: 0` on the pills, which cannot fit at a 420px panel. Panel cards stack the title above the pills.

## [0.12.1] — 2026-08-03

### Changed
- **Map homepage rebuilt as a map-first layout.** The map now fills the viewport with filters floating over it. Previously the map sat 75vh tall in page flow with the filter bar beneath it, which put the filters below the fold on every viewport measured — y=785 on an 800px desktop, y=841 on a 375×812 phone — so most visitors never discovered that filters existed. Camping-type chips and a Filters button sit top-left; the secondary panel opens beneath them on desktop and as a bottom sheet on mobile. The chips carry the pin colours, so the row doubles as a legend.
- The `touch-action: pan-y` override is lifted on the map page. It existed so the page could scroll "through" the map, but this page no longer scrolls, and on a phone it meant a vertical drag scrolled the page instead of panning the map — breaking the primary interaction. The results-page map keeps it.
- Result count is a compact pill and the zoom control moved to bottom-left, leaving the top corners to the filters. The RIDB credit and "verify before traveling" caveat moved into the map attribution, since the page footer is hidden on this layout.

### Fixed
- Reset button stopped clearing filters — its selector still referenced `.map-filters-bar`, a class the restructure removed.
- Leaflet's controls (z-index 1000) rendered above the filter overlay, covering the panel's first column on desktop and hiding a checkbox behind the legend on mobile.
- Opening a popup near a screen edge auto-panned the map, which triggered a pin reload that destroyed the popup the user had just opened.
- The map fetched pins three times on load, the first with zero-area bounds, because it measured itself before the flex layout settled.
- Keyboard users had to tab through the map container and every marker to reach the filters; the overlay now precedes the map in the DOM.
- The Min RV Length input rendered ~500px wide — Pico's `[type=number]` selector outranks a single class.
- Map controls were three different heights and misaligned by 10px: Pico gives buttons a bottom margin that the `.mf-*` rules never zeroed. Control sizing now comes from a `--ctl-h` custom property, so the mobile 44px touch target is one token change rather than a re-declaration of every selector — which is what caused the drift in the first place.

### Notes
- The map page's CSS was consolidated from four appended sections (with four separate `max-width: 640px` blocks setting the same properties at competing specificities) into one block. Net 36 lines shorter.
- Page weight: 6,020 → 7,938 bytes gzipped (+32%). Within budget but not free; speed is this site's advantage over the ad-heavy alternatives, so the number is worth watching.

## [0.12.0] — 2026-08-03

### Changed
- **Map pins are clustered.** A zoomed-out view returned 6,213 campgrounds and dropped every one into the DOM as an individual `divIcon` marker — `preferCanvas` does nothing for divIcons — which is what made the map crawl on phones and rendered the Pacific Northwest as overlapping pin soup. Leaflet.markercluster (34KB, loaded only on the map page, SRI-pinned) now groups them: an Oregon-wide view renders 993 campgrounds as 93 DOM nodes, and zoomed in, 458 as 82. Clusters break apart as you zoom and disappear entirely below zoom 11, so nothing is hidden — only aggregated. Markers are added in one bulk `addLayers` call rather than one at a time.
- Cluster styling is one brand green at three sizes rather than the library's green/yellow/red ramp, which would read as a severity scale on a site that already uses red for closures and exclusions. Bigger circle means more campgrounds, not worse.
- `/api/pins` no longer returns `has_electric_hookup`, `has_water_hookup`, `has_sewer_hookup` or `road_access`. They rode along in every pin and were used by nothing — the map's hookup and road filters are applied server-side from query params. The continental-US payload drops from 2,146,765 to 1,540,963 bytes.
- Caddy now serves responses with `zstd`/`gzip`, excluding `/api/download` (already-compact binary; compressing 77MB per request would burn CPU for nothing). Combined with the field trim, the continental-US pin payload goes from ~2.1MB to ~180KB — about 12x.

## [0.11.2] — 2026-08-03

### Fixed
- State-picker counts overstated every state with cross-border facilities — 406 phantom campgrounds nationwide (CA advertised 857 against 820 reachable, UT 717 against 601, ID 445 against 369). Two causes in the `n_state_cache` build in `prepare_db.py`: it joined *every* `facility_addresses` row, so a facility holding addresses in two states was counted in both while search assigns it exactly one preferred address; and it omitted the `facility_name IS NOT NULL AND <> ''` filter that search applies, counting rows the results page hides. The build now mirrors `search_by_state` exactly — same preferred-address join, same name filter, same camping types, all imported from `db.py` rather than reimplemented. Verified: the rebuilt cache matches the live search count for all 50 states, zero mismatches. National total 6,404 → 5,998.

### Added
- `rebuild_state_cache.py` regenerates `n_state_cache` in place from the facility data, so the fix reaches production without re-uploading the 77MB database. It is idempotent and refuses to write if the rebuild would produce no rows. `deploy.sh` now runs it on every deploy, while the service is stopped and from the code that just shipped, so the counts cannot drift out of step with the query that has to honour them.

## [0.11.1] — 2026-08-03

### Fixed
- Picking Oregon in the search form returned 237 campgrounds while the dropdown beside it advertised 604. The camping-type default was set in four places and three of them disagreed: `search_by_state`, `search_by_location` and `get_search_count` defaulted to `DEVELOPED` only, `search_pins_by_bounds` defaulted to all three types, the Advanced Search form pre-checked only `DEVELOPED`, and `n_state_cache` — which feeds the dropdown — counts all three. So the map already showed all 604 while search showed 237 of them. All four now derive from a single `db.DEFAULT_CAMPING_TYPES` constant, and the form pre-checks whatever that constant actually contains rather than hardcoding a guess. Oregon: 237 + 201 + 166 = 604.

### Known Issues
- The remaining dropdown gap is unrelated and still open: `n_state_cache` counts a facility once per state it holds an address in, so CA advertises 857 against 820 reachable. That needs `prepare_db.py` and a database regeneration.

## [0.11.0] — 2026-08-03

### Added
- **Exclusion filters.** Road Access, Season, Campfires and Agency are now tri-state chips: click once to require a value, twice to exclude it, a third time to clear. Exclusion deliberately *keeps* facilities with unknown data, which is the whole point — 75% of facilities have `road_access = 'UNKNOWN'`, 71% an unknown season and 79% an unknown fire status, so "not known to be 4WD" and "known to be something else" are wildly different sets. For Oregon, requiring Paved + Gravel + Dirt returns 283 campgrounds; excluding High Clearance + 4WD returns 581 (and 581 + the 23 known-bad = 604, the full state total). Exclusions apply to state search, radius search, the result count, and map pins.
- Query parameters are the `not_`-prefixed twins of the existing ones: `not_road_access`, `not_seasonal_status`, `not_fire_status`, `not_agency`, each repeatable. They work on `/search`, `/api/search` and `/api/pins`, and can be mixed with the positive filters.

### Changed
- Condition filters moved from checkboxes to chips in both the results drawer and Advanced Search. Chips are 44px tall, replacing 14px checkboxes that were well under the touch-target minimum. The trade-off is a taller filter drawer.
- Filter state round-trips entirely through the URL, so an exclusion search is shareable and the back button behaves. Only the click-to-cycle needs JavaScript; the server renders the correct state from the query string.

## [0.10.10] — 2026-08-03

### Fixed
- "Load More" never advanced past page 2, capping every search at 50 results — so Oregon's 604 campgrounds were 92% unreachable even after the state-search fix. Two causes. The button lived in `results.html` *outside* `#results-list`, the element htmx swapped into, so it was never replaced: its `hx-get` stayed pinned to `page=2` and each click re-appended the same page. And its URL was built as `request.query_string + "&page=" + (page + 1)`, but an htmx request for page 2 already carries `page=2`, so the next URL became `?page=2&page=3` — and `request.args.get("page")` reads the first value, pinning it on page 2 regardless. The control now lives inside `_results_cards.html` and replaces itself via `hx-target="#load-more"` / `hx-swap="outerHTML"`, so every response carries the button for the *next* page and it disappears when results run out. The next-page URL is built server-side with `page` stripped from the incoming args rather than appended to them.

## [0.10.9] — 2026-08-03

### Fixed
- State search returned ~2% of the results it should have: `/api/states` advertised Oregon at 604 campgrounds while searching by state returned 12. Two compounding causes, both in `db.py`. First, every address join filtered on `fa.address_type = 'Physical'`, but `Physical` is the *rarest* address type in the data — 1,812 rows vs 12,796 `Default` and 1,820 `Mailing` (Oregon: 46 facilities with a `Physical` row vs 867 with `Default`) — so the filter alone discarded ~85% of facilities. Second, the `WHERE fa.state_code IN (...)` predicate on the LEFT-JOINed table silently degraded it to an INNER JOIN (NULLs from unmatched rows never satisfy the predicate), so every facility without a `Physical` address row was dropped outright instead of surviving with a NULL state. Replaced with a shared `PREFERRED_ADDRESS_JOIN` fragment: a correlated subquery that selects exactly one address row per facility, ranked by (has non-empty `state_code`) → `Physical` → `Default` → `Mailing` → other, tie-broken on `facility_address_id` so the choice is deterministic. Applied at all five join sites: `search_by_state`, `search_by_location`, `get_facility`, `get_nearby`, and `get_search_count`. Verified: Oregon now returns 604 of 604, with no duplicate rows (the original reason the `Physical` filter existed).

### Changed
- Site name standardized to **Campdex** everywhere: page titles, nav brand link, meta tags, About page, and source file headers. Replaces the inconsistent mix of "RV Camping Finder", "FedCamp", and "Federal Camping Search".
- Condition pill, map legend, and bar chart colors darkened to meet WCAG AA contrast (≥ 4.5:1 against white text): mustard `#c49f17` → `#8a6d10` (4.91:1), orange `#d4782f` → `#a85a1e` (5.06:1), gray `#95a5a6` → `#5f6e6f` (5.32:1).
- Pico CSS primary color changed from default blue to forest green `#2d7d46`, matching the map pins and condition pills (hover/focus variants also pass WCAG AA).
- Facility page section headers ("Conditions", "Features", "Photos", etc.) are now real `<h2>` elements for the document outline, styled to match the old `<strong>` look. RIDB-injected description/directions HTML is scoped with a `.ridb-html` class so its own headings can't outrank the page structure.
- The Recreation.gov button on facility pages renders as a solid primary CTA when the facility is reservable (outline otherwise), giving reservable campgrounds a clear primary action.
- Filters button on the results page moved out of the "Search Results" `<h2>` into the actions row — a button inside a heading was semantically wrong and read badly in screen readers.
- External links now carry `rel="noopener"`.
- Feature tag category labels are formatted for display (e.g. "RIG_SIZE" → "Rig Size").

### Added
- `smart_title` Jinja filter: title-cases the ALL-CAPS facility names RIDB ships (search cards, facility pages, nearby lists, stats, map popup) while preserving agency acronyms (BLM, USFS, RV, …), state codes in trailing or post-comma position, small words (of, the, at, …), and hyphen/slash/apostrophe compounds (WALK-IN → Walk-in, O'BRIEN → O'Brien). Mixed-case names pass through untouched.
- Meta description, OpenGraph, and Twitter card tags on every page, with per-facility descriptions (agency, location, site count, max RV length) on facility pages; `theme-color` set to the brand green.
- "Clear all filters" action on the zero-results page — re-runs the same state or location search with every condition/amenity filter removed.

### Known Issues
- State dropdown counts read slightly high for cross-state facilities: `n_state_cache` (built in `prepare_db.py`) counts a facility in *every* state it has an address row for, while search now assigns each facility exactly one preferred address. CA advertises 857 but 820 are reachable via search; WA 262 vs 249. The proper fix belongs in `prepare_db.py` and requires regenerating the production database, so it was deliberately deferred.
- `/api/search` defaults `camping_type` to `DEVELOPED`, so a bare `/api/search?state=OR` returns 237 while the dropdown advertises 604 (which counts all three camping types). Pass `camping_type` repeatedly (`&camping_type=DEVELOPED&camping_type=PRIMITIVE&camping_type=DISPERSED`) to match the advertised number.
- Recommended long-term fix for both: precompute `city`/`state_code` into `n_facility_rollup` during `prepare_db.py` using the preferred-address ranking, and derive the state cache from that single per-facility value.

## [0.10.8] — 2026-08-03

### Changed
- `/api/download` is now served directly by Caddy instead of proxied through Flask. `send_file()` streamed the 77MB database through a sync gunicorn worker, occupying one of only two workers for the entire transfer and evicting the OS page cache on a 416MB box — a plausible cause of the intermittent ~1.2s page loads. Caddy serves it from `/var/www/fedcamp/fedcamp.db`, a hard link to the live `ridb.db` (same inode, so no extra disk and a shared page cache). Caddy cannot read `/home/ubuntu` (mode 0750), which is why the file is published under `/var/www` rather than served in place. Also gains HTTP range support, so downloads are resumable.
- `deploy.sh` refreshes that hard link on every deploy, after the database swap — the swap replaces the inode, so a stale link would silently serve the previous database. The step is unconditional and idempotent, and the script aborts if the inodes don't match afterwards.
- The Flask `/api/download` route is left in place. It is unreachable through Caddy now, but remains a working fallback.

## [0.10.7] — 2026-08-03

### Changed
- `purge_for_deploy.py` now runs `ANALYZE` before `VACUUM`, so the shipped database carries query planner statistics. Without `sqlite_stat1` the planner guesses, and it was guessing wrong: the facility-page photos query picked `idx_media_type` and scanned all ~35K image rows (34.7ms) instead of `idx_campsites_facility` → `idx_media_preview` (0.006ms) — a ~5,800× difference on a page users hit constantly. `VACUUM` preserves `sqlite_stat1`, so the order matters. Found while evaluating (and rejecting) a migration to DuckDB.

## [0.10.6] — 2026-08-03

### Fixed
- `/stats` returned 500 on every request except the first after a restart. `get_stats()` returns a `deepcopy` on a cache hit but handed back the cached object itself on a miss, and `app.py` assigns `data["top_facilities"] = resolve_facility_names(...)` in place — so the first request rewrote the cached `(facility_id, count)` tuples into dicts, and every request for the rest of the 5-minute TTL died on `KeyError: 0` in `resolve_facility_names`. Now copies on the miss path too. The bug was masked by deploys: each gunicorn restart cleared the cache, so the first check after any deploy always passed.

## [0.10.5] — 2026-08-03

### Fixed
- API rate limiter was one global bucket rather than per-IP. Behind Caddy → gunicorn on `127.0.0.1`, `request.remote_addr` is always `127.0.0.1`, so the documented "60 req/min per IP" was really 60 req/min shared by every visitor — one busy client could 429 the entire site, including the map's own `/api/pins` calls. `app.py` now resolves the caller through a new `_client_ip()` helper (`CF-Connecting-IP` → leftmost `X-Forwarded-For` → `remote_addr`).
- `/stats` unique-visitor counts came from Caddy's `remote_ip`, which is a Cloudflare edge address, not the visitor's. Measured against the live access log this over-counted by ~26% (436 reported vs 347 actual), because a single visitor is routed through several edge IPs. `stats.py` now prefers the `CF-Connecting-IP` request header and falls back to `remote_ip` for older log lines.

### Changed
- `deploy.sh` hardening:
  - Stops gunicorn around the database swap and deletes the stale `ridb.db-wal`/`ridb.db-shm`. Replacing `ridb.db` while the old WAL stayed in place was a SQLite corruption path, since the WAL is bound by filename rather than to file contents. Safe to discard here because `db.py` issues no writes.
  - Verifies `ridb_app.db` locally with `wal_checkpoint(TRUNCATE)` and `integrity_check` before upload, and refuses to deploy a corrupt database.
  - Real health checks after restart: `systemctl start` only proves the gunicorn master forked, so the script now polls the app on `127.0.0.1:5000` and then confirms `https://campdex.com/` publicly. An origin-only check would not have caught the Jul 2026 Caddy failure, through which gunicorn stayed perfectly healthy for 5 days.
  - Snapshots the current release to `~/fedcamp-rollback-<stamp>.tar.gz`, keeps the previous database as `ridb.db.prev`, and prints exact rollback commands on failure.
  - `StrictHostKeyChecking=no` → `accept-new`, pinning the host key after first contact.
  - Header comment points at `campdex.com` instead of the retired `fedcamp.cloudromeo.com`; temp tarballs cleaned up on both ends.

### Notes
- Production Caddy now serves the app on both `http://campdex.com` and `https://campdex.com`. Cloudflare's SSL/TLS mode for the zone is "Flexible", so it connects to the origin over plain :80, and a redirect there caused an infinite loop. This is a stopgap — the intended end state is Cloudflare "Full (strict)" plus a firewall limiting :80/:443 to Cloudflare's ranges, which is also what makes `_client_ip()` unspoofable.

## [0.10.4] — 2026-05-04

### Added
- `sync.py` — incremental RIDB sync orchestrator. Pulls facilities changed since `last_sync_date`, re-pulls their campsites/attributes/equipment/media, then runs the full pipeline (`normalize` → `rollup` → `classify` → `prepare_db`) and post-pipeline cleaning (`backfill_coords`, `scrape_seasonal`). CLI flags: `--since`, `--skip-pull`, `--skip-pipeline`, `--skip-coords`, `--skip-seasonal`.
- `last_sync_date` key in `n_meta`, written after the pipeline so `normalize.py`'s `DELETE FROM n_meta` doesn't wipe it.
- `purge_for_deploy.py` — produces a slimmed `ridb_app.db` from the synced 362MB working DB by dropping pipeline-only tables (raw EAV `campsite_attributes`/`campsite_equipment`, intermediate `n_campsite*`/`n_facility`, `rec_areas`, etc.) and `VACUUM`ing. Output ~73MB, matching the previous live footprint. `--check` flag previews the drop list without writing.

### Changed
- Map page now defaults to the Oregon region (center 44.0, -120.5, zoom 7) instead of a US-wide view.
- Removed automatic browser geolocation prompt on map load — pins load immediately for the default region.
- Refreshed RIDB data through 2026-05-04: 654 changed facilities, 15,640 campsites, 3,011 media records re-pulled. 1,484 API calls, 40.5 min. Campable facility count grew 6,319 → 7,201; coords coverage 12,474 → 13,141.
- `deploy.sh --db` now uploads `ridb_app.db` (the purged copy) instead of `ridb.db` directly, and uses an atomic mv on the server. The script errors out if `ridb_app.db` is missing, prompting the operator to run `purge_for_deploy.py` first.

### Fixed
- `docs/etl_update_plan.md` documented the wrong `lastupdated` date format. RIDB silently ignores `MM-DD-YYYY` and returns everything; the actual format is `YYYY-MM-DD`. Plan and `sync.py` corrected.
- Removed the plan's "independent campsites sweep" step — `/campsites?lastupdated=…` doesn't honor the filter (returns the full ~134K set regardless of date), so that step would fan-out to every facility.

### Safety
- `sync.py` re-fetches the first page of `/facilities/{id}/campsites` *before* deleting existing campsite rows for that facility. Transient API errors no longer wipe good data.
- Address/activity rewrites are skipped if the API response omits the field entirely (vs. an empty list, which is treated as a real "facility has none").

## [0.10.3] — 2026-02-23

### Added
- SVG favicon (pine tree)

### Fixed
- Hide 362 facilities with no name/agency data from map pins, search results, and nearby lists

### Changed
- About page updated for campdex.com domain and current map-based UI
- Replaced old state-click search description with interactive map and filter bar
- Updated API URL references from fedcamp.cloudromeo.com to campdex.com

## [0.10.2] — 2026-02-16

### Added
- Google Analytics (GA4) tracking

## [0.10.1] — 2026-02-13

### Changed
- Map filters moved below the map as a simple inline bar (removed slide-out drawer)
- Compact horizontal layout: type toggles, agency/road/hookup checkboxes, RV length input, reset button
- README updated: viewport-based map, JSON API docs, deployment info, corrected data stats

### Fixed
- Page scroll blocked by map on touch devices — vertical swipes now scroll the page instead of panning the map
- Disabled scroll-wheel zoom so mouse wheel scrolls the page (use +/- or pinch to zoom map)

## [0.10.0] — 2026-02-13

### Added
- Viewport-based map pins — campgrounds load automatically as you pan and zoom (replaces click-state-to-load)
- Map filter drawer with camping type toggles, agency/road/hookup checkboxes, and RV length input
- `search_pins_by_bounds()` lightweight bounding-box query in `db.py` (no address/photo/tag joins)
- AbortController cancels in-flight requests when viewport changes quickly
- Canvas rendering (`preferCanvas: true`) for smooth display of 6,700+ pins

### Changed
- `/api/pins` now requires `south, north, west, east` bounds instead of `state` param
- Home page no longer fetches state borders GeoJSON (~150KB saved per page load)
- Filter changes trigger immediate pin reload (no debounce); pan/zoom uses 300ms debounce

### Removed
- GeoJSON state border layer, point-in-polygon logic, and state click handlers
- `state_counts` template variable and `get_states()` call from index route

## [0.9.3] — 2026-02-13

### Fixed
- Map pins on mobile: tapping a pin no longer zooms out to state level (click events no longer bubble through pins to the state boundary layer)

### Added
- `scripts/backfill_coords.py` — fetches missing coordinates from recreation.gov campground API (recovered 545 of 970 facilities, coverage 86% → 94%)
- Coordinate backfill step documented in ETL pipeline (`docs/etl_update_plan.md`)

## [0.9.2] — 2026-02-13

### Added
- Public `/stats` page showing site usage metrics parsed from Caddy access logs
- Summary cards: unique visitors, page views, API requests, days of data
- Daily activity sparkline (CSS-only bar chart)
- Top campgrounds, states, referrers, and pages with horizontal bar charts
- `stats.py` module — standalone log parser with 5-minute cache (no Flask dependency)
- Bot filtering (50+ crawler patterns), Facebook/Reddit referrer normalization
- Graceful "no data" fallback for local development
- Nav link to Stats page
- `CADDY_LOG_DIR` env var override for testing

## [0.9.1] — 2026-02-13

### Added
- Multi-state search: select multiple states on the advanced search form (hold Ctrl/Cmd)
- API supports multiple `state` params: `/api/search?state=OR&state=WA`
- Filter drawer and pagination preserve multi-state selections

## [0.9.0] — 2026-02-13

### Added
- Public JSON API: `/api/search`, `/api/facility/<id>`, `/api/states`
- Search API supports all existing filters (state, lat/lon, camping type, agency, road access, seasonal status, fire status, RV length, amenity tags)
- Pagination via `limit` (max 100) and `offset` params
- Enables integration with AI chatbots (ChatGPT, Claude) and custom tools
- API rate limiting: 60 requests/minute per IP (returns 429 with Retry-After header)
- API documentation section on About page with endpoint reference, parameter list, examples, and chatbot integration instructions
- `/api/download` endpoint — download the full SQLite database file
- Database guide (`fedcamp-db-guide.md`) — table descriptions, column reference, and example queries

## [0.8.8] — 2026-02-13

### Fixed
- Campsite photos broken on live site — CSP img-src allowed `ridb-img.s3.us-west-2.amazonaws.com` but 99.6% of images come from `cdn.recreation.gov`
- Fee section showing raw HTML tags — strip HTML from `facility_use_fee`, hide empty-but-truthy values like `<ul><li></li></ul>`
- Empty HTML in `facility_description` and `facility_directions` showing blank sections (41 + 10 affected facilities)

### Added
- RV length filter on search form and results filter drawer — enter rig length in feet to exclude campgrounds confirmed too short (sites with unknown max length still appear)
- GitHub repo link in site footer
- Feedback form on About page (submits to Google Sheets)

## [0.8.7] — 2026-02-10

### Fixed
- Filter drawer overflows viewport on phones under 340px wide (now caps at 100vw)
- Nearby campgrounds grid causes horizontal scroll on narrow screens
- Map pins on mobile: tapping now shows a popup with name/details and a link, instead of immediately navigating away

### Changed
- Map heights moved from inline styles to CSS classes (enables media query overrides)
- Map page min-height reduced from 400px to 300px

### Added
- Pin color legend on map page (Developed, Primitive, Dispersed, Seasonal, Closed)
- 768px breakpoint: shorter maps, tighter grids, wrapped header links, smaller nav text
- 480px breakpoint: stacked layouts for header links, search toggle, geo-locate row; single-column tag/nearby grids; reduced map heights and container padding

## [0.8.6] — 2026-02-09

### Added
- Date-aware seasonal status: facility banners and result pills now show "Likely Open" or "Likely Closed" based on current month (PST)
- `likely_open` Jinja2 template filter using PST timezone (winter = Nov–Apr)
- `now_pst` and `current_month` injected into all templates via context processor

### Changed
- Seasonal/winter closure banners on facility detail pages show current month and estimated open/closed status
- Result card pills turn red with "Likely Closed" suffix during winter months for seasonal/winter closure campgrounds

## [0.8.5] — 2026-02-08

### Added
- `scripts/scrape_seasonal.py` — scrapes recreation.gov API for campground notices and availability data to reclassify UNKNOWN seasonal statuses
- Resumable scraping with JSON cache (`scripts/seasonal_cache.json`)
- `--dry-run` and `--apply-only` modes for flexible usage
- Notice-based classification: permanently closed, temporarily closed, winter closure, seasonal closure, open year-round
- Availability API fallback: detects closed campgrounds from 100% "Not Available" sites

## [0.8.4] — 2026-02-08

### Added
- Seasonal/closure warning banners on facility detail pages (Seasonal, Winter Closure, Temporarily Closed, Permanently Closed)
- Two new seasonal statuses: `TEMPORARILY_CLOSED` and `PERMANENTLY_CLOSED`
- Map pins turn orange for seasonal/winter closures, red for temporarily/permanently closed
- Seasonal status shown in map pin tooltips

### Changed
- More aggressive seasonal classification from facility descriptions — reclassified 606 facilities from UNKNOWN (patterns: "open year-round", "open from [month]", "closed for the season", "permanently closed", "closed due to", winter/snow closures)
- `classify.py` now reads raw facility descriptions for enhanced seasonal parsing (not just rollup boolean flags)

## [0.8.3] — 2026-02-08

### Added
- Google Maps / Apple Maps button on facility detail pages (auto-detects platform)

### Changed
- Renamed "Search" nav link to "Advanced Search"

## [0.8.2] — 2026-02-08

### Fixed
- Disabled Flask debug mode in production (was exposing Werkzeug interactive debugger)
- Added security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Added SRI integrity hashes to all CDN resources (Pico CSS, Leaflet, htmx)
- Removed `| safe` from `street1` and `facility_use_fee` fields (not HTML)
- CSP allows Facebook in-app browser scripts (links shared on Facebook failed to load)
- Fixed wrong SRI hashes for Leaflet JS and htmx (curl wasn't following unpkg redirects)
- Map page shows fallback link to search form if JS fails to load

## [0.8.1] — 2026-02-08

### Added
- "Limited data" notice on NPS facility detail pages that lack campsite records, with link to Recreation.gov

### Removed
- `docs/TODO.md` — open items migrated to GitHub Issues (#5, #6)

### Fixed
- 819 campgrounds (NPS, FS, BLM, USACE) missing from search results — facilities with `facility_type = 'Campground'` but zero campsite records in RIDB were misclassified as NON_CAMPING
- Campable facility count: 5,521 → 6,356

## [0.8.0] — 2026-02-08

### Added
- AWS Lightsail deployment (Ubuntu 24.04, nano instance, us-west-2)
- Live at https://fedcamp.cloudromeo.com
- `deploy.sh` — one-command SCP deploy script (`--db` flag to include database)
- `requirements.txt` — Flask + gunicorn
- Caddy reverse proxy with automatic HTTPS (Let's Encrypt)
- gunicorn WSGI server (2 workers) managed by systemd

## [0.7.3] — 2026-02-07

### Changed
- Purged 13 raw/intermediate tables from ridb.db (361MB → 72MB, 80% reduction)
- Archived full database as ridb_full.db for pipeline re-runs
- App database now contains only the 12 tables needed at runtime

### Removed
- Raw RIDB tables: campsite_attributes (2.4M rows), campsite_equipment (432K rows)
- Intermediate pipeline tables: n_campsite, n_campsite_equipment, n_facility
- Unused tables: links, rec_areas, rec_area_addresses, rec_area_activities, activities, permit_entrances, tours, events

## [0.7.2] — 2026-02-07

### Changed
- Moved data collection scripts (`pull_ridb_data.py`, `pull_campsites_bulk.py`, `pull_extras.py`, `pull_remaining.py`) to `scripts/`
- Moved reference docs (`PLAN.md`, `TODO.md`, `DB_ANALYSIS.md`, `etl_update_plan.md`) to `docs/`

### Removed
- Deleted scratch/analysis files (`analyze.py`, `deep_analysis.py`, `analysis_part*`, `_p3*.py`)
- Deleted one-off API exploration scripts (`fetch_ridb.py`, `explore_api.py`, `test_auth.py`, `test_auth2.py`)
- Deleted log files (`pull_log.txt`, `pull_extras_log.txt`, `pull_remaining_log.txt`)

## [0.7.1] — 2026-02-07

### Added
- `/api/pins?state=XX` JSON endpoint for campground map pins
- Auto-detect user's state on load via geolocation + point-in-polygon
- Campground pins preloaded on the map for the user's state automatically
- Hover over pins shows tooltip (name, site count, agency)
- Click a pin opens facility detail in a new tab (preserves map position)
- Click a state boundary to load that state's campgrounds

### Changed
- Map view is now the default home page (`/`)
- Clean map — removed state choropleth coloring, legend, and hover info panel
- Search form moved to `/search-form` with "Advanced Search" heading
- Nav updated: Map (home) | Search | About
- `/map` redirects to `/` for backwards compatibility

### Removed
- State color gradient (choropleth) and campground count legend
- "Hover over a state" info control

## [0.7.0] — 2026-02-07

### Added
- Geolocation "Search Nearby" — browser-based location detection replaces manual lat/lon entry
- "Use My Location" button with status feedback (locating, success, error)
- Form validation prevents submit without location set (nearby mode) or state selected
- Condition indicators: road access, seasonal status, campfire status, elevation, boondock accessibility
- Condition-based filters on search form and results filter drawer (Road Access, Season, Campfires)
- 8 new description signals parsed in normalize.py (seasonal closure, winter closure, snow, fire restrictions, elevation, remote/no-cell, flood risk)
- Campfire aggregation from campsite data (campfire_yes_sites, campfire_no_sites)
- `n_facility_conditions` table with classified road access, season, fire, elevation, boondock, max RV length

### Changed
- Results map markers colored by camping type (Developed/Primitive/Dispersed) instead of score
- State search sorted by total campsites (descending) instead of score
- About page rewritten to describe condition indicators instead of scoring methodology

### Removed
- Rig size tier scoring system (Tent/Small/Medium/Large 0-100 scores)
- `n_facility_score` table and all score-related columns
- Rig size selector dropdown and minimum score slider
- Score badges (single, triple, and quad) from result cards
- Score panel and breakdown table from facility detail page
- `score_color` and `confidence_color` template filters
- Manual lat/lon input fields (replaced by geolocation)

## [0.6.2] — 2026-02-07

### Fixed
- Clicking facility photos now opens a fullscreen lightbox instead of downloading
- Lightbox shows photo with caption, closes on click or Escape key

## [0.6.1] — 2026-02-07

### Added
- Slide-out filter drawer on results page (pops out from left)
- Filters: rig size, min score, camping type, agency, amenities — all pre-populated with current selections
- "Filters" button in results header toggles the drawer
- Dark overlay backdrop when drawer is open

## [0.6.0] — 2026-02-07

### Added
- Interactive US state map page (`/map`) with Leaflet choropleth
- States colored by campground count (green gradient)
- Click any state to search its campgrounds
- Hover tooltip shows state name and campground count
- Color legend and info panel
- "Map" link added to navigation bar

## [0.5.2] — 2026-02-07

### Added
- Agency filter (FS, BLM, USACE, NPS, BOR, FWS) on search form — leave unchecked for all
- Agency filtering works with both state and location searches

## [0.5.1] — 2026-02-07

### Fixed
- Result card stat pills and nearby items use light background for readability (replaced dark Pico CSS variable)

## [0.5.0] — 2026-02-07

### Added
- Tent camping tier with dedicated scoring (comp_tent_sites, comp_tent_amenities, comp_tent_access)
- Tent scores for all DEVELOPED, PRIMITIVE, and DISPERSED facilities
- Tent campers scored on: site availability, amenities (water, toilets), and access (walk-in/hike-in are positives)
- T/S/M/L quad score badges when no rig is selected

### Changed
- Score schema expanded: score_tent, score_label_tent, penalty_tent, plus 3 tent component columns
- Rig selector dropdown includes "Tent" option
- Dispersed facilities now get tent scores (RV scores remain NULL)

## [0.4.3] — 2026-02-07

### Changed
- Rig size is now optional — defaults to "Any / All Sizes"
- Search results show S/M/L triple score badges when no rig is selected
- Selecting a rig filters and sorts by that tier's score

## [0.4.2] — 2026-02-07

### Fixed
- All tags (search results, activities, features) now use lighter backgrounds for better readability

## [0.4.1] — 2026-02-07

### Added
- "View on Recreation.gov" link on facility detail page (links to real campground page)
- Recreation.gov link on each search result card

## [0.4.0] — 2026-02-07

### Added
- Flask web application (`app.py`, `db.py`, `prepare_db.py`)
- Search by state or lat/lon proximity with configurable radius (25–200 mi)
- Three rig size tiers: Small, Medium, Large — each shows its own score
- Amenity tag filters: Full Hookups, Electric, Pull-Through, Big Rig Friendly, etc.
- Minimum score slider and camping type toggles
- Results page with score badges, stats, photos, and top tags per facility
- Map view with color-coded Leaflet markers (score-based colors)
- Facility detail page: component score breakdown, tag groups, stats, map, photo gallery, nearby campgrounds, activities, reservation links
- htmx "Load More" pagination on results
- About page explaining scoring methodology
- State code normalization (full names like "ARIZONA" → "AZ", junk values nulled)
- `n_facility_photo` table mapping facilities to their best campsite photo
- `n_state_cache` table for fast state dropdown loading
- App-specific indexes on facility_addresses, campsites, media, facility_activities

### Technical
- Haversine distance via custom SQLite math functions (radians, cos, sin, acos)
- Bounding box pre-filter keeps geo queries fast on 15K rows
- Pico CSS + Leaflet.js + htmx loaded from CDN — no build step
- Server-rendered Jinja2 templates, no JavaScript framework

## [0.3.0] — 2026-02-07

### Added
- `classify.py` — RV suitability scoring and feature tags
- `n_facility_score` table: per-rig-tier scores (0–100) for Small/Medium/Large
- Five component scores: Length Fit, Hookup Quality, Driveway, RV Welcome, Inventory
- Tier-specific weights (large rigs prioritize length + hookups, small rigs prioritize welcome + inventory)
- Multiplicative penalty system (RV not recommended, hike/boat-in, 4WD, primitive)
- Data confidence metric (0–100) based on 8 data completeness signals
- Boondock accessibility rating (Easy/Moderate/Rough) for dispersed sites
- `n_facility_tags` table: 22 feature tags across 5 categories (WARNING, RIG_SIZE, HOOKUP, ACCESS, STYLE)
- Score labels: EXCELLENT, GOOD, FAIR, POOR, MARGINAL, NOT_SUITABLE

## [0.2.0] — 2026-02-07

### Added
- `rollup.py` — facility-level aggregation from campsite data
- `n_facility_rollup` table: 71 columns covering site counts, hookup stats, max RV length, surface types, driveway breakdown, access modes, description signals, activity signals
- Camping type inference via 16-step priority decision tree (DEVELOPED/PRIMITIVE/DISPERSED/DAY_USE/NON_CAMPING)
- Description enrichment: overrides boolean hookup/pullthrough flags from facility description text
- Three-source max RV length resolution (equipment, attributes, description parsing)
- Handles 388 orphaned facilities (campsites referencing missing facility_ids)

## [0.1.0] — 2026-02-07

### Added
- `normalize.py` — EAV pivot to flat campsite table
- `n_campsite` table: 132,974 rows with typed, cleaned attributes (driveway, hookups, amps, vehicle length, site access, shade, pets, campfire)
- `n_campsite_equipment` table: 392,604 rows with normalized equipment names (15 raw → 11 categories)
- `n_facility` table: 15,061 rows with description-parsed signals (20 regex patterns, RV length extraction)
- `n_meta` table for pipeline metadata tracking
- 17 parser helper functions for dirty data cleanup

## [0.0.0] — 2026-02-07

### Added
- Initial project: RIDB API data pipeline and analysis scripts
- `fetch_ridb.py`, `pull_ridb_data.py`, `pull_campsites_bulk.py`, `pull_extras.py`, `pull_remaining.py` — data collection from recreation.gov API
- `analyze.py`, `deep_analysis.py`, analysis_part*.py — exploratory data analysis
- `PLAN.md` — project roadmap
- `DB_ANALYSIS.md` — comprehensive database analysis report
- SQLite database with 132K campsites, 2.4M attributes, 432K equipment records, 15K facilities across 33 federal agencies
