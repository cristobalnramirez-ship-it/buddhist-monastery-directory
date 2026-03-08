// ===== State =====
let monasteries = [];
let filtered = [];
let map, markerCluster;
let markerMap = new Map(); // id -> marker
let activePopupId = null;

// ===== Country names =====
const COUNTRY_NAMES = {
  'US': 'United States', 'CA': 'Canada', 'MX': 'Mexico', 'BR': 'Brazil',
  'AR': 'Argentina', 'CO': 'Colombia', 'CL': 'Chile', 'CR': 'Costa Rica',
  'PE': 'Peru', 'CU': 'Cuba', 'UY': 'Uruguay', 'VE': 'Venezuela',
  'EC': 'Ecuador', 'GT': 'Guatemala', 'PA': 'Panama', 'BO': 'Bolivia',
  'PY': 'Paraguay', 'HN': 'Honduras', 'NI': 'Nicaragua', 'SV': 'El Salvador',
  'JM': 'Jamaica', 'TT': 'Trinidad & Tobago', 'PR': 'Puerto Rico'
};

function countryName(code) {
  return COUNTRY_NAMES[code] || code;
}

// ===== Tradition colors =====
const TRADITION_COLORS = {
  'Theravada':        '#c4820e',
  'Zen':              '#2D5A27',
  'Tibetan':          '#8B1A4A',
  'Insight/Vipassana':'#B8960C',
  'Pure Land':        '#2B5797',
  'Chan':             '#2B5797',
  'Shingon':          '#6B4C8A',
  'Won':              '#5A7A3A',
  'SGI/Nichiren':     '#3A7A7A',
  'Other':            '#a1a1aa'
};

function getTraditionClass(tradition) {
  const map = {
    'Theravada': 'theravada',
    'Zen': 'zen',
    'Tibetan': 'tibetan',
    'Insight/Vipassana': 'insight',
    'Pure Land': 'pureland',
    'Chan': 'chan'
  };
  return map[tradition] || 'other';
}

// ===== Helpers for null-safe display =====
function locationText(m) {
  return [m.city, m.state, m.country !== 'US' ? countryName(m.country) : '']
    .filter(Boolean).join(', ');
}

// ===== Init =====
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('monasteries.json');
    monasteries = await res.json();
    // Assign IDs
    monasteries.forEach((m, i) => { m.id = m.id || i; });
  } catch (e) {
    console.error('Failed to load monastery data:', e);
    monasteries = [];
  }

  initMap();
  buildCountryFilters();
  initFilters();
  initSearch();
  initModals();
  initSidebar();
  parseURLFilters();
  applyFilters();
});

// ===== Map =====
function initMap() {
  const americasBounds = L.latLngBounds(
    L.latLng(-60, -170),  // SW corner
    L.latLng(75, -30)     // NE corner
  );
  map = L.map('map', {
    zoomControl: true,
    scrollWheelZoom: true,
    maxBounds: americasBounds,
    maxBoundsViscosity: 1.0,
    minZoom: 2
  }).setView([15, -80], 3);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 18
  }).addTo(map);

  markerCluster = L.markerClusterGroup({
    maxClusterRadius: 45,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
  });
  map.addLayer(markerCluster);

  // Legend
  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = function() {
    const div = L.DomUtil.create('div', 'map-legend');
    div.innerHTML = `
      <h4>Traditions</h4>
      ${Object.entries(TRADITION_COLORS).filter(([k]) => !['Shingon','Won','SGI/Nichiren','Other'].includes(k)).map(([name, color]) =>
        `<div class="legend-item"><span class="legend-dot" style="background:${color}"></span>${name}</div>`
      ).join('')}
      <div class="legend-item"><span class="legend-dot" style="background:#a1a1aa"></span>Other</div>
    `;
    return div;
  };
  legend.addTo(map);

  // Near me button
  document.getElementById('locate-btn').addEventListener('click', locateUser);
}

