"""
Comments & Annotations Service (Band C #47)
────────────────────────────────────────────────────────────────────────────────
Provides:
  - Comment CRUD operations
  - Comment threading (replies)
  - Reactions (like, insightful, etc.)
  - Annotations (text highlights with notes)
  - Visibility controls (private, team, public)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, date


# ── Enums ──────────────────────────────────────────────────────────────────────


class EntityType(Enum):
    """Types of entities that can have comments."""
    STOCK = "stock"
    FILING = "filing"
    REPORT = "report"
    WATCHLIST = "watchlist"
    PORTFOLIO = "portfolio"
    TRANSCRIPT = "transcript"
    NEWS = "news"


class DocumentType(Enum):
    """Types of documents that can have annotations."""
    FILING = "filing"
    REPORT = "report"
    TRANSCRIPT = "transcript"
    NEWS = "news"


class Visibility(Enum):
    """Visibility levels for comments and annotations."""
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


class ReactionType(Enum):
    """Types of reactions on comments."""
    LIKE = "like"
    INSIGHTFUL = "insightful"
    DISAGREE = "disagree"
    QUESTION = "question"


class AnnotationColor(Enum):
    """Available annotation highlight colors."""
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    RED = "red"
    PURPLE = "purple"


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class CommentData:
    """Comment data structure."""
    comment_id: int
    user_id: str
    user_name: Optional[str]
    entity_type: EntityType
    entity_id: str
    content: str
    parent_id: Optional[int]
    visibility: Visibility
    is_edited: bool
    reply_count: int
    reactions: Dict[str, int]  # {reaction_type: count}
    created_at: datetime
    updated_at: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comment_id": self.comment_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "content": self.content,
            "parent_id": self.parent_id,
            "visibility": self.visibility.value,
            "is_edited": self.is_edited,
            "reply_count": self.reply_count,
            "reactions": self.reactions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class CommentThread:
    """Comment with its replies."""
    comment: CommentData
    replies: List[CommentData] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comment": self.comment.to_dict(),
            "replies": [r.to_dict() for r in self.replies],
            "total_replies": len(self.replies),
        }


@dataclass
class AnnotationData:
    """Annotation data structure."""
    annotation_id: int
    user_id: str
    document_type: DocumentType
    document_id: str
    start_offset: int
    end_offset: int
    selected_text: Optional[str]
    note: Optional[str]
    color: AnnotationColor
    tags: List[str]
    visibility: Visibility
    created_at: datetime
    updated_at: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "annotation_id": self.annotation_id,
            "user_id": self.user_id,
            "document_type": self.document_type.value,
            "document_id": self.document_id,
            "position": {
                "start": self.start_offset,
                "end": self.end_offset,
            },
            "selected_text": self.selected_text,
            "note": self.note,
            "color": self.color.value,
            "tags": self.tags,
            "visibility": self.visibility.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class UserReaction:
    """User's reaction to a comment."""
    reaction_id: int
    comment_id: int
    user_id: str
    reaction_type: ReactionType
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "reaction_id": self.reaction_id,
            "comment_id": self.comment_id,
            "user_id": self.user_id,
            "reaction_type": self.reaction_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class CommentStats:
    """Statistics for comments on an entity."""
    entity_type: EntityType
    entity_id: str
    total_comments: int
    total_reactions: int
    top_commenters: List[Dict[str, Any]]
    reaction_breakdown: Dict[str, int]
    recent_activity: List[CommentData]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "total_comments": self.total_comments,
            "total_reactions": self.total_reactions,
            "top_commenters": self.top_commenters,
            "reaction_breakdown": self.reaction_breakdown,
            "recent_activity": [c.to_dict() for c in self.recent_activity],
        }


# ── In-Memory Storage (for development/testing) ──────────────────────────────


_comments_store: Dict[int, Dict[str, Any]] = {}
_reactions_store: Dict[int, Dict[str, Any]] = {}
_annotations_store: Dict[int, Dict[str, Any]] = {}
_next_comment_id = 1
_next_reaction_id = 1
_next_annotation_id = 1


# ── Service Functions ──────────────────────────────────────────────────────────


