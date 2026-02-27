# Buddhist Monastery Directory — The Americas

A clean, filterable, map-based directory of Buddhist monasteries, temples, and practice centers across the Americas.

## Coverage

**88 monasteries** across **12 countries**:
- **United States** (55) — 24 states
- **Canada** (10) — BC, ON, AB, NS, QC
- **Brazil** (6) — SP, ES, RJ
- **Mexico** (5) — CDMX, Morelos
- **Argentina** (3) — Buenos Aires
- **Colombia** (2) — Bogota
- **Chile** (2) — Santiago
- **Costa Rica, Peru, Uruguay, Ecuador, Guatemala** (1 each)

**9 traditions**: Theravada, Zen, Tibetan, Pure Land, Insight/Vipassana, Chan, SGI/Nichiren, Shingon, Won, and multi-tradition centers.

## Features

- **Interactive map** with color-coded pins by tradition (Leaflet.js + OpenStreetMap)
- **Real-time filtering** by country, tradition, visitor-friendliness, retreat offerings, ordination, resident teacher, language, and setting
- **Search** by name, city, country, or tradition
- **Marker clustering** when zoomed out
- **"Near Me" geolocation** to find nearby monasteries
- **Shareable URLs** — filter state is encoded in query parameters
- **Submit a monastery** form (saves to localStorage for review)
- **Responsive** — works on desktop and mobile

## Deployment

This is a static site. No build step, no backend.

### GitHub Pages

1. Push the repository to GitHub
2. Go to Settings → Pages → Source → Deploy from branch → `main` → `/ (root)`
3. Site will be live at `https://yourusername.github.io/buddhist-monastery-directory/`

### Netlify

1. Drag and drop the project folder to [Netlify Drop](https://app.netlify.com/drop)
2. Or connect your GitHub repo for automatic deploys

### Vercel

```bash
npx vercel
```

### Local

Open `index.html` in a browser. If you need a local server (for fetch to work):

```bash
# Python 3
python -m http.server 8000

# Node.js
npx serve .
```

Then visit `http://localhost:8000`

## Adding a New Monastery

Edit `monasteries.json` and add an entry:

```json
{
  "name": "Monastery Name",
  "tradition": "Theravada",
  "subTradition": "Thai Forest",
  "country": "US",
  "city": "City Name",
  "state": "CA",
  "lat": 37.7749,
  "lng": -122.4194,
  "address": "123 Main St, City, CA 95000",
  "website": "https://example.org",
  "phone": "(555) 123-4567",
  "description": "A 2-3 sentence description of the monastery.",
  "visitorFriendly": true,
  "retreats": ["day", "weekend", "week", "month", "solitary"],
  "ordination": false,
  "residentTeacher": true,
  "language": "English-primary",
  "setting": "Rural"
}
```

### Field reference

| Field | Type | Values |
|-------|------|--------|
| `country` | string | ISO 2-letter code: `US`, `CA`, `MX`, `BR`, `AR`, `CO`, `CL`, `CR`, `PE`, `UY`, `EC`, `GT`, etc. |
| `tradition` | string | `Theravada`, `Zen`, `Tibetan`, `Pure Land`, `Insight/Vipassana`, `Chan`, `Shingon`, `Won`, `SGI/Nichiren`, `Other` |
| `retreats` | array | `day`, `weekend`, `week`, `month`, `solitary` |
| `language` | string | `English-primary`, `Bilingual`, `Non-English primary` |
| `setting` | string | `Urban`, `Suburban`, `Rural` |
| `visitorFriendly` | boolean | `true` / `false` |
| `ordination` | boolean | `true` / `false` |
| `residentTeacher` | boolean | `true` / `false` |

### Adding a new country

1. Add entries to `monasteries.json` with the new country code
2. In `index.html`, add a checkbox in the `#filter-country` section
3. In `app.js`, add the country name in the `COUNTRY_NAMES` object
4. In `index.html`, add the country to the submit form's country dropdown

### Getting coordinates

Look up the address on [Google Maps](https://maps.google.com), right-click the location, and the coordinates will appear (latitude, longitude).

## Modifying Filters/Traditions

### Adding a new tradition

1. Add entries to `monasteries.json` with the new tradition name
2. In `index.html`, add a checkbox in the `#filter-tradition` section
3. In `app.js`, add a color in the `TRADITION_COLORS` object
4. In `styles.css`, add tradition badge and marker classes

### Modifying filter categories

Filter checkboxes are in `index.html` in the sidebar. The filtering logic is in `app.js` in the `applyFilters()` function.

## Sharing filtered views

Filter state is automatically saved in the URL. Examples:

- `?country=CA` — show only Canadian monasteries
- `?country=BR,AR,CL` — South American monasteries
- `?tradition=Tibetan` — show only Tibetan monasteries
- `?tradition=Zen,Theravada&setting=Rural` — Zen and Theravada in rural settings
- `?q=brazil` — search for "brazil"
- `?country=US&retreats=month&ordination=yes` — US monasteries with month+ retreats and ordination

## Tech stack

- HTML, CSS, vanilla JavaScript
- [Leaflet.js](https://leafletjs.com/) for interactive maps
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) for marker clustering
- [OpenStreetMap](https://www.openstreetmap.org/) tiles (free, no API key)
- [Inter](https://rsms.me/inter/) font

## License

Public domain. Use however you want.
