import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline
from sklearn.compose import ColumnTransformer
import joblib

df = pd.read_csv('training_data.csv', delimiter=',', header=None, names=[
    'timestamp', 'temp', 'pressure', 'amplitude', 'frequency', 'stage', 'failure'
])
X = df[['temp', 'pressure', 'amplitude', 'frequency', 'stage']]
y = df['failure']

print("Loaded {len(df)} samples")
df = df.dropna(subset=['failure'])
print("Loaded {len(df)} samples")
num_failures = (df['failure'] == 1).sum()
print(num_failures)

preprocessor = ColumnTransformer(transformers=[('stage', OneHotEncoder(), ['stage'])], remainder='passthrough')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print("Making pipeline")
model = make_pipeline(preprocessor, RandomForestClassifier(n_estimators=100, random_state=42))
print("Training model")
model.fit(X_train, y_train)
joblib.dump(model, 'failure_model.joblib')
print("Model trained and saved!")