def create_comment(
    user_id: str,
    entity_type: EntityType,
    entity_id: str,
    content: str,
    user_name: Optional[str] = None,
    parent_id: Optional[int] = None,
    visibility: Visibility = Visibility.PRIVATE,
) -> CommentData:
    """
    Create a new comment.

    Args:
        user_id: User creating the comment
        entity_type: Type of entity being commented on
        entity_id: ID of the entity (ticker, filing ID, etc.)
        content: Comment text
        user_name: Display name of user
        parent_id: ID of parent comment (for replies)
        visibility: Visibility level

    Returns:
        Created comment data
    """
    global _next_comment_id

    now = datetime.now()
    comment_id = _next_comment_id
    _next_comment_id += 1

    comment = {
        "comment_id": comment_id,
        "user_id": user_id,
        "user_name": user_name,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "content": content,
        "parent_id": parent_id,
        "visibility": visibility,
        "is_edited": False,
        "is_deleted": False,
        "created_at": now,
        "updated_at": None,
    }

    _comments_store[comment_id] = comment

    return CommentData(
        comment_id=comment_id,
        user_id=user_id,
        user_name=user_name,
        entity_type=entity_type,
        entity_id=entity_id,
        content=content,
        parent_id=parent_id,
        visibility=visibility,
        is_edited=False,
        reply_count=0,
        reactions={},
        created_at=now,
        updated_at=None,
    )


def get_comment(comment_id: int) -> Optional[CommentData]:
    """Get a single comment by ID."""
    comment = _comments_store.get(comment_id)
    if not comment or comment.get("is_deleted"):
        return None

    # Count replies
    reply_count = sum(
        1 for c in _comments_store.values()
        if c.get("parent_id") == comment_id and not c.get("is_deleted")
    )

    # Count reactions
    reactions: Dict[str, int] = {}
    for r in _reactions_store.values():
        if r.get("comment_id") == comment_id:
            rt = r["reaction_type"].value
            reactions[rt] = reactions.get(rt, 0) + 1

    return CommentData(
        comment_id=comment["comment_id"],
        user_id=comment["user_id"],
        user_name=comment["user_name"],
        entity_type=comment["entity_type"],
        entity_id=comment["entity_id"],
        content=comment["content"],
        parent_id=comment["parent_id"],
        visibility=comment["visibility"],
        is_edited=comment["is_edited"],
        reply_count=reply_count,
        reactions=reactions,
        created_at=comment["created_at"],
        updated_at=comment["updated_at"],
    )


def update_comment(
    comment_id: int,
    user_id: str,
    content: str,
) -> Optional[CommentData]:
    """
    Update a comment's content.

    Only the original author can update their comment.
    """
    comment = _comments_store.get(comment_id)
    if not comment or comment.get("is_deleted"):
        return None

    if comment["user_id"] != user_id:
        raise ValueError("Only the author can edit this comment")

    comment["content"] = content
    comment["is_edited"] = True
    comment["updated_at"] = datetime.now()

    return get_comment(comment_id)


def delete_comment(comment_id: int, user_id: str) -> bool:
    """
    Soft-delete a comment.

    Only the original author can delete their comment.
    """
    comment = _comments_store.get(comment_id)
    if not comment or comment.get("is_deleted"):
        return False

    if comment["user_id"] != user_id:
        raise ValueError("Only the author can delete this comment")

    comment["is_deleted"] = True
    comment["updated_at"] = datetime.now()
    return True


