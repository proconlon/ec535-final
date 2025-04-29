import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline
from sklearn.compose import ColumnTransformer
import joblib

df = pd.read_csv('training_data.csv', delimiter=',', header=None, names=['timestamp', 'temp', 'pressure', 'amplitude', 'frequency', 'stage', 'unused'])
print(f"Loaded {len(df)} samples")
df = df.sort_values('timestamp').reset_index(drop=True)
df['failure'] = 0

LOOKBACK_US = 10 * 1_000_000  # 10 seconds in microseconds

# Find where PartReplacement happens and mark prior rows
for idx, row in df[df['stage'] == 'PartReplacement'].iterrows():
    failure_time = row['timestamp']
    early_window_start = failure_time - LOOKBACK_US
    # Mark rows in the 10s window before failure
    df.loc[(df['timestamp'] >= early_window_start) & (df['timestamp'] <= failure_time), 'failure'] = 1

num_failures = (df['failure'] == 1).sum()
print(f"Samples marked as failure: {num_failures}")
X = df[['temp', 'pressure', 'amplitude', 'frequency', 'stage']]
y = df['failure']

X = X.dropna()
y = y.loc[X.index]

preprocessor = ColumnTransformer(transformers=[('stage', OneHotEncoder(), ['stage'])], remainder='passthrough')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Making pipeline")
model = make_pipeline(preprocessor, RandomForestClassifier(n_estimators=100, random_state=42))
print("Training model")
model.fit(X_train, y_train)

joblib.dump(model, 'failure_model.joblib')
print("Model trained and saved!")