function createMarkerIcon(tradition) {
  const color = TRADITION_COLORS[tradition] || TRADITION_COLORS['Other'];
  return L.divIcon({
    className: '',
    html: `<div class="marker-icon ${getTraditionClass(tradition)}" style="width:14px;height:14px;"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -10]
  });
}

function updateMarkers() {
  markerCluster.clearLayers();
  markerMap.clear();

  filtered.forEach(m => {
    const marker = L.marker([m.lat, m.lng], {
      icon: createMarkerIcon(m.tradition)
    });

    const sub = m.subTradition ? ` (${m.subTradition})` : '';
    const loc = locationText(m);
    const dirDest = m.address || `${m.lat},${m.lng}`;
    marker.bindPopup(`
      <div class="popup-inner">
        <div class="popup-name">${esc(m.name)}</div>
        <div class="popup-tradition">${esc(m.tradition)}${esc(sub)}</div>
        ${loc ? `<div class="popup-location">${esc(loc)}</div>` : ''}
        <div class="popup-links">
          <a href="#" onclick="openDetail(${m.id}); return false;">Details</a>
          ${m.website ? `<a href="${esc(m.website)}" target="_blank" rel="noopener">Website</a>` : ''}
          <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dirDest)}" target="_blank" rel="noopener">Directions</a>
        </div>
      </div>
    `, { maxWidth: 280 });

    markerMap.set(m.id, marker);
    markerCluster.addLayer(marker);
  });
}

function panToMonastery(id) {
  const marker = markerMap.get(id);
  if (!marker) return;
  const m = monasteries.find(x => x.id === id);
  if (!m) return;

  map.setView([m.lat, m.lng], 12, { animate: true });
  setTimeout(() => {
    markerCluster.zoomToShowLayer(marker, () => {
      marker.openPopup();
    });
  }, 300);
}

function locateUser() {
  if (!navigator.geolocation) return;
  const btn = document.getElementById('locate-btn');
  btn.disabled = true;
  btn.textContent = 'Locating...';

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude: lat, longitude: lng } = pos.coords;
      map.setView([lat, lng], 8, { animate: true });

      // Add a subtle circle for user location
      L.circleMarker([lat, lng], {
        radius: 8,
        fillColor: '#4285f4',
        fillOpacity: 0.8,
        color: '#fff',
        weight: 2
      }).addTo(map).bindPopup('Your location');

      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4m10-10h-4M6 12H2"/></svg> Near Me`;
    },
    () => {
      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4m10-10h-4M6 12H2"/></svg> Near Me`;
    },
    { timeout: 8000 }
  );
}

// ===== Filters =====
function initFilters() {
  // Toggle filter section collapse
  document.querySelectorAll('.filter-heading').forEach(heading => {
    heading.addEventListener('click', () => {
      heading.classList.toggle('collapsed');
      const options = heading.nextElementSibling;
      options.classList.toggle('collapsed');
    });
  });

  // Listen for checkbox changes
  document.querySelectorAll('.filter-options input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      applyFilters();
      updateURL();
    });
  });

  // Clear all
  document.getElementById('clear-filters').addEventListener('click', () => {
    document.querySelectorAll('.filter-options input[type="checkbox"]').forEach(cb => {
      cb.checked = false;
    });
    document.getElementById('search-input').value = '';
    document.querySelector('.search-clear').classList.remove('visible');
    applyFilters();
    updateURL();
  });

  // Sort
  document.getElementById('sort-select').addEventListener('change', () => {
    sortFiltered();
    renderList();
  });
}

function getActiveFilters() {
  const filters = {};
  document.querySelectorAll('.filter-options input[type="checkbox"]:checked').forEach(cb => {
    const name = cb.name;
    if (!filters[name]) filters[name] = [];
    filters[name].push(cb.value);
  });
  return filters;
}

function matchesTraditionFilter(monastery, selectedTraditions) {
  if (!selectedTraditions || selectedTraditions.length === 0) return true;

  const m = monastery;
  for (const t of selectedTraditions) {
    // Check for sub-tradition match like "Zen/Soto"
    if (t.includes('/')) {
      const [trad, sub] = t.split('/');
      if (m.tradition === trad && m.subTradition && m.subTradition.toLowerCase().includes(sub.toLowerCase())) {
        return true;
      }
    } else {
      if (m.tradition === t) return true;
    }
  }
  return false;
}

