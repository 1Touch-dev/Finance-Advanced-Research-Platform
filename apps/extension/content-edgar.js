// Enterprise Intelligence - SEC EDGAR Content Script
// Overlays provenance and freshness data on SEC filings

(function() {
  'use strict';

  const API_BASE = 'http://localhost:3001';
  const PLATFORM_URL = 'http://localhost:3000';

  // Settings (loaded from storage)
  let settings = {
    showFreshness: true,
    highlightEntities: true,
    show13fWarnings: true,
  };

  // Initialize
  async function init() {
    // Load settings
    const stored = await chrome.storage.local.get([
      'showFreshness',
      'highlightEntities',
      'show13fWarnings',
    ]);
    settings = { ...settings, ...stored };

    // Detect page type and enhance
    if (window.location.href.includes('13F')) {
      enhance13FPage();
    } else if (window.location.href.includes('10-K') || window.location.href.includes('10K')) {
      enhance10KPage();
    } else if (window.location.href.includes('10-Q') || window.location.href.includes('10Q')) {
      enhance10QPage();
    }

    // Add provenance badges to all filing links
    enhanceFilingLinks();

    // Listen for settings changes
    chrome.runtime.onMessage.addListener((message) => {
      if (message.type === 'settingChanged') {
        settings[message.key] = message.value;
        refreshOverlays();
      }
    });
  }

  function enhance13FPage() {
    if (!settings.show13fWarnings) return;

    // Find the filing date
    const filingDateEl = document.querySelector('div.formContent');
    if (!filingDateEl) return;

    // Extract dates from the page
    const text = document.body.innerText;
    const quarterMatch = text.match(/QUARTER ENDED[:\s]+(\d{2}[-\/]\d{2}[-\/]\d{4})/i);
    const filedMatch = text.match(/FILED AS OF DATE[:\s]+(\d+)/i);

    // Create warning banner
    const banner = document.createElement('div');
    banner.id = 'ei-13f-warning';
    banner.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      background: linear-gradient(90deg, #f59e0b22, #f59e0b11);
      border-bottom: 2px solid #f59e0b;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    const warningContent = document.createElement('div');
    warningContent.innerHTML = `
      <span style="color: #f59e0b; font-weight: 700; margin-right: 10px;">⚠️ 13F DATA STALENESS WARNING</span>
      <span style="color: #334155; font-size: 13px;">
        13F filings are reported with a 45-day delay. These holdings may have changed significantly since the quarter end date.
        ${quarterMatch ? `<br>Quarter ended: ${quarterMatch[1]}` : ''}
      </span>
    `;

    const closeBtn = document.createElement('button');
    closeBtn.innerText = '✕';
    closeBtn.style.cssText = `
      background: none;
      border: 1px solid #f59e0b;
      color: #f59e0b;
      padding: 4px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
    `;
    closeBtn.onclick = () => banner.remove();

    const viewBtn = document.createElement('a');
    viewBtn.innerText = 'View in Platform →';
    viewBtn.style.cssText = `
      background: #f59e0b;
      color: white;
      padding: 6px 12px;
      border-radius: 4px;
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      margin-right: 10px;
    `;

    // Extract CIK for link
    const cikMatch = window.location.href.match(/CIK=(\d+)/i);
    if (cikMatch) {
      viewBtn.href = `${PLATFORM_URL}/institutional?cik=${cikMatch[1]}`;
      viewBtn.target = '_blank';
    }

    const actions = document.createElement('div');
    actions.style.display = 'flex';
    actions.style.alignItems = 'center';
    actions.style.gap = '8px';
    actions.appendChild(viewBtn);
    actions.appendChild(closeBtn);

    banner.appendChild(warningContent);
    banner.appendChild(actions);

    document.body.insertBefore(banner, document.body.firstChild);

    // Adjust body padding
    document.body.style.paddingTop = '60px';
  }

  function enhance10KPage() {
    // Add freshness badge
    addFreshnessBadge('10k');
  }

  function enhance10QPage() {
    // Add freshness badge
    addFreshnessBadge('10q');
  }

  function addFreshnessBadge(filingType) {
    if (!settings.showFreshness) return;

    const filedMatch = document.body.innerText.match(/FILED AS OF DATE[:\s]+(\d+)/i);
    if (!filedMatch) return;

    // Parse date (YYYYMMDD format)
    const dateStr = filedMatch[1];
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    const filedDate = new Date(`${year}-${month}-${day}`);
    const daysOld = Math.floor((Date.now() - filedDate.getTime()) / (1000 * 60 * 60 * 24));

    let badgeColor, badgeText;
    if (daysOld < 30) {
      badgeColor = '#10b981';
      badgeText = 'Fresh';
    } else if (daysOld < 90) {
      badgeColor = '#f59e0b';
      badgeText = 'Stale';
    } else {
      badgeColor = '#dc2626';
      badgeText = 'Outdated';
    }

    const badge = document.createElement('div');
    badge.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: ${badgeColor}22;
      border: 1px solid ${badgeColor};
      color: ${badgeColor};
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      z-index: 10000;
      display: flex;
      align-items: center;
      gap: 6px;
    `;
    badge.innerHTML = `
      <span style="width: 6px; height: 6px; background: ${badgeColor}; border-radius: 50%;"></span>
      ${badgeText} · ${daysOld} days old
    `;

    document.body.appendChild(badge);
  }

  function enhanceFilingLinks() {
    if (!settings.highlightEntities) return;

    // Find all filing links and add hover cards
    const links = document.querySelectorAll('a[href*="Archives/edgar/data"]');

    links.forEach(link => {
      link.addEventListener('mouseenter', showHoverCard);
      link.addEventListener('mouseleave', hideHoverCard);
    });
  }

  let hoverCard = null;

  function showHoverCard(e) {
    const link = e.target;
    const href = link.href;

    // Extract CIK and accession number
    const match = href.match(/data\/(\d+)\/(\d+)/);
    if (!match) return;

    const [, cik, accession] = match;

    hoverCard = document.createElement('div');
    hoverCard.style.cssText = `
      position: fixed;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      z-index: 10001;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 12px;
      color: #e2e8f0;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      max-width: 280px;
    `;

    const rect = link.getBoundingClientRect();
    hoverCard.style.left = `${rect.left}px`;
    hoverCard.style.top = `${rect.bottom + 5}px`;

    hoverCard.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 6px;">Enterprise Intelligence</div>
      <div style="color: #94a3b8; margin-bottom: 8px;">CIK: ${cik}</div>
      <a href="${PLATFORM_URL}/company?cik=${cik}" target="_blank"
         style="color: #6366f1; text-decoration: none; font-size: 11px;">
        View Full Intelligence Report →
      </a>
    `;

    document.body.appendChild(hoverCard);
  }

  function hideHoverCard() {
    if (hoverCard) {
      hoverCard.remove();
      hoverCard = null;
    }
  }

  function refreshOverlays() {
    // Remove and re-add overlays based on new settings
    const warning = document.getElementById('ei-13f-warning');
    if (warning) warning.remove();

    document.querySelectorAll('.ei-badge').forEach(el => el.remove());

    init();
  }

  // Run on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
