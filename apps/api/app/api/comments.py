"""
Comments & Annotations API (Band C #47)
────────────────────────────────────────────────────────────────────────────────
Endpoints:
- POST /comments - Create a comment
- GET /comments/{id} - Get a comment
- PUT /comments/{id} - Update a comment
- DELETE /comments/{id} - Delete a comment
- GET /comments/entity/{type}/{id} - Get comments for an entity
- GET /comments/entity/{type}/{id}/stats - Get comment statistics
- POST /comments/{id}/react - Add reaction to comment
- DELETE /comments/{id}/react - Remove reaction
- POST /annotations - Create an annotation
- GET /annotations/{id} - Get an annotation
- PUT /annotations/{id} - Update an annotation
- DELETE /annotations/{id} - Delete an annotation
- GET /annotations/document/{type}/{id} - Get annotations for a document
- GET /annotations/user - Get user's annotations
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
import logging

from app.auth.security import get_current_user

from app.services.comments_service import (
    # Comment functions
    create_comment,
    get_comment,
    update_comment,
    delete_comment,
    get_comments_for_entity,
    add_reaction,
    remove_reaction,
    get_comment_stats,
    # Annotation functions
    create_annotation,
    get_annotation,
    update_annotation,
    delete_annotation,
    get_annotations_for_document,
    get_user_annotations,
    # Enums
    EntityType,
    DocumentType,
    Visibility,
    ReactionType,
    AnnotationColor,
)

router = APIRouter(prefix="/comments", tags=["comments"])
logger = logging.getLogger(__name__)


# ── Reference Endpoints (MUST come before parameterized routes) ───────────────


@router.get("/types/entity-types")
def list_entity_types():
    """List available entity types for comments."""
    return {
        "entity_types": [
            {"value": t.value, "name": t.name}
            for t in EntityType
        ],
    }


@router.get("/types/document-types")
def list_document_types():
    """List available document types for annotations."""
    return {
        "document_types": [
            {"value": t.value, "name": t.name}
            for t in DocumentType
        ],
    }


@router.get("/types/visibility-levels")
def list_visibility_levels():
    """List available visibility levels."""
    return {
        "visibility_levels": [
            {"value": v.value, "name": v.name}
            for v in Visibility
        ],
    }


@router.get("/types/reaction-types")
def list_reaction_types():
    """List available reaction types."""
    return {
        "reaction_types": [
            {"value": r.value, "name": r.name}
            for r in ReactionType
        ],
    }


@router.get("/types/annotation-colors")
def list_annotation_colors():
    """List available annotation colors."""
    return {
        "annotation_colors": [
            {"value": c.value, "name": c.name}
            for c in AnnotationColor
        ],
    }


# ── Comment Endpoints ──────────────────────────────────────────────────────────


@router.post("")
def create_new_comment(
    user_id: Optional[str] = Query(None, description="User ID"),
    entity_type: str = Query(..., description="Entity type (stock, filing, report, etc.)"),
    entity_id: str = Query(..., description="Entity ID (ticker, document ID, etc.)"),
    content: str = Query(..., description="Comment content"),
    user_name: Optional[str] = Query(None, description="Display name"),
    parent_id: Optional[int] = Query(None, description="Parent comment ID (for replies)"),
    visibility: str = Query("private", description="Visibility: private, team, public"),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new comment (#47).

    Supports commenting on stocks, filings, reports, and other entities.
    Threading is supported via parent_id.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    # Parse entity type
    try:
        etype = EntityType(entity_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    # Parse visibility
    try:
        vis = Visibility(visibility.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid visibility: {visibility}")

    try:
        comment = create_comment(
            user_id=user_id,
            entity_type=etype,
            entity_id=entity_id,
            content=content,
            user_name=user_name,
            parent_id=parent_id,
            visibility=vis,
        )
        return comment.to_dict()

    except Exception as e:
        logger.error(f"Error creating comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@router.get("/entity/{entity_type}/{entity_id}")
def get_entity_comments(
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = Query(None, description="User ID for visibility filtering"),
    include_replies: bool = Query(True, description="Include reply threads"),
    limit: int = Query(50, ge=1, le=200, description="Maximum comments"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Get all comments for an entity (#47).

    Returns threaded comments with replies.
    """
    # Parse entity type
    try:
        etype = EntityType(entity_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    try:
        threads = get_comments_for_entity(
            entity_type=etype,
            entity_id=entity_id,
            user_id=user_id,
            include_replies=include_replies,
            limit=limit,
            offset=offset,
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "threads": [t.to_dict() for t in threads],
            "count": len(threads),
        }

    except Exception as e:
        logger.error(f"Error getting comments: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comments")


@router.get("/entity/{entity_type}/{entity_id}/stats")
def get_entity_comment_stats(
    entity_type: str,
    entity_id: str,
):
    """
    Get comment statistics for an entity (#47).

    Returns total comments, reactions, top commenters, etc.
    """
    # Parse entity type
    try:
        etype = EntityType(entity_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    try:
        stats = get_comment_stats(
            entity_type=etype,
            entity_id=entity_id,
        )
        return stats.to_dict()

    except Exception as e:
        logger.error(f"Error getting comment stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comment stats")


@router.get("/{comment_id}")
def get_single_comment(comment_id: int):
    """
    Get a single comment by ID (#47).
    """
    comment = get_comment(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return comment.to_dict()


@router.put("/{comment_id}")
def update_existing_comment(
    comment_id: int,
    user_id: Optional[str] = Query(None, description="User ID (must be author)"),
    content: str = Query(..., description="New comment content"),
    current_user: dict = Depends(get_current_user),
):
    """
    Update a comment (#47).

    Only the original author can edit their comment.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    try:
        comment = update_comment(
            comment_id=comment_id,
            user_id=user_id,
            content=content,
        )
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        return comment.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to update comment")


@router.delete("/{comment_id}")
def delete_existing_comment(
    comment_id: int,
    user_id: Optional[str] = Query(None, description="User ID (must be author)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a comment (#47).

    Only the original author can delete their comment.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    try:
        success = delete_comment(comment_id=comment_id, user_id=user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")

        return {"deleted": True, "comment_id": comment_id}

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete comment")


@router.post("/{comment_id}/react")
def add_comment_reaction(
    comment_id: int,
    user_id: Optional[str] = Query(None, description="User ID"),
    reaction_type: str = Query(..., description="Reaction type: like, insightful, disagree, question"),
    current_user: dict = Depends(get_current_user),
):
    """
    Add a reaction to a comment (#47).

    If user already has a reaction, it's updated to the new type.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    # Parse reaction type
    try:
        rtype = ReactionType(reaction_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid reaction type: {reaction_type}")

    try:
        reaction = add_reaction(
            comment_id=comment_id,
            user_id=user_id,
            reaction_type=rtype,
        )
        return reaction.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding reaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to add reaction")


@router.delete("/{comment_id}/react")
def remove_comment_reaction(
    comment_id: int,
    user_id: Optional[str] = Query(None, description="User ID"),
    current_user: dict = Depends(get_current_user),
):
    """
    Remove user's reaction from a comment (#47).
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    try:
        success = remove_reaction(comment_id=comment_id, user_id=user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Reaction not found")

        return {"removed": True, "comment_id": comment_id}

    except Exception as e:
        logger.error(f"Error removing reaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove reaction")


# ── Annotations Router ─────────────────────────────────────────────────────────


annotations_router = APIRouter(prefix="/annotations", tags=["annotations"])


@annotations_router.post("")
def create_new_annotation(
    user_id: Optional[str] = Query(None, description="User ID"),
    document_type: str = Query(..., description="Document type (filing, report, transcript, news)"),
    document_id: str = Query(..., description="Document ID"),
    start_offset: int = Query(..., ge=0, description="Start character offset"),
    end_offset: int = Query(..., description="End character offset"),
    selected_text: Optional[str] = Query(None, description="The highlighted text"),
    note: Optional[str] = Query(None, description="User's note"),
    color: str = Query("yellow", description="Highlight color"),
    tags: Optional[List[str]] = Query(None, description="Tags for organization"),
    visibility: str = Query("private", description="Visibility: private, team, public"),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new annotation (#47).

    Annotations highlight text in documents with optional notes.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    # Validate offsets
    if end_offset <= start_offset:
        raise HTTPException(status_code=400, detail="end_offset must be greater than start_offset")

    # Parse document type
    try:
        dtype = DocumentType(document_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")

    # Parse color
    try:
        acolor = AnnotationColor(color.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid color: {color}")

    # Parse visibility
    try:
        vis = Visibility(visibility.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid visibility: {visibility}")

    try:
        annotation = create_annotation(
            user_id=user_id,
            document_type=dtype,
            document_id=document_id,
            start_offset=start_offset,
            end_offset=end_offset,
            selected_text=selected_text,
            note=note,
            color=acolor,
            tags=tags,
            visibility=vis,
        )
        return annotation.to_dict()

    except Exception as e:
        logger.error(f"Error creating annotation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create annotation")


@annotations_router.get("/document/{document_type}/{document_id}")
def get_document_annotations(
    document_type: str,
    document_id: str,
    user_id: Optional[str] = Query(None, description="User ID for visibility filtering"),
):
    """
    Get all annotations for a document (#47).

    Returns annotations sorted by position in document.
    """
    # Parse document type
    try:
        dtype = DocumentType(document_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")

    try:
        annotations = get_annotations_for_document(
            document_type=dtype,
            document_id=document_id,
            user_id=user_id,
        )

        return {
            "document_type": document_type,
            "document_id": document_id,
            "annotations": [a.to_dict() for a in annotations],
            "count": len(annotations),
        }

    except Exception as e:
        logger.error(f"Error getting annotations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get annotations")


@annotations_router.get("/user")
def get_user_annotation_list(
    user_id: Optional[str] = Query(None, description="User ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum annotations"),
):
    """
    Get all annotations by a user (#47).
    """
    # Parse document type if provided
    dtype = None
    if document_type:
        try:
            dtype = DocumentType(document_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")

    try:
        annotations = get_user_annotations(
            user_id=user_id,
            document_type=dtype,
            limit=limit,
        )

        return {
            "user_id": user_id,
            "annotations": [a.to_dict() for a in annotations],
            "count": len(annotations),
        }

    except Exception as e:
        logger.error(f"Error getting user annotations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user annotations")


@annotations_router.get("/{annotation_id}")
def get_single_annotation(annotation_id: int):
    """
    Get a single annotation by ID (#47).
    """
    annotation = get_annotation(annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    return annotation.to_dict()


@annotations_router.put("/{annotation_id}")
def update_existing_annotation(
    annotation_id: int,
    user_id: Optional[str] = Query(None, description="User ID (must be author)"),
    note: Optional[str] = Query(None, description="Updated note"),
    color: Optional[str] = Query(None, description="Updated color"),
    tags: Optional[List[str]] = Query(None, description="Updated tags"),
    current_user: dict = Depends(get_current_user),
):
    """
    Update an annotation (#47).

    Only the original author can edit their annotation.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    # Parse color if provided
    acolor = None
    if color:
        try:
            acolor = AnnotationColor(color.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid color: {color}")

    try:
        annotation = update_annotation(
            annotation_id=annotation_id,
            user_id=user_id,
            note=note,
            color=acolor,
            tags=tags,
        )
        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        return annotation.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating annotation: {e}")
        raise HTTPException(status_code=500, detail="Failed to update annotation")


@annotations_router.delete("/{annotation_id}")
def delete_existing_annotation(
    annotation_id: int,
    user_id: Optional[str] = Query(None, description="User ID (must be author)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete an annotation (#47).

    Only the original author can delete their annotation.
    """
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    try:
        success = delete_annotation(annotation_id=annotation_id, user_id=user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Annotation not found")

        return {"deleted": True, "annotation_id": annotation_id}

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting annotation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete annotation")
