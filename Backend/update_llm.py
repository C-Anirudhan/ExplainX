import os

file_path = r'g:\Antigravity projects\MultiX\Backend\ExplainX_LLM.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We want to replace from '    def ask_question_ppt_pdf' to the end of the file.
start_idx = content.find('    def ask_question_ppt_pdf')
if start_idx != -1:
    new_methods = """    def ask_question_omni(self, session_id, video_files, doc_files, question):
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
                    all_context.append(f"--- SOURCE: VIDEO TRANSCRIPT ({video_id}) ---")
                    for t in transcripts:
                        all_context.append(t["document"])
                if frames:
                    all_context.append(f"--- SOURCE: VIDEO VISUALS ({video_id}) ---")
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
                    all_context.append(f"--- SOURCE: DOCUMENT ({fname}) ---")
                    all_context.extend(chunks)
            except Exception as e:
                print(f"Error fetching document context: {e}")
                
        if not all_context:
            return "No relevant information found in any uploaded documents or videos."
            
        full_context = "\\n".join(all_context)
        
        system_prompt = f\"\"\"
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
\"\"\"
        
        try:
            full_prompt_text = f"{system_prompt}\\n\\nUSER QUESTION: {question}"
            raw_response = self._generate(full_prompt_text)
            return clean_llm_text(raw_response)
        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return "I was unable to generate a response due to an internal error."
"""
    new_content = content[:start_idx] + new_methods
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully updated ExplainX_LLM.py")
else:
    print("Could not find ask_question_ppt_pdf")
