import re
import glob

for path in glob.glob("chapters/*.tex") + glob.glob("frontmatter/*.tex"):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    orig = content
    content = content.replace("\u25b6", r"$\blacktriangleright$")

    lines = content.split("\n")
    in_table = False
    new_lines = []
    for line in lines:
        if "\\begin{tabular" in line or "\\begin{longtable" in line:
            in_table = True
        if "\\end{tabular" in line or "\\end{longtable" in line:
            in_table = False
        
        if not in_table:
            # Replace unescaped & with \&
            line = re.sub(r"(?<!\\)&", r"\&", line)
        new_lines.append(line)
        
    content = "\n".join(new_lines)
    if content != orig:
        print(f"Sanitized: {path}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
