import pandas as pd

events = pd.read_csv(r"datasets\flood\floodevents_indofloods.csv")
rain = pd.read_csv(r"datasets\flood\precipitation_variables_indofloods.csv")

df = events.merge(rain, on="EventID")

df["target"] = df["Flood Type"].map({
    "Flood": 0,
    "Severe Flood": 1
})

corr = df.corr(numeric_only=True)["target"]

print(
    corr.sort_values(
        ascending=False
    )
)