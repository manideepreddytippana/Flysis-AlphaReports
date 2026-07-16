import re
import json
import math
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any
from collections import Counter, defaultdict

import fitz  

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(_ENC.encode(text))
except Exception:  
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        # not exact token count it is just a estimation
        return max(1, int(len(text.split()) * 1.3))




# PyMuPDF span "flags" bitfield
FLAG_SUPERSCRIPT = 1 << 0
FLAG_ITALIC = 1 << 1
FLAG_SERIFED = 1 << 2
FLAG_MONOSPACED = 1 << 3
FLAG_BOLD = 1 << 4

# Embedded font names look like "ABCDEF+Arial-Bold" -> strip prefix
SUBSET_PREFIX_RE = re.compile(r"^[A-Za-z0-9]{6}\+")


NUMBERING_PATTERNS = [
    re.compile(r"^(?P<num>\d+(?:\.\d+){1,5})\.?\s+\S"),        # 1.1 / 1.2.3
    re.compile(r"^(?P<num>[A-Z]\.\d+(?:\.\d+)*)\.?\s+\S"),      # A.1 / A.1.2
    re.compile(r"^(?P<num>\d+)[.)]\s+\S"),                      # 1.  / 1)
    re.compile(r"^(?P<num>[A-Z])[.)]\s+\S"),                    # A.  / A)
    re.compile(r"^(?P<num>[A-Z]\d+(?:\.\d+)*)\.?\s+\S"),        # A1 / A1.2
    re.compile(r"^(?P<num>[IVXLCDM]{1,7})\.\s+\S"),             # I.  II.  III.
    re.compile(
        r"^(?:Chapter|Section|Part|Appendix)\s+(?P<num>[\dA-Z]+)\b",
        re.IGNORECASE,
    ),
]

BULLET_RE = re.compile(
    r"^\s*([\u2022\u25CF\u25CB\u25E6\u25AA\u25B6\u27A4\u2023\u00B7\u2219\u2013\u2014\-]"
    r"|\*|[0-9]+[.)]|[a-zA-Z][.)])\s+\S"
)

CAPTION_RE = re.compile(
    r"^(Figure|Fig\.|Table|Exhibit|Chart|Diagram|Source|Note)\s*[:.]?\s*\d*[:.]?\s",
    re.IGNORECASE,
)

PAGE_NUM_RE = re.compile(r"^(page\s+)?\d+(\s*(of|/)\s*\d+)?\.?$", re.IGNORECASE)

SENTENCE_END_RE = re.compile(r"[.!?:;,]\s*$")

HYPHEN_WRAP_RE = re.compile(r"[A-Za-z]-$")

WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']+")

TOPIC_SHIFT_MARKERS = [
    "however", "in contrast", "on the other hand", "meanwhile", "turning to",
    "moving on", "moving to", "in addition", "additionally", "furthermore",
    "in summary", "to summarize", "in conclusion", "as a result", "therefore",
    "looking ahead", "separately", "elsewhere", "in a separate", "next,",
    "shifting focus", "by comparison", "notably", "overall,", "in short",
    "finally,", "lastly,", "more broadly",
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "as", "by", "at", "from", "is", "are", "was", "were", "be",
    "been", "being", "this", "that", "these", "those", "it", "its", "their",
    "our", "we", "they", "he", "she", "his", "her", "you", "your", "i",
    "not", "no", "do", "does", "did", "has", "have", "had", "will", "would",
    "can", "could", "should", "may", "might", "also", "than", "into", "over",
    "under", "about", "such", "more", "most", "other", "some", "any",
    "which", "who", "whom", "what", "when", "where", "why", "how", "all",
    "each", "per", "including", "etc",
}

@dataclass
class SpanInfo:
    text: str
    size: float
    font: str
    bold: bool
    italic: bool
    color: Tuple[int, int, int]
    bbox: Tuple[float, float, float, float]
    superscript: bool


@dataclass
class LineInfo:
    idx: int
    page: int
    block_id: int
    text: str
    bbox: Tuple[float, float, float, float]
    spans: List[SpanInfo]
    max_size: float
    dominant_font: str
    is_bold: bool
    color: Tuple[int, int, int]
    rotated: bool
    page_w: float
    page_h: float
    gap_before: float = 0.0
    gap_after: float = 0.0
    in_table: bool = False
    is_header_footer: bool = False
    is_page_number: bool = False
    is_caption: bool = False
    is_bullet: bool = False
    word_count: int = 0


