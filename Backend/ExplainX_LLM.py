import google.generativeai as genai
from retrieve import retrieve_combined
from pdf_chroma_ingest import ChromaMultimodalDB
from dotenv import load_dotenv
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
API = os.getenv("API")

# Validate API key is configured
if not API:
    logger.error("CRITICAL: Google API key is not configured!")
    logger.error("Please set the API environment variable with your Google Gemini API key")
    logger.error("Get one from: https://ai.google.dev/")
    raise ValueError("Missing required environment variable: API")

class LLM:
    def __init__(self):
        if not API:
            raise ValueError("Google API key not configured. Set the API environment variable.")
        
        try:
            genai.configure(api_key=API)
            self.MODEL_NAME = "models/gemini-2.5-flash"
        except Exception as e:
            logger.error(f"Failed to configure Google Generative AI: {str(e)}")
            raise


    def summarize_video(self,video_id):

        print("\n[INFO] Retrieving relevant transcript + frame chunks...")
        combined_text, transcripts, frames = retrieve_combined(
            video_id,
            top_k_transcript=500,
            top_k_frames=500,
            question="summarize the video fully"
        )

        print(f"[INFO] Transcript chunks retrieved: {len(transcripts)}")
        print(f"[INFO] Frame chunks retrieved: {len(frames)}")

        # Extract actual text from dicts
        transcript_texts = [t["document"] for t in transcripts]
        frame_texts = [f["document"] for f in frames]

        # Build final LLM message
        prompt = f"""
    You are an AI expert in video understanding and multimodal reasoning.

    Below is the retrieved context for a video.

    ==================== AUDIO TRANSCRIPTS ====================
    {chr(10).join(transcript_texts)}

    ==================== FRAME (YOLO + OCR) DATA ====================
    {chr(10).join(frame_texts)}

    ==================== TASK ====================
    Create a full, detailed summary of the video.

    Requirements:
    1. Chronological summary covering the entire video.
    2. Use BOTH transcript + YOLO/OCR frame data,but dont mention any YOLO/OCR words directly in any part of explanation.
    3. Understand the video yourself by combining transcription and YOLO/OCR data.
    4. Describe what visually happens in each part.
    5. Explain what is spoken, what objects appear, and any scene transitions.
    6. Write naturally like a human narrator.
    7. Don't give output as big paragraphs instead give output as points.Give sub heading for some content if required. 
    8. Use bulletin points to indicate the starting of a point. Use emojis for interactive conversation.

    Start now.
    """

        print("[INFO] Sending to LLM for summarization...")
        model = genai.GenerativeModel(self.MODEL_NAME)
        response = model.generate_content(prompt)


        return response.text
    
    def ask_question(self,video_id,question):
        print("\n[INFO] Retrieving relevant transcript + frame chunks...")
        combined_text, transcripts, frames = retrieve_combined(
            video_id,
            top_k_transcript=200,
            top_k_frames=300,
            question=question
        )

        print(f"[INFO] Transcript chunks retrieved: {len(transcripts)}")
        print(f"[INFO] Frame chunks retrieved: {len(frames)}")

        # Extract actual text from dicts
        transcript_texts = [t["document"] for t in transcripts]
        frame_texts = [f["document"] for f in frames]

        # Build final LLM message
        prompt = f"""
    You are an AI expert in video understanding and multimodal reasoning.

    Below is the retrieved context for a video.

    ==================== AUDIO TRANSCRIPTS ====================
    {chr(10).join(transcript_texts)}

    ==================== FRAME (YOLO + OCR) DATA ====================
    {chr(10).join(frame_texts)}

    ==================== TASK ====================
    Answer the below question based on the video content.

    question: {question}

    Requirements:
    1. Correct answer for the question using the given data.
    2. Use BOTH transcript + YOLO/OCR frame data,but dont mention any YOLO/OCR words directly in any part of explanation.
    3. Understand the content yourself by combining transcription and YOLO/OCR data.
    4. Describe what visually happens.
    5. Explain what is spoken, what objects appear, and any scene transitions based on the question.
    6. Write naturally like a human narrator.
    7. Don't give output as big paragraphs instead give output as points.Give sub heading for some points if required.
    8. Use '**' to indicate the starting of a point. Use emojis for interactive conversation.

    Answer now.
    """

        print("[INFO] Sending to LLM for summarization...")
        model = genai.GenerativeModel(self.MODEL_NAME)
        response = model.generate_content(prompt)


        return response.text
    def summarize_pdf(self,video_id):
        print("\n[INFO] Retrieving relevant text + images...")
        db = ChromaMultimodalDB(video_id)
        res = db.query_text("Summarize all pages",top_k=8)

        print(f"[INFO] Text chunks retrieved")
        print(f"[INFO] Images retrieved")

        
        

    
        prompt = f"""
        You are an AI expert in pdf understanding and multimodal reasoning.

        Below is the retrieved context for a pdf.

        ==================== TEXT ====================
        {res}

        

        ==================== TASK ====================
        Create a full, detailed summary of the pdf.

        Requirements:
        1. Chronological summary covering the entire pdf.
        2. Understand the pdf yourself by text given to you.
        3. Describe what visually happens in each topic.
        4. Explain what is the content present in the pdf.
        5. Write naturally like a human narrator.
        6. Don't give output as big paragraphs instead give output as points.Give sub heading for some content if required. 
        7. Use '**' to indicate the starting of a point. Use emojis for interactive conversation.

        Start now.
        """

        print("[INFO] Sending to LLM for summarization...")
        model = genai.GenerativeModel(self.MODEL_NAME)
        response = model.generate_content(prompt)

        answer = str(response.text).replace('\n','\n\n')

        return answer
    
    def ask_question_ppt_pdf(self,video_id,question):
        print("\n[INFO] Retrieving relevant text + images...")
        db = ChromaMultimodalDB(video_id)
        res = db.query_text(question,top_k=10)

        print(f"[INFO] Text chunks retrieved from ask   ",res)
        print(f"[INFO] Images retrieved")
        # Build final LLM message
        prompt = f"""
    You are an AI expert in video understanding and multimodal reasoning.

    Below is the retrieved context for a video.

    ==================== TEXT ====================
    {res}

    ==================== TASK ====================
    Answer the below question based on the content.

    question: {question}

    Requirements:
    1. Correct answer for the question using the given data.
    2. Understand the content yourself using the TEXT provided.
    3. Describe what visually happens.
    4. Explain what is spoken  based on the question.
    5. Write naturally like a human narrator.
    6. Don't give output as big paragraphs instead give output as points.Give sub heading for some points if required.
    7. Use '**' to indicate the starting of a point. Use emojis for interactive conversation.

    Answer now.
    """

        print("[INFO] Sending to LLM for summarization...")
        model = genai.GenerativeModel(self.MODEL_NAME)
        response = model.generate_content(prompt)


        return response.text



# ----------------------------- MAIN -----------------------------
if __name__ == "__main__":
    test=LLM()
    print("📌 VIDEO SUMMARIZER (RAG + Gemini 2.5 Flash)")
    print("--------------------------------------------")

    video_name = input("Enter video name EXACTLY as stored in Chroma: ").strip()

    if not video_name:
        print("❌ Video name cannot be empty.")
    else:
        test.summarize_video(video_name)
