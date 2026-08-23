/**
 * Annotations Component (Band C #47)
 *
 * Component for highlighting and annotating text in documents.
 * Supports colors, notes, tags, and visibility controls.
 */

import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Annotation Highlight Colors ───────────────────────────────────────────────

const COLORS = {
  yellow: { bg: 'bg-yellow-200', border: 'border-yellow-400', text: 'text-yellow-800' },
  green: { bg: 'bg-green-200', border: 'border-green-400', text: 'text-green-800' },
  blue: { bg: 'bg-blue-200', border: 'border-blue-400', text: 'text-blue-800' },
  red: { bg: 'bg-red-200', border: 'border-red-400', text: 'text-red-800' },
  purple: { bg: 'bg-purple-200', border: 'border-purple-400', text: 'text-purple-800' },
};

// ── Annotation Tooltip ────────────────────────────────────────────────────────

function AnnotationTooltip({ annotation, onEdit, onDelete, isOwner }) {
  const [isEditing, setIsEditing] = useState(false);
  const [note, setNote] = useState(annotation.note || '');
  const [color, setColor] = useState(annotation.color);

  const handleSave = () => {
    onEdit(annotation.annotation_id, { note, color });
    setIsEditing(false);
  };

  return (
    <div className="absolute z-50 bg-white rounded-lg shadow-lg p-4 w-72 border" style={{ top: '100%', left: 0 }}>
      {isEditing ? (
        <div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add a note..."
            className="w-full border rounded p-2 text-sm mb-2"
            rows={3}
          />
          <div className="flex gap-2 mb-3">
            {Object.keys(COLORS).map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-6 h-6 rounded-full ${COLORS[c].bg} ${
                  color === c ? 'ring-2 ring-offset-1 ring-gray-400' : ''
                }`}
              />
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
            >
              Save
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="text-gray-600 px-3 py-1 rounded text-sm hover:bg-gray-100"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div>
          <div className="text-sm text-gray-600 mb-2 italic">
            "{annotation.selected_text}"
          </div>
          {annotation.note && (
            <p className="text-sm mb-2">{annotation.note}</p>
          )}
          {annotation.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {annotation.tags.map((tag) => (
                <span key={tag} className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                  #{tag}
                </span>
              ))}
            </div>
          )}
          <div className="text-xs text-gray-400 mb-2">
            {new Date(annotation.created_at).toLocaleString()}
          </div>
          {isOwner && (
            <div className="flex gap-2 pt-2 border-t">
              <button
                onClick={() => setIsEditing(true)}
                className="text-xs text-blue-600 hover:underline"
              >
                Edit
              </button>
              <button
                onClick={() => onDelete(annotation.annotation_id)}
                className="text-xs text-red-600 hover:underline"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Annotation Mark ───────────────────────────────────────────────────────────

function AnnotationMark({ annotation, onEdit, onDelete, currentUserId }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const colors = COLORS[annotation.color] || COLORS.yellow;
  const isOwner = annotation.user_id === currentUserId;

  return (
    <span className="relative inline">
      <mark
        className={`${colors.bg} cursor-pointer hover:${colors.border} border-b-2 border-transparent hover:border-current`}
        onClick={() => setShowTooltip(!showTooltip)}
      >
        {annotation.selected_text}
      </mark>
      {showTooltip && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setShowTooltip(false)} />
          <AnnotationTooltip
            annotation={annotation}
            onEdit={onEdit}
            onDelete={onDelete}
            isOwner={isOwner}
          />
        </>
      )}
    </span>
  );
}

// ── New Annotation Popup ──────────────────────────────────────────────────────

function NewAnnotationPopup({ selection, position, onSave, onCancel }) {
  const [note, setNote] = useState('');
  const [color, setColor] = useState('yellow');
  const [tags, setTags] = useState('');

  const handleSave = () => {
    onSave({
      selectedText: selection.text,
      startOffset: selection.start,
      endOffset: selection.end,
      note,
      color,
      tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
    });
  };

  return (
    <div
      className="fixed z-50 bg-white rounded-lg shadow-xl p-4 w-80 border"
      style={{ top: position.y + 10, left: position.x }}
    >
      <div className="text-sm text-gray-600 mb-3 italic border-l-2 border-gray-300 pl-2">
        "{selection.text.slice(0, 100)}{selection.text.length > 100 ? '...' : ''}"
      </div>

      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Add a note (optional)..."
        className="w-full border rounded p-2 text-sm mb-3"
        rows={3}
        autoFocus
      />

      <div className="mb-3">
        <label className="text-xs text-gray-500 block mb-1">Highlight Color</label>
        <div className="flex gap-2">
          {Object.keys(COLORS).map((c) => (
            <button
              key={c}
              onClick={() => setColor(c)}
              className={`w-8 h-8 rounded-full ${COLORS[c].bg} ${
                color === c ? 'ring-2 ring-offset-2 ring-gray-400' : ''
              }`}
              title={c}
            />
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="text-xs text-gray-500 block mb-1">Tags (comma separated)</label>
        <input
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="e.g., risk, important, key-metric"
          className="w-full border rounded px-2 py-1 text-sm"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSave}
          className="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
        >
          Save Annotation
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-2 text-gray-600 rounded text-sm hover:bg-gray-100"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Annotations Sidebar ───────────────────────────────────────────────────────

function AnnotationsSidebar({ annotations, onNavigate, onDelete, currentUserId }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold mb-4">
        Annotations ({annotations.length})
      </h3>

      {annotations.length === 0 ? (
        <p className="text-sm text-gray-500">
          Select text to create an annotation
        </p>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {annotations.map((annotation) => {
            const colors = COLORS[annotation.color] || COLORS.yellow;
            const isOwner = annotation.user_id === currentUserId;

            return (
              <div
                key={annotation.annotation_id}
                className={`p-3 rounded border-l-4 ${colors.border} bg-gray-50 cursor-pointer hover:bg-gray-100`}
                onClick={() => onNavigate(annotation)}
              >
                <div className={`text-sm ${colors.text} font-medium mb-1 line-clamp-2`}>
                  "{annotation.selected_text}"
                </div>
                {annotation.note && (
                  <p className="text-sm text-gray-600 mb-1">{annotation.note}</p>
                )}
                {annotation.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-1">
                    {annotation.tags.map((tag) => (
                      <span key={tag} className="text-xs bg-gray-200 px-1 rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-400">
                    {new Date(annotation.created_at).toLocaleDateString()}
                  </span>
                  {isOwner && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(annotation.annotation_id);
                      }}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main Annotatable Document Component ───────────────────────────────────────

export default function AnnotatableDocument({
  documentType,
  documentId,
  content,
  currentUserId = 'anonymous',
}) {
  const [annotations, setAnnotations] = useState([]);
  const [showNewAnnotation, setShowNewAnnotation] = useState(false);
  const [selection, setSelection] = useState(null);
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });
  const [loading, setLoading] = useState(false);

  const fetchAnnotations = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/annotations/document/${documentType}/${documentId}?user_id=${currentUserId}`
      );
      if (res.ok) {
        const data = await res.json();
        setAnnotations(data.annotations || []);
      }
    } catch (err) {
      console.error('Failed to fetch annotations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnnotations();
  }, [documentType, documentId]);

  const handleTextSelect = () => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return;

    const text = sel.toString().trim();
    if (!text) return;

    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    // Simple offset calculation (would need refinement for complex documents)
    const container = document.getElementById('annotatable-content');
    if (!container) return;

    const fullText = container.textContent || '';
    const startOffset = fullText.indexOf(text);
    if (startOffset === -1) return;

    setSelection({
      text,
      start: startOffset,
      end: startOffset + text.length,
    });
    setPopupPosition({
      x: Math.min(rect.left, window.innerWidth - 320),
      y: rect.bottom + window.scrollY,
    });
    setShowNewAnnotation(true);
  };

  const handleSaveAnnotation = async (annotationData) => {
    try {
      const params = new URLSearchParams({
        user_id: currentUserId,
        document_type: documentType,
        document_id: documentId,
        start_offset: annotationData.startOffset,
        end_offset: annotationData.endOffset,
        selected_text: annotationData.selectedText,
        note: annotationData.note || '',
        color: annotationData.color,
      });

      if (annotationData.tags?.length) {
        annotationData.tags.forEach((tag) => params.append('tags', tag));
      }

      const res = await apiFetch(`/annotations?${params}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to save annotation');

      await fetchAnnotations();
      setShowNewAnnotation(false);
      setSelection(null);
      window.getSelection()?.removeAllRanges();
    } catch (err) {
      console.error('Save annotation error:', err);
    }
  };

  const handleEditAnnotation = async (annotationId, updates) => {
    try {
      const params = new URLSearchParams({
        user_id: currentUserId,
        ...updates,
      });

      const res = await apiFetch(`/annotations/${annotationId}?${params}`, { method: 'PUT',
      });
      if (!res.ok) throw new Error('Failed to update annotation');

      await fetchAnnotations();
    } catch (err) {
      console.error('Edit annotation error:', err);
    }
  };

  const handleDeleteAnnotation = async (annotationId) => {
    if (!window.confirm('Delete this annotation?')) return;

    try {
      const res = await apiFetch(`/annotations/${annotationId}?user_id=${currentUserId}`, { method: 'DELETE' }
      );
      if (!res.ok) throw new Error('Failed to delete annotation');

      await fetchAnnotations();
    } catch (err) {
      console.error('Delete annotation error:', err);
    }
  };

  const handleNavigateToAnnotation = (annotation) => {
    // Scroll to the annotation in the document
    // This is a simplified implementation
    const container = document.getElementById('annotatable-content');
    if (container) {
      const marks = container.querySelectorAll('mark');
      marks.forEach((mark) => {
        if (mark.textContent === annotation.selected_text) {
          mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
          mark.classList.add('ring-2', 'ring-blue-500');
          setTimeout(() => mark.classList.remove('ring-2', 'ring-blue-500'), 2000);
        }
      });
    }
  };

  // Render content with annotations applied
  const renderAnnotatedContent = () => {
    if (!content || annotations.length === 0) {
      return <div dangerouslySetInnerHTML={{ __html: content }} />;
    }

    // Sort annotations by position (descending) to apply from end
    const sortedAnnotations = [...annotations].sort(
      (a, b) => b.position.start - a.position.start
    );

    let annotatedContent = content;
    sortedAnnotations.forEach((annotation) => {
      const { start, end } = annotation.position;
      const colors = COLORS[annotation.color] || COLORS.yellow;

      const before = annotatedContent.slice(0, start);
      const highlighted = annotatedContent.slice(start, end);
      const after = annotatedContent.slice(end);

      annotatedContent =
        before +
        `<mark class="${colors.bg} cursor-pointer" data-annotation-id="${annotation.annotation_id}">` +
        highlighted +
        '</mark>' +
        after;
    });

    return <div dangerouslySetInnerHTML={{ __html: annotatedContent }} />;
  };

  return (
    <div className="flex gap-4">
      {/* Document Content */}
      <div className="flex-1">
        <div
          id="annotatable-content"
          className="bg-white rounded-lg shadow p-6 prose max-w-none"
          onMouseUp={handleTextSelect}
        >
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : (
            renderAnnotatedContent()
          )}
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-72 flex-shrink-0">
        <AnnotationsSidebar
          annotations={annotations}
          onNavigate={handleNavigateToAnnotation}
          onDelete={handleDeleteAnnotation}
          currentUserId={currentUserId}
        />
      </div>

      {/* New Annotation Popup */}
      {showNewAnnotation && selection && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setShowNewAnnotation(false)} />
          <NewAnnotationPopup
            selection={selection}
            position={popupPosition}
            onSave={handleSaveAnnotation}
            onCancel={() => {
              setShowNewAnnotation(false);
              setSelection(null);
            }}
          />
        </>
      )}
    </div>
  );
}

// ── Export sidebar separately for flexible layouts ────────────────────────────

export { AnnotationsSidebar };
