// Enterprise Intelligence - Background Service Worker

const API_BASE = 'http://localhost:3001';

// Initialize default settings
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    showFreshness: true,
    highlightEntities: true,
    show13fWarnings: true,
    apiConnected: false,
  });

  // Check API connection
  checkApiConnection();
});

// Check API connection periodically
async function checkApiConnection() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    const connected = response.ok;
    chrome.storage.local.set({ apiConnected: connected });
    return connected;
  } catch (e) {
    chrome.storage.local.set({ apiConnected: false });
    return false;
  }
}

// Check connection every 5 minutes
setInterval(checkApiConnection, 5 * 60 * 1000);

// Handle messages from content scripts and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'checkConnection') {
    checkApiConnection().then(sendResponse);
    return true; // Keep channel open for async response
  }

  if (message.type === 'getEntityData') {
    fetchEntityData(message.entityId).then(sendResponse);
    return true;
  }

  if (message.type === 'getFreshness') {
    fetchFreshnessData(message.dataType, message.asOfDate).then(sendResponse);
    return true;
  }
});

async function fetchEntityData(entityId) {
  try {
    const response = await fetch(`${API_BASE}/entities/${entityId}`);
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch (e) {
    console.error('Failed to fetch entity data:', e);
    return null;
  }
}

async function fetchFreshnessData(dataType, asOfDate) {
  try {
    const response = await fetch(
      `${API_BASE}/honesty/check/${dataType}?as_of_date=${asOfDate}`
    );
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch (e) {
    console.error('Failed to fetch freshness data:', e);
    return null;
  }
}
