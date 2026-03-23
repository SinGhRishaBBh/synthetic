path = r"d:\synthetic\app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "default_epochs =" in line and "1000" in line:
        print(f"Index found: {i}")
        lines[i] = '                  default_epochs = 15 if len(real_df) < 1000 else 30 if len(real_df) < 5000 else 60\n'
        lines[i+1] = '                  epochs = st.slider("Epoch Processing Cycle", min_value=5, max_value=200, value=default_epochs, step=5)\n'
        lines[i+2] = '                  min_rows = max(10, len(real_df))\n'
        lines[i+3] = '                  optimized_default = max(min_rows, min(len(real_df) * 3, 1000))\n'
        lines[i+4] = '                  sample_size = st.number_input("Density size", min_value=10, max_value=max(1000, len(real_df)*10), value=optimized_default, step=10)\n'
        
        # Delete index i+5 so it doesn't leave remnants
        del lines[i+5]
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Repaired")
