/**
 * Comments & Annotations Page
 * Wired to /comments/* and /annotations/* APIs
 */

import React, { useState, useEffect } from 'react';
import Layout from '../src/components/Layout';
import { apiFetch } from '../lib/api';

const ENTITY_TYPES = [
  { value: 'stock', label: 'Stock' },
  { value: 'filing', label: 'SEC Filing' },
  { value: 'report', label: 'Intelligence Report' },
  { value: 'news', label: 'News Article' },
  { value: 'person', label: 'Person' },
  { value: 'company', label: 'Company' },
];

const REACTION_TYPES = [
  { value: 'like', label: 'Like', emoji: '👍' },
  { value: 'insightful', label: 'Insightful', emoji: '💡' },
  { value: 'disagree', label: 'Disagree', emoji: '👎' },
  { value: 'question', label: 'Question', emoji: '❓' },
];

const VISIBILITY_OPTIONS = [
  { value: 'private', label: 'Private (Only Me)' },
  { value: 'team', label: 'Team' },
  { value: 'public', label: 'Public' },
];

export default function Comments() {
  const [view, setView] = useState('browse');
  const [entityType, setEntityType] = useState('stock');
  const [entityId, setEntityId] = useState('');
  const [comments, setComments] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // New comment form
  const [newComment, setNewComment] = useState('');
  const [commentVisibility, setCommentVisibility] = useState('private');
  const [replyingTo, setReplyingTo] = useState(null);

  // Fetch comments for entity
  const fetchComments = async () => {
    if (!entityId.trim()) {
      setError('Please enter an entity ID');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/comments/entity/${entityType}/${entityId}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to fetch comments');
      }
      const data = await res.json();
      setComments(data.threads || []);

      // Also fetch stats
      const statsRes = await apiFetch(`/comments/entity/${entityType}/${entityId}/stats`);
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Create comment
  const createComment = async () => {
    if (!newComment.trim() || !entityId.trim()) return;

    try {
      const params = new URLSearchParams({
        entity_type: entityType,
        entity_id: entityId,
        content: newComment,
        visibility: commentVisibility,
      });
      if (replyingTo) {
        params.append('parent_id', replyingTo.toString());
      }

      const res = await apiFetch(`/comments?${params}`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create comment');
      }

      setNewComment('');
      setReplyingTo(null);
      fetchComments(); // Refresh
    } catch (err) {
      setError(err.message);
    }
  };

  // Add reaction
  const addReaction = async (commentId, reactionType) => {
    try {
      const params = new URLSearchParams({
        reaction_type: reactionType,
      });
      const res = await apiFetch(`/comments/${commentId}/react?${params}`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to add reaction');
      }
      fetchComments(); // Refresh
    } catch (err) {
      setError(err.message);
    }
  };

  // Delete comment
  const deleteComment = async (commentId) => {
    if (!confirm('Delete this comment?')) return;

    try {
      const res = await apiFetch(`/comments/${commentId}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to delete comment');
      }
      fetchComments(); // Refresh
    } catch (err) {
      setError(err.message);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getVisibilityBadge = (visibility) => {
    const badges = {
      private: 'bg-gray-100 text-gray-600',
      team: 'bg-blue-100 text-blue-600',
      public: 'bg-green-100 text-green-600',
    };
    return badges[visibility] || badges.private;
  };

  // Render comment thread
  const renderComment = (comment, depth = 0) => (
    <div key={comment.id} className={`${depth > 0 ? 'ml-8 border-l-2 border-gray-200 pl-4' : ''} mb-4`}>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <span className="font-medium">{comment.user_name || comment.user_id}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${getVisibilityBadge(comment.visibility)}`}>
              {comment.visibility}
            </span>
          </div>
          <span className="text-xs text-gray-500">{formatDate(comment.created_at)}</span>
        </div>

        <p className="text-gray-800 mb-3">{comment.content}</p>

        {/* Reactions */}
        <div className="flex items-center gap-4">
          <div className="flex gap-1">
            {REACTION_TYPES.map((rt) => (
              <button
                key={rt.value}
                onClick={() => addReaction(comment.id, rt.value)}
                className="text-lg hover:bg-gray-100 rounded px-1"
                title={rt.label}
              >
                {rt.emoji}
              </button>
            ))}
          </div>

          {comment.reactions && Object.keys(comment.reactions).length > 0 && (
            <div className="flex gap-2 text-sm text-gray-500">
              {Object.entries(comment.reactions).map(([type, count]) => (
                count > 0 && (
                  <span key={type}>
                    {REACTION_TYPES.find(r => r.value === type)?.emoji} {count}
                  </span>
                )
              ))}
            </div>
          )}

          <button
            onClick={() => setReplyingTo(comment.id)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Reply
          </button>

          <button
            onClick={() => deleteComment(comment.id)}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Delete
          </button>
        </div>

        {/* Reply input */}
        {replyingTo === comment.id && (
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Write a reply..."
              className="flex-1 border rounded px-3 py-2"
            />
            <button
              onClick={createComment}
              className="bg-blue-600 text-white px-4 py-2 rounded"
            >
              Reply
            </button>
            <button
              onClick={() => { setReplyingTo(null); setNewComment(''); }}
              className="text-gray-500 px-2"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="mt-2">
          {comment.replies.map((reply) => renderComment(reply, depth + 1))}
        </div>
      )}
    </div>
  );

  return (
    <Layout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Comments & Annotations</h1>
        <p className="text-gray-600 mb-6">
          Add comments and annotations to stocks, filings, reports, and other entities.
        </p>

        {/* Entity Selector */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Entity Type</label>
              <select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                {ENTITY_TYPES.map((et) => (
                  <option key={et.value} value={et.value}>
                    {et.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Entity ID</label>
              <input
                type="text"
                placeholder={entityType === 'stock' ? 'e.g., AAPL' : 'Enter ID...'}
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={fetchComments}
                disabled={loading}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Load Comments'}
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Stats */}
        {stats && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold">{stats.total_comments || 0}</div>
                <div className="text-sm text-gray-500">Comments</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{stats.total_reactions || 0}</div>
                <div className="text-sm text-gray-500">Reactions</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{stats.unique_users || 0}</div>
                <div className="text-sm text-gray-500">Participants</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{stats.total_replies || 0}</div>
                <div className="text-sm text-gray-500">Replies</div>
              </div>
            </div>
          </div>
        )}

        {/* New Comment */}
        {entityId && !replyingTo && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="font-medium mb-3">Add Comment</h3>
            <div className="space-y-3">
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Write your comment..."
                rows={3}
                className="w-full border rounded px-3 py-2"
              />
              <div className="flex gap-4 items-center">
                <select
                  value={commentVisibility}
                  onChange={(e) => setCommentVisibility(e.target.value)}
                  className="border rounded px-3 py-2"
                >
                  {VISIBILITY_OPTIONS.map((v) => (
                    <option key={v.value} value={v.value}>{v.label}</option>
                  ))}
                </select>
                <button
                  onClick={createComment}
                  disabled={!newComment.trim()}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  Post Comment
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Comments List */}
        {comments.length > 0 ? (
          <div className="space-y-2">
            <h3 className="font-medium text-gray-700 mb-4">
              Comments for {entityType}: {entityId}
            </h3>
            {comments.map((comment) => renderComment(comment))}
          </div>
        ) : entityId && !loading ? (
          <div className="bg-gray-50 text-gray-600 text-center py-8 rounded-lg">
            No comments yet. Be the first to comment!
          </div>
        ) : null}
      </div>
    </Layout>
  );
}