function applyFilters() {
  const filters = getActiveFilters();
  const searchTerm = document.getElementById('search-input').value.toLowerCase().trim();

  filtered = monasteries.filter(m => {
    // Search
    if (searchTerm) {
      const haystack = `${m.name} ${m.city} ${m.state} ${m.tradition} ${m.subTradition || ''} ${countryName(m.country)} ${m.country}`.toLowerCase();
      if (!haystack.includes(searchTerm)) return false;
    }

    // Country
    if (filters.country && filters.country.length > 0) {
      if (!filters.country.includes(m.country)) return false;
    }

    // Tradition
    if (!matchesTraditionFilter(m, filters.tradition)) return false;

    // Visitor friendly (null = unknown, exclude from explicit filters)
    if (filters.visitor && filters.visitor.length > 0) {
      let match = false;
      if (filters.visitor.includes('public') && m.visitorFriendly === true) match = true;
      if (filters.visitor.includes('retreat') && m.retreats && m.retreats.length > 0) match = true;
      if (filters.visitor.includes('residential') && m.visitorFriendly === false) match = true;
      if (!match) return false;
    }

    // Retreats
    if (filters.retreats && filters.retreats.length > 0) {
      if (!m.retreats || !filters.retreats.some(r => m.retreats.includes(r))) return false;
    }

    // Ordination (null = unknown, exclude from explicit filters)
    if (filters.ordination && filters.ordination.length > 0) {
      if (filters.ordination.includes('yes') && !filters.ordination.includes('no') && m.ordination !== true) return false;
      if (filters.ordination.includes('no') && !filters.ordination.includes('yes') && m.ordination !== false) return false;
    }

    // Resident teacher (null = unknown, exclude from explicit filters)
    if (filters.teacher && filters.teacher.length > 0) {
      if (filters.teacher.includes('yes') && !filters.teacher.includes('no') && m.residentTeacher !== true) return false;
      if (filters.teacher.includes('no') && !filters.teacher.includes('yes') && m.residentTeacher !== false) return false;
    }

    // Language
    if (filters.language && filters.language.length > 0) {
      if (!filters.language.includes(m.language)) return false;
    }

    // Setting
    if (filters.setting && filters.setting.length > 0) {
      if (!filters.setting.includes(m.setting)) return false;
    }

    return true;
  });

  sortFiltered();
  updateMarkers();
  renderList();
  updateCounts();
}

function sortFiltered() {
  const sort = document.getElementById('sort-select').value;
  filtered.sort((a, b) => {
    if (sort === 'country') return (a.country + a.state + a.name).localeCompare(b.country + b.state + b.name);
    if (sort === 'state') return (a.country + a.state + a.name).localeCompare(b.country + b.state + b.name);
    if (sort === 'tradition') return (a.tradition + a.name).localeCompare(b.tradition + b.name);
    return a.name.localeCompare(b.name);
  });
}

function updateCounts() {
  const total = monasteries.length;
  const shown = filtered.length;
  document.getElementById('result-count').textContent = `Showing ${shown} of ${total} monasteries`;
  document.getElementById('list-count').textContent = `(${shown})`;
}

// ===== Search =====
function initSearch() {
  const input = document.getElementById('search-input');
  const clearBtn = document.querySelector('.search-clear');

  let debounceTimer;
  input.addEventListener('input', () => {
    clearBtn.classList.toggle('visible', input.value.length > 0);
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      applyFilters();
      updateURL();
    }, 150);
  });

  clearBtn.addEventListener('click', () => {
    input.value = '';
    clearBtn.classList.remove('visible');
    applyFilters();
    updateURL();
  });
}

