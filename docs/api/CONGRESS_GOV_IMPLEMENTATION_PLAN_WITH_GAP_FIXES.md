# Congress.gov Legislation Upgrade — Implementation Plan with Gap Fixes

**Feature ID:** F-05  
**Date:** July 29, 2026  
**Lead Feedback:** 4 gaps identified - all addressed below

---

## ✅ Gap Fixes Integration

### Gap 1 Fix: Caching Strategy
**Recommendation:** 20-minute TTL cache for all Congress.gov calls

**Rationale:**
- Rate limit: 1,000 req/hr = ~16.6 req/min
- Average user session: 5-15 minutes
- Bill data updates: Every few hours (not real-time)
- **20-minute cache** balances freshness with rate limit protection

**Implementation:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

# Module-level cache with 20-min expiry
_congress_cache = {}
_cache_expiry = timedelta(minutes=20)

def _get_cached_or_fetch(cache_key, fetch_func, *args, **kwargs):
    """Cache wrapper with 20-min TTL"""
    now = datetime.utcnow()
    
    if cache_key in _congress_cache:
        data, timestamp = _congress_cache[cache_key]
        if now - timestamp < _cache_expiry:
            return data  # Return cached
    
    # Cache miss or expired - fetch fresh
    data = fetch_func(*args, **kwargs)
    _congress_cache[cache_key] = (data, now)
    return data
```

**Cache Keys:**
- Bill search: `bill_search_{query}_{from_date}_{to_date}`
- Bill details: `bill_{congress}_{type}_{number}`
- Politician legislation: `politician_leg_{bioguide_id}`
- Recent laws: `laws_{congress}`

**Cache Invalidation:**
- Automatic: 20-minute expiry
- Manual: Clear cache endpoint for admins (optional)

---

### Gap 2 Fix: Unit Test Plan

**Test File:** `tests/connectors/test_congress_gov.py`

#### Phase 1 Tests (Immediate Fix)
```python
import pytest
from app.connectors.gov_trading_connector import get_politician_profile

class TestCongressAPIKeyUsage:
    """Verify DEMO_KEY is replaced with real key"""
    
    def test_politician_profile_uses_real_api_key(self, monkeypatch):
        """Test that get_politician_profile uses CONGRESS_API_KEY not DEMO_KEY"""
        monkeypatch.setenv("CONGRESS_API_KEY", "test_key_12345")
        # Mock requests to verify key passed correctly
        # Assert "test_key_12345" in request params, not "DEMO_KEY"
        
    def test_politician_profile_falls_back_to_demo_key(self, monkeypatch):
        """Test fallback to DEMO_KEY if env var missing"""
        monkeypatch.delenv("CONGRESS_API_KEY", raising=False)
        # Assert "DEMO_KEY" used as fallback
```

#### Phase 2 Tests (New Functions)
```python
class TestBillSearch:
    def test_search_bills_returns_valid_data(self):
        """Test successful bill search"""
        results = search_bills("banking reform", from_date="2024-01-01")
        assert len(results) > 0
        assert "title" in results[0]
        assert "number" in results[0]
    
    def test_search_bills_empty_query_handled(self):
        """Test empty search query returns gracefully"""
        results = search_bills("")
        assert results == []
    
    def test_search_bills_no_results(self):
        """Test query with zero results"""
        results = search_bills("xyznonexistentbill12345")
        assert results == []
    
    def test_search_bills_rate_limit_handled(self, monkeypatch):
        """Test 429 rate limit error handled gracefully"""
        # Mock 429 response
        # Assert function returns [] with logged warning, no crash

class TestBillDetails:
    def test_get_bill_details_valid_bill(self):
        """Test fetching real bill details"""
        # Example: HR 1 from 118th Congress
        bill = get_bill_details(118, "hr", 1)
        assert bill is not None
        assert "title" in bill
        assert "sponsors" in bill
    
    def test_get_bill_details_invalid_bill_number(self):
        """Test invalid bill returns None gracefully"""
        bill = get_bill_details(118, "hr", 999999)
        assert bill is None
    
    def test_get_bill_details_cache_hit(self):
        """Test cached response returned on second call"""
        # First call - should hit API
        bill1 = get_bill_details(118, "hr", 1)
        # Second call - should return from cache
        bill2 = get_bill_details(118, "hr", 1)
        assert bill1 == bill2  # Same data

class TestRecentLaws:
    def test_get_recent_laws_returns_data(self):
        """Test recent laws endpoint"""
        laws = get_recent_laws(118)
        assert isinstance(laws, list)
        assert len(laws) > 0
    
    def test_get_recent_laws_invalid_congress(self):
        """Test invalid congress number"""
        laws = get_recent_laws(999)
        assert laws == []

class TestCommitteeBills:
    def test_get_committee_bills_valid_committee(self):
        """Test fetching bills from Senate Banking Committee"""
        bills = get_committee_bills("senate", "ssba")
        assert isinstance(bills, list)
    
    def test_get_committee_bills_invalid_committee(self):
        """Test invalid committee code"""
        bills = get_committee_bills("senate", "invalid")
        assert bills == []

