import pandas as pd
import re

# Load CSV
input_file = "ethiopia.csv"   # change if needed
df = pd.read_csv(input_file)

print("📌 Original column count:", len(df.columns))


df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]

print("📌 Column count after removing Unnamed:", len(df.columns))


df.columns = (
    df.columns
    .str.strip()
    .str.replace(r'\s+', ' ', regex=True)
)

# -------------------------------
# 3️⃣ CLEAN CELL VALUES
# -------------------------------
def clean_text(value):
    if pd.isna(value):
        return value
    value = str(value)
    value = value.replace('\n', ' ').replace('\t', ' ')
    value = re.sub(r'\s+', ' ', value)
    return value.strip()

df = df.applymap(clean_text)

# -------------------------------
# 4️⃣ COURSE NORMALIZATION SETUP
# -------------------------------
PROGRAM_COLUMNS = {
    "Programs Offered -Undergraduate": "Undergraduate",
    "Programs Offered-Postgraduate": "Postgraduate",
    "Programs Offered -PhD": "PhD",
    "Programs Offered-Diploma": "Diploma",
    "Programs Offered Online courses": "Online",
    "Popular Courses": "Popular"
}

def split_courses(text):
    if pd.isna(text) or text == "":
        return []
    parts = re.split(r',|\n|;|\||/|•', text)
    return [p.strip() for p in parts if p.strip()]

rows = []

for _, row in df.iterrows():
    base_data = row.to_dict()

    for col, level in PROGRAM_COLUMNS.items():
        if col in df.columns:
            courses = split_courses(row[col])
            for course in courses:
                new_row = base_data.copy()
                new_row["Program Level"] = level
                new_row["Course"] = course
                rows.append(new_row)

final_df = pd.DataFrame(rows)

# -------------------------------
# 5️⃣ FINAL VALIDATION
# -------------------------------
print("📌 Final column count:", len(final_df.columns))
print("📌 Final columns:")
print(final_df.columns.tolist())

# -------------------------------
# 6️⃣ SAVE OUTPUT
# -------------------------------
output_file = "ethiopia_final.csv"
final_df.to_csv(output_file, index=False)

print("✅ SUCCESS")
print("✔ Unnamed columns removed")
print("✔ Program Level & Course added")
print("✔ Final CSV has exactly 44 columns")
print(f"📁 Output file: {output_file}")
