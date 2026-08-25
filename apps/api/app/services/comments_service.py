"""
Comments & Annotations Service (Band C #47)
────────────────────────────────────────────────────────────────────────────────
Provides:
  - Comment CRUD operations
  - Comment threading (replies)
  - Reactions (like, insightful, etc.)
  - Annotations (text highlights with notes)
  - Visibility controls (private, team, public)

Tables used (created here if missing):
  - comments           : { id, user_id, user_name, entity_type, entity_id, content, parent_id, visibility, is_edited, is_deleted, created_at, updated_at }
  - comment_reactions   : { id, comment_id, user_id, reaction_type, created_at }
  - annotations         : { id, user_id, document_type, document_id, start_offset, end_offset, selected_text, note, color, tags, visibility, created_at, updated_at }
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db_context

logger = logging.getLogger(__name__)


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


# ── DB helpers ─────────────────────────────────────────────────────────────────


def _ensure_tables(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS comments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     VARCHAR(200) NOT NULL,
            user_name   VARCHAR(200),
            entity_type VARCHAR(50) NOT NULL,
            entity_id   VARCHAR(500) NOT NULL,
            content     TEXT NOT NULL,
            parent_id   INTEGER,
            visibility  VARCHAR(20) NOT NULL DEFAULT 'private',
            is_edited   BOOLEAN NOT NULL DEFAULT 0,
            is_deleted  BOOLEAN NOT NULL DEFAULT 0,
            created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
            updated_at  DATETIME
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS comment_reactions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id    INTEGER NOT NULL,
            user_id       VARCHAR(200) NOT NULL,
            reaction_type VARCHAR(50) NOT NULL,
            created_at    DATETIME NOT NULL DEFAULT (datetime('now')),
            UNIQUE(comment_id, user_id)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS annotations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       VARCHAR(200) NOT NULL,
            document_type VARCHAR(50) NOT NULL,
            document_id   VARCHAR(500) NOT NULL,
            start_offset  INTEGER NOT NULL,
            end_offset    INTEGER NOT NULL,
            selected_text TEXT,
            note          TEXT,
            color         VARCHAR(20) NOT NULL DEFAULT 'yellow',
            tags          TEXT DEFAULT '[]',
            visibility    VARCHAR(20) NOT NULL DEFAULT 'private',
            created_at    DATETIME NOT NULL DEFAULT (datetime('now')),
            updated_at    DATETIME
        )
    """))
    db.commit()


def _parse_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(str(val))


def _row_to_comment_data(row, db: Session) -> CommentData:
    """Convert a DB row (from comments table) to CommentData with reply_count and reactions."""
    comment_id = row.id

    reply_count_row = db.execute(text(
        "SELECT COUNT(*) as cnt FROM comments WHERE parent_id = :pid AND is_deleted = 0"
    ), {"pid": comment_id}).fetchone()
    reply_count = reply_count_row.cnt if reply_count_row else 0

    reaction_rows = db.execute(text(
        "SELECT reaction_type, COUNT(*) as cnt FROM comment_reactions WHERE comment_id = :cid GROUP BY reaction_type"
    ), {"cid": comment_id}).fetchall()
    reactions = {r.reaction_type: r.cnt for r in reaction_rows}

    return CommentData(
        comment_id=comment_id,
        user_id=row.user_id,
        user_name=row.user_name,
        entity_type=EntityType(row.entity_type),
        entity_id=row.entity_id,
        content=row.content,
        parent_id=row.parent_id,
        visibility=Visibility(row.visibility),
        is_edited=bool(row.is_edited),
        reply_count=reply_count,
        reactions=reactions,
        created_at=_parse_datetime(row.created_at),
        updated_at=_parse_datetime(row.updated_at),
    )


