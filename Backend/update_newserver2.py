import os

file_path = r'g:\Antigravity projects\MultiX\Backend\newserver.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Import content_details_col
content = content.replace(
    'from mongo import users_col, sessions_col',
    'from mongo import users_col, sessions_col, content_details_col'
)

# 2. Add to upload_file
# We need to find the `upload_file` route and add a DB insert.
# Here is where the path is generated:
# ext = os.path.splitext(file.filename)[1].lower()
# path = os.path.join(UPLOAD_DIR,f"{uuid.uuid4()}{ext}")

upload_file_code_old = """    ext = os.path.splitext(file.filename)[1].lower()
    path = os.path.join(UPLOAD_DIR,f"{uuid.uuid4()}{ext}")
    
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)"""

upload_file_code_new = """    ext = os.path.splitext(file.filename)[1].lower()
    generated_uuid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR,f"{generated_uuid}{ext}")
    
    with open(path,"wb") as f: shutil.copyfileobj(file.file,f)
    
    # Store content details for real filename lookup
    content_details_col.insert_one({
        "uuid": f"{generated_uuid}{ext}",
        "base_uuid": generated_uuid,
        "real_name": file.filename,
        "session_id": session_id,
        "user_email": current_user["email"],
        "content_type": ext,
        "uploaded_at": datetime.utcnow()
    })"""

content = content.replace(upload_file_code_old, upload_file_code_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("newserver.py updated")
