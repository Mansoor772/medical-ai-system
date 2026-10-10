import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import settings


def send_email(to: str, subject: str, body_html: str) -> bool:
    """Send an email via Gmail SMTP. Returns True on success."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL SKIPPED] No SMTP credentials. Would send to {to}: {subject}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to, msg.as_string())

        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to}: {e}")
        return False


def send_alert_notification(
    to: str,
    hospital_name: str,
    patient_name: str,
    test_name: str,
    result_value: str,
    unit: str | None,
    reference_range: str | None,
    doctor_notes: str | None,
) -> bool:
    unit_str = f" {unit}" if unit else ""
    ref_str = f"<br><strong>Reference Range:</strong> {reference_range}" if reference_range else ""
    notes_str = f"<br><strong>Doctor Notes:</strong> {doctor_notes}" if doctor_notes else ""

    subject = f"[ALERT] Abnormal Lab Result — {patient_name} | {hospital_name}"
    body = f"""
    <html><body>
    <h2 style="color:#c0392b;">Lab Result Alert — {hospital_name}</h2>
    <p>A doctor has approved an alert for the following lab result:</p>
    <table style="border-collapse:collapse;">
      <tr><td><strong>Patient:</strong></td><td>{patient_name}</td></tr>
      <tr><td><strong>Test:</strong></td><td>{test_name}</td></tr>
      <tr><td><strong>Result:</strong></td><td>{result_value}{unit_str}</td></tr>
    </table>
    {ref_str}{notes_str}
    <br>
    <p style="color:#7f8c8d;font-size:12px;">
      This alert was reviewed and approved by the treating doctor before being sent.
      Log in to the system for full patient details.
    </p>
    </body></html>
    """
    return send_email(to, subject, body)
