import os

files = ['g:\\Antigravity projects\\MultiX\\Backend\\newserver.py', 'g:\\Antigravity projects\\MultiX\\Backend\\server.py']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    insert_str = '\nos.environ["ANONYMIZED_TELEMETRY"] = "False"\nos.environ["CHROMA_TELEMETRY"] = "False"\n\nimport logging\nlogging.getLogger("chromadb").setLevel(logging.ERROR)\nlogging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.ERROR)\n'
    
    if 'import os' in content:
        if 'os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"' in content:
            content = content.replace('os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"', 'os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"' + insert_str)
        else:
            content = content.replace('import os', 'import os' + insert_str, 1)
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Updated {f}")