@dataclass
class Heading:
    text: str
    level: int
    page: int
    bbox: Tuple[float, float, float, float]
    score: float
    numbering: str | None
    line_indices: List[int]
    style_key: Tuple | None = None


@dataclass
class ContentUnit:
    type: str  # "heading" | "paragraph" | "table" | "list" | "caption"
    text: str
    page_start: int
    page_end: int
    line_indices: List[int]
    heading_ref: Heading | None = None
    topic_break: str | None = None       # None | "hard" | "soft"
    topic_break_score: float = 0.0


@dataclass
class Chunk:
    chunk_id: int
    text: str
    page_start: int
    page_end: int
    heading_path: List[str]
    chunk_type: str  # "narrative" | "table" | "list" | "title"
    token_estimate: int
    boundary_reason: str


class PDFReportAnalyzer:
    """
    Usage:
        analyzer = PDFReportAnalyzer("report.pdf").run()
        for h in analyzer.outline():
            print(h)
        for c in analyzer.chunks_as_dicts():
            print(c)
    """

    HEADING_SPLIT_LEVEL = 2        
    HEADING_SCORE_THRESHOLD = 3.0   
    SOFT_BREAK_THRESHOLD = 0.85     

    def __init__(
        self,
        path: str,
        max_chunk_tokens: int = 450,
        min_chunk_tokens: int = 80,
        overlap_tokens: int = 0,
    ):
        self.path = path
        self.doc = fitz.open(path)
        self.max_chunk_tokens = max_chunk_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.overlap_tokens = overlap_tokens

        self.lines: List[LineInfo] = []
        self.ordered_line_indices: List[int] = []
        self.profile: Dict[str, Any] = {}
        self.table_bboxes: Dict[int, List[Tuple]] = defaultdict(list)
        self.table_texts: Dict[int, List[Tuple]] = defaultdict(list)
        self.headings: List[Heading] = []
        self.units: List[ContentUnit] = []
        self.chunks: List[Chunk] = []
        self.report: Dict[str, Any] = {}

    def run(self) -> "PDFReportAnalyzer":
        self._extract_lines()
        if not self.lines:
            self.report["empty_or_scanned"] = True
            self.report["num_pages"] = len(self.doc)
            return self

        self._build_profile()
        self._detect_header_footer()
        self._detect_tables()
        self._annotate_lines()
        self._compute_gaps()
        self._detect_headings()
        self._assign_heading_levels()
        self._build_chunks()
        self._build_report()
        return self

    def _extract_lines(self) -> None:
        idx_counter = 0
        block_counter = 0
        image_block_pages = set()
        text_char_total = 0

        for pno in range(len(self.doc)):
            page = self.doc[pno]
            try:
                page_dict = page.get_text("dict")
            except Exception:
                continue
            pw, ph = page.rect.width, page.rect.height

            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    image_block_pages.add(pno)
                    continue
                block_counter += 1

                for line in block.get("lines", []):
                    spans_raw = line.get("spans", [])
                    if not spans_raw:
                        continue
                    text = "".join(s.get("text", "") for s in spans_raw)
                    if not text.strip():
                        continue  # if whitespace-only

                    spans: List[SpanInfo] = []
                    for s in spans_raw:
                        font_name = SUBSET_PREFIX_RE.sub("", s.get("font", ""))
                        flags = s.get("flags", 0)
                        color_int = s.get("color", 0)
                        color = (
                            (color_int >> 16) & 255,
                            (color_int >> 8) & 255,
                            color_int & 255,
                        )
                        spans.append(SpanInfo(
                            text=s.get("text", ""),
                            size=round(s.get("size", 0.0), 2),
                            font=font_name,
                            bold=bool(flags & FLAG_BOLD) or "bold" in font_name.lower(),
                            italic=bool(flags & FLAG_ITALIC)
                            or "italic" in font_name.lower()
                            or "oblique" in font_name.lower(),
                            color=color,
                            bbox=tuple(s.get("bbox", (0, 0, 0, 0))),
                            superscript=bool(flags & FLAG_SUPERSCRIPT),
                        ))

          
                    non_super = [sp for sp in spans if not sp.superscript] or spans
                    max_size = max(sp.size for sp in non_super)
                    dominant = max(non_super, key=lambda sp: sp.size)
                    is_bold = any(
                        sp.bold for sp in non_super if sp.size >= max_size - 0.3
                    )

                    dirv = line.get("dir", (1, 0))
                    rotated = abs(dirv[0]) < 0.9

                    li = LineInfo(
                        idx=idx_counter,
                        page=pno,
                        block_id=block_counter,
                        text=text.strip(),
                        bbox=tuple(line.get("bbox", (0, 0, 0, 0))),
                        spans=spans,
                        max_size=max_size,
                        dominant_font=dominant.font,
                        is_bold=is_bold,
                        color=dominant.color,
                        rotated=rotated,
                        page_w=pw,
                        page_h=ph,
                        word_count=len(text.strip().split()),
                    )
                    self.lines.append(li)
                    text_char_total += len(text)
                    idx_counter += 1

        # Heuristic flag for scanned/image-only documents (edge case 13)
        if text_char_total < 50 and image_block_pages:
            self.report["scanned_pdf_warning"] = True

    def _build_profile(self) -> None:
        size_chars: Counter = Counter()
        font_chars: Counter = Counter()
        color_chars: Counter = Counter()

        for li in self.lines:
            if li.rotated:
                continue
            n = max(1, len(li.text))
            size_chars[li.max_size] += n
            font_chars[li.dominant_font] += n
            color_chars[li.color] += n

        if size_chars:
            body_size = size_chars.most_common(1)[0][0]
            body_font = font_chars.most_common(1)[0][0]
            body_color = color_chars.most_common(1)[0][0]
        else:  # edge case 25: degenerate document
            body_size, body_font, body_color = 10.0, "Helvetica", (0, 0, 0)

        self.profile = dict(
            body_size=body_size,
            body_font=body_font,
            body_color=body_color,
            size_counter=size_chars,
            median_line_gap=body_size * 0.3,  # placeholder, refined later
        )

    def _detect_header_footer(self) -> None:
        n_pages = len(self.doc)
        header_zone, footer_zone = 0.10, 0.90
        normalized_pages: Dict[str, set] = defaultdict(set)

        for li in self.lines:
            if li.page_h <= 0:
                continue
            rel_top = li.bbox[1] / li.page_h
            rel_bot = li.bbox[3] / li.page_h
            in_zone = rel_top <= header_zone or rel_bot >= footer_zone
            if not in_zone:
                continue

            stripped = li.text.strip()
            if PAGE_NUM_RE.match(stripped):
                li.is_page_number = True
                continue

            norm = re.sub(r"\d+", "#", stripped.lower())
            norm = re.sub(r"\s+", " ", norm).strip()
            if norm:
                normalized_pages[norm].add(li.page)

        min_repeat = max(3, math.ceil(n_pages * 0.4))
        repeated = {norm for norm, pages in normalized_pages.items() if len(pages) >= min_repeat}

        for li in self.lines:
            if li.is_page_number or li.page_h <= 0:
                continue
            rel_top = li.bbox[1] / li.page_h
            rel_bot = li.bbox[3] / li.page_h
            if rel_top <= header_zone or rel_bot >= footer_zone:
                norm = re.sub(r"\d+", "#", li.text.strip().lower())
                norm = re.sub(r"\s+", " ", norm).strip()
                if norm in repeated:
                    li.is_header_footer = True

    def _detect_tables(self) -> None:
        for pno in range(len(self.doc)):
            page = self.doc[pno]
            try:
                finder = page.find_tables()
                tables = finder.tables if finder else []
            except Exception:
                tables = []

            for t in tables:
                try:
                    bbox = tuple(t.bbox)
                except Exception:
                    continue
                self.table_bboxes[pno].append(bbox)
                try:
                    data = t.extract()
                    md = self._table_to_markdown(data)
                except Exception:
                    md = None
                self.table_texts[pno].append((bbox, md))

        for li in self.lines:
            for bbox in self.table_bboxes.get(li.page, []):
                if self._bbox_inside(li.bbox, bbox):
                    li.in_table = True
                    break

    @staticmethod
    def _table_to_markdown(data) -> str | None:
        if not data:
            return None
        rows = [
            [("" if c is None else str(c).replace("\n", " ").replace("|", "/").strip()) for c in row]
            for row in data
        ]
        header = rows[0]
        width = len(header)
        lines_out = ["| " + " | ".join(header) + " |"]
        lines_out.append("| " + " | ".join(["---"] * width) + " |")
        for row in rows[1:]:
            if len(row) < width:
                row = row + [""] * (width - len(row))
            else:
                row = row[:width]
            lines_out.append("| " + " | ".join(row) + " |")
        return "\n".join(lines_out)

    @staticmethod
    def _bbox_inside(line_bbox, table_bbox, margin: float = 1.0) -> bool:
        lx0, ly0, lx1, ly1 = line_bbox
        tx0, ty0, tx1, ty1 = table_bbox
        cx, cy = (lx0 + lx1) / 2.0, (ly0 + ly1) / 2.0
        return (tx0 - margin <= cx <= tx1 + margin) and (ty0 - margin <= cy <= ty1 + margin)

    def _annotate_lines(self) -> None:
        for li in self.lines:
            t = li.text.strip()
            if CAPTION_RE.match(t):
                li.is_caption = True
            if BULLET_RE.match(t):
                li.is_bullet = True

    def _ordered_lines_for_page(self, page_lines: List[LineInfo]) -> List[LineInfo]:
        if not page_lines:
            return []
        pw = page_lines[0].page_w

        left = [li for li in page_lines if li.bbox[2] <= pw * 0.52]
        right = [li for li in page_lines if li.bbox[0] >= pw * 0.48]
        left_ids = {l.idx for l in left}
        right_ids = {l.idx for l in right}
        rest = [li for li in page_lines if li.idx not in left_ids and li.idx not in right_ids]

        if len(left) >= 3 and len(right) >= 3 and len(rest) <= max(2, len(page_lines) // 6):
            left_sorted = sorted(left, key=lambda l: (round(l.bbox[1], 1), l.bbox[0]))
            right_sorted = sorted(right, key=lambda l: (round(l.bbox[1], 1), l.bbox[0]))
            rest_sorted = sorted(rest, key=lambda l: (round(l.bbox[1], 1), l.bbox[0]))
            return rest_sorted[:1] + left_sorted + right_sorted + rest_sorted[1:]

        return sorted(page_lines, key=lambda l: (round(l.bbox[1], 1), l.bbox[0]))

    def _compute_gaps(self) -> None:
        gaps_sample: List[float] = []
        body_size = self.profile["body_size"]

        for pno in range(len(self.doc)):
            page_lines = [li for li in self.lines if li.page == pno]
            ordered = self._ordered_lines_for_page(page_lines)
            prev: LineInfo | None = None
            for li in ordered:
                if prev is not None and li.bbox[1] >= prev.bbox[1]:
                    gap = max(0.0, li.bbox[1] - prev.bbox[3])
                    li.gap_before = gap
                    prev.gap_after = gap
                    if (
                        not li.is_header_footer
                        and not li.in_table
                        and abs(li.max_size - body_size) < 0.5
                        and gap < body_size * 4
                    ):
                        gaps_sample.append(gap)
                prev = li
            self.ordered_line_indices.extend(li.idx for li in ordered)

        if gaps_sample:
            median_gap = statistics.median(gaps_sample)
        else: 
            median_gap = body_size * 0.3
        
        self.profile["median_line_gap"] = max(median_gap, body_size * 0.15)

    def _score_heading_line(self, li: LineInfo):
        """Return (score, numbering_str_or_None) or None if not a candidate."""
        text = li.text.strip()
        if not text:
            return None
        if li.is_header_footer or li.is_page_number or li.in_table or li.rotated:
            return None
        if li.is_caption:
            return None

        profile = self.profile
        body_size = profile["body_size"]
        body_font = profile["body_font"]
        body_color = profile["body_color"]
        median_gap = profile["median_line_gap"]

        size_ratio = li.max_size / body_size if body_size else 1.0
        score = 0.0
        numbering: str | None = None

        bullet_match = bool(BULLET_RE.match(text))
        for pat in NUMBERING_PATTERNS:
            m = pat.match(text)
            if m:
                candidate_num = m.group("num")
                heading_like_context = (
                    size_ratio >= 1.12
                    or li.is_bold
                    or li.gap_before >= median_gap * 1.4
                    or li.word_count <= 8
                )
                if bullet_match and not heading_like_context:
                    score += 0.4
                else:
                    numbering = candidate_num
                    score += 2.0
                break

        if size_ratio >= 1.8:
            score += 3.0
        elif size_ratio >= 1.4:
            score += 2.2
        elif size_ratio >= 1.15:
            score += 1.2
        elif size_ratio < 0.95:
            score -= 1.0  

        if li.is_bold and size_ratio >= 0.98:
            score += 1.3

        letters = [c for c in text if c.isalpha()]
        if letters and all(c.isupper() for c in letters) and 1 <= li.word_count <= 12:
            score += 1.0

        stripped_end = text.rstrip()
        if li.word_count <= 14 and not SENTENCE_END_RE.search(stripped_end):
            score += 0.8
        elif li.word_count <= 14 and stripped_end.endswith(":"):
            score += 0.5
        elif li.word_count > 22:
            score -= 1.0

        if li.gap_before >= median_gap * 1.6:
            score += 1.2
        if li.gap_after >= median_gap * 1.4:
            score += 0.6

        page_w = li.page_w
        line_w = li.bbox[2] - li.bbox[0]
        if page_w:
            ratio = line_w / page_w
            if ratio < 0.65:
                score += 0.4
            if ratio > 0.75:
                score -= 1.0 

            center_offset = abs(((li.bbox[0] + li.bbox[2]) / 2) - page_w / 2)
            if center_offset < page_w * 0.06 and ratio < 0.85:
                score += 0.4  

        if li.dominant_font != body_font:
            score += 0.4
        if li.color != body_color:
            score += 0.4

        if li.is_bullet and numbering is None:
            score -= 3.0

        return score, numbering

    def _detect_headings(self) -> None:
        ordered = [self.lines[i] for i in self.ordered_line_indices]
        candidates = []  

        for pos, li in enumerate(ordered):
            result = self._score_heading_line(li)
            if result is None:
                continue
            score, numbering = result

            size_ratio = li.max_size / self.profile["body_size"] if self.profile["body_size"] else 1.0
            if li.page == 0 and size_ratio >= 2.0:
                score += 1.0

            if score >= self.HEADING_SCORE_THRESHOLD:
                candidates.append((pos, li, score, numbering))

        merged: List[Heading] = []
        used = set()
        for c_idx in range(len(candidates)):
            pos, li, score, numbering = candidates[c_idx]
            if pos in used:
                continue

            text_parts = [li.text.strip()]
            bbox = list(li.bbox)
            line_idx_group = [li.idx]
            last_pos = pos

            j = c_idx + 1
            while j < len(candidates):
                npos, nli, nscore, nnum = candidates[j]
                if (
                    npos == last_pos + 1
                    and nli.block_id == li.block_id
                    and abs(nli.max_size - li.max_size) < 0.5
                    and nli.is_bold == li.is_bold
                    and nnum is None
                ):
                    text_parts.append(nli.text.strip())
                    bbox[2] = max(bbox[2], nli.bbox[2])
                    bbox[3] = max(bbox[3], nli.bbox[3])
                    line_idx_group.append(nli.idx)
                    used.add(npos)
                    last_pos = npos
                    j += 1
                else:
                    break

            full_text = self._join_wrapped(text_parts)
            merged.append(Heading(
                text=full_text,
                level=0,
                page=li.page,
                bbox=tuple(bbox),
                score=score,
                numbering=numbering,
                line_indices=line_idx_group,
            ))

        self.headings = merged

    @staticmethod
    def _join_wrapped(parts: List[str]) -> str:
        result = parts[0]
        for p in parts[1:]:
            if HYPHEN_WRAP_RE.search(result) and p[:1].islower():
                result = result[:-1] + p  
            else:
                result = result + " " + p
        return result

    def _assign_heading_levels(self) -> None:
        if not self.headings:
            return

        style_sizes: Dict[Tuple, List[float]] = defaultdict(list)
        for h in self.headings:
            li0 = self.lines[h.line_indices[0]]
            key = (round(li0.max_size * 2) / 2, li0.is_bold, li0.color)
            h.style_key = key
            style_sizes[key].append(li0.max_size)

        style_rank = {
            key: rank
            for rank, (key, _) in enumerate(
                sorted(style_sizes.items(), key=lambda kv: -statistics.mean(kv[1]))
            )
        }

        depths = [h.numbering.count(".") + 1 for h in self.headings if h.numbering]
        max_numbered_depth = max(depths) if depths else 0

        for i, h in enumerate(self.headings):
            li0 = self.lines[h.line_indices[0]]
            size_ratio = (
                li0.max_size / self.profile["body_size"] if self.profile["body_size"] else 1.0
            )

            if i == 0 and h.page == 0 and size_ratio >= 2.0:
                h.level = 0
                continue

            if h.numbering:
                h.level = h.numbering.count(".") + 1
            else:
                h.level = style_rank[h.style_key] + 1

        if max_numbered_depth:
            cap = max_numbered_depth + 2
            for h in self.headings:
                if not h.numbering and h.level > cap:
                    h.level = cap

        self._cross_check_toc()

    def _cross_check_toc(self) -> None:
        try:
            toc = self.doc.get_toc(simple=True)
        except Exception:
            toc = []
        if not toc:
            return

        def norm(s: str) -> str:
            return re.sub(r"\s+", " ", s.strip().lower())

        for level, title, page in toc:
            ntitle = norm(title)
            if not ntitle:
                continue
            target_page = page - 1
            for h in self.headings:
                if abs(h.page - target_page) > 1:
                    continue
                nh = norm(h.text)
                if nh == ntitle or ntitle in nh or nh in ntitle:
                    h.level = max(1, level)
                    break

    def _build_content_units(self) -> None:
        ordered = [self.lines[i] for i in self.ordered_line_indices]
        heading_line_idx = set()
        heading_by_first_line: Dict[int, Heading] = {}
        for h in self.headings:
            heading_line_idx.update(h.line_indices)
            heading_by_first_line[h.line_indices[0]] = h

        units: List[ContentUnit] = []
        current_para_lines: List[LineInfo] = []
        current_list_lines: List[LineInfo] = []
        median_gap = self.profile["median_line_gap"]
        emitted_tables = set()

        def flush_para():
            if current_para_lines:
                text = self._join_lines_to_paragraph(current_para_lines)
                units.append(ContentUnit(
                    type="paragraph",
                    text=text,
                    page_start=current_para_lines[0].page,
                    page_end=current_para_lines[-1].page,
                    line_indices=[l.idx for l in current_para_lines],
                ))
                current_para_lines.clear()

        def flush_list():
            if current_list_lines:
                text = "\n".join("- " + l.text.strip() for l in current_list_lines)
                units.append(ContentUnit(
                    type="list",
                    text=text,
                    page_start=current_list_lines[0].page,
                    page_end=current_list_lines[-1].page,
                    line_indices=[l.idx for l in current_list_lines],
                ))
                current_list_lines.clear()

        for li in ordered:
            if li.is_header_footer or li.is_page_number or li.rotated:
                continue

            if li.in_table:
                flush_para()
                flush_list()
                for tidx, bbox in enumerate(self.table_bboxes.get(li.page, [])):
                    key = (li.page, tidx)
                    if key in emitted_tables:
                        continue
                    if self._bbox_inside(li.bbox, bbox):
                        emitted_tables.add(key)
                        _, md = self.table_texts[li.page][tidx]
                        units.append(ContentUnit(
                            type="table",
                            text=md or "[TABLE: content could not be extracted]",
                            page_start=li.page,
                            page_end=li.page,
                            line_indices=[],
                        ))
                continue

            if li.idx in heading_line_idx:
                flush_para()
                flush_list()
                h = heading_by_first_line.get(li.idx)
                if h is not None:
                    units.append(ContentUnit(
                        type="heading",
                        text=h.text,
                        page_start=h.page,
                        page_end=h.page,
                        line_indices=h.line_indices,
                        heading_ref=h,
                        topic_break="hard",
                    ))
                continue

            if li.is_caption:
                flush_para()
                flush_list()
                units.append(ContentUnit(
                    type="caption",
                    text=li.text.strip(),
                    page_start=li.page,
                    page_end=li.page,
                    line_indices=[li.idx],
                ))
                continue

            if li.is_bullet:
                flush_para()
                if current_list_lines and li.gap_before >= median_gap * 2.5:
                    flush_list()
                current_list_lines.append(li)
                continue

            flush_list()
            if current_para_lines and li.gap_before >= median_gap * 1.5:
                flush_para()
            current_para_lines.append(li)

        flush_para()
        flush_list()
        self.units = units

    @staticmethod
    def _join_lines_to_paragraph(lines: List[LineInfo]) -> str:
        parts = [l.text.strip() for l in lines]
        result = parts[0]
        for p in parts[1:]:
            if HYPHEN_WRAP_RE.search(result) and p[:1].islower():
                result = result[:-1] + p
            else:
                result = result + " " + p
        return result

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [
            w.lower() for w in WORD_RE.findall(text)
            if w.lower() not in STOPWORDS and len(w) > 2
        ]

    @staticmethod
    def _cosine_sim(tokens_a: List[str], tokens_b: List[str]) -> float:
        if not tokens_a or not tokens_b:
            return 0.0
        ca, cb = Counter(tokens_a), Counter(tokens_b)
        common = set(ca) & set(cb)
        dot = sum(ca[w] * cb[w] for w in common)
        na = math.sqrt(sum(v * v for v in ca.values()))
        nb = math.sqrt(sum(v * v for v in cb.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _detect_topic_breaks(self) -> None:
        prev_tokens: List[str] | None = None
        median_gap = self.profile["median_line_gap"]

        for u in self.units:
            if u.type == "heading":
                prev_tokens = None
                continue
            if u.type != "paragraph":
                prev_tokens = None
                continue

            tokens = self._tokenize(u.text)
            if prev_tokens is not None:
                sim = self._cosine_sim(prev_tokens, tokens)
                score = (1.0 - sim)

                low = u.text.strip().lower()
                if any(low.startswith(m) for m in TOPIC_SHIFT_MARKERS):
                    score += 0.4

                first_line = self.lines[u.line_indices[0]]
                if first_line.gap_before >= median_gap * 1.8:
                    score += 0.3

                u.topic_break_score = score
                if score >= self.SOFT_BREAK_THRESHOLD:
                    u.topic_break = "soft"

            prev_tokens = tokens

    def _build_chunks(self) -> None:
        self._build_content_units()
        self._detect_topic_breaks()

        chunks: List[Chunk] = []
        cur_parts: List[str] = []
        cur_pages: set = set()
        cur_reason = "document_start"
        heading_stack: List[Heading] = []
        pending_caption: str | None = None

        def heading_path() -> List[str]:
            return [h.text for h in heading_stack]

        def cur_tokens() -> int:
            return count_tokens("\n\n".join(cur_parts)) if cur_parts else 0

        def finalize(chunk_type: str = "narrative"):
            nonlocal cur_parts, cur_pages
            if not cur_parts:
                return
            text = "\n\n".join(cur_parts)
            chunks.append(Chunk(
                chunk_id=len(chunks),
                text=text,
                page_start=(min(cur_pages) if cur_pages else 0),
                page_end=(max(cur_pages) if cur_pages else 0),
                heading_path=heading_path(),
                chunk_type=chunk_type,
                token_estimate=count_tokens(text),
                boundary_reason=cur_reason,
            ))
            cur_parts = []
            cur_pages = set()

        for u in self.units:
            if u.type == "heading":
                h = u.heading_ref
                if (
                    cur_parts
                    and h.level >= 1
                    and h.level <= self.HEADING_SPLIT_LEVEL
                    and cur_tokens() >= self.min_chunk_tokens
                ):
                    finalize()
                    cur_reason = "heading"

                while heading_stack and heading_stack[-1].level >= h.level and h.level >= 1:
                    heading_stack.pop()
                if h.level >= 1:
                    heading_stack.append(h)

                cur_parts.append(u.text)
                cur_pages.add(u.page_start)
                pending_caption = None
                continue

            if u.type == "caption":
                pending_caption = u.text
                cur_parts.append(u.text)
                cur_pages.add(u.page_start)
                continue

            if u.type == "table":
               
                if cur_parts and pending_caption and cur_parts[-1] == pending_caption:
                    cur_parts.pop()
                if cur_parts:
                    finalize()
                table_text = u.text
                if pending_caption:
                    table_text = pending_caption + "\n" + table_text
                cur_parts.append(table_text)
                cur_pages.add(u.page_start)
                finalize(chunk_type="table")
                cur_reason = "table"
                pending_caption = None
                continue

            pending_caption = None

            if u.type == "list":
                projected = count_tokens("\n\n".join(cur_parts + [u.text])) if cur_parts else count_tokens(u.text)
                if cur_parts and projected > self.max_chunk_tokens and cur_tokens() >= self.min_chunk_tokens:
                    finalize()
                    cur_reason = "size_limit"
                cur_parts.append(u.text)
                cur_pages.update(range(u.page_start, u.page_end + 1))
                continue

            projected = count_tokens("\n\n".join(cur_parts + [u.text])) if cur_parts else count_tokens(u.text)
            if cur_parts:
                if (
                    u.topic_break == "soft"
                    and cur_tokens() >= self.min_chunk_tokens
                    and projected > self.max_chunk_tokens * 0.6
                ):
                    finalize()
                    cur_reason = "topic_shift"
                elif projected > self.max_chunk_tokens and cur_tokens() >= self.min_chunk_tokens:
                    finalize()
                    cur_reason = "size_limit"

            cur_parts.append(u.text)
            cur_pages.update(range(u.page_start, u.page_end + 1))

        finalize()

     
        merged: List[Chunk] = []
        for c in chunks:
            if (
                merged
                and c.token_estimate < self.min_chunk_tokens
                and c.chunk_type != "table"
                and merged[-1].chunk_type != "table"
            ):
                prev = merged[-1]
                prev.text = prev.text + "\n\n" + c.text
                prev.page_end = max(prev.page_end, c.page_end)
                prev.token_estimate = count_tokens(prev.text)
                if not prev.heading_path and c.heading_path:
                    prev.heading_path = c.heading_path
            else:
                merged.append(c)

        for i, c in enumerate(merged):
            c.chunk_id = i

        if self.overlap_tokens > 0:
            for i in range(1, len(merged)):
                words = merged[i - 1].text.split()
                tail = words[-self.overlap_tokens:] if len(words) > self.overlap_tokens else words
                if tail:
                    merged[i].text = " ".join(tail) + "\n\n" + merged[i].text
                    merged[i].token_estimate = count_tokens(merged[i].text)

        self.chunks = merged

    def _build_report(self) -> None:
        self.report.update(dict(
            num_pages=len(self.doc),
            num_lines=len(self.lines),
            body_font_size=self.profile["body_size"],
            body_font=self.profile["body_font"],
            median_line_gap=round(self.profile["median_line_gap"], 2),
            num_headings=len(self.headings),
            num_tables=sum(len(v) for v in self.table_bboxes.values()),
            num_header_footer_lines=sum(1 for l in self.lines if l.is_header_footer),
            num_page_number_lines=sum(1 for l in self.lines if l.is_page_number),
            num_rotated_or_watermark_lines=sum(1 for l in self.lines if l.rotated),
            num_chunks=len(self.chunks),
        ))

    def outline(self) -> List[Dict[str, Any]]:
        return [
            {
                "level": h.level,
                "text": h.text,
                "page": h.page + 1,
                "numbering": h.numbering,
            }
            for h in self.headings
        ]

    def chunks_as_dicts(self) -> List[Dict[str, Any]]:
        return [
            dict(
                chunk_id=c.chunk_id,
                heading_path=c.heading_path,
                page_range=[c.page_start + 1, c.page_end + 1],
                chunk_type=c.chunk_type,
                token_estimate=c.token_estimate,
                boundary_reason=c.boundary_reason,
                text=c.text,
            )
            for c in self.chunks
        ]

    def export_json(self, path: str) -> Dict[str, Any]:
        data = {
            "report": self.report,
            "outline": self.outline(),
            "chunks": self.chunks_as_dicts(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

def main():
    import argparse

    ap = argparse.ArgumentParser(
        description="Analyze a business-report PDF for headings, topic changes, and chunking."
    )
    ap.add_argument("pdf", help="Path to the input PDF")
    ap.add_argument("-o", "--output", help="Write full JSON result to this path")
    ap.add_argument("--max-tokens", type=int, default=450, help="Max tokens per chunk")
    ap.add_argument("--min-tokens", type=int, default=80, help="Min tokens per chunk")
    ap.add_argument("--overlap", type=int, default=0, help="Token overlap between chunks")
    ap.add_argument("--show-outline", action="store_true", help="Print the heading outline")
    ap.add_argument("--show-chunks", action="store_true", help="Print a preview of each chunk")
    args = ap.parse_args()

    analyzer = PDFReportAnalyzer(
        args.pdf,
        max_chunk_tokens=args.max_tokens,
        min_chunk_tokens=args.min_tokens,
        overlap_tokens=args.overlap,
    ).run()

    if analyzer.report.get("empty_or_scanned"):
        print("No extractable text found -- this PDF may be scanned/image-only.")
        print("Run OCR (e.g. PyMuPDF's textpage OCR mode, or an external OCR tool) first.")
        return

    if args.show_outline:
        print("\n=== HEADING OUTLINE ===")
        for h in analyzer.outline():
            indent = "  " * max(h["level"], 0)
            num = f"[{h['numbering']}] " if h["numbering"] else ""
            print(f"{indent}H{h['level']} (p.{h['page']:>3}) {num}{h['text']}")
        print()

    print("=== SUMMARY ===")
    for k, v in analyzer.report.items():
        print(f"{k}: {v}")

    if args.show_chunks:
        print("\n=== CHUNKS ===")
        for c in analyzer.chunks_as_dicts():
            path = " > ".join(c["heading_path"]) or "(no heading)"
            preview = c["text"].replace("\n", " ")[:120]
            print(
                f"[{c['chunk_id']:>3}] type={c['chunk_type']:<9} "
                f"pages={c['page_range']} tokens~{c['token_estimate']:<5} "
                f"reason={c['boundary_reason']:<12} | {path}"
            )
            print(f"      {preview}...")

    if args.output:
        analyzer.export_json(args.output)
        print(f"\nWrote full results to {args.output}")


if __name__ == "__main__":
    main()
