import os

file_path = r'g:\Antigravity projects\MultiX\Backend\ExplainX_LLM.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add _resolve_filename helper right before ask_question_omni
start_idx = content.find('    def ask_question_omni(')

helper = """    def _resolve_filename(self, fname):
        doc = content_details_col.find_one({"$or": [{"uuid": fname}, {"base_uuid": fname}]})
        if doc and "real_name" in doc:
            return doc["real_name"]
        return fname

"""
content = content[:start_idx] + helper + content[start_idx:]

# Replace video source tagging
content = content.replace(
    'all_context.append(f"--- SOURCE: VIDEO TRANSCRIPT ({video_id}) ---")',
    'real_video_name = self._resolve_filename(video_id)\n                    all_context.append(f"--- SOURCE: VIDEO TRANSCRIPT ({real_video_name}) ---")'
)

content = content.replace(
    'all_context.append(f"--- SOURCE: VIDEO VISUALS ({video_id}) ---")',
    'all_context.append(f"--- SOURCE: VIDEO VISUALS ({real_video_name}) ---")'
)

# Replace document source tagging
content = content.replace(
    'all_context.append(f"--- SOURCE: DOCUMENT ({fname}) ---")',
    'real_doc_name = self._resolve_filename(fname)\n                    all_context.append(f"--- SOURCE: DOCUMENT ({real_doc_name}) ---")'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated ExplainX_LLM.py")
