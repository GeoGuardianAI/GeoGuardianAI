import pandas as pd
import joblib

# ==================================================
# LOAD MODEL ONCE
# ==================================================

MODEL_PATH = "models/flood_prediction_model.pkl"
FEATURES_PATH = "models/flood_prediction_features.pkl"

model = joblib.load(MODEL_PATH)
feature_names = joblib.load(FEATURES_PATH)


# ==================================================
# PREDICTION FUNCTION
# ==================================================

def predict_flood(input_data: dict):
    """
    Predict flood severity from input features.

    Parameters
    ----------
    input_data : dict
        Dictionary containing feature values.

    Returns
    -------
    dict
        Prediction result
    """

    # Create dataframe
    input_df = pd.DataFrame([input_data])

    # Align columns with training features
    input_df = input_df.reindex(
        columns=feature_names,
        fill_value=0
    )

    # Prediction
    prediction = model.predict(input_df)[0]

    probability = model.predict_proba(
        input_df
    )[0][1]

    severity = (
        "Severe Flood"
        if prediction == 1
        else "Flood"
    )

    return {
        "severity": severity,
        "probability": round(float(probability), 4)
    }


# ==================================================
# TEST BLOCK
# ==================================================

if __name__ == "__main__":

    sample_data = {
        "T1d": 120,
        "T2d": 150,
        "T3d": 180,
        "T4d": 210,
        "T5d": 250,
        "T6d": 270,
        "T7d": 300,
        "T8d": 320,
        "T9d": 350,
        "T10d": 400
    }

    result = predict_flood(sample_data)

    print("\nPrediction Result")
    print("=" * 30)

    print(result)