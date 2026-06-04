import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from sqlalchemy.orm import Session
from database import Settings, Job

def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Send a markdown formatted message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram Notification Error: {e}")
        return False

def send_discord_webhook(webhook_url: str, job: Job) -> bool:
    """Send a rich embed message via Discord Webhook"""
    payload = {
        "embeds": [
            {
                "title": f"🚀 New Fresher Job at {job.company}",
                "description": f"**Position:** {job.title}\n**Location:** {job.location or 'N/A'}\n**Source:** {job.source.capitalize()}",
                "url": job.url,
                "color": 5763719,  # Premium green color hex (5763719 -> 0x57F287)
                "footer": {
                    "text": "Tier 2 Fresher Jobs Alert System"
                }
            }
        ]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Discord Notification Error: {e}")
        return False

def send_email_notification(settings: Settings, jobs: list[Job]) -> bool:
    """Send an HTML email containing a list of new job openings"""
    recipient = settings.email_recipient or "rathan.gangishetty@gmail.com"
    
    if not (settings.email_smtp_server and settings.email_sender and settings.email_password):
        print(f"\n--- [MOCK EMAIL DISPATCH TO {recipient}] ---")
        print(f"Subject: [ALERT] {len(jobs)} New Fresher Openings in Tier 2 Companies!")
        print(f"Recipient: {recipient}")
        print("Job Openings Details:")
        for job in jobs:
            print(f"  * Company: {job.company}")
            print(f"    Role Name: {job.title}")
            print(f"    Location: {job.location or 'India'}")
            print(f"    Source Platform: {job.source.capitalize()}")
            print(f"    Application Link: {job.url}")
            print(f"    Experience Tag: {job.experience_level or '0-1 yoe'}")
            print("  --------------------------------------")
        print("------------------------------------------\n")
        return True
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔥 {len(jobs)} New Fresher Openings in Tier 2 Companies!"
    msg["From"] = settings.email_sender
    msg["To"] = settings.email_recipient
    
    # Build HTML Content with a premium aesthetic
    job_rows = ""
    for job in jobs:
        job_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 16px; font-weight: bold; color: #1a202c;">{job.company}</td>
            <td style="padding: 16px; color: #2d3748;">{job.title}</td>
            <td style="padding: 16px; color: #718096;">{job.location or 'India'}</td>
            <td style="padding: 16px; color: #718096;">{job.source.capitalize()}</td>
            <td style="padding: 16px;">
                <a href="{job.url}" target="_blank" style="background-color: #4f46e5; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 14px;">Apply Direct</a>
            </td>
        </tr>
        """
        
    html = f"""
    <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f7fafc; padding: 24px; margin: 0;">
            <div style="max-width: 800px; margin: 0 auto; background-color: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden; border: 1px solid #edf2f7;">
                <div style="background-color: #4f46e5; padding: 32px 24px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">Tier 2 Fresher Jobs Alert</h1>
                    <p style="margin: 8px 0 0 0; color: #c7d2fe; font-size: 16px;">Verified job postings for 0-1 yoe engineers</p>
                </div>
                <div style="padding: 24px;">
                    <p style="color: #4a5568; font-size: 16px; margin-top: 0;">Hi,</p>
                    <p style="color: #4a5568; font-size: 16px; line-height: 1.6;">We found {len(jobs)} new legitimate job openings in your tracked Tier 2 companies. Here is the list:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 15px; text-align: left;">
                        <thead>
                            <tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; color: #475569; font-weight: 600;">
                                <th style="padding: 12px 16px;">Company</th>
                                <th style="padding: 12px 16px;">Role</th>
                                <th style="padding: 12px 16px;">Location</th>
                                <th style="padding: 12px 16px;">Source</th>
                                <th style="padding: 12px 16px;">Link</th>
                            </tr>
                        </thead>
                        <tbody>
                            {job_rows}
                        </tbody>
                    </table>
                    
                    <p style="color: #718096; font-size: 13px; margin-top: 32px; border-top: 1px solid #edf2f7; padding-top: 16px;">
                        This is an automated alert from your Fresher Job Aggregator. You can modify your tracking lists or notifications in your local dashboard.
                    </p>
                </div>
            </div>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(html, "html"))
    
    try:
        server = smtplib.SMTP(settings.email_smtp_server, settings.email_smtp_port)
        server.starttls()
        server.login(settings.email_sender, settings.email_password)
        server.sendmail(settings.email_sender, settings.email_recipient, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email Notification Error: {e}")
        return False

def dispatch_notifications(db: Session, new_jobs: list[Job]) -> int:
    """Send notifications for list of new jobs across enabled channels"""
    if not new_jobs:
        return 0
        
    settings = db.query(Settings).first()
    if not settings:
        return 0
        
    notified_count = 0
    
    # 1. Telegram Notifications (Sends all jobs in one message block or multiple if too long)
    if settings.telegram_enabled and settings.telegram_token and settings.telegram_chat_id:
        tg_text = "*🚀 New Fresher Job Alerts!* \n\n"
        for job in new_jobs:
            tg_text += (
                f"🏢 *{job.company}*\n"
                f"💼 *Role:* {job.title}\n"
                f"📍 *Location:* {job.location or 'India'}\n"
                f"🔗 *Apply:* [Direct Link]({job.url})\n"
                f"📡 *Source:* {job.source.capitalize()}\n"
                f"───────────────────\n"
            )
        # Handle maximum message size limits in Telegram (4096 chars)
        if len(tg_text) > 4000:
            tg_text = tg_text[:3900] + "\n...Some alerts truncated. View dashboard for full list."
            
        if send_telegram_message(settings.telegram_token, settings.telegram_chat_id, tg_text):
            notified_count += len(new_jobs)

    # 2. Discord Webhook (Sends individual embeds)
    if settings.discord_enabled and settings.discord_webhook_url:
        for job in new_jobs:
            if send_discord_webhook(settings.discord_webhook_url, job):
                if not settings.telegram_enabled:  # Don't double count notified if telegram already counted
                    notified_count += 1

    # 3. Email Alerts (Sends digest email)
    if settings.email_enabled:
        if send_email_notification(settings, new_jobs):
            if not (settings.telegram_enabled or settings.discord_enabled):
                notified_count += len(new_jobs)
                
    # Mark jobs as notified in database
    for job in new_jobs:
        job.is_notified = True
    db.commit()
    
    return notified_count

def test_channel_notification(settings: Settings, channel: str) -> tuple[bool, str]:
    """Test notification credentials by sending a dummy alert"""
    if channel == "telegram":
        if not settings.telegram_token or not settings.telegram_chat_id:
            return False, "Telegram Token or Chat ID is missing."
        test_msg = "🔔 *Test Notification* from your Tier 2 Fresher Job Alert dashboard! Credentials are valid."
        success = send_telegram_message(settings.telegram_token, settings.telegram_chat_id, test_msg)
        return success, "Telegram notification sent!" if success else "Failed to send Telegram message. Check token/chat ID."
        
    elif channel == "discord":
        if not settings.discord_webhook_url:
            return False, "Discord Webhook URL is missing."
        dummy_job = Job(
            company="Test Company",
            title="Software Engineering Intern",
            location="Remote",
            url="https://unstop.com",
            source="unstop"
        )
        success = send_discord_webhook(settings.discord_webhook_url, dummy_job)
        return success, "Discord notification sent!" if success else "Failed to send Discord webhook. Check URL."
        
    elif channel == "email":
        dummy_job = Job(
            company="Test Company",
            title="Software Engineer (Test)",
            location="Bengaluru",
            url="https://google.com",
            source="linkedin"
        )
        success = send_email_notification(settings, [dummy_job])
        return success, "Test email sent!" if success else "Failed to send email. Check SMTP server/credentials."
        
    return False, "Unknown notification channel."
