import os

file_path = r'g:\Antigravity projects\MultiX\Backend\newserver.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "    # 3. Route the Request (Video vs PDF vs Hybrid)"
end_marker = "    except Exception as e:\n        print(f\"Error during QA: {e}\")"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_logic = """    # 3. Route the Request via Omni Search
    try:
        if not files:
            answer = "I don't see any files in this session yet. Please upload a PDF, PPT, or Video."
        else:
            answer = llm.ask_question_omni(req.session_id, video_files, doc_files, req.question)

"""
    new_content = content[:start_idx] + new_logic + content[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully updated newserver.py")
else:
    print("Markers not found in newserver.py")
