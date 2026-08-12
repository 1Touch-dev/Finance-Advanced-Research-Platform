"""
Chunking strategies for ingestion.

- recursive: split on a priority list of separators (paragraph → line → sentence
  → word), packing up to a target size with overlap. Robust, dependency-free,
  keeps semantic units intact better than a naive fixed-window split.
- semantic: group adjacent sentences while their embeddings stay similar; start a
  new chunk when the topic shifts (cosine drop past a threshold). Requires
  embeddings; callers fall back to recursive when unavailable.

Chosen at ingest via RAG_CHUNK_STRATEGY = recursive (default) | semantic.
"""
from __future__ import annotations

import os
import re
from typing import List

_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
# Default to semantic chunking: proven to split multi-fact docs into per-fact
# chunks (recursive merged a 5-fact memo into 1 unsearchable chunk). Set
# RAG_CHUNK_STRATEGY=recursive to force the dependency-free splitter.
_STRATEGY = os.getenv("RAG_CHUNK_STRATEGY", "semantic")
_SEM_THRESHOLD = float(os.getenv("RAG_SEMANTIC_THRESHOLD", "0.55"))
# Tiny chunks embed poorly and match spuriously; anything shorter than this is
# merged forward into the next chunk (or backward if it is the last one).
_MIN_CHUNK_CHARS = int(os.getenv("RAG_MIN_CHUNK_CHARS", "80"))
# Table-aware chunking: keep tabular rows intact and re-attach the header row to
# every row-group chunk (a balance-sheet row is meaningless without its columns).
_TABLE_AWARE = os.getenv("RAG_TABLE_AWARE", "true").lower() in ("1", "true", "yes")
_TABLE_ROWS_PER_CHUNK = int(os.getenv("RAG_TABLE_ROWS_PER_CHUNK", "20"))

_SEPARATORS = ["\n\n", "\n", ". ", " "]

# A line is "tabular" if it carries column delimiters. Both our XLSX and CSV
# extractors emit " | "-joined rows; markdown/aligned tables use "|" too.
_PIPE_RE = re.compile(r"\S\s*\|\s*\S")
_MD_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _is_table_row(line: str) -> bool:
    return bool(_PIPE_RE.search(line)) and not _MD_SEP_RE.match(line)


def _segment_tables(text: str) -> List[dict]:
    """
    Split raw text into ordered segments: {"kind": "table"|"prose", "lines": [...]}.
    A table segment is a maximal run of >=2 consecutive pipe-delimited rows. The
    nearest preceding non-empty non-table line (e.g. '## Sheet: Balance') is kept
    as the segment's caption so it can be prepended for context.
    """
    lines = text.split("\n")
    # Pass 1: classify each line index as table-row or not, and find table blocks.
    blocks = []  # (start, end_exclusive)
    i, n = 0, len(lines)
    while i < n:
        if _is_table_row(lines[i]):
            j = i
            while j < n and (_is_table_row(lines[j]) or _MD_SEP_RE.match(lines[j])):
                j += 1
            if j - i >= 2:
                blocks.append((i, j))
                i = j
                continue
        i += 1

    # Pass 2: for each block, find a heading-like caption line just above it and
    # mark it consumed so it is not also emitted as prose.
    consumed = set()
    captions = {}
    for (s, e) in blocks:
        for k in range(s - 1, -1, -1):
            if lines[k].strip():
                prev = lines[k].strip()
                if not _is_table_row(lines[k]) and (len(prev) < 60 or prev.startswith("#")):
                    captions[s] = prev
                    consumed.add(k)
                break

    # Pass 3: walk lines, emitting prose runs and table blocks in order.
    block_starts = {s: e for (s, e) in blocks}
    segments: List[dict] = []
    i = 0
    while i < n:
        if i in block_starts:
            e = block_starts[i]
            segments.append({"kind": "table", "lines": lines[i:e], "caption": captions.get(i, "")})
            i = e
            continue
        if i not in consumed:
            if segments and segments[-1]["kind"] == "prose":
                segments[-1]["lines"].append(lines[i])
            else:
                segments.append({"kind": "prose", "lines": [lines[i]]})
        i += 1
    return [s for s in segments if s["kind"] == "table" or "".join(s["lines"]).strip()]


def _chunk_table_segment(seg: dict) -> List[str]:
    """
    Chunk a detected table: header row (+ optional markdown separator) is repeated
    at the top of every row-group so each chunk is self-describing. Rows are never
    split mid-row; groups are capped at _TABLE_ROWS_PER_CHUNK.
    """
    rows = seg["lines"]
    caption = seg.get("caption", "")
    header_lines: List[str] = []
    body = rows
    if rows:
        header_lines = [rows[0]]
        body = rows[1:]
        if body and _MD_SEP_RE.match(body[0]):  # markdown alignment row
            header_lines.append(body[0])
            body = body[1:]
    if not body:  # header-only table
        prefix = (caption + "\n") if caption else ""
        return [prefix + "\n".join(header_lines)]

    chunks: List[str] = []
    for start in range(0, len(body), _TABLE_ROWS_PER_CHUNK):
        group = body[start:start + _TABLE_ROWS_PER_CHUNK]
        parts = []
        if caption:
            parts.append(caption)
        parts.extend(header_lines)
        parts.extend(group)
        chunks.append("\n".join(parts))
    return chunks


