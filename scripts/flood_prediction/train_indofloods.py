import pandas as pd
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

print("=" * 60)
print("INDOFLOODS MODEL TRAINING")
print("=" * 60)

# ==================================================
# LOAD DATA
# ==================================================

X_train = pd.read_csv(
    "datasets/processed/X_train_indofloods.csv"
)

X_test = pd.read_csv(
    "datasets/processed/X_test_indofloods.csv"
)

y_train = pd.read_csv(
    "datasets/processed/y_train_indofloods.csv"
).squeeze()

y_test = pd.read_csv(
    "datasets/processed/y_test_indofloods.csv"
).squeeze()

print(f"Training shape: {X_train.shape}")
print(f"Testing shape: {X_test.shape}")

# ==================================================
# MODELS
# ==================================================

models = {
    "Logistic Regression": LogisticRegression(
        max_iter=3000,
        random_state=42
    ),

    "Decision Tree": DecisionTreeClassifier(
        max_depth=10,
        min_samples_split=10,
        random_state=42
    ),

    "Random Forest": RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )
}

results = {}

best_model = None
best_model_name = None
best_auc = 0

# ==================================================
# TRAINING LOOP
# ==================================================

for name, model in models.items():

    print(f"\nTraining {name}...")

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    y_prob = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)

    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_test,
        y_prob
    )

    results[name] = {
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "ROC_AUC": roc_auc
    }

    if roc_auc > best_auc:
        best_auc = roc_auc
        best_model = model
        best_model_name = name

# ==================================================
# RESULTS
# ==================================================

results_df = pd.DataFrame(results).T

print("\n")
print("=" * 60)
print("MODEL COMPARISON")
print("=" * 60)

print(results_df)

print("\nBest Model:", best_model_name)
print("Best ROC-AUC:", round(best_auc, 4))

# ==================================================
# FEATURE IMPORTANCE
# ==================================================

if best_model_name == "Random Forest":

    print("\n")
    print("=" * 60)
    print("TOP 20 FEATURE IMPORTANCES")
    print("=" * 60)

    feature_importance = pd.DataFrame({
        "Feature": X_train.columns,
        "Importance": best_model.feature_importances_
    })

    feature_importance = (
        feature_importance
        .sort_values(
            by="Importance",
            ascending=False
        )
    )

    print(feature_importance.head(20))

# ==================================================
# SAVE MODEL
# ==================================================

# Save trained model
joblib.dump(
    best_model,
    "models/flood_prediction_model.pkl"
)

# Save feature names used during training
joblib.dump(
    list(X_train.columns),
    "models/flood_prediction_features.pkl"
)

print("\nModel saved successfully.")
print("Location: models/flood_prediction_model.pkl")
print("Feature list saved.")
print("Location: models/flood_prediction_features.pkl")