// ===== List =====
function renderList() {
  const container = document.getElementById('monastery-list');

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="no-results">
        <p>No monasteries match your filters</p>
        <p class="sub">Try adjusting your search or clearing some filters</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(m => {
    const tradClass = getTraditionClass(m.tradition);
    const sub = m.subTradition ? ` \u00b7 ${esc(m.subTradition)}` : '';
    const loc = locationText(m);
    const desc = m.description || `${m.tradition} Buddhist center`;
    const badges = [];
    if (m.visitorFriendly === true) badges.push('<span class="badge badge-visitor">Open to visitors</span>');
    if (m.retreats && m.retreats.length > 0) badges.push('<span class="badge">Retreats</span>');
    if (m.ordination === true) badges.push('<span class="badge">Ordination</span>');

    return `
      <div class="card" onclick="cardClick(${m.id})" data-id="${m.id}">
        <div class="card-top">
          <div class="card-name">${esc(m.name)}</div>
          <span class="card-tradition tradition-${tradClass}">${esc(m.tradition)}</span>
        </div>
        ${loc || sub ? `<div class="card-location">${esc(loc)}${sub}</div>` : ''}
        <div class="card-description">${esc(desc)}</div>
        ${badges.length ? `<div class="card-badges">${badges.join('')}</div>` : ''}
      </div>
    `;
  }).join('');
}

function cardClick(id) {
  panToMonastery(id);
}

// ===== Detail Modal =====
function openDetail(id) {
  const m = monasteries.find(x => x.id === id);
  if (!m) return;

  // Close map popup
  map.closePopup();

  const tradClass = getTraditionClass(m.tradition);
  const sub = m.subTradition ? ` \u2014 ${esc(m.subTradition)}` : '';
  const retreatLabels = { day: 'Day visits', weekend: 'Weekend', week: 'Week-long', month: 'Month+', solitary: 'Solitary' };

  const dirDest = m.address || `${m.lat},${m.lng}`;

  // Null-safe boolean display
  const visitorText = m.visitorFriendly === true ? 'Open to visitors' :
                      m.visitorFriendly === false ? 'Not open to public' : null;
  const teacherText = m.residentTeacher === true ? 'Resident teacher' :
                      m.residentTeacher === false ? 'No resident teacher' : null;
  const ordinationText = m.ordination === true ? 'Ordination program' :
                         m.ordination === false ? 'No ordination' : null;

  const detailTags = [];
  if (visitorText) detailTags.push(`<span class="detail-tag ${m.visitorFriendly ? 'active' : ''}">${visitorText}</span>`);
  if (teacherText) detailTags.push(`<span class="detail-tag ${m.residentTeacher ? 'active' : ''}">${teacherText}</span>`);
  if (ordinationText) detailTags.push(`<span class="detail-tag ${m.ordination ? 'active' : ''}">${ordinationText}</span>`);
  if (m.language) detailTags.push(`<span class="detail-tag">${esc(m.language)}</span>`);
  if (m.setting) detailTags.push(`<span class="detail-tag">${esc(m.setting)}</span>`);

  let html = `
    <div class="detail-header">
      <div class="detail-name">${esc(m.name)}</div>
      <div class="detail-tradition">
        <span class="card-tradition tradition-${tradClass}" style="font-size:0.75rem">${esc(m.tradition)}</span>
        ${sub}
      </div>
    </div>

    <div class="detail-section">
      <h3>About</h3>
      <p>${m.description ? esc(m.description) : '<span class="text-muted">No description available yet.</span>'}</p>
    </div>

    <div class="detail-section">
      <h3>Location</h3>
      <p>${m.address ? esc(m.address) + '<br>' : ''}${m.country ? '<span style="color:#71717a">' + esc(countryName(m.country)) + '</span>' : ''}</p>
    </div>

    ${m.website ? `
    <div class="detail-section">
      <h3>Website</h3>
      <p><a href="${esc(m.website)}" target="_blank" rel="noopener">${esc(m.website.replace(/^https?:\/\/(www\.)?/, ''))}</a></p>
    </div>` : ''}

    ${m.phone ? `
    <div class="detail-section">
      <h3>Phone</h3>
      <p><a href="tel:${esc(m.phone)}">${esc(m.phone)}</a></p>
    </div>` : ''}

    ${detailTags.length ? `
    <div class="detail-section">
      <h3>Details</h3>
      <div class="detail-tags">
        ${detailTags.join('')}
      </div>
    </div>` : ''}

    ${m.retreats && m.retreats.length > 0 ? `
    <div class="detail-section">
      <h3>Retreat Offerings</h3>
      <div class="detail-tags">
        ${m.retreats.map(r => `<span class="detail-tag active">${retreatLabels[r] || r}</span>`).join('')}
      </div>
    </div>` : ''}

    <div class="detail-actions">
      <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dirDest)}" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        Get Directions
      </a>
      ${m.website ? `
      <a href="${esc(m.website)}" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        Visit Website
      </a>` : ''}
    </div>
  `;

  document.getElementById('modal-content').innerHTML = html;
  document.getElementById('detail-modal').classList.add('active');
  document.getElementById('detail-modal').setAttribute('aria-hidden', 'false');
}

