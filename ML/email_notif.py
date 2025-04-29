import pandas as pd
import joblib
import smtplib
from email.mime.text import MIMEText
import time

model = joblib.load('failure_model.joblib')

EMAIL_FROM = "animishcs23@gmail.com"
EMAIL_PASSWORD = ""  
EMAIL_TO = "anics@bu.edu"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_email_alert(probability):
    msg = MIMEText("Machine warning: Predicted failure risk = {probability:.2f}")
    msg['Subject'] = "Predictive Maintenance Alert!"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(" Alert email sent!")

def get_live_data():
   #TODO: Get the live data, Probably reading off of a CSV file. Do it tomorrow in class
    return {
        'temp': 21.4,
        'pressure': 52.7,
        'amplitude': 0.31,
        'frequency': 6.8,
        'stage': 'Cooling'
    }

while True:
    data = get_live_data()
    df = pd.DataFrame([data])
    prob_failure = model.predict_proba(df)[0][1] 
    print(f"Prediction: Failure probability = {prob_failure:.2f}")
    if prob_failure > 0.50: #Testing
        send_email_alert(prob_failure)
        exit() # Just to avoid spam 

    time.sleep(1) 
