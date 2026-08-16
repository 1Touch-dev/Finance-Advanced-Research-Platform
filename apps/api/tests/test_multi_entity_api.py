"""
Tests for app.api.entities_multi API endpoints (Band B #18)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints for:
  - /entities/multi/ - Entity discovery and filtering
  - /entities/multi/sectors - List sectors
  - /entities/multi/industries - List industries
  - /entities/multi/by-sector/{sector} - Get entities by sector
  - /entities/multi/by-industry/{industry} - Get entities by industry
  - /entities/multi/by-theme/{theme} - Get entities by theme
  - /entities/multi/supply-chain/{ticker} - Supply chain analysis
  - /entities/multi/relationships/{ticker} - Entity relationships
  - /entities/multi/corpora - Thematic corpora management
  - /entities/multi/analyze/* - Cross-entity analysis
  - /entities/multi/compare - Entity comparison
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -- Entity Discovery Tests ---------------------------------------------------

class TestEntityDiscovery:
    """Tests for entity listing and search."""

    def test_list_all_entities(self):
        """List all entities without filters."""
        response = client.get("/entities/multi/")
        assert response.status_code == 200

        data = response.json()
        assert "entities" in data
        assert "total" in data
        assert data["total"] > 0

    def test_list_entities_by_sector(self):
        """Filter entities by sector."""
        response = client.get("/entities/multi/?sector=technology")
        assert response.status_code == 200

        data = response.json()
        assert "entities" in data
        for entity in data["entities"]:
            assert entity["sector"] == "technology"

    def test_list_entities_by_industry(self):
        """Filter entities by industry."""
        response = client.get("/entities/multi/?industry=semiconductors")
        assert response.status_code == 200

        data = response.json()
        assert "entities" in data
        for entity in data["entities"]:
            assert entity["industry"] == "semiconductors"

    def test_list_entities_by_theme(self):
        """Filter entities by theme."""
        response = client.get("/entities/multi/?theme=AI")
        assert response.status_code == 200

        data = response.json()
        assert "entities" in data
        assert data["total"] > 0

    def test_list_entities_by_query(self):
        """Search entities by name or ticker."""
        response = client.get("/entities/multi/?query=nvidia")
        assert response.status_code == 200

        data = response.json()
        assert any("NVDA" in e["ticker"] or "nvidia" in e["name"].lower() for e in data["entities"])

    def test_list_entities_with_min_market_cap(self):
        """Filter by minimum market cap."""
        response = client.get("/entities/multi/?min_market_cap=500000000000")
        assert response.status_code == 200

        data = response.json()
        for entity in data["entities"]:
            assert entity["market_cap"] >= 500000000000

    def test_invalid_sector_returns_400(self):
        """Invalid sector returns 400."""
        response = client.get("/entities/multi/?sector=invalid_sector")
        assert response.status_code == 400

    def test_invalid_industry_returns_400(self):
        """Invalid industry returns 400."""
        response = client.get("/entities/multi/?industry=invalid_industry")
        assert response.status_code == 400


# -- Reference Data Tests -----------------------------------------------------

class TestReferenceData:
    """Tests for sectors and industries listings."""

    def test_list_sectors(self):
        """List all sectors."""
        response = client.get("/entities/multi/sectors")
        assert response.status_code == 200

        data = response.json()
        assert "sectors" in data
        assert len(data["sectors"]) > 0

        sector = data["sectors"][0]
        assert "value" in sector
        assert "name" in sector

    def test_list_industries(self):
        """List all industries."""
        response = client.get("/entities/multi/industries")
        assert response.status_code == 200

        data = response.json()
        assert "industries" in data
        assert len(data["industries"]) > 0

        industry = data["industries"][0]
        assert "value" in industry
        assert "name" in industry

    def test_sectors_include_expected(self):
        """Sectors include expected values."""
        response = client.get("/entities/multi/sectors")
        data = response.json()

        sector_values = [s["value"] for s in data["sectors"]]
        assert "technology" in sector_values
        assert "healthcare" in sector_values
        assert "financials" in sector_values

    def test_industries_include_expected(self):
        """Industries include expected values."""
        response = client.get("/entities/multi/industries")
        data = response.json()

        industry_values = [i["value"] for i in data["industries"]]
        assert "semiconductors" in industry_values
        assert "software" in industry_values


# -- Sector/Industry/Theme Queries --------------------------------------------

class TestCategoricalQueries:
    """Tests for categorical entity queries."""

    def test_get_by_sector(self):
        """Get entities by sector."""
        response = client.get("/entities/multi/by-sector/technology")
        assert response.status_code == 200

        data = response.json()
        assert "sector" in data
        assert "entities" in data
        assert "total" in data
        assert data["sector"] == "technology"

    def test_get_by_sector_invalid(self):
        """Invalid sector returns 400."""
        response = client.get("/entities/multi/by-sector/invalid")
        assert response.status_code == 400

    def test_get_by_industry(self):
        """Get entities by industry."""
        response = client.get("/entities/multi/by-industry/semiconductors")
        assert response.status_code == 200

        data = response.json()
        assert "industry" in data
        assert "entities" in data
        assert data["industry"] == "semiconductors"

    def test_get_by_industry_invalid(self):
        """Invalid industry returns 400."""
        response = client.get("/entities/multi/by-industry/invalid")
        assert response.status_code == 400

    def test_get_by_theme(self):
        """Get entities by theme."""
        response = client.get("/entities/multi/by-theme/AI")
        assert response.status_code == 200

        data = response.json()
        assert "theme" in data
        assert "entities" in data
        assert "total" in data

    def test_get_by_theme_gpu(self):
        """Get entities with GPU theme."""
        response = client.get("/entities/multi/by-theme/GPU")
        assert response.status_code == 200

        data = response.json()
        # NVDA should be in results
        tickers = [e["ticker"] for e in data["entities"]]
        assert "NVDA" in tickers


# -- Supply Chain Tests -------------------------------------------------------

class TestSupplyChain:
    """Tests for supply chain analysis."""

    def test_supply_chain_returns_200(self):
        """Supply chain endpoint returns 200."""
        response = client.get("/entities/multi/supply-chain/NVDA")
        assert response.status_code == 200

    def test_supply_chain_structure(self):
        """Supply chain has expected structure."""
        response = client.get("/entities/multi/supply-chain/AAPL")
        data = response.json()

        assert "focal_ticker" in data
        assert "focal_name" in data
        assert "nodes" in data
        assert "total_suppliers" in data
        assert "total_customers" in data
        assert "concentration_score" in data
        assert "supply_chain_risk_score" in data
        assert "key_risks" in data
        assert "geographic_exposure" in data

    def test_supply_chain_nodes(self):
        """Supply chain nodes have expected structure."""
        response = client.get("/entities/multi/supply-chain/NVDA")
        data = response.json()

        if data["nodes"]:
            node = data["nodes"][0]
            assert "ticker" in node
            assert "name" in node
            assert "tier" in node
            assert "relationship_type" in node
            assert "concentration_risk" in node

    def test_supply_chain_unknown_ticker(self):
        """Unknown ticker returns 404."""
        response = client.get("/entities/multi/supply-chain/UNKNOWN_TICKER")
        assert response.status_code == 404


# -- Relationships Tests ------------------------------------------------------

class TestRelationships:
    """Tests for entity relationships."""

    def test_relationships_returns_200(self):
        """Relationships endpoint returns 200."""
        response = client.get("/entities/multi/relationships/NVDA")
        assert response.status_code == 200

    def test_relationships_structure(self):
        """Relationships have expected structure."""
        response = client.get("/entities/multi/relationships/AAPL")
        data = response.json()

        assert "ticker" in data
        assert "company_name" in data
        assert "relationships" in data
        assert "total" in data

    def test_relationships_filter_by_type(self):
        """Filter relationships by type."""
        response = client.get("/entities/multi/relationships/NVDA?relationship_type=supplier")
        assert response.status_code == 200

        data = response.json()
        for rel in data["relationships"]:
            assert rel["relationship_type"] == "supplier"

    def test_relationships_invalid_type(self):
        """Invalid relationship type returns 400."""
        response = client.get("/entities/multi/relationships/NVDA?relationship_type=invalid")
        assert response.status_code == 400

    def test_relationships_unknown_ticker(self):
        """Unknown ticker returns 404."""
        response = client.get("/entities/multi/relationships/UNKNOWN_TICKER")
        assert response.status_code == 404


# -- Thematic Corpora Tests ---------------------------------------------------

class TestThematicCorpora:
    """Tests for thematic corpora management."""

    def test_list_corpora(self):
        """List all corpora."""
        response = client.get("/entities/multi/corpora")
        assert response.status_code == 200

        data = response.json()
        assert "corpora" in data
        assert "total" in data
        assert data["total"] > 0

    def test_corpora_structure(self):
        """Corpora have expected structure."""
        response = client.get("/entities/multi/corpora")
        data = response.json()

        corpus = data["corpora"][0]
        assert "id" in corpus
        assert "name" in corpus
        assert "description" in corpus
        assert "theme_keywords" in corpus
        assert "entities" in corpus

    def test_get_corpus_by_id(self):
        """Get specific corpus by ID."""
        response = client.get("/entities/multi/corpora/ai_leaders")
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["id"] == "ai_leaders"
        assert "entity_details" in data

    def test_get_corpus_not_found(self):
        """Unknown corpus returns 404."""
        response = client.get("/entities/multi/corpora/unknown_corpus")
        assert response.status_code == 404

    def test_create_corpus(self):
        """Create custom corpus."""
        response = client.post(
            "/entities/multi/corpora/create",
            params={
                "name": "Test Corpus",
                "description": "Test description",
                "tickers": "NVDA,AMD,INTC",
                "keywords": "test,chips",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "corpus" in data
        assert len(data["corpus"]["entities"]) == 3

    def test_create_corpus_invalid_tickers(self):
        """Create corpus with invalid tickers returns 400."""
        response = client.post(
            "/entities/multi/corpora/create",
            params={
                "name": "Invalid Corpus",
                "description": "Test",
                "tickers": "INVALID1,INVALID2",
            },
        )
        assert response.status_code == 400


# -- Thematic Analysis Tests --------------------------------------------------

class TestThematicAnalysis:
    """Tests for cross-entity thematic analysis."""

    def test_analyze_theme(self):
        """Analyze theme across entities."""
        response = client.get("/entities/multi/analyze/theme?theme=AI")
        assert response.status_code == 200

        data = response.json()
        assert "theme" in data
        assert "entities_analyzed" in data
        assert "exposure_scores" in data
        assert "exposure_rankings" in data
        assert "avg_exposure_score" in data

    def test_analyze_theme_with_tickers(self):
        """Analyze theme with specific tickers."""
        response = client.get("/entities/multi/analyze/theme?theme=cloud&tickers=MSFT,AMZN,GOOGL")
        assert response.status_code == 200

        data = response.json()
        assert set(data["entities_analyzed"]) == {"MSFT", "AMZN", "GOOGL"}

    def test_analyze_theme_with_corpus(self):
        """Analyze theme using corpus."""
        response = client.get("/entities/multi/analyze/theme?theme=AI&corpus_id=ai_leaders")
        assert response.status_code == 200

        data = response.json()
        assert len(data["entities_analyzed"]) > 0

    def test_analyze_theme_invalid_corpus(self):
        """Invalid corpus returns 400."""
        response = client.get("/entities/multi/analyze/theme?theme=AI&corpus_id=invalid")
        assert response.status_code == 400

    def test_analyze_theme_response_structure(self):
        """Theme analysis has complete structure."""
        response = client.get("/entities/multi/analyze/theme?theme=GPU&tickers=NVDA,AMD")
        data = response.json()

        assert "theme_description" in data
        assert "total_mentions" in data
        assert "sentiment_by_entity" in data
        assert "key_excerpts" in data
        assert "trend_direction" in data
        assert "risk_flags" in data
        assert "opportunity_flags" in data


# -- Entity Comparison Tests --------------------------------------------------

class TestEntityComparison:
    """Tests for entity comparison."""

    def test_compare_entities(self):
        """Compare multiple entities."""
        response = client.get("/entities/multi/compare?tickers=NVDA,AMD,INTC")
        assert response.status_code == 200

        data = response.json()
        assert "tickers" in data
        assert "metrics" in data
        assert "total_metrics" in data

    def test_compare_entities_structure(self):
        """Comparison metrics have expected structure."""
        response = client.get("/entities/multi/compare?tickers=MSFT,GOOGL")
        data = response.json()

        if data["metrics"]:
            metric = data["metrics"][0]
            assert "metric_name" in metric
            assert "metric_description" in metric
            assert "values" in metric
            assert "statistics" in metric
            assert "leader" in metric

    def test_compare_entities_with_specific_metrics(self):
        """Compare with specific metrics."""
        response = client.get("/entities/multi/compare?tickers=NVDA,AMD&metrics=market_cap")
        assert response.status_code == 200

        data = response.json()
        assert data["total_metrics"] >= 1

    def test_compare_entities_need_two(self):
        """Need at least 2 tickers to compare."""
        response = client.get("/entities/multi/compare?tickers=NVDA")
        assert response.status_code == 400

    def test_compare_statistics(self):
        """Comparison includes statistics."""
        response = client.get("/entities/multi/compare?tickers=AAPL,MSFT,GOOGL")
        data = response.json()

        for metric in data["metrics"]:
            stats = metric["statistics"]
            assert "mean" in stats
            assert "median" in stats
            assert "min" in stats
            assert "max" in stats


# -- Entity Profile Tests -----------------------------------------------------

class TestEntityProfile:
    """Tests for individual entity profiles."""

    def test_get_entity_profile(self):
        """Get entity profile."""
        response = client.get("/entities/multi/NVDA")
        assert response.status_code == 200

        data = response.json()
        assert "entity" in data
        assert "relationships" in data
        assert "relationship_summary" in data

    def test_entity_profile_structure(self):
        """Entity profile has expected structure."""
        response = client.get("/entities/multi/AAPL")
        data = response.json()

        entity = data["entity"]
        assert "ticker" in entity
        assert "name" in entity
        assert "sector" in entity
        assert "industry" in entity
        assert "market_cap" in entity
        assert "themes" in entity

    def test_entity_profile_relationships_summary(self):
        """Profile includes relationship summary."""
        response = client.get("/entities/multi/NVDA")
        data = response.json()

        summary = data["relationship_summary"]
        assert "suppliers" in summary
        assert "customers" in summary
        assert "competitors" in summary
        assert "partners" in summary

    def test_entity_profile_unknown_ticker(self):
        """Unknown ticker returns 404."""
        response = client.get("/entities/multi/UNKNOWN_TICKER")
        assert response.status_code == 404


# -- Sector Analysis Tests ----------------------------------------------------

class TestSectorAnalysis:
    """Tests for sector analysis."""

    def test_analyze_sector(self):
        """Analyze sector."""
        response = client.get("/entities/multi/analyze/sector/technology")
        assert response.status_code == 200

        data = response.json()
        assert "sector" in data
        assert "total_entities" in data
        assert "entities" in data
        assert "market_cap_breakdown" in data
        assert "industries" in data

    def test_analyze_sector_with_theme(self):
        """Analyze sector with theme."""
        response = client.get("/entities/multi/analyze/sector/technology?theme=AI")
        assert response.status_code == 200

        data = response.json()
        assert "theme_analysis" in data

    def test_analyze_sector_invalid(self):
        """Invalid sector returns 400."""
        response = client.get("/entities/multi/analyze/sector/invalid")
        assert response.status_code == 400

    def test_sector_market_cap_breakdown(self):
        """Sector analysis includes market cap breakdown."""
        response = client.get("/entities/multi/analyze/sector/technology")
        data = response.json()

        breakdown = data["market_cap_breakdown"]
        assert "mega" in breakdown
        assert "large" in breakdown
        assert "mid" in breakdown
        assert "small" in breakdown


# -- Service Tests ------------------------------------------------------------

class TestMultiEntityService:
    """Tests for the underlying multi_entity_service module."""

    def test_enums_exist(self):
        """Enums are properly defined."""
        from app.services.multi_entity_service import (
            Sector,
            Industry,
            RelationshipType,
        )

        assert Sector.TECHNOLOGY.value == "technology"
        assert Industry.SEMICONDUCTORS.value == "semiconductors"
        assert RelationshipType.SUPPLIER.value == "supplier"

    def test_dataclasses_exist(self):
        """Dataclasses are properly defined."""
        from app.services.multi_entity_service import (
            EntityProfile,
            EntityRelationship,
            ThematicCorpus,
            CrossEntityMetric,
            SupplyChainAnalysis,
            Sector,
            Industry,
        )

        # EntityProfile
        entity = EntityProfile(
            ticker="TEST",
            name="Test Corp",
            sector=Sector.TECHNOLOGY,
            industry=Industry.SOFTWARE,
        )
        assert entity.ticker == "TEST"

    def test_service_functions_exist(self):
        """Service functions are callable."""
        from app.services.multi_entity_service import (
            get_entity,
            get_entities_by_sector,
            get_entities_by_industry,
            get_entities_by_theme,
            search_entities,
            get_entity_relationships,
            get_supply_chain,
            get_thematic_corpus,
            list_thematic_corpora,
            create_custom_corpus,
            analyze_theme_across_entities,
            compare_entities_metrics,
        )

        assert callable(get_entity)
        assert callable(get_entities_by_sector)
        assert callable(search_entities)
        assert callable(get_supply_chain)
        assert callable(analyze_theme_across_entities)

    def test_serializers_exist(self):
        """Serializer functions exist."""
        from app.services.multi_entity_service import (
            entity_to_dict,
            relationship_to_dict,
            supply_chain_to_dict,
            corpus_to_dict,
            thematic_result_to_dict,
            metric_to_dict,
        )

        assert callable(entity_to_dict)
        assert callable(relationship_to_dict)
        assert callable(supply_chain_to_dict)


# -- Edge Cases ---------------------------------------------------------------

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_ticker_case_insensitive(self):
        """Ticker should be case insensitive."""
        r1 = client.get("/entities/multi/nvda")
        r2 = client.get("/entities/multi/NVDA")

        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_empty_query(self):
        """Empty query returns all entities."""
        response = client.get("/entities/multi/?query=")
        assert response.status_code == 200
        assert response.json()["total"] > 0

    def test_multiple_filters(self):
        """Multiple filters work together."""
        response = client.get("/entities/multi/?sector=technology&theme=AI")
        assert response.status_code == 200

        data = response.json()
        for entity in data["entities"]:
            assert entity["sector"] == "technology"

    def test_predefined_corpora_exist(self):
        """Predefined corpora are available."""
        response = client.get("/entities/multi/corpora")
        data = response.json()

        corpus_ids = [c["id"] for c in data["corpora"]]
        assert "ai_leaders" in corpus_ids
        assert "semiconductor_supply_chain" in corpus_ids
        assert "cloud_hyperscalers" in corpus_ids
