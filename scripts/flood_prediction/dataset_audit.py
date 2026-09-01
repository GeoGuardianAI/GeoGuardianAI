import pandas as pd

events = pd.read_csv(r"datasets\flood\floodevents_indofloods.csv")
rain = pd.read_csv(r"datasets\flood\precipitation_variables_indofloods.csv")
catchment = pd.read_csv(r"datasets\flood\catchment_characteristics_indofloods.csv")

events["GaugeID"] = events["EventID"].str.rsplit("-", n=1).str[0]

df = events.merge(rain, on="EventID")
df = df.merge(catchment, on="GaugeID")

print("=" * 60)
print("DATASET SHAPE")
print("=" * 60)
print(df.shape)

print("\n" + "=" * 60)
print("MISSING VALUES")
print("=" * 60)

missing = df.isnull().sum()
missing = missing[missing > 0]

print(missing.sort_values(ascending=False))

print("\nColumns with >50% missing values:")

threshold = len(df) * 0.5

high_missing = missing[missing > threshold]

print(high_missing.index.tolist())

print("\nTotal Columns:", len(df.columns))
print("Columns with Missing Values:", len(missing))