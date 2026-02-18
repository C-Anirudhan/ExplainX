import os
import google.generativeai as genai
from retrieve import retrieve_combined
from pdf_chroma_ingest import ChromaMultimodalDB
from dotenv import load_dotenv
from mongo import sessions_col
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
        genai.configure(api_key=API)
        self.MODEL_NAME = "models/gemini-2.5-flash"

    # ---------------- Helpers ---------------- #

    def _quick_answer(self, context, question):
        prompt = f"""
Use the context below to answer briefly.

CONTEXT:
{context}

QUESTION: {question}
"""
        return genai.GenerativeModel(self.MODEL_NAME).generate_content(prompt).text.strip()

    def _final_answer(self, context, question):
        prompt = f"""
Use the context below to answer accurately.

CONTEXT:
{context}

QUESTION: {question}
"""
        return genai.GenerativeModel(self.MODEL_NAME).generate_content(prompt).text.strip()

    # ---------------- VIDEO ---------------- #

    def summarize_video(self, video_id):
        _, transcripts, frames = retrieve_combined(video_id, "summarize the video fully", 500, 500)
        context = "\n".join([t["document"] for t in transcripts] + [f["document"] for f in frames])
        raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(
            build_prompt(context, "Summarize the full video", mode="narrative")
        ).text
        return clean_llm_text(raw)

    def ask_question(self, video_id, question):
        _, transcripts, frames = retrieve_combined(video_id, question, 30, 30)
        context = "\n".join([t["document"] for t in transcripts] + [f["document"] for f in frames])
        raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(
            build_prompt(context, question, mode="regulatory")
        ).text
        return clean_llm_text(raw)

    # ---------------- PDF ---------------- #

    def summarize_pdf(self, chat_id):
        db = ChromaMultimodalDB(chat_id)
        chunks = db.query_text("Summarize all pages", top_k=20)
        raw = genai.GenerativeModel(self.MODEL_NAME).generate_content(
            build_prompt("\n".join(chunks), "Summarize the PDF", mode="regulatory")
        ).text
        return clean_llm_text(raw)

    # ---------------- MULTI-DOC SMART QA ---------------- #

    def ask_question_ppt_pdf(self, chat_id, question):
        session = sessions_col.find_one({"_id": chat_id})
        active_doc = session.get("active_doc")

        db = ChromaMultimodalDB(chat_id)
        grouped = db.query_grouped(question, only_doc=None)

        # Nothing found
        if not grouped:
            return "No relevant information found in the uploaded documents."

        # One document — auto-lock
        if len(grouped) == 1:
            fname, chunks = list(grouped.items())[0]
            sessions_col.update_one({"_id": chat_id}, {"$set": {"active_doc": fname}})
            return clean_llm_text(self._final_answer("\n".join(chunks), question))

        # Multiple docs — ask user
        msg = "Your question matches multiple documents:\n\n"
        for fname, chunks in grouped.items():
            short = self._quick_answer("\n".join(chunks[:6]), question)
            msg += f"• {fname}: {short}\n"
        msg += "\nPlease reply with the document name you meant."
        return clean_llm_text(msg)

    def ask_question_multimodal(self, session_id, video_filename, question):
        """
        Retrieves context from BOTH Video and PDF databases and fuses them.
        """
        print(f"--- Multimodal Query: {question} ---")

        # 1. Get Video Context
        # We try to use the VectorDB. If it fails or returns nothing, we warn the user.
        video_context = ""
        try:
            vid_db = VectorDB(video_filename)
            # Ensure your VectorDB class has a 'query' or 'similarity_search' method!
            # If your VectorDB uses 'similarity_search', change '.query' to '.similarity_search' below.
            vid_results = vid_db.query(session_id,question) 
            
            if isinstance(vid_results, list):
                # Handle list of objects (e.g., LangChain Documents)
                video_context = "\n".join([doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in vid_results])
            else:
                video_context = str(vid_results)
        except Exception as e:
            print(f"Error fetching video context: {e}")
            video_context = "No video context available due to error."

        # 2. Get PDF/PPT Context
        pdf_context = ""
        try:
            # We use filename="" because we query by session_id in ChromaMultimodalDB
            pdf_db = ChromaMultimodalDB(session_id) 
            
            # FIXED: Used 'query_text' to match your summarize_pdf method
            pdf_results = pdf_db.query_text(question, top_k=5)
            
            if isinstance(pdf_results, list):
                pdf_context = "\n".join(pdf_results)
            else:
                pdf_context = str(pdf_results)
        except Exception as e:
            print(f"Error fetching PDF context: {e}")
            pdf_context = "No document context available due to error."

        # 3. Construct the "Collaboration" System Prompt
        system_prompt = f"""
You are a highly intelligent researcher assistant capable of synthesizing information from multiple sources.

You have two distinct sources of information:
1. A VIDEO TRANSCRIPT (visual/auditory content).
2. A DOCUMENT (PDF/PPT slides or text).

Your goal is to answer the user's question by COLLABORATING information from both sources.

--- VIDEO CONTEXT ---
{video_context}

--- DOCUMENT CONTEXT ---
{pdf_context}

--- INSTRUCTIONS ---
- If the answer is found in both, mention how they support each other.
- If the answer is only in one, specify which source it came from.
- If the Video explains 'X' and the Document explains 'Y', synthesize them to explain 'X and Y'.
- Do not hallucinate. If the answer isn't in either context, say so.
        """

        # 4. Generate Answer using Gemini (FIXED: Added actual generation call)
        try:
            full_prompt = f"{system_prompt}\n\nUSER QUESTION: {question}"
            raw_response = genai.GenerativeModel(self.MODEL_NAME).generate_content(full_prompt).text
            return clean_llm_text(raw_response)
        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return "I was unable to generate a response due to an internal error."