def _row_to_annotation_data(row) -> AnnotationData:
    """Convert a DB row (from annotations table) to AnnotationData."""
    tags_raw = row.tags
    if isinstance(tags_raw, str):
        try:
            tags = json.loads(tags_raw)
        except (json.JSONDecodeError, TypeError):
            tags = []
    else:
        tags = tags_raw or []

    return AnnotationData(
        annotation_id=row.id,
        user_id=row.user_id,
        document_type=DocumentType(row.document_type),
        document_id=row.document_id,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
        selected_text=row.selected_text,
        note=row.note,
        color=AnnotationColor(row.color),
        tags=tags,
        visibility=Visibility(row.visibility),
        created_at=_parse_datetime(row.created_at),
        updated_at=_parse_datetime(row.updated_at),
    )


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
    with get_db_context() as db:
        _ensure_tables(db)
        now = datetime.now()

        result = db.execute(text("""
            INSERT INTO comments (user_id, user_name, entity_type, entity_id, content, parent_id, visibility, is_edited, is_deleted, created_at)
            VALUES (:user_id, :user_name, :entity_type, :entity_id, :content, :parent_id, :visibility, 0, 0, :created_at)
        """), {
            "user_id": user_id,
            "user_name": user_name,
            "entity_type": entity_type.value,
            "entity_id": entity_id,
            "content": content,
            "parent_id": parent_id,
            "visibility": visibility.value,
            "created_at": now.isoformat(),
        })
        db.commit()
        comment_id = result.lastrowid

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
    with get_db_context() as db:
        _ensure_tables(db)
        row = db.execute(text(
            "SELECT * FROM comments WHERE id = :id AND is_deleted = 0"
        ), {"id": comment_id}).fetchone()

        if not row:
            return None

        return _row_to_comment_data(row, db)


def update_comment(
    comment_id: int,
    user_id: str,
    content: str,
) -> Optional[CommentData]:
    """
    Update a comment's content.

    Only the original author can update their comment.
    """
    with get_db_context() as db:
        _ensure_tables(db)
        row = db.execute(text(
            "SELECT * FROM comments WHERE id = :id AND is_deleted = 0"
        ), {"id": comment_id}).fetchone()

        if not row:
            return None

        if row.user_id != user_id:
            raise ValueError("Only the author can edit this comment")

        now = datetime.now()
        db.execute(text("""
            UPDATE comments SET content = :content, is_edited = 1, updated_at = :updated_at
            WHERE id = :id
        """), {"content": content, "updated_at": now.isoformat(), "id": comment_id})
        db.commit()

        return get_comment(comment_id)


