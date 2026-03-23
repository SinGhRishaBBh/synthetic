import re

path = r"d:\synthetic\app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "selected_model = st.selectbox" in line:
        match = re.search(r'^(\s*)selected_model', line)
        if match:
             spaces = match.group(1)
             print(f"Indentation is {len(spaces)} spaces.")
             
             # Apply exact spaces Indentations
             lines[i+1] = f'{spaces}default_epochs = 15 if len(real_df) < 1000 else 30 if len(real_df) < 5000 else 60\n'
             lines[i+2] = f'{spaces}epochs = st.slider("Epoch Processing Cycle", min_value=5, max_value=200, value=default_epochs, step=5)\n'
             lines[i+3] = f'{spaces}min_rows = max(10, len(real_df))\n'
             lines[i+4] = f'{spaces}optimized_default = max(min_rows, min(len(real_df) * 3, 1000))\n'
             lines[i+5] = f'{spaces}sample_size = st.number_input("Density Size (Sample count)", min_value=10, max_value=max(1000, len(real_df)*10), value=optimized_default, step=10)\n'
             
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Done alignment")
