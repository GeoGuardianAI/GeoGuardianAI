import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer

print("=" * 60)
print("INDOFLOODS PREPROCESSING")
print("=" * 60)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

events = pd.read_csv(
    r"datasets\flood\floodevents_indofloods.csv"
)

rain = pd.read_csv(
    r"datasets\flood\precipitation_variables_indofloods.csv"
)

catchment = pd.read_csv(
    r"datasets\flood\catchment_characteristics_indofloods.csv"
)

print("Files loaded successfully.")

# --------------------------------------------------
# MERGE DATASETS
# --------------------------------------------------

events["GaugeID"] = (
    events["EventID"]
    .str.rsplit("-", n=1)
    .str[0]
)

df = events.merge(rain, on="EventID")
df = df.merge(catchment, on="GaugeID")

print(f"Merged Shape: {df.shape}")

# --------------------------------------------------
# TARGET
# --------------------------------------------------

df["target"] = df["Flood Type"].map({
    "Flood": 0,
    "Severe Flood": 1
})

# --------------------------------------------------
# DROP LEAKAGE COLUMNS
# --------------------------------------------------

leakage_cols = [
    "Peak Flood Level (m)",
    "Peak FL Date",
    "Num Peak FL",
    "Peak Discharge Q (cumec)",
    "Peak Discharge Date",
    "Flood Volume (cumec)",
    "Event Duration (days)",
    "Time to Peak (days)",
    "Recession Time (day)"
]

# --------------------------------------------------
# DROP IDENTIFIERS
# --------------------------------------------------

id_cols = [
    "EventID",
    "GaugeID",
    "Start Date",
    "End Date",
    "Flood Type"
]

# --------------------------------------------------
# DROP HIGH-MISSING COLUMNS
# --------------------------------------------------

high_missing_cols = [
    "No. of Fifthorder Streams",
    "No. of Sixthorder Streams",
    "No. of Seventhorder Streams",
    "No. of Eigthorder Streams",
    "Fifthorder Streams Length",
    "Sixthorder Streams Length",
    "Seventhorder Streams Length",
    "Eighthorder Streams Length",
    "Fifthorder Streams Mean Length",
    "Sixthorder Streams Mean Length",
    "Seventhorder Streams Mean Length",
    "Eighthorder Streams Mean Length",
    "FourthFifth Stream Length Ratio",
    "FifthSixth Stream Length Ratio",
    "SixthSeventh Stream Length Ratio",
    "SeventhEighth Stream Length Ratio",
    "FourthFifth Bifurcation Ratio",
    "FifthSixth Bifurcation Ratio",
    "Sixthseventh Bifurcation Ratio",
    "SeventhEighth Bifurcation Ratio"
]

df.drop(
    columns=leakage_cols + id_cols + high_missing_cols,
    inplace=True,
    errors="ignore"
)

print(f"Shape after dropping columns: {df.shape}")

# --------------------------------------------------
# HANDLE MISSING VALUES
# --------------------------------------------------

numeric_cols = df.select_dtypes(
    include=["int64", "float64"]
).columns.tolist()

numeric_cols.remove("target")

categorical_cols = df.select_dtypes(
    include=["object"]
).columns.tolist()

print("\nCategorical Columns:")
print(categorical_cols)

num_imputer = SimpleImputer(strategy="median")
cat_imputer = SimpleImputer(strategy="most_frequent")

df[numeric_cols] = num_imputer.fit_transform(
    df[numeric_cols]
)

df[categorical_cols] = cat_imputer.fit_transform(
    df[categorical_cols]
)

# --------------------------------------------------
# ONE-HOT ENCODING
# --------------------------------------------------

df = pd.get_dummies(
    df,
    columns=categorical_cols,
    drop_first=True
)

print(f"Shape after encoding: {df.shape}")

# --------------------------------------------------
# SPLIT FEATURES / TARGET
# --------------------------------------------------

X = df.drop("target", axis=1)
y = df["target"]

# --------------------------------------------------
# TRAIN TEST SPLIT
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTrain Shape:", X_train.shape)
print("Test Shape:", X_test.shape)

# --------------------------------------------------
# SAVE
# --------------------------------------------------

output_dir = "datasets/processed"

X_train.to_csv(
    f"{output_dir}/X_train_indofloods.csv",
    index=False
)

X_test.to_csv(
    f"{output_dir}/X_test_indofloods.csv",
    index=False
)

y_train.to_csv(
    f"{output_dir}/y_train_indofloods.csv",
    index=False
)

y_test.to_csv(
    f"{output_dir}/y_test_indofloods.csv",
    index=False
)

print("\nProcessed datasets saved.")
print("Preprocessing completed successfully.")