class TestCRSReports:
    def test_get_crs_reports_returns_data(self):
        """Test CRS reports endpoint"""
        reports = get_crs_reports(limit=5)
        assert len(reports) <= 5
        assert "title" in reports[0] if reports else True

class TestErrorHandling:
    def test_network_timeout_handled(self, monkeypatch):
        """Test network timeout doesn't crash"""
        # Mock timeout exception
        # Assert function returns None/[] with logged error
    
    def test_malformed_json_handled(self, monkeypatch):
        """Test malformed API response"""
        # Mock invalid JSON
        # Assert function handles gracefully
```

**Test Coverage Target:** 85%+ for new functions

**Test Execution:**
```bash
# Run tests
pytest tests/connectors/test_congress_gov.py -v

# With coverage
pytest tests/connectors/test_congress_gov.py --cov=app.connectors.gov_trading_connector --cov-report=html
```

---

### Gap 3 Fix: Handoff Doc Correction

**File:** `docs/handoff/Finance_Platform_Handoff.md`  
**Location:** Line 281 (in API keys section)

**Current (INCORRECT):**
```markdown
| `CONGRESS_API_KEY` | Congress.gov | ✅ DEMO | Limited — needs paid key for full data |
```

**Corrected:**
```markdown
| `CONGRESS_API_KEY` | Congress.gov | ✅ Live | 1,000 req/hr — **free API** (no paid tier exists), full legislation data |
```

**Additional clarification to add:**
```markdown
> **Note:** Congress.gov is a **completely free** government API. There is no paid tier. 
> The "DEMO_KEY" is a public key with 30 req/hr limit for testing. 
> Our registered key (`CONGRESS_API_KEY`) provides 1,000 req/hr at no cost.
```

**Files to update:**
1. `docs/handoff/Finance_Platform_Handoff.md` - Line 281
2. `.env.example` - Add comment clarifying it's free
3. `docs/api/API_INTEGRATIONS_GUIDE.md` - Update Congress.gov section

---

### Gap 4 Fix: OS Import Verification

**File:** `apps/api/app/connectors/gov_trading_connector.py`

**Step 1: Verify import exists**
Check top of file (lines 1-20) for:
```python
import os
```

**Step 2a: If `os` already imported** ✅
- Proceed with Phase 1 fix as planned

**Step 2b: If `os` NOT imported** ⚠️
- Add import at top of file with other imports:

```python
# gov_trading_connector.py - Top of file
import os
import requests as req
from datetime import datetime, timedelta
# ... other imports
```

**Step 3: Use consistent pattern**
```python
# Get API key with fallback
congress_api_key = os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")

# Use in all Congress.gov API calls
params = {
    "api_key": congress_api_key,
    "format": "json",
    # ... other params
}
```

**Alternative approach (if `os` import conflicts exist):**
```python
# Use os.getenv() instead (same result)
congress_api_key = os.getenv("CONGRESS_API_KEY", "DEMO_KEY")
```

---

## 📋 Updated Implementation Plan

### Phase 1: Immediate Fix (30 minutes - extended from 15 min)

**Day 0 - Today:**

1. **Verify `os` import** (Gap 4 fix)
   - [ ] Check if `import os` exists in `gov_trading_connector.py`
   - [ ] Add if missing
   - [ ] Test import works

2. **Replace DEMO_KEY** (Original Phase 1)
   - [ ] Line 404: Replace `"DEMO_KEY"` with `congress_api_key`
   - [ ] Line 420: Replace `"DEMO_KEY"` with `congress_api_key`
   - [ ] Add `congress_api_key = os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")` at function start

3. **Add basic caching** (Gap 1 fix - simplified for Phase 1)
   - [ ] Add 20-minute TTL cache for politician legislation
   - [ ] Use existing connector cache pattern

4. **Update documentation** (Gap 3 fix)
   - [ ] Fix `Finance_Platform_Handoff.md` line 281
   - [ ] Update `.env.example` comment
   - [ ] Clarify Congress.gov is free

5. **Test Phase 1**
   - [ ] Run politician profile endpoint
   - [ ] Verify legislation data returns
   - [ ] Confirm real API key used (check logs)
   - [ ] Test cache works (second call faster)

**Phase 1 Verification:**
```bash
# Test politician profile
curl "http://localhost:3001/market/gov/politician/Pelosi"

# Should return legislation data (not empty [])
# Check logs for API key used (should NOT see "DEMO_KEY")
```

---

### Phase 2: Full Feature (2-3 days)

**Day 1: Core Functions + Tests**

Morning:
- [ ] Write `search_bills()` function
- [ ] Write unit tests for `search_bills()`
- [ ] Add 20-min cache to `search_bills()`
- [ ] Write `get_bill_details()` function
- [ ] Write unit tests for `get_bill_details()`

Afternoon:
- [ ] Write `get_recent_laws()` function
- [ ] Write unit tests for `get_recent_laws()`
- [ ] Add `/market/gov-trading/legislation/search` API endpoint
- [ ] Add `/market/gov-trading/legislation/laws/{congress}` API endpoint
- [ ] Manual test via API docs

**Day 2: Additional Functions + UI**

