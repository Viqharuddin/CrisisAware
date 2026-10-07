"""Gmail SMTP helpers for CrisisAware NGO application emails."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to_email, subject, body):
    """Send a plain-text email via Gmail SMTP. Returns True on success."""
    if not to_email:
        print('Email not sent: missing recipient')
        return False

    host = os.getenv('MAIL_SERVER') or os.getenv('SMTP_SERVER') or 'smtp.gmail.com'
    port = int(os.getenv('MAIL_PORT') or os.getenv('SMTP_PORT') or '587')
    username = (os.getenv('MAIL_USERNAME') or os.getenv('SMTP_USER') or '').strip()
    password = (os.getenv('MAIL_PASSWORD') or os.getenv('SMTP_PASSWORD') or '').strip()
    from_addr = (
        os.getenv('MAIL_DEFAULT_SENDER')
        or os.getenv('MAIL_FROM')
        or os.getenv('SMTP_FROM')
        or username
    ).strip()
    use_tls = (os.getenv('MAIL_USE_TLS') or os.getenv('SMTP_USE_TLS') or 'True').strip().lower() in ('1', 'true', 't', 'yes')

    if not username or not password:
        print('Email not sent: SMTP_USER/MAIL_USERNAME or SMTP_PASSWORD/MAIL_PASSWORD is not configured')
        return False

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception as exc:
        print(f'Email send failed: {exc}')
        return False


def send_application_received(to_email, org_name, contact_person):
    subject = 'CrisisAware — NGO application received'
    body = (
        f'Dear {contact_person or org_name},\n\n'
        f'Thank you for applying to register {org_name} on CrisisAware.\n\n'
        'Your application is now PENDING review by the CrisisAware administrator. '
        'You will receive another email when it is approved or rejected. '
        'A login account is not created until approval.\n\n'
        'Regards,\nCrisisAware Team'
    )
    return send_email(to_email, subject, body)


def send_application_approved(to_email, org_name, contact_person, login_id, temp_password, login_url=None):
    subject = 'CrisisAware — NGO application approved'
    login_url = login_url or 'the CrisisAware login page'
    body = (
        f'Dear {contact_person or org_name},\n\n'
        f'Your NGO application for {org_name} has been approved.\n\n'
        'Your CrisisAware login credentials are:\n'
        f'  NGO name: {org_name}\n'
        f'  Login ID: {login_id}\n'
        f'  Temporary password: {temp_password}\n'
        f'  Login URL: {login_url}\n\n'
        'Please log in using the Login ID and temporary password above, then change '
        'this password immediately from the "Change password" page for security.\n\n'
        'Regards,\nCrisisAware Team'
    )
    return send_email(to_email, subject, body)


def send_admin_new_application(admin_email, org_name, contact_person, applicant_email):
    """Notify the administrator that a new NGO application is awaiting review."""
    subject = 'CrisisAware — new NGO application pending approval'
    body = (
        'A new NGO application has been submitted and is awaiting your review.\n\n'
        f'  Organization: {org_name}\n'
        f'  Contact person: {contact_person}\n'
        f'  Applicant email: {applicant_email}\n\n'
        'Log in to the admin dashboard to approve or reject this application.\n\n'
        'Regards,\nCrisisAware System'
    )
    return send_email(admin_email, subject, body)


def send_application_rejected(to_email, org_name, contact_person, reason=None):
    subject = 'CrisisAware — NGO application not approved'
    body = (
        f'Dear {contact_person or org_name},\n\n'
        f'Thank you for applying to register {org_name} on CrisisAware.\n\n'
        'After review, we are unable to approve this application at this time.\n'
    )
    if reason:
        body += f'\nReason: {reason}\n'
    body += (
        '\nYou may submit a new application with updated details if appropriate.\n\n'
        'Regards,\nCrisisAware Team'
    )
    return send_email(to_email, subject, body)


def send_credentials_resent(to_email, org_name, contact_person, login_id, temp_password):
    subject = 'CrisisAware — NGO login credentials'
    body = (
        f'Dear {contact_person or org_name},\n\n'
        'Your CrisisAware NGO login credentials have been reset by the administrator.\n\n'
        f'  Login ID: {login_id}\n'
        f'  Temporary password: {temp_password}\n\n'
        'Please log in and change this password immediately. '
        'This does not create a new account; your existing NGO profile is unchanged.\n\n'
        'Regards,\nCrisisAware Team'
    )
    return send_email(to_email, subject, body)