def get_comments_for_entity(
    entity_type: EntityType,
    entity_id: str,
    user_id: Optional[str] = None,
    include_replies: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> List[CommentThread]:
    """
    Get all comments for an entity.

    Args:
        entity_type: Type of entity
        entity_id: ID of entity
        user_id: If provided, filter by visibility accessible to this user
        include_replies: Whether to include reply threads
        limit: Maximum comments to return
        offset: Pagination offset

    Returns:
        List of comment threads
    """
    # Filter comments for this entity
    entity_comments = [
        c for c in _comments_store.values()
        if c["entity_type"] == entity_type
        and c["entity_id"] == entity_id
        and not c.get("is_deleted")
        and c.get("parent_id") is None  # Top-level only
    ]

    # Sort by created_at descending
    entity_comments.sort(key=lambda x: x["created_at"], reverse=True)

    # Apply pagination
    paginated = entity_comments[offset:offset + limit]

    threads = []
    for comment in paginated:
        comment_data = get_comment(comment["comment_id"])
        if not comment_data:
            continue

        replies = []
        if include_replies:
            # Get replies
            reply_comments = [
                c for c in _comments_store.values()
                if c.get("parent_id") == comment["comment_id"]
                and not c.get("is_deleted")
            ]
            reply_comments.sort(key=lambda x: x["created_at"])
            for rc in reply_comments:
                reply_data = get_comment(rc["comment_id"])
                if reply_data:
                    replies.append(reply_data)

        threads.append(CommentThread(comment=comment_data, replies=replies))

    return threads


def add_reaction(
    comment_id: int,
    user_id: str,
    reaction_type: ReactionType,
) -> UserReaction:
    """
    Add a reaction to a comment.

    If user already has a reaction, it's updated.
    """
    global _next_reaction_id

    comment = _comments_store.get(comment_id)
    if not comment or comment.get("is_deleted"):
        raise ValueError("Comment not found")

    # Check for existing reaction
    for reaction_id, r in _reactions_store.items():
        if r["comment_id"] == comment_id and r["user_id"] == user_id:
            # Update existing reaction
            r["reaction_type"] = reaction_type
            return UserReaction(
                reaction_id=reaction_id,
                comment_id=comment_id,
                user_id=user_id,
                reaction_type=reaction_type,
                created_at=r["created_at"],
            )

    # Create new reaction
    reaction_id = _next_reaction_id
    _next_reaction_id += 1
    now = datetime.now()

    _reactions_store[reaction_id] = {
        "reaction_id": reaction_id,
        "comment_id": comment_id,
        "user_id": user_id,
        "reaction_type": reaction_type,
        "created_at": now,
    }

    return UserReaction(
        reaction_id=reaction_id,
        comment_id=comment_id,
        user_id=user_id,
        reaction_type=reaction_type,
        created_at=now,
    )


def remove_reaction(comment_id: int, user_id: str) -> bool:
    """Remove user's reaction from a comment."""
    for reaction_id, r in list(_reactions_store.items()):
        if r["comment_id"] == comment_id and r["user_id"] == user_id:
            del _reactions_store[reaction_id]
            return True
    return False


def get_comment_stats(
    entity_type: EntityType,
    entity_id: str,
) -> CommentStats:
    """Get statistics for comments on an entity."""
    # Filter comments for this entity
    entity_comments = [
        c for c in _comments_store.values()
        if c["entity_type"] == entity_type
        and c["entity_id"] == entity_id
        and not c.get("is_deleted")
    ]

    # Count reactions
    comment_ids = {c["comment_id"] for c in entity_comments}
    reaction_breakdown: Dict[str, int] = {}
    total_reactions = 0
    for r in _reactions_store.values():
        if r["comment_id"] in comment_ids:
            rt = r["reaction_type"].value
            reaction_breakdown[rt] = reaction_breakdown.get(rt, 0) + 1
            total_reactions += 1

    # Top commenters
    commenter_counts: Dict[str, int] = {}
    for c in entity_comments:
        uid = c["user_id"]
        commenter_counts[uid] = commenter_counts.get(uid, 0) + 1

    top_commenters = [
        {"user_id": uid, "count": count}
        for uid, count in sorted(commenter_counts.items(), key=lambda x: -x[1])[:5]
    ]

    # Recent activity
    recent = sorted(entity_comments, key=lambda x: x["created_at"], reverse=True)[:5]
    recent_activity = [get_comment(c["comment_id"]) for c in recent]
    recent_activity = [c for c in recent_activity if c is not None]

    return CommentStats(
        entity_type=entity_type,
        entity_id=entity_id,
        total_comments=len(entity_comments),
        total_reactions=total_reactions,
        top_commenters=top_commenters,
        reaction_breakdown=reaction_breakdown,
        recent_activity=recent_activity,
    )


# ── Annotation Functions ───────────────────────────────────────────────────────


def create_annotation(
    user_id: str,
    document_type: DocumentType,
    document_id: str,
    start_offset: int,
    end_offset: int,
    selected_text: Optional[str] = None,
    note: Optional[str] = None,
    color: AnnotationColor = AnnotationColor.YELLOW,
    tags: Optional[List[str]] = None,
    visibility: Visibility = Visibility.PRIVATE,
) -> AnnotationData:
    """
    Create a new annotation.

    Args:
        user_id: User creating the annotation
        document_type: Type of document
        document_id: ID of the document
        start_offset: Start character offset in document
        end_offset: End character offset in document
        selected_text: The highlighted text
        note: User's note
        color: Highlight color
        tags: Tags for organization
        visibility: Visibility level

    Returns:
        Created annotation data
    """
    global _next_annotation_id

    now = datetime.now()
    annotation_id = _next_annotation_id
    _next_annotation_id += 1

    annotation = {
        "annotation_id": annotation_id,
        "user_id": user_id,
        "document_type": document_type,
        "document_id": document_id,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "selected_text": selected_text,
        "note": note,
        "color": color,
        "tags": tags or [],
        "visibility": visibility,
        "created_at": now,
        "updated_at": None,
    }

    _annotations_store[annotation_id] = annotation

    return AnnotationData(
        annotation_id=annotation_id,
        user_id=user_id,
        document_type=document_type,
        document_id=document_id,
        start_offset=start_offset,
        end_offset=end_offset,
        selected_text=selected_text,
        note=note,
        color=color,
        tags=tags or [],
        visibility=visibility,
        created_at=now,
        updated_at=None,
    )


def get_annotation(annotation_id: int) -> Optional[AnnotationData]:
    """Get a single annotation by ID."""
    annotation = _annotations_store.get(annotation_id)
    if not annotation:
        return None

    return AnnotationData(
        annotation_id=annotation["annotation_id"],
        user_id=annotation["user_id"],
        document_type=annotation["document_type"],
        document_id=annotation["document_id"],
        start_offset=annotation["start_offset"],
        end_offset=annotation["end_offset"],
        selected_text=annotation["selected_text"],
        note=annotation["note"],
        color=annotation["color"],
        tags=annotation["tags"],
        visibility=annotation["visibility"],
        created_at=annotation["created_at"],
        updated_at=annotation["updated_at"],
    )


def update_annotation(
    annotation_id: int,
    user_id: str,
    note: Optional[str] = None,
    color: Optional[AnnotationColor] = None,
    tags: Optional[List[str]] = None,
) -> Optional[AnnotationData]:
    """
    Update an annotation.

    Only the original author can update their annotation.
    """
    annotation = _annotations_store.get(annotation_id)
    if not annotation:
        return None

    if annotation["user_id"] != user_id:
        raise ValueError("Only the author can edit this annotation")

    if note is not None:
        annotation["note"] = note
    if color is not None:
        annotation["color"] = color
    if tags is not None:
        annotation["tags"] = tags

    annotation["updated_at"] = datetime.now()

    return get_annotation(annotation_id)


def delete_annotation(annotation_id: int, user_id: str) -> bool:
    """
    Delete an annotation.

    Only the original author can delete their annotation.
    """
    annotation = _annotations_store.get(annotation_id)
    if not annotation:
        return False

    if annotation["user_id"] != user_id:
        raise ValueError("Only the author can delete this annotation")

    del _annotations_store[annotation_id]
    return True


def get_annotations_for_document(
    document_type: DocumentType,
    document_id: str,
    user_id: Optional[str] = None,
) -> List[AnnotationData]:
    """
    Get all annotations for a document.

    Args:
        document_type: Type of document
        document_id: ID of document
        user_id: If provided, filter by user's own annotations or public ones

    Returns:
        List of annotations sorted by position
    """
    annotations = [
        a for a in _annotations_store.values()
        if a["document_type"] == document_type
        and a["document_id"] == document_id
    ]

    # Filter by visibility if user_id provided
    if user_id:
        annotations = [
            a for a in annotations
            if a["user_id"] == user_id or a["visibility"] == Visibility.PUBLIC
        ]

    # Sort by position
    annotations.sort(key=lambda x: x["start_offset"])

    return [
        AnnotationData(
            annotation_id=a["annotation_id"],
            user_id=a["user_id"],
            document_type=a["document_type"],
            document_id=a["document_id"],
            start_offset=a["start_offset"],
            end_offset=a["end_offset"],
            selected_text=a["selected_text"],
            note=a["note"],
            color=a["color"],
            tags=a["tags"],
            visibility=a["visibility"],
            created_at=a["created_at"],
            updated_at=a["updated_at"],
        )
        for a in annotations
    ]


def get_user_annotations(
    user_id: str,
    document_type: Optional[DocumentType] = None,
    limit: int = 50,
) -> List[AnnotationData]:
    """Get all annotations by a user."""
    annotations = [
        a for a in _annotations_store.values()
        if a["user_id"] == user_id
    ]

    if document_type:
        annotations = [a for a in annotations if a["document_type"] == document_type]

    # Sort by created_at descending
    annotations.sort(key=lambda x: x["created_at"], reverse=True)
    annotations = annotations[:limit]

    return [
        AnnotationData(
            annotation_id=a["annotation_id"],
            user_id=a["user_id"],
            document_type=a["document_type"],
            document_id=a["document_id"],
            start_offset=a["start_offset"],
            end_offset=a["end_offset"],
            selected_text=a["selected_text"],
            note=a["note"],
            color=a["color"],
            tags=a["tags"],
            visibility=a["visibility"],
            created_at=a["created_at"],
            updated_at=a["updated_at"],
        )
        for a in annotations
    ]
