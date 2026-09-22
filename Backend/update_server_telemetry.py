import os

file_path = r'g:\Antigravity projects\MultiX\Backend\server.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'os.environ["CHROMA_TELEMETRY"] = "False"'
replacement = 'os.environ["CHROMA_TELEMETRY"] = "False"\nos.environ["CHROMA_TELEMETRY_IMPL"] = "None"'

if target in content and replacement not in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("server.py updated")
else:
    print("No change needed or target not found")
