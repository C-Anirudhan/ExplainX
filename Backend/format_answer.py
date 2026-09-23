import re
import json

def clean_llm_text(text: str) -> str:
    """Normalize whitespace and paragraph formatting."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n\s*\n(?=\$)', '\n\n', text)
    text = re.sub(r'(?<=\$)\n\s*\n', '\n\n', text)
    text = re.sub(r'\n\s*•', '\n•', text)
    text = re.sub(r'\n\s*-\s+', '\n- ', text)
    return text.strip()


def parse_structured_citations(raw_text: str, context_catalog: list = None):
    """
    Parses structured citation tags from raw LLM output into clean text and interactive citation pills.
    
    Supported Citation Tags in LLM Text:
      - [[Doc: Report.pdf, Page: 1, Label: Page 1 Table 1, BBox: [50.0, 150.0, 450.0, 240.0]]]
      - [[Video: presentation.mp4, Time: 02:14, Sec: 134]]
      - [Doc: Report.pdf P.1 Table 1]
      - [Video: 02:14]
    
    Returns:
      (clean_display_text, citations_list, is_refusal, is_verified)
    """
    if not raw_text:
        return "", [], False, False

    citations = []
    citation_id_map = {}
    citation_counter = 1

    # Check for refusal / abstention patterns
    refusal_patterns = [
        "information not found in the uploaded",
        "not found in the uploaded documents",
        "refusing to guess",
        "insufficient evidence",
        "not mentioned in the context",
        "no relevant information found"
    ]
    is_refusal = any(p in raw_text.lower() for p in refusal_patterns)

    # 1. Parse double-bracket explicit tags: [[Doc: ...]] or [[Video: ...]]
    def replace_double_bracket(match):
        nonlocal citation_counter
        content = match.group(1).strip()

        if content.lower().startswith("doc:"):
            # Format: Doc: <name>, Page: <page>, Label: <label>, BBox: <bbox>
            doc_name = "Document"
            page = 1
            label = "Document Source"
            bbox = [0, 0, 0, 0]
            chunk_type = "text"

            # Extract BBox cleanly with regex before comma-splitting
            bbox_match = re.search(r'bbox:\s*(\[[^\]]+\])', content, re.IGNORECASE)
            if bbox_match:
                try:
                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", bbox_match.group(1))
                    if len(nums) >= 4:
                        bbox = [float(x) for x in nums[:4]]
                except Exception:
                    pass
                content = content[:bbox_match.start()] + content[bbox_match.end():]

            parts = [p.strip() for p in content.split(",") if p.strip()]
            for p in parts:
                if ":" in p:
                    k, v = p.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in ["doc", "name", "file"]:
                        doc_name = v
                    elif k in ["page", "p"]:
                        try: page = int(re.sub(r'[^0-9]', '', v))
                        except Exception: pass
                    elif k in ["label", "tag"]:
                        label = v
                    elif k in ["type"]:
                        chunk_type = v

            pill_key = f"{doc_name}_{page}_{label}"
            if pill_key not in citation_id_map:
                cid = citation_counter
                citation_counter += 1
                cit_obj = {
                    "id": cid,
                    "type": "document",
                    "doc_name": doc_name,
                    "page": page,
                    "bbox": bbox,
                    "chunk_type": chunk_type,
                    "label": label
                }
                citations.append(cit_obj)
                citation_id_map[pill_key] = cid
            else:
                cid = citation_id_map[pill_key]

            return f" [{label}]"

        elif content.lower().startswith("video:"):
            # Format: Video: <name>, Time: <mm:ss>, Sec: <seconds>
            video_name = "Video"
            time_str = "00:00"
            seconds = 0

            parts = [p.strip() for p in content.split(",")]
            for p in parts:
                if ":" in p:
                    k, v = p.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in ["video", "name"]:
                        video_name = v
                    elif k in ["time", "ts", "timestamp"]:
                        time_str = v
                    elif k in ["sec", "seconds"]:
                        try: seconds = int(float(v))
                        except Exception: pass

            if seconds == 0 and ":" in time_str:
                try:
                    m, s = time_str.split(":")
                    seconds = int(m) * 60 + int(s)
                except Exception:
                    pass

            label = f"{time_str} Video"
            pill_key = f"{video_name}_{seconds}"
            if pill_key not in citation_id_map:
                cid = citation_counter
                citation_counter += 1
                cit_obj = {
                    "id": cid,
                    "type": "video",
                    "video_name": video_name,
                    "timestamp": time_str,
                    "seconds": seconds,
                    "label": label
                }
                citations.append(cit_obj)
                citation_id_map[pill_key] = cid
            else:
                cid = citation_id_map[pill_key]

            return f" [{label}]"

        return match.group(0)

    # Replace [[...]] tags (supporting nested [ ... ] in BBox and optional extra closing bracket)
    processed_text = re.sub(r'\[\[((?:\[[^\]]*\]|[^\]])+)\]\]+', replace_double_bracket, raw_text)

    # 2. If no explicit double-bracket tags, match context catalog items if provided
    if not citations and context_catalog and not is_refusal:
        for idx, item in enumerate(context_catalog[:5], start=1):
            if item.get("chunk_type") == "table":
                citations.append({
                    "id": idx,
                    "type": "document",
                    "doc_name": item.get("doc_name", "Document"),
                    "page": item.get("page", 1),
                    "bbox": item.get("bbox", [0, 0, 0, 0]),
                    "chunk_type": "table",
                    "label": item.get("label", f"Page {item.get('page', 1)} Table")
                })
            elif "seconds" in item:
                citations.append({
                    "id": idx,
                    "type": "video",
                    "video_name": item.get("video_name", "Video"),
                    "timestamp": item.get("timestamp", "00:00"),
                    "seconds": item.get("seconds", 0),
                    "label": item.get("label", f"{item.get('timestamp')} Video")
                })

    is_verified = (len(citations) > 0 and not is_refusal)

    return clean_llm_text(processed_text), citations, is_refusal, is_verified