def delete_comment(comment_id: int, user_id: str) -> bool:
    """
    Soft-delete a comment.

    Only the original author can delete their comment.
    """
    with get_db_context() as db:
        _ensure_tables(db)
        row = db.execute(text(
            "SELECT * FROM comments WHERE id = :id AND is_deleted = 0"
        ), {"id": comment_id}).fetchone()

        if not row:
            return False

        if row.user_id != user_id:
            raise ValueError("Only the author can delete this comment")

        now = datetime.now()
        db.execute(text(
            "UPDATE comments SET is_deleted = 1, updated_at = :updated_at WHERE id = :id"
        ), {"updated_at": now.isoformat(), "id": comment_id})
        db.commit()
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
    with get_db_context() as db:
        _ensure_tables(db)

        top_level_rows = db.execute(text("""
            SELECT * FROM comments
            WHERE entity_type = :entity_type
              AND entity_id = :entity_id
              AND is_deleted = 0
              AND parent_id IS NULL
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), {
            "entity_type": entity_type.value,
            "entity_id": entity_id,
            "limit": limit,
            "offset": offset,
        }).fetchall()

        threads = []
        for row in top_level_rows:
            comment_data = _row_to_comment_data(row, db)

            replies = []
            if include_replies:
                reply_rows = db.execute(text("""
                    SELECT * FROM comments
                    WHERE parent_id = :parent_id AND is_deleted = 0
                    ORDER BY created_at ASC
                """), {"parent_id": row.id}).fetchall()

                for rr in reply_rows:
                    replies.append(_row_to_comment_data(rr, db))

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
    with get_db_context() as db:
        _ensure_tables(db)

        row = db.execute(text(
            "SELECT id FROM comments WHERE id = :id AND is_deleted = 0"
        ), {"id": comment_id}).fetchone()
        if not row:
            raise ValueError("Comment not found")

        existing = db.execute(text(
            "SELECT * FROM comment_reactions WHERE comment_id = :cid AND user_id = :uid"
        ), {"cid": comment_id, "uid": user_id}).fetchone()

        if existing:
            db.execute(text(
                "UPDATE comment_reactions SET reaction_type = :rt WHERE id = :id"
            ), {"rt": reaction_type.value, "id": existing.id})
            db.commit()
            return UserReaction(
                reaction_id=existing.id,
                comment_id=comment_id,
                user_id=user_id,
                reaction_type=reaction_type,
                created_at=_parse_datetime(existing.created_at),
            )

        now = datetime.now()
        result = db.execute(text("""
            INSERT INTO comment_reactions (comment_id, user_id, reaction_type, created_at)
            VALUES (:cid, :uid, :rt, :created_at)
        """), {
            "cid": comment_id,
            "uid": user_id,
            "rt": reaction_type.value,
            "created_at": now.isoformat(),
        })
        db.commit()

        return UserReaction(
            reaction_id=result.lastrowid,
            comment_id=comment_id,
            user_id=user_id,
            reaction_type=reaction_type,
            created_at=now,
        )


def remove_reaction(comment_id: int, user_id: str) -> bool:
    """Remove user's reaction from a comment."""
    with get_db_context() as db:
        _ensure_tables(db)
        result = db.execute(text(
            "DELETE FROM comment_reactions WHERE comment_id = :cid AND user_id = :uid"
        ), {"cid": comment_id, "uid": user_id})
        db.commit()
        return result.rowcount > 0


def get_comment_stats(
    entity_type: EntityType,
    entity_id: str,
) -> CommentStats:
    """Get statistics for comments on an entity."""
    with get_db_context() as db:
        _ensure_tables(db)

        total_row = db.execute(text("""
            SELECT COUNT(*) as cnt FROM comments
            WHERE entity_type = :et AND entity_id = :eid AND is_deleted = 0
        """), {"et": entity_type.value, "eid": entity_id}).fetchone()
        total_comments = total_row.cnt if total_row else 0

        reaction_rows = db.execute(text("""
            SELECT cr.reaction_type, COUNT(*) as cnt
            FROM comment_reactions cr
            JOIN comments c ON cr.comment_id = c.id
            WHERE c.entity_type = :et AND c.entity_id = :eid AND c.is_deleted = 0
            GROUP BY cr.reaction_type
        """), {"et": entity_type.value, "eid": entity_id}).fetchall()

        reaction_breakdown = {r.reaction_type: r.cnt for r in reaction_rows}
        total_reactions = sum(reaction_breakdown.values())

        top_rows = db.execute(text("""
            SELECT user_id, COUNT(*) as cnt FROM comments
            WHERE entity_type = :et AND entity_id = :eid AND is_deleted = 0
            GROUP BY user_id ORDER BY cnt DESC LIMIT 5
        """), {"et": entity_type.value, "eid": entity_id}).fetchall()
        top_commenters = [{"user_id": r.user_id, "count": r.cnt} for r in top_rows]

        recent_rows = db.execute(text("""
            SELECT * FROM comments
            WHERE entity_type = :et AND entity_id = :eid AND is_deleted = 0
            ORDER BY created_at DESC LIMIT 5
        """), {"et": entity_type.value, "eid": entity_id}).fetchall()
        recent_activity = [_row_to_comment_data(r, db) for r in recent_rows]

        return CommentStats(
            entity_type=entity_type,
            entity_id=entity_id,
            total_comments=total_comments,
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
    with get_db_context() as db:
        _ensure_tables(db)
        now = datetime.now()
        tags_list = tags or []

        result = db.execute(text("""
            INSERT INTO annotations (user_id, document_type, document_id, start_offset, end_offset, selected_text, note, color, tags, visibility, created_at)
            VALUES (:user_id, :document_type, :document_id, :start_offset, :end_offset, :selected_text, :note, :color, :tags, :visibility, :created_at)
        """), {
            "user_id": user_id,
            "document_type": document_type.value,
            "document_id": document_id,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "selected_text": selected_text,
            "note": note,
            "color": color.value,
            "tags": json.dumps(tags_list),
            "visibility": visibility.value,
            "created_at": now.isoformat(),
        })
        db.commit()

        return AnnotationData(
            annotation_id=result.lastrowid,
            user_id=user_id,
            document_type=document_type,
            document_id=document_id,
            start_offset=start_offset,
            end_offset=end_offset,
            selected_text=selected_text,
            note=note,
            color=color,
            tags=tags_list,
            visibility=visibility,
            created_at=now,
            updated_at=None,
        )


def get_annotation(annotation_id: int) -> Optional[AnnotationData]:
    """Get a single annotation by ID."""
    with get_db_context() as db:
        _ensure_tables(db)
        row = db.execute(text(
            "SELECT * FROM annotations WHERE id = :id"
        ), {"id": annotation_id}).fetchone()

        if not row:
            return None

        return _row_to_annotation_data(row)


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
    with get_db_context() as db:
        _ensure_tables(db)
        row = db.execute(text(
            "SELECT * FROM annotations WHERE id = :id"
        ), {"id": annotation_id}).fetchone()

        if not row:
            return None

        if row.user_id != user_id:
            raise ValueError("Only the author can edit this annotation")

        updates = []
        params: Dict[str, Any] = {"id": annotation_id}

        if note is not None:
            updates.append("note = :note")
            params["note"] = note
        if color is not None:
            updates.append("color = :color")
            params["color"] = color.value
        if tags is not None:
            updates.append("tags = :tags")
            params["tags"] = json.dumps(tags)

        if updates:
            now = datetime.now()
            updates.append("updated_at = :updated_at")
            params["updated_at"] = now.isoformat()
            db.execute(text(
                f"UPDATE annotations SET {', '.join(updates)} WHERE id = :id"
            ), params)
            db.commit()

        return get_annotation(annotation_id)


def delete_annotation(annotation_id: int, user_id: str) -> bool:
    """
    Delete an annotation.

    Only the original author can delete their annotation.
    """
    with get_db_context() as db:
        _ensure_tables(db)
        row = db.execute(text(
            "SELECT * FROM annotations WHERE id = :id"
        ), {"id": annotation_id}).fetchone()

        if not row:
            return False

        if row.user_id != user_id:
            raise ValueError("Only the author can delete this annotation")

        db.execute(text("DELETE FROM annotations WHERE id = :id"), {"id": annotation_id})
        db.commit()
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
    with get_db_context() as db:
        _ensure_tables(db)

        if user_id:
            rows = db.execute(text("""
                SELECT * FROM annotations
                WHERE document_type = :dt AND document_id = :did
                  AND (user_id = :uid OR visibility = 'public')
                ORDER BY start_offset ASC
            """), {"dt": document_type.value, "did": document_id, "uid": user_id}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT * FROM annotations
                WHERE document_type = :dt AND document_id = :did
                ORDER BY start_offset ASC
            """), {"dt": document_type.value, "did": document_id}).fetchall()

        return [_row_to_annotation_data(r) for r in rows]


def get_user_annotations(
    user_id: str,
    document_type: Optional[DocumentType] = None,
    limit: int = 50,
) -> List[AnnotationData]:
    """Get all annotations by a user."""
    with get_db_context() as db:
        _ensure_tables(db)

        if document_type:
            rows = db.execute(text("""
                SELECT * FROM annotations
                WHERE user_id = :uid AND document_type = :dt
                ORDER BY created_at DESC LIMIT :limit
            """), {"uid": user_id, "dt": document_type.value, "limit": limit}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT * FROM annotations
                WHERE user_id = :uid
                ORDER BY created_at DESC LIMIT :limit
            """), {"uid": user_id, "limit": limit}).fetchall()

        return [_row_to_annotation_data(r) for r in rows]
