// Enterprise Intelligence Browser Extension - Popup Script

const API_BASE = 'http://localhost:3001'; // Configure for production
const PLATFORM_URL = 'http://localhost:3000';

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  // Load settings
  const settings = await chrome.storage.local.get([
    'showFreshness',
    'highlightEntities',
    'show13fWarnings',
  ]);

  // Set toggle states
  setToggle('toggle-freshness', settings.showFreshness !== false);
  setToggle('toggle-highlight', settings.highlightEntities !== false);
  setToggle('toggle-13f', settings.show13fWarnings !== false);

  // Get current tab info
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.url) {
    detectEntity(tab.url);
  }

  // Toggle handlers
  document.getElementById('toggle-freshness').addEventListener('click', (e) => {
    toggleSetting(e.target, 'showFreshness');
  });
  document.getElementById('toggle-highlight').addEventListener('click', (e) => {
    toggleSetting(e.target, 'highlightEntities');
  });
  document.getElementById('toggle-13f').addEventListener('click', (e) => {
    toggleSetting(e.target, 'show13fWarnings');
  });

  // Button handlers
  document.getElementById('open-report').addEventListener('click', openReport);
  document.getElementById('open-platform').addEventListener('click', () => {
    chrome.tabs.create({ url: PLATFORM_URL });
  });
});

function setToggle(id, active) {
  const el = document.getElementById(id);
  if (active) {
    el.classList.add('active');
  } else {
    el.classList.remove('active');
  }
}

async function toggleSetting(el, key) {
  const isActive = el.classList.toggle('active');
  await chrome.storage.local.set({ [key]: isActive });

  // Notify content script
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    chrome.tabs.sendMessage(tab.id, { type: 'settingChanged', key, value: isActive });
  }
}

async function detectEntity(url) {
  const entityCard = document.getElementById('current-entity');

  // Detect entity from URL patterns
  let entity = null;

  // SEC EDGAR patterns
  const cikMatch = url.match(/CIK=(\d+)/i) || url.match(/cik=(\d+)/i);
  if (cikMatch) {
    entity = { type: 'cik', value: cikMatch[1], source: 'SEC EDGAR' };
  }

  // Yahoo Finance
  const yahooMatch = url.match(/finance\.yahoo\.com\/quote\/([A-Z0-9.-]+)/i);
  if (yahooMatch) {
    entity = { type: 'ticker', value: yahooMatch[1], source: 'Yahoo Finance' };
  }

  // Bloomberg
  const bbgMatch = url.match(/bloomberg\.com\/quote\/([A-Z0-9:]+)/i);
  if (bbgMatch) {
    entity = { type: 'ticker', value: bbgMatch[1], source: 'Bloomberg' };
  }

  if (entity) {
    entityCard.innerHTML = `
      <div class="entity-name">${entity.value}</div>
      <div class="entity-meta">
        Detected from ${entity.source}
        <span class="badge badge-fresh">Tracked</span>
      </div>
    `;

    // Fetch additional data from platform
    try {
      const response = await fetch(`${API_BASE}/entities/search?q=${entity.value}`);
      if (response.ok) {
        const data = await response.json();
        if (data.entities?.length > 0) {
          const e = data.entities[0];
          entityCard.innerHTML = `
            <div class="entity-name">${e.name || entity.value}</div>
            <div class="entity-meta">
              ${e.type || 'Entity'} · ${entity.source}
              <span class="badge badge-fresh">Tracked</span>
            </div>
          `;
        }
      }
    } catch (err) {
      console.error('Failed to fetch entity data:', err);
    }
  } else {
    entityCard.innerHTML = `
      <div class="entity-name">No entity detected</div>
      <div class="entity-meta">Navigate to a company page to see data</div>
    `;
  }
}

async function openReport() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;

  // Extract entity and open report
  const yahooMatch = tab.url.match(/finance\.yahoo\.com\/quote\/([A-Z0-9.-]+)/i);
  if (yahooMatch) {
    chrome.tabs.create({ url: `${PLATFORM_URL}/stock?symbol=${yahooMatch[1]}` });
    return;
  }

  const cikMatch = tab.url.match(/CIK=(\d+)/i);
  if (cikMatch) {
    chrome.tabs.create({ url: `${PLATFORM_URL}/company?cik=${cikMatch[1]}` });
    return;
  }

  // Default to search
  chrome.tabs.create({ url: `${PLATFORM_URL}/search` });
}
