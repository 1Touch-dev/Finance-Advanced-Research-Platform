"""
Tests for Comments & Annotations API (Band C #47)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Service Unit Tests ────────────────────────────────────────────────────────


class TestEnums:
    """Test enum definitions."""

    def test_entity_type_values(self):
        """EntityType has expected values."""
        from app.services.comments_service import EntityType

        assert EntityType.STOCK.value == "stock"
        assert EntityType.FILING.value == "filing"
        assert EntityType.REPORT.value == "report"

    def test_document_type_values(self):
        """DocumentType has expected values."""
        from app.services.comments_service import DocumentType

        assert DocumentType.FILING.value == "filing"
        assert DocumentType.TRANSCRIPT.value == "transcript"

    def test_visibility_values(self):
        """Visibility has expected values."""
        from app.services.comments_service import Visibility

        assert Visibility.PRIVATE.value == "private"
        assert Visibility.TEAM.value == "team"
        assert Visibility.PUBLIC.value == "public"

    def test_reaction_type_values(self):
        """ReactionType has expected values."""
        from app.services.comments_service import ReactionType

        assert ReactionType.LIKE.value == "like"
        assert ReactionType.INSIGHTFUL.value == "insightful"
        assert ReactionType.DISAGREE.value == "disagree"

    def test_annotation_color_values(self):
        """AnnotationColor has expected values."""
        from app.services.comments_service import AnnotationColor

        assert AnnotationColor.YELLOW.value == "yellow"
        assert AnnotationColor.RED.value == "red"


class TestCommentData:
    """Test CommentData dataclass."""

    def test_to_dict(self):
        """CommentData serializes correctly."""
        from app.services.comments_service import (
            CommentData,
            EntityType,
            Visibility,
        )
        from datetime import datetime

        comment = CommentData(
            comment_id=1,
            user_id="user123",
            user_name="Test User",
            entity_type=EntityType.STOCK,
            entity_id="AAPL",
            content="This is a test comment",
            parent_id=None,
            visibility=Visibility.PRIVATE,
            is_edited=False,
            reply_count=0,
            reactions={},
            created_at=datetime.now(),
            updated_at=None,
        )

        data = comment.to_dict()
        assert data["comment_id"] == 1
        assert data["entity_type"] == "stock"
        assert data["content"] == "This is a test comment"


class TestAnnotationData:
    """Test AnnotationData dataclass."""

    def test_to_dict(self):
        """AnnotationData serializes correctly."""
        from app.services.comments_service import (
            AnnotationData,
            DocumentType,
            Visibility,
            AnnotationColor,
        )
        from datetime import datetime

        annotation = AnnotationData(
            annotation_id=1,
            user_id="user123",
            document_type=DocumentType.FILING,
            document_id="doc123",
            start_offset=100,
            end_offset=200,
            selected_text="This is important",
            note="Key metric",
            color=AnnotationColor.YELLOW,
            tags=["risk", "important"],
            visibility=Visibility.PRIVATE,
            created_at=datetime.now(),
            updated_at=None,
        )

        data = annotation.to_dict()
        assert data["annotation_id"] == 1
        assert data["document_type"] == "filing"
        assert data["position"]["start"] == 100
        assert data["position"]["end"] == 200


class TestCommentServiceFunctions:
    """Test comment service functions."""

    def test_create_comment(self):
        """create_comment creates a comment."""
        from app.services.comments_service import (
            create_comment,
            EntityType,
            Visibility,
        )

        comment = create_comment(
            user_id="user123",
            entity_type=EntityType.STOCK,
            entity_id="AAPL",
            content="Test comment",
            user_name="Test User",
        )

        assert comment.user_id == "user123"
        assert comment.entity_type == EntityType.STOCK
        assert comment.content == "Test comment"

    def test_get_comment(self):
        """get_comment retrieves a comment."""
        from app.services.comments_service import (
            create_comment,
            get_comment,
            EntityType,
        )

        comment = create_comment(
            user_id="user456",
            entity_type=EntityType.FILING,
            entity_id="filing123",
            content="Another test",
        )

        retrieved = get_comment(comment.comment_id)
        assert retrieved is not None
        assert retrieved.content == "Another test"

    def test_update_comment(self):
        """update_comment updates content."""
        from app.services.comments_service import (
            create_comment,
            update_comment,
            EntityType,
        )

        comment = create_comment(
            user_id="user789",
            entity_type=EntityType.STOCK,
            entity_id="MSFT",
            content="Original content",
        )

        updated = update_comment(
            comment_id=comment.comment_id,
            user_id="user789",
            content="Updated content",
        )

        assert updated is not None
        assert updated.content == "Updated content"
        assert updated.is_edited is True

    def test_update_comment_wrong_user(self):
        """update_comment rejects wrong user."""
        from app.services.comments_service import (
            create_comment,
            update_comment,
            EntityType,
        )

        comment = create_comment(
            user_id="author123",
            entity_type=EntityType.STOCK,
            entity_id="GOOGL",
            content="Test content",
        )

        with pytest.raises(ValueError):
            update_comment(
                comment_id=comment.comment_id,
                user_id="other_user",
                content="Hacked!",
            )

    def test_delete_comment(self):
        """delete_comment soft-deletes a comment."""
        from app.services.comments_service import (
            create_comment,
            delete_comment,
            get_comment,
            EntityType,
        )

        comment = create_comment(
            user_id="deleter123",
            entity_type=EntityType.STOCK,
            entity_id="META",
            content="To be deleted",
        )

        success = delete_comment(comment.comment_id, "deleter123")
        assert success is True

        # Should not be retrievable after deletion
        retrieved = get_comment(comment.comment_id)
        assert retrieved is None

    def test_add_reaction(self):
        """add_reaction adds a reaction."""
        from app.services.comments_service import (
            create_comment,
            add_reaction,
            get_comment,
            EntityType,
            ReactionType,
        )

        comment = create_comment(
            user_id="reactor123",
            entity_type=EntityType.STOCK,
            entity_id="AMZN",
            content="React to this",
        )

        reaction = add_reaction(
            comment_id=comment.comment_id,
            user_id="liker123",
            reaction_type=ReactionType.LIKE,
        )

        assert reaction.reaction_type == ReactionType.LIKE

        # Check reaction count
        updated = get_comment(comment.comment_id)
        assert updated is not None
        assert "like" in updated.reactions

    def test_remove_reaction(self):
        """remove_reaction removes a reaction."""
        from app.services.comments_service import (
            create_comment,
            add_reaction,
            remove_reaction,
            EntityType,
            ReactionType,
        )

        comment = create_comment(
            user_id="owner123",
            entity_type=EntityType.STOCK,
            entity_id="NVDA",
            content="Remove reaction test",
        )

        add_reaction(
            comment_id=comment.comment_id,
            user_id="liker456",
            reaction_type=ReactionType.LIKE,
        )

        success = remove_reaction(comment.comment_id, "liker456")
        assert success is True


class TestAnnotationServiceFunctions:
    """Test annotation service functions."""

    def test_create_annotation(self):
        """create_annotation creates an annotation."""
        from app.services.comments_service import (
            create_annotation,
            DocumentType,
            AnnotationColor,
        )

        annotation = create_annotation(
            user_id="annotator123",
            document_type=DocumentType.FILING,
            document_id="10k-aapl-2025",
            start_offset=100,
            end_offset=200,
            selected_text="Revenue increased 15%",
            note="Key growth metric",
            color=AnnotationColor.GREEN,
            tags=["revenue", "growth"],
        )

        assert annotation.user_id == "annotator123"
        assert annotation.start_offset == 100
        assert annotation.end_offset == 200

    def test_get_annotation(self):
        """get_annotation retrieves an annotation."""
        from app.services.comments_service import (
            create_annotation,
            get_annotation,
            DocumentType,
        )

        annotation = create_annotation(
            user_id="user999",
            document_type=DocumentType.TRANSCRIPT,
            document_id="transcript123",
            start_offset=50,
            end_offset=100,
        )

        retrieved = get_annotation(annotation.annotation_id)
        assert retrieved is not None
        assert retrieved.document_id == "transcript123"

    def test_update_annotation(self):
        """update_annotation updates an annotation."""
        from app.services.comments_service import (
            create_annotation,
            update_annotation,
            DocumentType,
            AnnotationColor,
        )

        annotation = create_annotation(
            user_id="editor123",
            document_type=DocumentType.REPORT,
            document_id="report456",
            start_offset=0,
            end_offset=50,
            note="Original note",
        )

        updated = update_annotation(
            annotation_id=annotation.annotation_id,
            user_id="editor123",
            note="Updated note",
            color=AnnotationColor.BLUE,
        )

        assert updated is not None
        assert updated.note == "Updated note"
        assert updated.color == AnnotationColor.BLUE

    def test_delete_annotation(self):
        """delete_annotation removes an annotation."""
        from app.services.comments_service import (
            create_annotation,
            delete_annotation,
            get_annotation,
            DocumentType,
        )

        annotation = create_annotation(
            user_id="remover123",
            document_type=DocumentType.NEWS,
            document_id="news789",
            start_offset=10,
            end_offset=20,
        )

        success = delete_annotation(annotation.annotation_id, "remover123")
        assert success is True

        retrieved = get_annotation(annotation.annotation_id)
        assert retrieved is None


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestReferenceEndpoints:
    """Test reference data endpoints."""

    def test_list_entity_types(self):
        """GET /comments/types/entity-types returns types."""
        response = client.get("/comments/types/entity-types")
        assert response.status_code == 200
        data = response.json()
        assert "entity_types" in data
        assert len(data["entity_types"]) > 0

    def test_list_document_types(self):
        """GET /comments/types/document-types returns types."""
        response = client.get("/comments/types/document-types")
        assert response.status_code == 200
        data = response.json()
        assert "document_types" in data

    def test_list_visibility_levels(self):
        """GET /comments/types/visibility-levels returns levels."""
        response = client.get("/comments/types/visibility-levels")
        assert response.status_code == 200
        data = response.json()
        assert "visibility_levels" in data

    def test_list_reaction_types(self):
        """GET /comments/types/reaction-types returns types."""
        response = client.get("/comments/types/reaction-types")
        assert response.status_code == 200
        data = response.json()
        assert "reaction_types" in data

    def test_list_annotation_colors(self):
        """GET /comments/types/annotation-colors returns colors."""
        response = client.get("/comments/types/annotation-colors")
        assert response.status_code == 200
        data = response.json()
        assert "annotation_colors" in data


class TestCommentsAPI:
    """Test comments API endpoints."""

    def test_create_comment(self):
        """POST /comments creates a comment."""
        response = client.post(
            "/comments",
            params={
                "user_id": "apiuser1",
                "entity_type": "stock",
                "entity_id": "AAPL",
                "content": "API test comment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # user_id is taken from the JWT token (not the query param), so we
        # only verify it is a non-empty string — its exact value depends on
        # which registered user the test client is authenticated as.
        assert isinstance(data["user_id"], str) and data["user_id"]
        assert data["content"] == "API test comment"

    def test_create_comment_invalid_entity_type(self):
        """POST /comments rejects invalid entity type."""
        response = client.post(
            "/comments",
            params={
                "user_id": "apiuser2",
                "entity_type": "invalid",
                "entity_id": "AAPL",
                "content": "Test",
            },
        )
        assert response.status_code == 400

    def test_get_entity_comments(self):
        """GET /comments/entity/{type}/{id} returns comments."""
        # Create a comment first
        client.post(
            "/comments",
            params={
                "user_id": "apiuser3",
                "entity_type": "stock",
                "entity_id": "MSFT",
                "content": "Comment for retrieval",
            },
        )

        response = client.get("/comments/entity/stock/MSFT")
        assert response.status_code == 200
        data = response.json()
        assert "threads" in data

    def test_get_entity_comment_stats(self):
        """GET /comments/entity/{type}/{id}/stats returns stats."""
        response = client.get("/comments/entity/stock/AAPL/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_comments" in data
        assert "reaction_breakdown" in data

    def test_add_reaction(self):
        """POST /comments/{id}/react adds a reaction."""
        # Create a comment
        create_resp = client.post(
            "/comments",
            params={
                "user_id": "apiuser4",
                "entity_type": "stock",
                "entity_id": "GOOGL",
                "content": "Like this",
            },
        )
        comment_id = create_resp.json()["comment_id"]

        # Add reaction
        response = client.post(
            f"/comments/{comment_id}/react",
            params={
                "user_id": "liker_api",
                "reaction_type": "like",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reaction_type"] == "like"

    def test_add_reaction_invalid_type(self):
        """POST /comments/{id}/react rejects invalid reaction type."""
        response = client.post(
            "/comments/1/react",
            params={
                "user_id": "user1",
                "reaction_type": "love",  # Invalid
            },
        )
        assert response.status_code == 400


class TestAnnotationsAPI:
    """Test annotations API endpoints."""

    def test_create_annotation(self):
        """POST /annotations creates an annotation."""
        response = client.post(
            "/annotations",
            params={
                "user_id": "annotator_api",
                "document_type": "filing",
                "document_id": "10k-test",
                "start_offset": 100,
                "end_offset": 200,
                "selected_text": "Important text",
                "note": "My note",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # user_id comes from the JWT token, not the query param
        assert isinstance(data["user_id"], str) and data["user_id"]
        assert data["position"]["start"] == 100

    def test_create_annotation_invalid_offsets(self):
        """POST /annotations rejects invalid offsets."""
        response = client.post(
            "/annotations",
            params={
                "user_id": "user1",
                "document_type": "filing",
                "document_id": "test",
                "start_offset": 200,
                "end_offset": 100,  # End before start
            },
        )
        assert response.status_code == 400

    def test_create_annotation_invalid_document_type(self):
        """POST /annotations rejects invalid document type."""
        response = client.post(
            "/annotations",
            params={
                "user_id": "user1",
                "document_type": "invalid",
                "document_id": "test",
                "start_offset": 0,
                "end_offset": 10,
            },
        )
        assert response.status_code == 400

    def test_get_document_annotations(self):
        """GET /annotations/document/{type}/{id} returns annotations."""
        # Create an annotation first
        client.post(
            "/annotations",
            params={
                "user_id": "doc_annotator",
                "document_type": "transcript",
                "document_id": "earnings-call-123",
                "start_offset": 50,
                "end_offset": 100,
            },
        )

        response = client.get("/annotations/document/transcript/earnings-call-123")
        assert response.status_code == 200
        data = response.json()
        assert "annotations" in data

    def test_get_user_annotations(self):
        """GET /annotations/user returns user's annotations."""
        response = client.get("/annotations/user?user_id=annotator_api")
        assert response.status_code == 200
        data = response.json()
        assert "annotations" in data
        # user_id is resolved from JWT token, not the query param
        assert isinstance(data["user_id"], str) and data["user_id"]

    def test_update_annotation(self):
        """PUT /annotations/{id} updates an annotation."""
        # Create annotation
        create_resp = client.post(
            "/annotations",
            params={
                "user_id": "updater_api",
                "document_type": "report",
                "document_id": "report-456",
                "start_offset": 0,
                "end_offset": 50,
                "note": "Original",
            },
        )
        annotation_id = create_resp.json()["annotation_id"]

        # Update it
        response = client.put(
            f"/annotations/{annotation_id}",
            params={
                "user_id": "updater_api",
                "note": "Updated note",
                "color": "blue",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["note"] == "Updated note"
        assert data["color"] == "blue"

    def test_delete_annotation(self):
        """DELETE /annotations/{id} deletes an annotation."""
        # Create annotation
        create_resp = client.post(
            "/annotations",
            params={
                "user_id": "deleter_api",
                "document_type": "news",
                "document_id": "news-789",
                "start_offset": 10,
                "end_offset": 20,
            },
        )
        annotation_id = create_resp.json()["annotation_id"]

        # Delete it
        response = client.delete(
            f"/annotations/{annotation_id}",
            params={"user_id": "deleter_api"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
