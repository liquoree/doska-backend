import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tt5342912@gmail.com"
SMTP_PASSWORD = "evgc ohty kitp dlyi"  # app password

def send_responsible_email(to_email: str, task_title: str):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = "Вас назначили ответственным"

    msg.attach(MIMEText(f"Вас назначили ответственным за задачу: {task_title}", "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            print(f"Email отправлен на {to_email}")
    except Exception as e:
        print(f"Ошибка отправки email: {e}")