def table_aware_chunk(text: str, size: int = None, overlap: int = None) -> List[str]:
    """
    Split into prose vs table segments; chunk tables row-group-wise (header
    preserved) and prose with the normal strategy. Interleaving order preserved.
    """
    size = _SIZE if size is None else size
    overlap = _OVERLAP if overlap is None else overlap
    text = text.strip()
    if not text:
        return []
    segments = _segment_tables(text)
    if not any(s["kind"] == "table" for s in segments):
        return None  # signal caller: no tables, use normal path
    out: List[str] = []
    for seg in segments:
        if seg["kind"] == "table":
            out.extend(_chunk_table_segment(seg))
        else:
            prose = "\n".join(seg["lines"]).strip()
            if prose:
                if _STRATEGY == "semantic":
                    out.extend(semantic_chunk(prose, size))
                else:
                    out.extend(recursive_chunk(prose, size, overlap))
    # NOTE: deliberately do NOT _merge_tiny across segments here — merging a short
    # prose chunk into an adjacent table chunk would defeat table isolation. Each
    # segment is already internally coherent.
    return out


def _split_recursive(text: str, size: int, seps: List[str]) -> List[str]:
    if len(text) <= size or not seps:
        return [text] if text.strip() else []
    sep = seps[0]
    parts = text.split(sep)
    chunks, cur = [], ""
    for part in parts:
        piece = part + sep
        if len(cur) + len(piece) <= size:
            cur += piece
        else:
            if cur.strip():
                chunks.append(cur.strip())
            if len(piece) > size:
                chunks.extend(_split_recursive(part, size, seps[1:]))
                cur = ""
            else:
                cur = piece
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def _apply_overlap(chunks: List[str], overlap: int) -> List[str]:
    if overlap <= 0 or len(chunks) < 2:
        return chunks
    out = [chunks[0]]
    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap:]
        out.append((tail + "\n" + chunks[i]).strip())
    return out


def _merge_tiny(chunks: List[str], min_chars: int = _MIN_CHUNK_CHARS) -> List[str]:
    """Merge sub-min-length chunks into a neighbor so we never embed 3-word
    fragments that match spuriously. Merges forward, or backward for a trailing
    runt."""
    if min_chars <= 0 or not chunks:
        return chunks
    out: List[str] = []
    carry = ""
    for ch in chunks:
        piece = (carry + " " + ch).strip() if carry else ch
        if len(piece) < min_chars:
            carry = piece  # keep accumulating until we clear the floor
        else:
            out.append(piece)
            carry = ""
    if carry:  # trailing runt → append to the last chunk, or stand alone if none
        if out:
            out[-1] = (out[-1] + " " + carry).strip()
        else:
            out.append(carry)
    return out


def recursive_chunk(text: str, size: int = _SIZE, overlap: int = _OVERLAP) -> List[str]:
    text = text.strip()
    if not text:
        return []
    base = _split_recursive(text, size, _SEPARATORS)
    base = _merge_tiny(base)
    return _apply_overlap(base, overlap)


def semantic_chunk(text: str, max_size: int = _SIZE) -> List[str]:
    """Group sentences by embedding similarity; falls back to recursive on error."""
    text = text.strip()
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= 1:
        return recursive_chunk(text, max_size)
    try:
        import numpy as np
        from . import embeddings
        vecs = embeddings.embed_texts(sentences)  # normalized rows
        chunks, cur, cur_len = [], [sentences[0]], len(sentences[0])
        for i in range(1, len(sentences)):
            sim = float(vecs[i] @ vecs[i - 1])
            if sim < _SEM_THRESHOLD or cur_len + len(sentences[i]) > max_size:
                chunks.append(" ".join(cur))
                cur, cur_len = [sentences[i]], len(sentences[i])
            else:
                cur.append(sentences[i])
                cur_len += len(sentences[i])
        if cur:
            chunks.append(" ".join(cur))
        return _merge_tiny(chunks)
    except Exception:
        return recursive_chunk(text, max_size)


def chunk_text(text: str, size: int = _SIZE, overlap: int = _OVERLAP) -> List[str]:
    # Table-aware first: if the text contains tabular blocks, chunk them row-wise
    # with headers preserved (prose segments still use the configured strategy).
    if _TABLE_AWARE:
        try:
            tabled = table_aware_chunk(text, size, overlap)
            if tabled is not None:  # None = no tables detected → fall through
                return tabled
        except Exception:
            pass  # any failure → normal path
    if _STRATEGY == "semantic":
        return semantic_chunk(text, size)
    return recursive_chunk(text, size, overlap)
