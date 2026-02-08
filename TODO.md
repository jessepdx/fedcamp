# TODO

## Geolocation not working on localhost

**Problem:** Browser geolocation (`navigator.geolocation.getCurrentPosition`) times out on `http://localhost:5000`. The "Locate Me" button on the map page never resolves.

**Context:** Geolocation previously worked with the "Use My Location" button on the search form (same API call, same localhost). Unclear why it fails now — may be browser/OS-level Location Services issue, or a change in browser security policy.

**Possible fixes:**
- Run Flask with HTTPS (`ssl_context='adhoc'` — requires `pyopenssl`)
- Try a different port (5000 conflicts with AirPlay Receiver on macOS)
- Test in different browsers (Chrome vs Safari vs Firefox)
- Check macOS System Settings > Privacy > Location Services is enabled for the browser
- Fall back to IP-based geolocation API as a backup

## Map homepage: clicking a state doesn't load pins

**Problem:** State boundaries are nearly invisible (transparent fill, 1px border). Clicks only register on the thin border line. Changed to `fillOpacity: 0.02` but still hard to click. The whole map-as-homepage flow (auto-locate, detect state, load pins) needs more work.

**What works:** The `/api/pins?state=XX` endpoint returns correct data. The pin rendering and popup code works. The issue is the interaction flow getting to that point.

**Possible fixes:**
- Make state fills more visible/clickable
- Add a state dropdown on the map page as a fallback
- Consider a different UX: search-first instead of map-first
