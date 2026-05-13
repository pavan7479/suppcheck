import pandas as pd
import os
import glob

data_dir = r"c:\Users\Admin\Desktop\suppcheck\data\raw\extracted_data\DSLD-full-database-CSV"
csv_files = glob.glob(os.path.join(data_dir, "DietarySupplementFacts_*.csv"))

ingredient_counts = {}

print(f"Counting unique ingredients across {len(csv_files)} files...")
for file in csv_files:
    print(f"Processing {os.path.basename(file)}...")
    # Read only the 'Ingredient' column to save memory
    df = pd.read_csv(file, usecols=["Ingredient"], encoding="utf-8")
    for ing in df["Ingredient"].dropna():
        ingredient_counts[ing] = ingredient_counts.get(ing, 0) + 1

print(f"Total unique ingredients found: {len(ingredient_counts)}")

# Sort by frequency
sorted_ingredients = sorted(ingredient_counts.items(), key=lambda x: x[1], reverse=True)

# Save to a temporary text file with counts
with open("unique_ingredients.txt", "w", encoding="utf-8") as f:
    for ing, count in sorted_ingredients:
        f.write(f"{ing} ({count})\n")
