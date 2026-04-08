import pandas as pd

df = pd.read_excel("Grant_Opportunities_Template_v2.xlsx", sheet_name="Opportunities Dashboard")

print(f"TOTAL ROWS: {len(df)}")
print(f"COLUMNS:    {list(df.columns)}")
print()
print(f"{'#':>3}  {'Calls (+ ID Number)':<52} {'Status':<12} {'Total Eligible Cost':<22} {'Close Date'}")
print("-" * 110)
for i, row in df.iterrows():
    name   = str(row.get("Calls (+ ID Number)", ""))[:50]
    status = str(row.get("Status", ""))[:10]
    cost   = str(row.get("Total Eligible Cost", ""))[:20]
    close  = str(row.get("Close Date", ""))[:15]
    print(f"{i+1:>3}  {name:<52} {status:<12} {cost:<22} {close}")
