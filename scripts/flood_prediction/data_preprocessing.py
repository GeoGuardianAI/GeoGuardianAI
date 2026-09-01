import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

df = pd.read_csv("datasets/prediction/raw/flood_data.csv")

# Drop duplicates and nulls
df.drop_duplicates(inplace=True)
df.dropna(inplace=True)

# Feature engineering (example)
# df['rainfall_humidity_index'] = df['rainfall'] * df['humidity'] / 100

# Separate features and target
X = df.drop(columns=['flood_occurred'])  # adjust column name
y = df['flood_occurred']

# Scale
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

print("Train size:", X_train.shape)
print("Test size:", X_test.shape)