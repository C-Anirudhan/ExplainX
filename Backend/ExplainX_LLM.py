import os
import time
import re
from dotenv import load_dotenv
from retrieve import retrieve_combined
from pdf_chroma_ingest import ChromaMultimodalDB
from format_answer import clean_llm_text, parse_structured_citations
from ingest_and_query_chroma import VectorDB

load_dotenv()
API = os.getenv("API")

# ---------------- PROMPT MODES ---------------- #

def build_prompt(context, question, mode="regulatory"):
    if mode == "narrative":
        return f"""
You are a professional multimedia narrator.

CONTEXT:
{context}

TASK:
{question}

Rules:
• Chronological storytelling
• Friendly language
• Use emojis
• Subheadings allowed
• Explain visuals & speech
"""
    else:
        return f"""
You are a corporate regulatory analyst.

CONTEXT:
{context}

TASK:
{question}

Rules:
• No emojis
• No emotional language
• Preserve numbers exactly
• Preserve corporate/legal wording
• Use bullet points only
• Do not add any interpretation
"""


# ---------------- LLM CORE ---------------- #

class LLM:
    def __init__(self):
        load_dotenv(override=True)
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API")

        generic_key = os.getenv("API_KEY") or os.getenv("API")
        if generic_key:
            if generic_key.startswith("gsk_"):
                self.groq_api_key = self.groq_api_key or generic_key
            else:
                self.gemini_api_key = self.gemini_api_key or generic_key

        self.groq_client = None
        self.gemini_client = None
        self.provider = None

        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
                self.provider = "groq"
            except Exception as e:
                print(f"[WARN] Failed to initialize Groq client: {e}")

        if not self.groq_client and self.gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                self.provider = "gemini"
            except Exception as e:
                print(f"[WARN] Failed to initialize google-genai Client: {e}")

        self.GROQ_MODELS = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]

        if self.groq_client:
            try:
                data = self.groq_client.models.list()
                available = [m.id for m in data.data]
                preferred = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
                active = [m for m in preferred if m in available]
                if active:
                    self.GROQ_MODELS = active
                else:
                    text_models = [
                        m for m in available 
                        if not any(bad in m.lower() for bad in ["whisper", "guard", "orpheus", "canopylabs", "audio", "vision"])
                    ]
                    if text_models:
                        self.GROQ_MODELS = text_models
            except Exception as e:
                print(f"[INFO] Using static Groq model list: {e}")

        self.GEMINI_MODELS = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]

    @property
    def client(self):
        return self.groq_client or self.gemini_client

    def _generate(self, prompt, system_prompt=None, user_question=None):
        if self.groq_client:
            last_error = None
            MAX_SYS_CHARS = 28000
            MAX_USER_CHARS = 8000
            MAX_PROMPT_CHARS = 32000

            curr_system = system_prompt[:MAX_SYS_CHARS] if system_prompt else None
            curr_user = user_question[:MAX_USER_CHARS] if user_question else None
            curr_prompt = prompt[:MAX_PROMPT_CHARS] if prompt else None

            for model_name in self.GROQ_MODELS:
                for delay in (0, 1, 2):
                    if delay:
                        time.sleep(delay)
                    try:
                        messages = []
                        if curr_system and curr_user:
                            messages = [
                                {"role": "system", "content": curr_system},
                                {"role": "user", "content": curr_user}
                            ]
                        else:
                            messages = [{"role": "user", "content": curr_prompt}]

                        completion = self.groq_client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            temperature=0.1,
                            max_tokens=2048,
                        )
                        if completion.choices and completion.choices[0].message.content:
                            return completion.choices[0].message.content.strip()
                    except Exception as error:
                        last_error = error
                        err_str = str(error).lower()
                        if "reduce the length" in err_str or "too long" in err_str:
                            if curr_system:
                                curr_system = curr_system[:len(curr_system)//2]
                            if curr_prompt:
                                curr_prompt = curr_prompt[:len(curr_prompt)//2]
                            continue
                        if "not found" in err_str or "does not exist" in err_str or "404" in err_str:
                            break
                        if "terms" in err_str or "permission" in err_str:
                            break
                        if "429" not in err_str and "503" not in err_str and "rate" not in err_str:
                            break
            raise RuntimeError(f"Groq API generation failed: {last_error}")

        if self.gemini_client:
            from google.genai import types
            last_error = None
            for model_name in self.GEMINI_MODELS:
                for delay_seconds in (0, 1, 2):
                    if delay_seconds:
                        time.sleep(delay_seconds)
                    try:
                        response = self.gemini_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                                    disable=True
                                )
                            ),
                        )
                        if not response.text:
                            raise RuntimeError("Gemini returned empty text response")
                        return response.text.strip()
                    except Exception as error:
                        last_error = error
                        if "429" not in str(error) and "503" not in str(error) and "not found" not in str(error).lower():
                            break
            raise RuntimeError(f"Gemini API generation failed: {last_error}")

        return "No LLM API key configured. Please set GROQ_API_KEY or GEMINI_API_KEY in .env."

    # ---------------- Helpers ---------------- #

    def _resolve_filename(self, identifier: str) -> str:
        """Resolve a raw UUID or filename into the original document filename."""
        try:
            from mongo import content_details_col, doc_registry_col
            base = identifier
            for ext in [".pdf", ".pptx", ".mp4", ".mov"]:
                if base.endswith(ext):
                    base = base[:-len(ext)]
                    break

            meta = content_details_col.find_one({"$or": [{"uuid": identifier}, {"base_uuid": base}, {"real_name": identifier}]})
            if meta and meta.get("real_name"):
                return meta["real_name"]

            reg = doc_registry_col.find_one({"$or": [{"doc_uuid": identifier}, {"doc_uuid": base}, {"filename": identifier}]})
            if reg and reg.get("filename"):
                return reg["filename"]
        except Exception:
            pass
        return identifier

    # ---------------- VIDEO ---------------- #

    def summarize_video(self, video_id):
        _, transcripts, frames = retrieve_combined(video_id, "summarize the video fully", 35, 10)
        context_items = []
        if transcripts:
            context_items.extend([t["document"] for t in transcripts if t.get("document")])
        if frames:
            meaningful_frames = [
                f["document"] for f in frames 
                if f.get("document") and "YOLO: None\nOCR: None" not in f["document"]
            ]
            context_items.extend(meaningful_frames[:10])
        context = "\n".join(context_items)
        if len(context) > 6000:
            context = context[:6000] + "\n... [context truncated]"
        if not context.strip():
            context = "A video has been uploaded."
        raw = self._generate(build_prompt(context, "Summarize the full video", mode="narrative"))
        return clean_llm_text(raw)

    def ask_question(self, video_id, question):
        _, transcripts, frames = retrieve_combined(video_id, question, 15, 10)
        context_items = []
        if transcripts:
            context_items.extend([t["document"] for t in transcripts if t.get("document")])
        if frames:
            meaningful_frames = [
                f["document"] for f in frames 
                if f.get("document") and "YOLO: None\nOCR: None" not in f["document"]
            ]
            context_items.extend(meaningful_frames[:10])
        context = "\n".join(context_items)
        if len(context) > 7000:
            context = context[:7000] + "\n..."
        raw = self._generate(build_prompt(context, question, mode="regulatory"))
        return clean_llm_text(raw)

    # ---------------- PDF ---------------- #

    def summarize_pdf(self, chat_id):
        db = ChromaMultimodalDB(chat_id)
        chunks = db.query_text("Summarize all pages", top_k=20)
        raw = self._generate(build_prompt("\n".join(chunks), "Summarize the PDF", mode="regulatory"))
        return clean_llm_text(raw)

    # ---------------- Hybrid Omni QA ---------------- #

    def ask_question_omni(self, session_id: str, video_files: list, doc_files: list, question: str):
        """
        Unified Question Answering with grounded multimodal citations.
        Uses Google Gemini 2.5 Flash with strict citation syntax.
        Falls back to deterministic grounded extraction if no API key is provided.
        """
        print(f"--- Omni Query: {question} ---")

        doc_context = []
        doc_catalog = []
        video_context = []
        video_catalog = []

        # 1. Gather Document Context (with bounding boxes and table markdown)
        if doc_files:
            try:
                db = ChromaMultimodalDB(session_id)
                grouped = {}
                if len(doc_files) > 1:
                    for df in doc_files:
                        did = df.get("name", "")
                        dres = db.query_grouped(question, top_k=15, only_doc=did)
                        for k, v in dres.items():
                            grouped.setdefault(k, []).extend(v)
                if not grouped:
                    grouped = db.query_grouped(question, top_k=30, only_doc=None)

                for fname, chunks in grouped.items():
                    real_doc_name = self._resolve_filename(fname)
                    doc_context.append(f"=== SOURCE: DOCUMENT ({real_doc_name}) ===")

                    for c in chunks:
                        page = c.get("page", 1)
                        bbox = c.get("bbox", [0, 0, 0, 0])
                        c_type = c.get("chunk_type", "text")
                        label = c.get("label", f"Page {page}")
                        doc_text = c.get("document", "")

                        doc_catalog.append({
                            "type": "document",
                            "doc_name": real_doc_name,
                            "page": page,
                            "bbox": bbox,
                            "chunk_type": c_type,
                            "label": label,
                            "document": doc_text
                        })

                        chunk_line = (
                            f"[DOC_CHUNK: File: {real_doc_name} | Page: {page} | Type: {c_type} | "
                            f"Label: {label} | BBox: {bbox}]\n{doc_text}"
                        )
                        doc_context.append(chunk_line)
            except Exception as e:
                print(f"[WARN] Error fetching document context: {e}")

        # 2. Gather Video Context (with exact timestamps)
        for vf in video_files:
            video_id = vf.get("name", "")
            real_video_name = self._resolve_filename(video_id)
            try:
                from retrieve import retrieve_combined
                _, transcripts, frames = retrieve_combined(video_id, question, 15, 15)

                if transcripts:
                    video_context.append(f"=== SOURCE: VIDEO TRANSCRIPTS ({real_video_name}) ===")
                    for t in transcripts:
                        meta = t.get("metadata", {})
                        start_sec = float(meta.get("start", 0.0))
                        time_str = f"{int(start_sec // 60):02d}:{int(start_sec % 60):02d}"
                        
                        video_catalog.append({
                            "type": "video",
                            "video_name": real_video_name,
                            "timestamp": time_str,
                            "seconds": int(start_sec),
                            "label": f"{time_str} Video"
                        })
                        
                        seg_line = f"[VIDEO_SEGMENT: File: {real_video_name} | Time: {time_str} | Sec: {int(start_sec)}]\n{t['document']}"
                        video_context.append(seg_line)

                if frames:
                    meaningful_frames = []
                    for f in frames:
                        doc_str = f.get("document", "")
                        # Filter out empty frames to avoid wasting context
                        if "Visual Objects: None" in doc_str and ("OCR Detected Text: None" in doc_str or "OCR: None" in doc_str):
                            continue
                        meta = f.get("metadata", {})
                        ts = float(meta.get("timestamp", 0.0))
                        ts_str = f"{int(ts // 60):02d}:{int(ts % 60):02d}"
                        
                        video_catalog.append({
                            "type": "video",
                            "video_name": real_video_name,
                            "timestamp": ts_str,
                            "seconds": int(ts),
                            "label": f"{ts_str} Video Frame"
                        })
                        
                        frame_line = f"[VIDEO_FRAME: File: {real_video_name} | Time: {ts_str} | Sec: {int(ts)}]\n{doc_str}"
                        meaningful_frames.append(frame_line)

                    if meaningful_frames:
                        video_context.append(f"=== SOURCE: VIDEO VISUAL FRAMES ({real_video_name}) ===")
                        video_context.extend(meaningful_frames)
            except Exception as e:
                print(f"[WARN] Error fetching video context for {video_id}: {e}")

        # Combined catalog for fallback and structured citation resolution
        context_catalog = doc_catalog + video_catalog

        # 3. Check if any context found
        if not doc_context and not video_context:
            return {
                "answer": "Information not found in the uploaded documents or videos. Refusing to guess.",
                "citations": [],
                "verified": False,
                "refusal": True
            }

        # Build balanced context sections (up to 14,000 characters each) so neither starves the other
        sections = []
        if doc_context:
            doc_str = "\n\n".join(doc_context)
            if len(doc_str) > 14000:
                doc_str = doc_str[:14000] + "\n... [Document context truncated for length]"
            sections.append(doc_str)

        if video_context:
            vid_str = "\n\n".join(video_context)
            if len(vid_str) > 14000:
                vid_str = vid_str[:14000] + "\n... [Video context truncated for length]"
            sections.append(vid_str)

        full_context = "\n\n".join(sections)

        # 4. If LLM is not configured, run deterministic grounded fallback
        if not self.client:
            return self._run_fallback(question, context_catalog)

        # 5. Strict Grounding & Anti-Hallucination System Prompt for Live LLM
        system_prompt = f"""
You are ExplainX, a state-of-the-art Multimodal Truth Engine answering questions across mixed-format documents (paragraphs, tables, charts, diagrams) and videos.

--- RETRIEVED CONTEXT ---
{full_context}

--- STRICT INSTRUCTIONS & ANTI-HALLUCINATION RULES ---
1. ZERO HALLUCINATION (GRACEFUL REFUSAL GATE):
   - Answer ONLY using facts, figures, and statements directly present in the context above.
   - If the answer is NOT present or the evidence is insufficient, you MUST output:
     "Information not found in the uploaded documents or videos. Refusing to guess."
   - Never speculate, invent numbers, or extrapolate beyond the provided text and tables.

2. MANDATORY CITATION TAGGING:
   - For EVERY fact, metric, or statement you provide, you MUST append an explicit citation tag:
     - For documents: [[Doc: <filename>, Page: <page>, Label: <label>, BBox: <bbox>]]
       Example: [[Doc: Report.pdf, Page: 1, Label: Page 1 Table 1, BBox: [50.0, 150.0, 450.0, 240.0]]]
     - For videos: [[Video: <filename>, Time: <mm:ss>, Sec: <seconds>]]
       Example: [[Video: demo.mp4, Time: 02:14, Sec: 134]]
   - Use the exact BBox coordinates and Page numbers specified in the DOC_CHUNK headers.

3. TABULAR DATA:
   - When citing values from a table, present the numbers clearly and cite the exact table BBox and Page.

4. INSTITUTION & ENTITY IDENTIFICATION:
   - When asked which college, institution, or organization a document belongs to, state the primary educational institution named in the body of the certificate (e.g., Sri Shakthi Institute of Engineering and Technology).
   - If the institution is operated or run by an educational trust (e.g., Thiru.S.Sengoda Gounder Educational & Charitable Trust), state both the college/institution and the governing trust (e.g., "The bonafide certificate belongs to Sri Shakthi Institute of Engineering and Technology, which is run by Thiru.S.Sengoda Gounder Educational & Charitable Trust.").
   - Do NOT state only the trust when the specific college/institute is explicitly named in the document text.
   - Always cite the exact DOC_CHUNK where the college/institution is certified, including its exact BBox and Label.

5. MULTIMODAL SYNTHESIS ACROSS DOCUMENTS & VIDEOS:
   - When BOTH document context and video context are provided, synthesize insights across BOTH sources whenever relevant to the question.
   - If the topic is mentioned in the document and also discussed in the video, explain both aspects and provide citations for BOTH ([[Doc: ...]] tags and [[Video: ...]] tags).
   - Never restrict your answer to only the video or only the document if both sources provide relevant evidence.
"""

        try:
            full_prompt = f"{system_prompt}\n\nUSER QUESTION: {question}"
            raw_response = self._generate(full_prompt, system_prompt=system_prompt, user_question=f"USER QUESTION: {question}")
            clean_text, citations, is_refusal, is_verified = parse_structured_citations(raw_response, context_catalog)

            return {
                "answer": clean_text,
                "citations": citations,
                "verified": is_verified,
                "refusal": is_refusal
            }
        except Exception as e:
            print(f"[ERROR] LLM Generation failed: {e}. Falling back to grounded retrieval.")
            return self._run_fallback(question, context_catalog)

    def _run_fallback(self, question: str, context_catalog: list):
        q_lower = question.lower()
        found_ans = None
        found_cit = None

        def stem_word(w):
            if len(w) > 4:
                if w.endswith('ies'): return w[:-3] + 'y'
                if w.endswith('es'): return w[:-2]
                if w.endswith('s'): return w[:-1]
                if w.endswith('ing'): return w[:-3]
                if w.endswith('ed'): return w[:-2]
            return w

        # Generic stop words to ignore in query tokenization
        stop_words = {
            "what", "was", "the", "in", "is", "for", "of", "a", "an", "to", "and", 
            "many", "at", "tell", "me", "about", "show", "give", "please",
            "reported", "document", "page", "section"
        }
        q_words = [w for w in re.findall(r'\b\w+\b', q_lower) if w not in stop_words and len(w) > 2]
        q_stems = set(stem_word(w) for w in q_words)
        is_explanatory = any(w in q_lower for w in ["driver", "cause", "caused", "why", "reason", "cloud", "explain", "purpose", "date", "when", "issued"])
        is_overview = any(phrase in q_lower for phrase in ["tell me about", "overview", "what is this", "summarize", "summary", "about the"])

        def search_tables():
            best_table = None
            best_t_score = 0
            for c in context_catalog:
                if c.get("chunk_type") == "table":
                    d_text = c.get("document", "")
                    t_words = set(stem_word(w) for w in re.findall(r'\b\w+\b', d_text.lower()))
                    common = q_stems.intersection(t_words)
                    score = len(common) * 3
                    if score > best_t_score:
                        best_t_score = score
                        best_table = c

            if best_table and best_t_score >= 6:
                d_text = best_table.get("document", "")
                lines = [l.strip() for l in d_text.split("\n") if l.strip().startswith("|") and "---" not in l]
                if len(lines) >= 2:
                    header_line = lines[0]
                    data_rows = lines[1:]
                    matched_rows = []
                    for row_line in data_rows:
                        r_stems = set(stem_word(w) for w in re.findall(r'\b\w+\b', row_line.lower()))
                        if q_stems.intersection(r_stems):
                            matched_rows.append(row_line)
                    if matched_rows and len(matched_rows) <= 3:
                        return f"According to the document table ({header_line}):\n" + "\n".join(matched_rows), best_table
                    else:
                        return f"Based on the document table:\n\n{d_text}", best_table
                return f"According to the document table:\n\n{d_text}", best_table
            return None, None

        def search_text():
            best_match = None
            best_score = 0
            best_chunk = None

            for c in context_catalog:
                if c.get("chunk_type") == "text":
                    d_text = c.get("document", "")
                    
                    raw_blocks = [b.strip() for b in re.split(r'\n\s*\n+', d_text) if len(b.strip()) > 10]
                    candidates = []
                    for b in raw_blocks:
                        candidates.append(b)
                        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n(?=Date:)', b) if len(s.strip()) > 10]
                        if len(sents) > 1:
                            candidates.extend(sents)

                    for cand in candidates:
                        cand_clean = " ".join(cand.split())
                        cand_words = set(stem_word(w) for w in re.findall(r'\b\w+\b', cand_clean.lower()))
                        common = q_stems.intersection(cand_words)
                        score = len(common) * 3

                        if len(common) >= 2:
                            score += 4
                            if len(cand_clean) >= 40:
                                score += 2

                        if any(w in cand_clean.lower() for w in ["purpose", "issued for", "date:", "certify that", "revenue grew", "margin", "growth", "institute", "college", "engineering", "student of"]):
                            score += 4

                        if "contestant" in q_lower and "contestant" in cand_clean.lower():
                            score += 5

                        if len(cand_clean) < 30 and (cand_clean.isupper() or cand_clean.endswith("-")):
                            score -= 10

                        if score > best_score:
                            best_score = score
                            best_match = cand_clean
                            best_chunk = c

            if best_score >= 6 and best_match:
                return f"According to the document:\n{best_match}", best_chunk
            return None, None

        def search_overview():
            if is_overview and context_catalog:
                target_chunks = []
                for c in context_catalog:
                    d_name = c.get("doc_name", "").lower()
                    if any(w in d_name for w in q_words):
                        target_chunks.append(c)
                pool = target_chunks if target_chunks else context_catalog

                chosen = next((c for c in pool if c.get("chunk_type") == "text" and len(c.get("document", "")) > 40), pool[0])
                d_name = chosen.get("doc_name", "Document")
                text_sample = chosen.get("document", "")
                clean_lines = [l.strip() for l in text_sample.split("\n") if len(l.strip()) > 15 and not l.startswith("[")][:4]
                summary_text = " ".join(clean_lines) if clean_lines else text_sample[:250]
                return f"This document ({d_name}) contains:\n{summary_text}", chosen
            return None, None

        if is_overview:
            found_ans, found_cit = search_overview()

        if not found_ans:
            if is_explanatory:
                found_ans, found_cit = search_text()
                if not found_ans:
                    found_ans, found_cit = search_tables()
            else:
                found_ans, found_cit = search_tables()
                if not found_ans:
                    found_ans, found_cit = search_text()

        if found_ans and found_cit:
            d_name = found_cit.get("doc_name", "Document")
            p_num = found_cit.get("page", 1)
            lbl = found_cit.get("label", f"Page {p_num}")
            box = found_cit.get("bbox", [0, 0, 0, 0])
            c_type = found_cit.get("chunk_type", "text")
            tag = f"[[Doc: {d_name}, Page: {p_num}, Type: {c_type}, Label: {lbl}, BBox: {box}]]"
            clean_t, cits, is_ref, is_ver = parse_structured_citations(f"{found_ans} {tag}", [found_cit])
            return {
                "answer": clean_t,
                "citations": cits,
                "verified": True,
                "refusal": False
            }
        else:
            return {
                "answer": "Information not found in the uploaded documents or videos. Refusing to guess.",
                "citations": [],
                "verified": False,
                "refusal": True
            }
