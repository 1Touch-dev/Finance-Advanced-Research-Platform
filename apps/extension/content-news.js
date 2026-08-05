// Enterprise Intelligence - News Sites Content Script
// Overlays intelligence data on financial news pages

(function() {
  'use strict';

  const API_BASE = 'http://localhost:3001';
  const PLATFORM_URL = 'http://localhost:3000';

  let settings = {
    showFreshness: true,
    highlightEntities: true,
  };

  async function init() {
    const stored = await chrome.storage.local.get(['showFreshness', 'highlightEntities']);
    settings = { ...settings, ...stored };

    // Detect tickers in the page and add enhancements
    detectAndEnhanceTickers();

    // Listen for settings changes
    chrome.runtime.onMessage.addListener((message) => {
      if (message.type === 'settingChanged') {
        settings[message.key] = message.value;
      }
    });
  }

  function detectAndEnhanceTickers() {
    if (!settings.highlightEntities) return;

    // Common ticker patterns
    const tickerPattern = /\b([A-Z]{1,5})\b/g;

    // Known tickers to highlight (in production, fetch from platform)
    const knownTickers = new Set([
      'AAPL', 'GOOGL', 'GOOG', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA',
      'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BRK.A', 'BRK.B',
      'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK',
      'XOM', 'CVX', 'COP', 'SLB',
    ]);

    // Find text nodes with tickers
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );

    const nodesToEnhance = [];

    while (walker.nextNode()) {
      const node = walker.currentNode;
      const text = node.textContent;

      // Skip script/style elements
      const parent = node.parentElement;
      if (!parent || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(parent.tagName)) continue;

      // Check for ticker mentions
      let match;
      while ((match = tickerPattern.exec(text)) !== null) {
        const ticker = match[1];
        if (knownTickers.has(ticker)) {
          nodesToEnhance.push({ node, ticker, index: match.index });
        }
      }
    }

    // Enhance found tickers (limit to prevent performance issues)
    nodesToEnhance.slice(0, 50).forEach(({ node, ticker, index }) => {
      try {
        enhanceTickerMention(node, ticker);
      } catch (e) {
        console.error('Failed to enhance ticker:', e);
      }
    });
  }

  function enhanceTickerMention(textNode, ticker) {
    const text = textNode.textContent;
    const regex = new RegExp(`\\b(${ticker})\\b`);
    const match = text.match(regex);

    if (!match) return;

    const parent = textNode.parentElement;
    if (!parent || parent.querySelector('.ei-ticker-badge')) return;

    // Create enhanced span
    const before = text.substring(0, match.index);
    const after = text.substring(match.index + ticker.length);

    const wrapper = document.createElement('span');
    wrapper.className = 'ei-ticker-wrapper';

    const tickerSpan = document.createElement('span');
    tickerSpan.className = 'ei-ticker-badge';
    tickerSpan.style.cssText = `
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      color: #818cf8;
      padding: 1px 6px;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.9em;
      cursor: pointer;
      position: relative;
    `;
    tickerSpan.textContent = ticker;

    // Add hover tooltip
    tickerSpan.addEventListener('mouseenter', (e) => showTickerTooltip(e, ticker));
    tickerSpan.addEventListener('mouseleave', hideTickerTooltip);
    tickerSpan.addEventListener('click', () => openInPlatform(ticker));

    wrapper.appendChild(document.createTextNode(before));
    wrapper.appendChild(tickerSpan);
    wrapper.appendChild(document.createTextNode(after));

    parent.replaceChild(wrapper, textNode);
  }

  let tooltip = null;

  function showTickerTooltip(e, ticker) {
    const target = e.target;

    tooltip = document.createElement('div');
    tooltip.className = 'ei-ticker-tooltip';
    tooltip.style.cssText = `
      position: fixed;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      z-index: 100000;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 12px;
      color: #e2e8f0;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
      min-width: 200px;
    `;

    const rect = target.getBoundingClientRect();
    tooltip.style.left = `${rect.left}px`;
    tooltip.style.top = `${rect.bottom + 5}px`;

    tooltip.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="font-weight: 700; font-size: 14px; color: #818cf8;">${ticker}</span>
        <span style="background: #10b98133; color: #10b981; padding: 2px 6px; border-radius: 4px; font-size: 10px;">Tracked</span>
      </div>
      <div style="color: #94a3b8; font-size: 11px; margin-bottom: 8px;">
        Click to view full intelligence report
      </div>
      <div style="display: flex; gap: 6px;">
        <a href="${PLATFORM_URL}/stock?symbol=${ticker}" target="_blank"
           style="flex: 1; background: #6366f1; color: white; padding: 6px 10px; border-radius: 4px; text-align: center; text-decoration: none; font-size: 11px; font-weight: 600;">
          Stock Analysis
        </a>
        <a href="${PLATFORM_URL}/intelligence?q=${ticker}" target="_blank"
           style="flex: 1; background: #1e293b; color: #e2e8f0; padding: 6px 10px; border-radius: 4px; text-align: center; text-decoration: none; font-size: 11px; font-weight: 600;">
          Intelligence
        </a>
      </div>
    `;

    document.body.appendChild(tooltip);
  }

  function hideTickerTooltip() {
    if (tooltip) {
      tooltip.remove();
      tooltip = null;
    }
  }

  function openInPlatform(ticker) {
    window.open(`${PLATFORM_URL}/stock?symbol=${ticker}`, '_blank');
  }

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
