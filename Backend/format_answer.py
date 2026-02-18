import re

def clean_llm_text(text: str) -> str:
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Preserve paragraph separation (DO NOT collapse them)
    text = re.sub(r'\n{4,}', '\n\n\n', text)   # allow triple newline max

    # Clean trailing spaces
    text = re.sub(r'[ \t]+\n', '\n', text)

    # Preserve equation blocks
    text = re.sub(r'\n\s*\n(?=\$)', '\n\n', text)
    text = re.sub(r'(?<=\$)\n\s*\n', '\n\n', text)

    # Keep bullets readable
    text = re.sub(r'\n\s*•', '\n•', text)
    text = re.sub(r'\n\s*-\s+', '\n- ', text)

    # Do NOT touch internal newlines
    return text.strip()