Morning:
- [ ] Write `get_committee_bills()` function
- [ ] Write `get_crs_reports()` function
- [ ] Write unit tests for both
- [ ] Add API endpoints for committee and CRS

Afternoon:
- [ ] Build `LegislationSearch` React component
- [ ] Wire up to `/gov-trading` page
- [ ] Add search input + results table
- [ ] Add bill status badges

**Day 3: Advanced Features + Polish**

Morning:
- [ ] Add `PoliticianVoteRecord` tab on politician page
- [ ] Add `get_bill_cosponsors()` function
- [ ] Wire up vote history data

Afternoon:
- [ ] Add `BillImpactBadge` on company deep-report page
- [ ] Full end-to-end testing
- [ ] Run all unit tests (target 85% coverage)
- [ ] Update all documentation
- [ ] Push PR for review

---

## 🧪 Comprehensive Test Plan (Gap 2 Implementation)

### Unit Tests: `tests/connectors/test_congress_gov.py`
- **Total test cases:** 18
- **Estimated time to write:** 3 hours
- **Coverage target:** 85%+

### Integration Tests: `tests/api/test_legislation_endpoints.py`
```python
class TestLegislationEndpoints:
    def test_search_endpoint_returns_200(self, client):
        """Test /legislation/search endpoint"""
        response = client.get("/market/gov-trading/legislation/search?query=banking")
        assert response.status_code == 200
        assert len(response.json()) > 0
    
    def test_bill_details_endpoint(self, client):
        """Test /legislation/bill endpoint"""
        response = client.get("/market/gov-trading/legislation/bill/118/hr/1")
        assert response.status_code == 200
        assert "title" in response.json()
    
    # ... more integration tests
```

### Manual Test Cases
```
Test Case 1: Search bills
  1. Go to /gov-trading
  2. Enter "AI regulation" in search
  3. Verify results appear within 2 seconds
  4. Verify at least 5 bills shown
  5. Click a bill → should show details

Test Case 2: View politician legislation
  1. Go to /gov-trading/politician/Pelosi
  2. Verify "Sponsored Bills" section shows data (not empty)
  3. Verify bills have title + status badge
  4. Click "View All Legislation" → should expand

Test Case 3: Cache verification
  1. Search "banking" → note response time
  2. Search "banking" again within 20 minutes
  3. Second search should be < 100ms (cached)
  4. Wait 21 minutes, search again
  5. Should be slow again (cache expired, fresh fetch)

Test Case 4: Rate limit handling
  1. Make 1,000+ requests rapidly (use script)
  2. Verify 1,001st request returns cached data or error (no crash)
  3. Verify error is logged properly
```

---

## 📊 Cache Performance Metrics

**Expected cache hit rate:** 60-80%

**Calculation:**
- Average user searches 2-3 popular queries ("banking", "crypto", "AI")
- 20-minute cache means 3 cache cycles per hour
- If 100 users search in 1 hour:
  - Without cache: 100 API calls
  - With cache (60% hit rate): 40 API calls + 60 cache hits
  - **API call reduction: 60%**

**Rate limit protection:**
- Limit: 1,000 req/hr = ~16.6 req/min
- With 60% cache hit rate: Supports ~40 searches/min (2,400 searches/hr)
- **Without cache:** Only supports 16 searches/min (960 searches/hr)

---

## ✅ Gap Resolution Checklist

Before PR submission, verify:

- [ ] **Gap 1:** Cache strategy implemented with 20-min TTL
- [ ] **Gap 1:** Cache hit/miss logging added
- [ ] **Gap 1:** Cache performance documented

- [ ] **Gap 2:** Unit test file created with 18+ tests
- [ ] **Gap 2:** All tests passing
- [ ] **Gap 2:** Coverage report shows 85%+

- [ ] **Gap 3:** `Finance_Platform_Handoff.md` line 281 corrected
- [ ] **Gap 3:** `.env.example` comment updated
- [ ] **Gap 3:** API guide updated

- [ ] **Gap 4:** `import os` verified in file
- [ ] **Gap 4:** All `os.environ.get()` calls working
- [ ] **Gap 4:** Fallback to DEMO_KEY tested

---

## 📈 Success Metrics

**Phase 1:**
- [ ] Politician profiles return legislation data (not empty `[]`)
- [ ] API key logs show real key used (not "DEMO_KEY")
- [ ] No 429 rate limit errors in logs

**Phase 2:**
- [ ] Bill search returns results in < 2 seconds
- [ ] Cache hit rate > 60%
- [ ] All 18+ unit tests passing
- [ ] Zero crashes from malformed API responses
- [ ] Documentation updated and accurate

---

## 🚀 Ready for Approval

This updated plan addresses all 4 gaps identified by your lead:
1. ✅ Caching strategy specified (20-min TTL)
2. ✅ Comprehensive unit test plan (18+ tests)
3. ✅ Handoff doc correction included
4. ✅ OS import verification step added

**Estimated Total Effort:**
- Phase 1: 30 minutes (was 15, now includes gap fixes)
- Phase 2: 2.5 days (includes test writing time)

---

*All gaps addressed. Ready for lead approval.*
