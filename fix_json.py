import os
import glob

agents_dir = r"c:\Users\wahid\Desktop\E-to-E_Agent\agents"
py_files = glob.glob(os.path.join(agents_dir, "*.py"))

count = 0
for py_file in py_files:
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "json.loads(raw)" in content:
        content = content.replace("json.loads(raw)", "json.loads(raw, strict=False)")
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {os.path.basename(py_file)}")
        count += 1

print(f"Total files updated: {count}")