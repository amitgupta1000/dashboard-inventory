import pandas as pd

# Read the Excel file with proper header
df = pd.read_excel('stock_report.xlsx', header=0)

print("=" * 60)
print("Stock Report Data Structure")
print("=" * 60)
print(f"\nTotal rows: {len(df)}")
print(f"Columns: {list(df.columns)}\n")
print("\nAll data:")
print(df.to_string())
print("\nData types:")
print(df.dtypes)
