import os
import time
from google import genai
from google.genai import types
from retrieve import retrieve_combined
from pdf_chroma_ingest import ChromaMultimodalDB
from dotenv import load_dotenv
from mongo import sessions_col, content_details_col
from format_answer import clean_llm_text
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
        self.client = genai.Client(api_key=API)
        self.MODEL_NAME = "gemini-3.5-flash"
        self.FALLBACK_MODEL_NAME = "gemini-3.5-flash-lite"

    def _generate(self, prompt):
        last_error = None
        for model_name in (self.MODEL_NAME, self.FALLBACK_MODEL_NAME):
            for delay_seconds in (0, 1, 2):
                if delay_seconds:
                    time.sleep(delay_seconds)
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                                disable=True
                            )
                        ),
                    )
                    if not response.text:
                        raise RuntimeError("Gemini returned no text response")
                    return response.text.strip()
                except Exception as error:
                    last_error = error
                    if "429" not in str(error) and "503" not in str(error):
                        raise

        raise RuntimeError(
            "Gemini is temporarily unavailable after retrying both configured models."
        ) from last_error

    # ---------------- Helpers ---------------- #

    def _quick_answer(self, context, question):
        prompt = f"""
Use the context below to answer briefly.

CONTEXT:
{context}

QUESTION: {question}
"""
        return self._generate(prompt)

    def _final_answer(self, context, question):
        prompt = f"""
Use the context below to answer accurately.

CONTEXT:
{context}

QUESTION: {question}
"""
        return self._generate(prompt)

    # ---------------- VIDEO ---------------- #

    def summarize_video(self, video_id):
        _, transcripts, frames = retrieve_combined(video_id, "summarize the video fully", 500, 500)
        context = "\n".join([t["document"] for t in transcripts] + [f["document"] for f in frames])
        raw = self._generate(build_prompt(context, "Summarize the full video", mode="narrative"))
        return clean_llm_text(raw)

    def ask_question(self, video_id, question):
        _, transcripts, frames = retrieve_combined(video_id, question, 30, 30)
        context = "\n".join([t["document"] for t in transcripts] + [f["document"] for f in frames])
        raw = self._generate(build_prompt(context, question, mode="regulatory"))
        return clean_llm_text(raw)

    # ---------------- PDF ---------------- #

    def summarize_pdf(self, chat_id):
        db = ChromaMultimodalDB(chat_id)
        chunks = db.query_text("Summarize all pages", top_k=20)
        raw = self._generate(build_prompt("\n".join(chunks), "Summarize the PDF", mode="regulatory"))
        return clean_llm_text(raw)

    # ---------------- MULTI-DOC SMART QA ---------------- #

    def _resolve_filename(self, fname):
        doc = content_details_col.find_one({"$or": [{"uuid": fname}, {"base_uuid": fname}]})
        if doc and "real_name" in doc:
            return doc["real_name"]
        return fname

    def ask_question_omni(self, session_id, video_files, doc_files, question):
        print(f"--- Omni Query: {question} ---")
        
        all_context = []
        
        # 1. Gather Video Context
        for vf in video_files:
            video_id = vf["name"]
            try:
                # retrieve_combined returns (combined_text, transcripts, frames)
                from retrieve import retrieve_combined
                _, transcripts, frames = retrieve_combined(video_id, question, 15, 15)
                
                if transcripts:
                    real_video_name = self._resolve_filename(video_id)
                    all_context.append(f"--- SOURCE: VIDEO TRANSCRIPT ({real_video_name}) ---")
                    for t in transcripts:
                        all_context.append(t["document"])
                if frames:
                    all_context.append(f"--- SOURCE: VIDEO VISUALS ({real_video_name}) ---")
                    for f in frames:
                        all_context.append(f["document"])
            except Exception as e:
                print(f"Error fetching video context for {video_id}: {e}")
        
        # 2. Gather Document Context
        if doc_files:
            try:
                db = ChromaMultimodalDB(session_id)
                grouped = db.query_grouped(question, top_k=25, only_doc=None)
                
                for fname, chunks in grouped.items():
                    real_doc_name = self._resolve_filename(fname)
                    all_context.append(f"--- SOURCE: DOCUMENT ({real_doc_name}) ---")
                    all_context.extend(chunks)
            except Exception as e:
                print(f"Error fetching document context: {e}")
                
        if not all_context:
            return "No relevant information found in any uploaded documents or videos."
            
        full_context = "\n".join(all_context)
        
        system_prompt = f"""
You are a highly intelligent researcher assistant capable of synthesizing information from multiple sources.

You have access to context from multiple videos and documents. Each piece of context is prefixed with its SOURCE.

Your goal is to answer the user's question by COLLABORATING information from all available sources.

--- COMBINED CONTEXT ---
{full_context}

--- INSTRUCTIONS ---
- ALWAYS cite your sources based on the SOURCE provided (e.g., "According to document.pdf..." or "As seen in video.mp4...").
- If the answer spans multiple sources, synthesize the information and cite all relevant sources.
- If the answer is only found in one source, specify which source it came from.
- Do not hallucinate. If the answer isn't in the context, say so.
"""
        
        try:
            full_prompt_text = f"{system_prompt}\n\nUSER QUESTION: {question}"
            raw_response = self._generate(full_prompt_text)
            return clean_llm_text(raw_response)
        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return "I was unable to generate a response due to an internal error."
