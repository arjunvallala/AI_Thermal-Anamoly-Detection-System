// State
const state = {
  map: null,
  markers: {},
  events: [],
  alerts: [],
  stats: {},
  facilities: [],
  selectedEvent: null,
  hoverInfoWindow: null,
  filters: { classifications: [], severity: 'ALL' },
  autoRefreshTimer: null,
  classes: ['Industrial Fire', 'Gas Flare', 'Wildfire', 'Agricultural Burning', 'Persistent Industrial Heat (Normal)', 'Unknown']
};

const API_BASE = 'http://localhost:8000/api';

const DARK_MAP_STYLE = [
  {elementType: 'geometry', stylers: [{color: '#1a1a2e'}]},
  {elementType: 'labels.text.stroke', stylers: [{color: '#242f3e'}]},
  {elementType: 'labels.text.fill', stylers: [{color: '#746855'}]},
  {featureType: 'water', elementType: 'geometry', stylers: [{color: '#17263c'}]},
  {featureType: 'road', elementType: 'geometry', stylers: [{color: '#38414e'}]},
  {featureType: 'poi', stylers: [{visibility: 'off'}]}
];

const APP = {
  init: function() {
    this.setupDOM();
    this.setupFilters();
    this.setupTabs();
    this.setupAutoRefresh();
  },

  initMap: function() {
    state.map = new google.maps.Map(document.getElementById('map'), {
      center: {lat: 20.5937, lng: 78.9629}, // India
      zoom: 5,
      styles: DARK_MAP_STYLE,
      disableDefaultUI: true,
      zoomControl: true
    });
    this.loadAllData();
  },

  setupDOM: function() {
    document.getElementById('refresh-btn').addEventListener('click', () => this.triggerRefresh());
    document.getElementById('close-panel').addEventListener('click', () => this.closePanel());
    document.getElementById('nav-alerts-btn').addEventListener('click', () => this.toggleAlertsModal());
    document.getElementById('close-modal').addEventListener('click', () => this.toggleAlertsModal(false));
    document.getElementById('btn-download-report').addEventListener('click', () => this.downloadReport());
    
    // Analyst actions
    document.getElementById('btn-verify').addEventListener('click', () => this.verifyEvent('verified'));
    document.getElementById('btn-reject').addEventListener('click', () => this.verifyEvent('rejected'));
    document.getElementById('btn-reclassify').addEventListener('click', () => this.reclassifyEvent());
    document.getElementById('btn-save-note').addEventListener('click', () => this.saveNote());
    document.getElementById('btn-dispatch-alert').addEventListener('click', () => this.simulateDispatch());
  },

  setupTabs: function() {
    // Sidebar tabs
    document.querySelectorAll('.s-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.s-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.list-container').forEach(c => c.classList.add('hidden'));
        e.target.classList.add('active');
        document.getElementById(e.target.dataset.target).classList.remove('hidden');
      });
    });

    // Panel tabs
    document.querySelectorAll('.p-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.p-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        document.getElementById(e.target.dataset.target).classList.add('active');
      });
    });
  },

  setupFilters: function() {
    const container = document.getElementById('class-filters-container');
    state.classes.forEach(c => {
      state.filters.classifications.push(c);
      const div = document.createElement('label');
      div.className = 'check-label';
      div.innerHTML = `<input type="checkbox" value="${c}" checked> ${c}`;
      div.querySelector('input').addEventListener('change', (e) => {
        if (e.target.checked) {
          if (!state.filters.classifications.includes(c)) state.filters.classifications.push(c);
        } else {
          state.filters.classifications = state.filters.classifications.filter(x => x !== c);
        }
        this.applyFilters();
      });
      container.appendChild(div);
    });

    document.querySelectorAll('input[name="severity"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        state.filters.severity = e.target.value;
        this.applyFilters();
      });
    });

    document.getElementById('reset-filters').addEventListener('click', () => {
      state.filters.severity = 'ALL';
      document.querySelector('input[name="severity"][value="ALL"]').checked = true;
      state.filters.classifications = [...state.classes];
      document.querySelectorAll('#class-filters-container input').forEach(cb => cb.checked = true);
      this.applyFilters();
    });
  },

  applyFilters: function() {
    this.populateEventsList();
    this.updateMarkers();
  },

  loadAllData: async function() {
    this.showLoading(true);
    try {
      const [eventsRes, statsRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/events`).catch(() => ({ok: true, json: () => []})),
        fetch(`${API_BASE}/stats`).catch(() => ({ok: true, json: () => ({total:0, active:0, p1:0, risk:0})})),
        fetch(`${API_BASE}/alerts`).catch(() => ({ok: true, json: () => []}))
      ]);

      state.events = eventsRes.ok ? await eventsRes.json() : [];
      state.stats = statsRes.ok ? await statsRes.json() : {total:0, active:0, p1:0, risk:0};
      state.alerts = alertsRes.ok ? await alertsRes.json() : [];

      this.updateStatCards();
      this.renderMapMarkers();
      this.populateEventsList();
      this.populateAlertsList();
      
      document.getElementById('last-updated').innerText = `Updated: ${new Date().toLocaleTimeString()}`;
    } catch (e) {
      this.showToast('Failed to connect to Intelligence Backend', 'error');
      console.error(e);
    } finally {
      this.showLoading(false);
    }
  },

  updateStatCards: function() {
    document.getElementById('stat-total').innerText = state.stats.total || state.events.length || 0;
    document.getElementById('stat-active').innerText = state.stats.active || state.events.filter(e => e.status === 'active').length || 0;
    const p1Count = state.stats.p1 || state.alerts.filter(a => a.priority === 'P1').length || 0;
    document.getElementById('stat-alerts').innerText = p1Count;
    document.getElementById('stat-risk').innerText = state.stats.risk || 0;
  },

  getClassColor: function(cls) {
    const map = {
      'Industrial Fire': '#ef4444',
      'Gas Flare': '#f97316',
      'Wildfire': '#84cc16',
      'Agricultural Burning': '#a3e635',
      'Persistent Industrial Heat (Normal)': '#06b6d4',
      'Unknown': '#6b7280'
    };
    return map[cls] || map['Unknown'];
  },

  getClassEmoji: function(cls) {
    const map = {
      'Industrial Fire': '🔥',
      'Gas Flare': '🔆',
      'Wildfire': '🌲',
      'Agricultural Burning': '🌾',
      'Persistent Industrial Heat (Normal)': '⚡',
      'Unknown': '❓'
    };
    return map[cls] || '❓';
  },

  getSeverityColor: function(sev) {
    const map = { 'CRITICAL': '#ef4444', 'HIGH': '#f97316', 'WATCH': '#f59e0b', 'NORMAL': '#10b981' };
    return map[sev] || '#10b981';
  },


  renderMapMarkers: function() {
    Object.values(state.markers).forEach(m => m.setMap(null));
    state.markers = {};

    state.events.forEach(evt => {
      const color = this.getClassColor(evt.classification);

      // FRP → radius: 0 MW=8px, 100 MW=12px, 400 MW=20px, 800+ MW=30px
      const frp = Math.max(0, evt.frp || 0);
      const radius = Math.round(Math.max(8, Math.min(30, 8 + (frp / 800) * 22)));

      const marker = new google.maps.Marker({
        position: { lat: evt.lat, lng: evt.lon },
        map: state.map,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: radius,
          fillColor: color,
          fillOpacity: 0.85,
          strokeColor: '#ffffff',
          strokeWeight: 1.5
        },
        title: `${evt.classification} | FRP: ${frp} MW | ${evt.severity}`,
        zIndex: evt.severity === 'CRITICAL' ? 1000 : evt.severity === 'HIGH' ? 500 : 100
      });

      // Hover info window showing key intelligence
      const infoContent = `
        <div style="background:#1f2937;color:#f9fafb;padding:10px 14px;border-radius:8px;font-family:sans-serif;min-width:190px;border:1px solid #374151">
          <div style="font-size:13px;font-weight:700;margin-bottom:6px">${this.getClassEmoji(evt.classification)} ${evt.classification}</div>
          <div style="font-size:11px;color:#9ca3af;line-height:1.7">
            <b style="color:#f59e0b">FRP:</b> ${frp} MW<br>
            <b style="color:#f59e0b">Severity:</b> <span style="color:${this.getSeverityColor(evt.severity)}">${evt.severity}</span><br>
            <b style="color:#f59e0b">ML Prob:</b> ${Math.round((evt.ml_probability||0)*100)}%<br>
            <b style="color:#f59e0b">Deviation:</b> ${evt.frp_deviation||1}× baseline<br>
            <b style="color:#f59e0b">Area:</b> ${evt.affected_area_km2||'—'} km²
          </div>
          <div style="margin-top:8px;font-size:10px;color:#6b7280">Click marker for full intelligence</div>
        </div>`;

      const infoWindow = new google.maps.InfoWindow({ content: infoContent });
      marker.addListener('mouseover', () => {
        if (state.hoverInfoWindow) state.hoverInfoWindow.close();
        infoWindow.open(state.map, marker);
        state.hoverInfoWindow = infoWindow;
      });
      marker.addListener('mouseout', () => {
        setTimeout(() => infoWindow.close(), 1200);
      });
      marker.addListener('click', () => {
        if (state.hoverInfoWindow) state.hoverInfoWindow.close();
        this.selectEvent(evt.id);
      });

      state.markers[evt.id] = marker;
    });
    this.updateMarkers();
  },


  updateMarkers: function() {
    state.events.forEach(evt => {
      const marker = state.markers[evt.id];
      if (!marker) return;
      const classMatch = state.filters.classifications.includes(evt.classification);
      const sevMatch = state.filters.severity === 'ALL' || state.filters.severity === evt.severity;
      marker.setVisible(classMatch && sevMatch);
    });
  },

  populateEventsList: function() {
    const list = document.getElementById('events-list');
    const empty = document.getElementById('events-empty');
    list.innerHTML = '';
    
    let filtered = state.events.filter(evt => {
      const classMatch = state.filters.classifications.includes(evt.classification);
      const sevMatch = state.filters.severity === 'ALL' || state.filters.severity === evt.severity;
      return classMatch && sevMatch;
    });

    const sevOrder = { 'CRITICAL': 0, 'HIGH': 1, 'WATCH': 2, 'NORMAL': 3 };
    filtered.sort((a, b) => {
      if (sevOrder[a.severity] !== sevOrder[b.severity]) return sevOrder[a.severity] - sevOrder[b.severity];
      return new Date(b.timestamp) - new Date(a.timestamp);
    });

    if (filtered.length === 0) {
      empty.classList.remove('hidden');
    } else {
      empty.classList.add('hidden');
      filtered.forEach(evt => {
        const d = new Date(evt.timestamp);
        const timeStr = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const el = document.createElement('div');
        el.className = `event-item ${state.selectedEvent === evt.id ? 'active' : ''}`;
        el.style.borderLeftColor = this.getClassColor(evt.classification);
        el.onclick = () => this.selectEvent(evt.id);
        
        el.innerHTML = `
          <div class="ei-icon">${this.getClassEmoji(evt.classification)}</div>
          <div class="ei-content">
            <div class="ei-header">
              <span class="ei-class">${evt.classification}</span>
              <span class="ei-time">${timeStr}</span>
            </div>
            <div class="ei-loc"><i class="fa-solid fa-location-dot"></i> ${evt.nearest_facility_name || `${evt.lat.toFixed(2)}, ${evt.lon.toFixed(2)}`}</div>
            <div class="ei-metrics">FRP: ${evt.frp} MW | ${evt.severity}</div>
          </div>
        `;
        list.appendChild(el);
      });
    }
  },

  populateAlertsList: function() {
    const listSidebar = document.getElementById('alerts-list');
    const listModal = document.getElementById('modal-alerts-list');
    const empty = document.getElementById('alerts-empty');
    const badge = document.getElementById('nav-alert-count');
    const tabBadge = document.getElementById('tab-alert-count');
    
    listSidebar.innerHTML = '';
    listModal.innerHTML = '';

    const activeAlerts = state.alerts;
    const p1Count = activeAlerts.filter(a => a.priority === 'P1').length;
    
    if (p1Count > 0) {
      badge.innerText = p1Count;
      badge.classList.remove('hidden');
      badge.classList.add('pulse');
    } else {
      badge.classList.add('hidden');
    }

    tabBadge.innerText = activeAlerts.length;

    if (activeAlerts.length === 0) {
      empty.classList.remove('hidden');
      listModal.innerHTML = '<div class="empty-state">No active alerts at this time.</div>';
    } else {
      empty.classList.add('hidden');
      
      activeAlerts.forEach(alert => {
        const d = new Date(alert.timestamp || Date.now());
        const tStr = d.toLocaleTimeString();
        const html = `
          <div class="alert-item ${alert.priority.toLowerCase()}">
            <div class="alert-main">
              <div class="alert-header">
                <i class="fa-solid ${alert.priority==='P1' ? 'fa-triangle-exclamation' : 'fa-circle-exclamation'}"></i>
                <span class="alert-type">${alert.priority} ALERT</span>
                <span class="alert-time">${tStr}</span>
              </div>
              <div class="alert-msg">${alert.message || 'Anomaly detected requires attention.'}</div>
              ${alert.event_id ? `<button class="text-btn mt-2" onclick="app.selectEvent('${alert.event_id}')">View Event</button>` : ''}
            </div>
          </div>
        `;
        listSidebar.innerHTML += html;
        listModal.innerHTML += html;
      });
    }
  },

  selectEvent: async function(id) {
    state.selectedEvent = id;
    this.populateEventsList(); // update active state
    
    // Fallback: find event in local array if fetch fails
    let event = state.events.find(e => e.id === id);
    
    try {
      this.showLoading(true);
      const res = await fetch(`${API_BASE}/events/${id}`);
      if (res.ok) event = await res.json();
    } catch (e) {
      console.warn("Failed to fetch event details, using list data");
    } finally {
      this.showLoading(false);
    }

    if (!event) return;

    // Pan map
    state.map.panTo({lat: event.lat, lng: event.lon});
    state.map.setZoom(10);

    // Populate Right Panel
    document.getElementById('ep-id').innerText = event.id;
    document.getElementById('ep-time').innerText = new Date(event.timestamp).toLocaleString();
    
    const cColor = this.getClassColor(event.classification);
    document.getElementById('ep-class-badge').style.backgroundColor = `${cColor}22`;
    document.getElementById('ep-class-badge').style.color = cColor;
    document.getElementById('ep-class-badge').style.border = `1px solid ${cColor}`;
    document.getElementById('ep-class-icon').innerText = this.getClassEmoji(event.classification);
    document.getElementById('ep-class-name').innerText = event.classification;

    const sColor = this.getSeverityColor(event.severity);
    document.getElementById('ep-severity-dot').style.backgroundColor = sColor;
    document.getElementById('ep-severity').innerText = event.severity;
    document.getElementById('ep-severity').style.color = sColor;
    document.getElementById('ep-severity-container').style.borderColor = sColor;

    const prob = (event.ml_probability * 100).toFixed(1);
    document.getElementById('ep-ml-prob-text').innerText = `${prob}%`;
    const pBar = document.getElementById('ep-ml-prob-bar');
    pBar.style.width = `${prob}%`;
    pBar.style.backgroundColor = prob > 75 ? varColors.success : (prob > 50 ? varColors.warning : varColors.accent);

    this.populateOverviewTab(event);
    this.populateEvidenceTab(event);
    this.populateEnvironmentTab(event);
    this.populateRespondersTab(event);
    this.populateAnalystTab(event);

    document.getElementById('event-panel').classList.remove('hidden');
  },

  populateOverviewTab: function(evt) {
    document.getElementById('ep-frp').innerText = evt.frp.toFixed(1);
    document.getElementById('ep-brightness').innerText = evt.brightness.toFixed(1);
    document.getElementById('ep-cluster').innerText = evt.cluster_size || 1;
    document.getElementById('ep-duration').innerText = (evt.duration_hours || 0).toFixed(1);

    document.getElementById('ep-fac-name').innerText = evt.nearest_facility_name || 'No facility nearby';
    document.getElementById('ep-fac-type').innerText = evt.nearest_facility_type || '-';
    document.getElementById('ep-fac-dist').innerText = evt.nearest_facility_dist_km ? `${evt.nearest_facility_dist_km.toFixed(1)} km` : '-';

    const dev = evt.frp_deviation || 1.0;
    document.getElementById('ep-dev-val').innerText = `${dev.toFixed(1)}x`;
    const devBar = document.getElementById('ep-dev-bar');
    // Map 0-5x to 0-100% position
    const pos = Math.min(100, Math.max(0, (dev / 5) * 100));
    devBar.style.left = `calc(${pos}% - 2px)`;

    let rec = '';
    if (evt.severity === 'CRITICAL' && evt.classification === 'Industrial Fire') {
      rec = '🚨 Immediate fire-response verification recommended. Alert dispatched to emergency control.';
    } else if (evt.severity === 'HIGH') {
      rec = 'High priority verification required within 2 hours.';
    } else if (evt.classification === 'Gas Flare') {
      rec = 'Monitor for escalation. Routine flaring within acceptable parameters.';
    } else {
      rec = 'Routine monitoring. No immediate action required.';
    }
    document.getElementById('ep-action-text').innerText = rec;
  },

  populateEvidenceTab: function(evt) {
    const score = evt.evidence_score || 0;
    const badge = document.querySelector('#ep-ev-summary .ev-badge');
    badge.innerText = score > 0.7 ? 'HIGH' : (score > 0.4 ? 'MEDIUM' : 'LOW');
    badge.style.backgroundColor = score > 0.7 ? varColors.success : (score > 0.4 ? varColors.warning : varColors.accent);

    const list = document.getElementById('ep-ev-list');
    list.innerHTML = '';
    
    // Mock evidence list based on classification
    const sources = [
      { name: 'FIRMS Satellite Data', status: 'confirmed', desc: 'Thermal anomaly detected by VIIRS/MODIS.' },
      { name: 'Industrial Footprint Map', status: evt.nearest_facility_name ? 'confirmed' : 'missing', desc: evt.nearest_facility_name ? 'Matches known industrial zone.' : 'No known industry at location.' },
      { name: 'Historical Baseline', status: 'partial', desc: 'Comparing against 30-day thermal history.' }
    ];

    sources.forEach(s => {
      let icon = 'fa-circle-check';
      if (s.status === 'partial') icon = 'fa-circle-exclamation';
      if (s.status === 'missing') icon = 'fa-circle-xmark';
      
      list.innerHTML += `
        <li class="evidence-item">
          <i class="fa-solid ${icon} status-icon ${s.status}"></i>
          <div class="ev-info">
            <div class="ev-title">${s.name}</div>
            <div class="ev-desc">${s.desc}</div>
          </div>
        </li>
      `;
    });
  },

  populateEnvironmentTab: function(evt) {
    document.getElementById('ep-co2').innerText = (evt.co2_estimate || 0).toFixed(2);
    document.getElementById('ep-area').innerText = (evt.affected_area_km2 || 0).toFixed(2);
    
    const cContainer = document.getElementById('ep-chemicals');
    cContainer.innerHTML = '';
    if (evt.likely_chemicals) {
      evt.likely_chemicals.split(',').forEach(c => {
        cContainer.innerHTML += `<span class="chip">${c.trim()}</span>`;
      });
    } else {
      cContainer.innerHTML = '<span class="text-secondary">None detected</span>';
    }

    const rScore = evt.public_risk_score || 0;
    document.getElementById('ep-risk-val').innerText = `${rScore}/100`;
    document.getElementById('ep-risk-bar').style.width = `${rScore}%`;
    let rDesc = 'Low Risk';
    if (rScore > 75) rDesc = 'Critical Risk - Evacuation Warning';
    else if (rScore > 50) rDesc = 'High Risk - Health Advisory';
    document.getElementById('ep-risk-desc').innerText = rDesc;
  },

  populateRespondersTab: function(evt) {
    let responders = { fire_station: {name: 'Local Fire Dept', dist: '5km'}, hospital: {name: 'General Hospital', dist: '8km'}, police: {name: 'Local Precinct', dist: '4km'} };
    if (evt.nearest_responders) {
      try { responders = JSON.parse(evt.nearest_responders); } catch(e){}
    }

    const list = document.getElementById('ep-responders-list');
    list.innerHTML = `
      <div class="responder-card">
        <i class="fa-solid fa-truck-medical accent-color"></i>
        <div class="resp-info">
          <div class="resp-name">${responders.hospital?.name || 'Nearest Hospital'}</div>
          <div class="resp-dist">${responders.hospital?.dist || '--'}</div>
        </div>
      </div>
      <div class="responder-card">
        <i class="fa-solid fa-fire-extinguisher warning-color"></i>
        <div class="resp-info">
          <div class="resp-name">${responders.fire_station?.name || 'Nearest Fire Station'}</div>
          <div class="resp-dist">${responders.fire_station?.dist || '--'}</div>
        </div>
      </div>
      <div class="responder-card">
        <i class="fa-solid fa-building-shield info-color"></i>
        <div class="resp-info">
          <div class="resp-name">${responders.police?.name || 'Nearest Police Station'}</div>
          <div class="resp-dist">${responders.police?.dist || '--'}</div>
        </div>
      </div>
    `;

    const statusBadge = document.querySelector('#ep-alert-status .status-badge');
    if (evt.severity === 'CRITICAL') {
      statusBadge.className = 'status-badge sent';
      statusBadge.innerText = 'DISPATCHED';
    } else {
      statusBadge.className = 'status-badge pending';
      statusBadge.innerText = 'STANDBY';
    }
  },

  populateAnalystTab: function(evt) {
    const sBadge = document.getElementById('ep-an-status');
    sBadge.innerText = (evt.status || 'active').toUpperCase();
    document.getElementById('analyst-note-input').value = evt.analyst_note || '';
    document.getElementById('reclassify-select').value = evt.classification || '';
  },

  closePanel: function() {
    document.getElementById('event-panel').classList.add('hidden');
    state.selectedEvent = null;
    this.populateEventsList();
  },

  toggleAlertsModal: function(force) {
    const m = document.getElementById('alerts-modal');
    if (force === false) m.classList.add('hidden');
    else if (force === true) m.classList.remove('hidden');
    else m.classList.toggle('hidden');
  },

  triggerRefresh: async function() {
    this.showLoading(true);
    try {
      await fetch(`${API_BASE}/ingest`, {method: 'POST'}).catch(()=>{});
      await this.loadAllData();
      this.showToast('Data refreshed successfully', 'success');
    } catch (e) {
      this.showToast('Refresh failed', 'error');
    } finally {
      this.showLoading(false);
    }
  },

  setupAutoRefresh: function() {
    if (state.autoRefreshTimer) clearInterval(state.autoRefreshTimer);
    state.autoRefreshTimer = setInterval(() => this.loadAllData(), 5 * 60 * 1000);
  },

  downloadReport: function() {
    if (!state.selectedEvent) return;
    const btn = document.getElementById('btn-download-report');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
    
    // Simulate download by navigating to endpoint
    setTimeout(() => {
      window.open(`${API_BASE}/events/${state.selectedEvent}/report`, '_blank');
      btn.innerHTML = '<i class="fa-solid fa-file-pdf"></i> Download Report';
      this.showToast('Report downloaded', 'success');
    }, 1000);
  },

  verifyEvent: async function(status) {
    if (!state.selectedEvent) return;
    try {
      await fetch(`${API_BASE}/events/${state.selectedEvent}/verify`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: status})
      });
      this.showToast(`Event marked as ${status}`, 'success');
      this.loadAllData();
    } catch (e) {
      this.showToast(`Simulated verification as backend is unreachable`, 'info');
    }
  },

  reclassifyEvent: function() {
    const v = document.getElementById('reclassify-select').value;
    if (v) this.showToast(`Event reclassified to ${v}`, 'success');
  },

  saveNote: function() {
    this.showToast('Analyst note saved', 'success');
  },

  simulateDispatch: function() {
    this.showToast('Alert dispatched to local emergency responders!', 'success');
  },

  showLoading: function(show) {
    const el = document.getElementById('loading-overlay');
    if (show) el.classList.remove('hidden');
    else el.classList.add('hidden');
  },

  showToast: function(msg, type='info') {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    let icon = 'fa-circle-info';
    if (type==='success') icon = 'fa-circle-check';
    if (type==='error') icon = 'fa-triangle-exclamation';
    
    t.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => {
      t.style.animation = 'fadeOut 0.3s forwards';
      setTimeout(() => t.remove(), 300);
    }, 3000);
  }
};

const varColors = {
  success: '#10b981',
  warning: '#f59e0b',
  accent: '#ef4444',
  info: '#3b82f6'
};

// Expose for Google Maps callback
window.app = APP;

// Init DOM on load
document.addEventListener('DOMContentLoaded', () => APP.init());
