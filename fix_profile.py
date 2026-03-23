import os

path = r"d:\synthetic\modules\profiling.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines(True)
found = False

for i, line in enumerate(lines):
    if 'return df.describe(include="all", datetime_is_numeric=True).transpose()' in line:
        lines[i] = """    try:
        return df.describe(include="all", datetime_is_numeric=True).transpose()
    except TypeError:
        return df.describe(include="all").transpose()
"""
        found = True
        break

if found:
    content = "".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: Summary statistics patched.")
else:
    print("TARGET LINE NOT FOUND.")
