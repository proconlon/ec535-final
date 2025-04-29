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
    try:
        with open('live_data', 'r') as file: # open the continously updated data file
            lines = file.readlines()
            if len(lines) < 2:
                raise ValueError("not enough lines")

            data_line = lines[1].strip() # 2nd line of file has csv live data
            values = data_line.split(',') #csv

            return {
                'timestamp': int(values[0]),
                'temp': float(values[1]),
                'pressure': float(values[2]),
                'amplitude': float(values[3]),
                'frequency': float(values[4]),
                'stage': values[5],
                'failure_label': int(values[6])
            }
    except Exception as e:
        print(f"Error reading live_data: {e}")
        return None


email_last_5 = 0

while True:
    data = get_live_data()
    df = pd.DataFrame([data])
    prob_failure = model.predict_proba(df)[0][1] 
    print(f"Prediction: Failure probability = {prob_failure:.2f}")

    # write to file the current timestamp and the current prob
    with open('predict_result.txt', 'a') as f:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp}, - Current failure probability: {prob_failure:.2f}\n")


    if prob_failure > 0.50:
        current_time = time.time()
        if current_time - email_last_5 >= 5*60:  # max 1 email per 5 min
            send_email_alert(prob_failure)
            email_last_5 = current_time
        print("Waiting for cooldown before sending next alert...")

    time.sleep(1) 