// ===== Modals =====
function initModals() {
  // Detail modal close
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModals();
    });
    overlay.querySelector('.modal-close').addEventListener('click', closeModals);
  });

  // Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModals();
  });

  // Submit button
  document.getElementById('submit-btn').addEventListener('click', () => {
    document.getElementById('submit-modal').classList.add('active');
    document.getElementById('submit-modal').setAttribute('aria-hidden', 'false');
  });

  // Submit form
  document.getElementById('submit-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const data = {
      name: document.getElementById('sub-name').value,
      tradition: document.getElementById('sub-tradition').value,
      address: document.getElementById('sub-address').value,
      city: document.getElementById('sub-city').value,
      state: document.getElementById('sub-state').value.toUpperCase(),
      country: document.getElementById('sub-country').value,
      website: document.getElementById('sub-website').value,
      phone: document.getElementById('sub-phone').value,
      description: document.getElementById('sub-description').value,
      email: document.getElementById('sub-email').value,
      submittedAt: new Date().toISOString()
    };

    // Save to localStorage
    const submissions = JSON.parse(localStorage.getItem('monastery-submissions') || '[]');
    submissions.push(data);
    localStorage.setItem('monastery-submissions', JSON.stringify(submissions));

    document.getElementById('submit-form').hidden = true;
    document.getElementById('submit-success').hidden = false;

    setTimeout(() => {
      closeModals();
      document.getElementById('submit-form').hidden = false;
      document.getElementById('submit-success').hidden = true;
      document.getElementById('submit-form').reset();
    }, 2000);
  });
}

function closeModals() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
  });
}

// ===== Sidebar (mobile) =====
function initSidebar() {
  const toggle = document.getElementById('filter-toggle');
  const sidebar = document.getElementById('sidebar');

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 900 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && e.target !== toggle && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    }
  });
}

// ===== Dynamic country filters =====
function buildCountryFilters() {
  const countries = [...new Set(monasteries.map(m => m.country))].filter(Boolean).sort((a, b) => {
    // Sort by full name
    return countryName(a).localeCompare(countryName(b));
  });
  const container = document.getElementById('filter-country');
  container.innerHTML = countries.map(code =>
    `<label><input type="checkbox" name="country" value="${code}"> ${countryName(code)}</label>`
  ).join('');
}

// ===== URL params =====
function parseURLFilters() {
  const params = new URLSearchParams(window.location.search);

  params.forEach((value, key) => {
    if (key === 'q') {
      document.getElementById('search-input').value = value;
      document.querySelector('.search-clear').classList.toggle('visible', value.length > 0);
      return;
    }

    const values = value.split(',');
    values.forEach(v => {
      const cb = document.querySelector(`input[name="${key}"][value="${v}"]`);
      if (cb) cb.checked = true;
    });
  });
}

function updateURL() {
  const params = new URLSearchParams();
  const filters = getActiveFilters();

  Object.entries(filters).forEach(([key, values]) => {
    if (values.length > 0) {
      params.set(key, values.join(','));
    }
  });

  const search = document.getElementById('search-input').value.trim();
  if (search) params.set('q', search);

  const qs = params.toString();
  const newURL = window.location.pathname + (qs ? '?' + qs : '');
  window.history.replaceState(null, '', newURL);
}

// ===== Utility =====
function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Make openDetail available globally for popup links
window.openDetail = openDetail;
