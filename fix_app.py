import sys
import re

path = r"d:\synthetic\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace epochs
new_epochs = '''default_epochs = 15 if len(real_df) < 1000 else 30 if len(real_df) < 5000 else 60
                  epochs = st.slider("Epoch Processing Cycle", min_value=5, max_value=200, value=default_epochs, step=5)'''

if 'epochs = st.slider("Epoch Processing Cycle"' in content:
    content = re.sub(r'epochs\s*=\s*st\.slider\("Epoch Processing Cycle",.*?\)', new_epochs, content)
else:
    print("Epochs line not matched.")

# Replace sample_size
new_sample = '''optimized_default = max(min_rows, min(len(real_df) * 3, 1000))
                  sample_size = st.number_input("Density size", min_value=10, max_value=max(1000, len(real_df)*10), value=optimized_default, step=10)'''

if 'sample_size = st.number_input("Density size"' in content:
    content = re.sub(r'sample_size\s*=\s*st\.number_input\("Density size",.*?\)', new_sample, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
