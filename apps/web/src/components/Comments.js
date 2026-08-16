/**
 * Comments & Annotations Component (Band C #47)
 *
 * Reusable component for adding comments to any entity type.
 * Supports threading, reactions, and visibility controls.
 */

import React, { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Reaction Button ───────────────────────────────────────────────────────────

function ReactionButton({ type, count, isActive, onClick }) {
  const icons = {
    like: '👍',
    insightful: '💡',
    disagree: '👎',
    question: '❓',
  };

  return (
    <button
      onClick={() => onClick(type)}
      className={`flex items-center gap-1 px-2 py-1 rounded text-sm ${
        isActive ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      <span>{icons[type]}</span>
      <span>{count || 0}</span>
    </button>
  );
}

// ── Single Comment ────────────────────────────────────────────────────────────

function Comment({
  comment,
  currentUserId,
  onReply,
  onReact,
  onEdit,
  onDelete,
  isReply = false,
}) {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);

  const handleSubmitReply = () => {
    if (replyContent.trim()) {
      onReply(comment.comment_id, replyContent);
      setReplyContent('');
      setShowReplyForm(false);
    }
  };

  const handleSubmitEdit = () => {
    if (editContent.trim() && editContent !== comment.content) {
      onEdit(comment.comment_id, editContent);
      setIsEditing(false);
    }
  };

  const isAuthor = comment.user_id === currentUserId;

  return (
    <div className={`${isReply ? 'ml-8 border-l-2 border-gray-200 pl-4' : ''} mb-4`}>
      <div className="bg-white rounded-lg shadow-sm p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
              {comment.user_name?.[0]?.toUpperCase() || comment.user_id?.[0]?.toUpperCase()}
            </div>
            <div>
              <div className="font-medium text-sm">{comment.user_name || comment.user_id}</div>
              <div className="text-xs text-gray-500">
                {new Date(comment.created_at).toLocaleString()}
                {comment.is_edited && <span className="ml-1">(edited)</span>}
              </div>
            </div>
          </div>

          {isAuthor && (
            <div className="flex gap-2">
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="text-xs text-gray-500 hover:text-blue-600"
              >
                Edit
              </button>
              <button
                onClick={() => onDelete(comment.comment_id)}
                className="text-xs text-gray-500 hover:text-red-600"
              >
                Delete
              </button>
            </div>
          )}
        </div>

        {/* Content */}
        {isEditing ? (
          <div className="mb-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full border rounded p-2 text-sm"
              rows={3}
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={handleSubmitEdit}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setIsEditing(false);
                  setEditContent(comment.content);
                }}
                className="text-gray-600 px-3 py-1 rounded text-sm hover:bg-gray-100"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-700 mb-3">{comment.content}</p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <ReactionButton
              type="like"
              count={comment.reactions?.like || 0}
              onClick={() => onReact(comment.comment_id, 'like')}
            />
            <ReactionButton
              type="insightful"
              count={comment.reactions?.insightful || 0}
              onClick={() => onReact(comment.comment_id, 'insightful')}
            />
          </div>

          {!isReply && (
            <button
              onClick={() => setShowReplyForm(!showReplyForm)}
              className="text-sm text-gray-500 hover:text-blue-600"
            >
              Reply ({comment.reply_count || 0})
            </button>
          )}
        </div>

        {/* Reply Form */}
        {showReplyForm && (
          <div className="mt-3 pt-3 border-t">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              className="w-full border rounded p-2 text-sm"
              rows={2}
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={handleSubmitReply}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
              >
                Reply
              </button>
              <button
                onClick={() => setShowReplyForm(false)}
                className="text-gray-600 px-3 py-1 rounded text-sm hover:bg-gray-100"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Comments Thread ───────────────────────────────────────────────────────────

function CommentsThread({ thread, currentUserId, onReply, onReact, onEdit, onDelete }) {
  return (
    <div className="mb-6">
      <Comment
        comment={thread.comment}
        currentUserId={currentUserId}
        onReply={onReply}
        onReact={onReact}
        onEdit={onEdit}
        onDelete={onDelete}
      />
      {thread.replies?.map((reply) => (
        <Comment
          key={reply.comment_id}
          comment={reply}
          currentUserId={currentUserId}
          onReply={onReply}
          onReact={onReact}
          onEdit={onEdit}
          onDelete={onDelete}
          isReply
        />
      ))}
    </div>
  );
}

// ── New Comment Form ──────────────────────────────────────────────────────────

function NewCommentForm({ onSubmit, loading }) {
  const [content, setContent] = useState('');
  const [visibility, setVisibility] = useState('private');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (content.trim()) {
      onSubmit(content, visibility);
      setContent('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-4 mb-4">
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Add a comment..."
        className="w-full border rounded p-3 text-sm"
        rows={3}
      />
      <div className="flex items-center justify-between mt-3">
        <select
          value={visibility}
          onChange={(e) => setVisibility(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          <option value="private">Private</option>
          <option value="team">Team</option>
          <option value="public">Public</option>
        </select>
        <button
          type="submit"
          disabled={loading || !content.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {loading ? 'Posting...' : 'Post Comment'}
        </button>
      </div>
    </form>
  );
}

// ── Main Comments Component ───────────────────────────────────────────────────

export default function Comments({
  entityType,
  entityId,
  currentUserId = 'anonymous',
  currentUserName = 'Anonymous User',
}) {
  const [threads, setThreads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchComments = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/comments/entity/${entityType}/${entityId}?user_id=${currentUserId}`
      );
      if (!res.ok) throw new Error('Failed to fetch comments');
      const data = await res.json();
      setThreads(data.threads || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/comments/entity/${entityType}/${entityId}/stats`);
      if (res.ok) setStats(await res.json());
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  useEffect(() => {
    fetchComments();
    fetchStats();
  }, [entityType, entityId]);

  const handleCreateComment = async (content, visibility) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        user_id: currentUserId,
        entity_type: entityType,
        entity_id: entityId,
        content,
        user_name: currentUserName,
        visibility,
      });

      const res = await fetch(`${API_BASE}/comments?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to create comment');
      await fetchComments();
      await fetchStats();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReply = async (parentId, content) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        user_id: currentUserId,
        entity_type: entityType,
        entity_id: entityId,
        content,
        user_name: currentUserName,
        parent_id: parentId,
      });

      const res = await fetch(`${API_BASE}/comments?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to create reply');
      await fetchComments();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReact = async (commentId, reactionType) => {
    try {
      const res = await fetch(
        `${API_BASE}/comments/${commentId}/react?user_id=${currentUserId}&reaction_type=${reactionType}`,
        { method: 'POST' }
      );
      if (!res.ok) throw new Error('Failed to add reaction');
      await fetchComments();
    } catch (err) {
      console.error('Reaction error:', err);
    }
  };

  const handleEdit = async (commentId, content) => {
    try {
      const res = await fetch(
        `${API_BASE}/comments/${commentId}?user_id=${currentUserId}&content=${encodeURIComponent(content)}`,
        { method: 'PUT' }
      );
      if (!res.ok) throw new Error('Failed to edit comment');
      await fetchComments();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (commentId) => {
    if (!window.confirm('Delete this comment?')) return;
    try {
      const res = await fetch(
        `${API_BASE}/comments/${commentId}?user_id=${currentUserId}`,
        { method: 'DELETE' }
      );
      if (!res.ok) throw new Error('Failed to delete comment');
      await fetchComments();
      await fetchStats();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="comments-container">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg">
          Comments
          {stats && (
            <span className="text-sm font-normal text-gray-500 ml-2">
              ({stats.total_comments})
            </span>
          )}
        </h3>
      </div>

      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {/* New Comment Form */}
      <NewCommentForm onSubmit={handleCreateComment} loading={loading} />

      {/* Comments List */}
      {loading && threads.length === 0 ? (
        <div className="text-center py-8 text-gray-500">Loading comments...</div>
      ) : threads.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No comments yet. Be the first to comment!
        </div>
      ) : (
        threads.map((thread) => (
          <CommentsThread
            key={thread.comment.comment_id}
            thread={thread}
            currentUserId={currentUserId}
            onReply={handleReply}
            onReact={handleReact}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        ))
      )}
    </div>
  );
}
