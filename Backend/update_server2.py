import os

file_path = r'g:\Antigravity projects\MultiX\Backend\server.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import if missing
if 'content_details_col' not in content:
    # Let's import it near top or just before using it
    # We can just import it where it's used
    pass

upload_file_code_old = """    saved_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.{ext}")
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)"""

upload_file_code_new = """    generated_uuid = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{generated_uuid}.{ext}")
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        from mongo import content_details_col
        from datetime import datetime
        content_details_col.insert_one({
            "uuid": f"{generated_uuid}.{ext}",
            "base_uuid": generated_uuid,
            "real_name": file.filename,
            "session_id": session_id,
            "user_email": "unknown", # not tracked easily in server.py
            "content_type": ext,
            "uploaded_at": datetime.utcnow()
        })
    except Exception as e:
        print("Failed to save to content_details:", e)"""

if upload_file_code_old in content:
    content = content.replace(upload_file_code_old, upload_file_code_new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("server.py updated")
else:
    print("Could not find upload_file block in server.py")
