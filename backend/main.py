import datetime
import threading
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import init_db, get_db, Company, Job, Settings, ScraperLog, SessionLocal
from scraper import run_scraper
from notifier import dispatch_notifications, test_channel_notification
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="Tier 2 Fresher Job Alert API")

# Configure CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the Vite development port (e.g. http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background scheduler setup
scheduler = BackgroundScheduler()
scraper_status = {
    "is_running": False,
    "last_run": None,
    "last_run_jobs_added": 0,
    "last_run_status": "Idle"
}

# Pydantic Schemas
class CompanyCreate(BaseModel):
    name: str
    domain: str

class SettingsUpdate(BaseModel):
    telegram_enabled: bool
    telegram_token: str | None = None
    telegram_chat_id: str | None = None
    discord_enabled: bool
    discord_webhook_url: str | None = None
    email_enabled: bool
    email_smtp_server: str | None = None
    email_smtp_port: int = 587
    email_sender: str | None = None
    email_password: str | None = None
    email_recipient: str | None = None
    scraper_interval_hours: int = 12

class TestNotificationRequest(BaseModel):
    channel: str # telegram, discord, email

def run_scraper_task():
    """Execution block for scraper runs to be done asynchronously"""
    global scraper_status
    if scraper_status["is_running"]:
        print("Scraper is already running.")
        return
        
    scraper_status["is_running"] = True
    db = SessionLocal()
    try:
        # Fetch target companies and execute scraper
        new_jobs = run_scraper(db, hours_old=48)
        notified = dispatch_notifications(db, new_jobs)
        scraper_status["last_run"] = datetime.datetime.utcnow().isoformat()
        scraper_status["last_run_jobs_added"] = len(new_jobs)
        scraper_status["last_run_status"] = f"Success (Added {len(new_jobs)} jobs, notified {notified})"
    except Exception as e:
        scraper_status["last_run_status"] = f"Failed: {str(e)}"
        print(f"Background Scraper Task Error: {e}")
    finally:
        scraper_status["is_running"] = False
        db.close()

def update_scheduler_interval(hours: int):
    """Reschedule the background scrapers frequency"""
    try:
        if scheduler.get_job('job_scraper_id'):
            scheduler.reschedule_job('job_scraper_id', trigger='interval', hours=hours)
            print(f"Rescheduled background job to every {hours} hours.")
        else:
            scheduler.add_job(run_scraper_task, 'interval', hours=hours, id='job_scraper_id')
    except Exception as e:
        print(f"Error rescheduling job: {e}")

@app.on_event("startup")
def startup_event():
    # 1. Initialize SQLite Database
    init_db()
    
    # 2. Start APScheduler
    db = SessionLocal()
    settings = db.query(Settings).first()
    interval = settings.scraper_interval_hours if settings else 12
    db.close()
    
    scheduler.add_job(run_scraper_task, 'interval', hours=interval, id='job_scraper_id')
    scheduler.start()
    print(f"Background scheduler started. Scraping interval: every {interval} hours.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

# --- JOB ENDPOINTS ---
@app.get("/api/jobs")
def get_jobs(
    search: str | None = None,
    company: str | None = None,
    source: str | None = None,
    notified: bool | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if search:
        query = query.filter(Job.title.ilike(f"%{search}%"))
    if company:
        query = query.filter(Job.company == company)
    if source:
        query = query.filter(Job.source == source)
    if notified is not None:
        query = query.filter(Job.is_notified == notified)
        
    # Return latest jobs first
    return query.order_by(Job.date_scraped.desc()).all()

@app.post("/api/jobs/{job_id}/verify")
def verify_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_verified = not job.is_verified
    db.commit()
    return {"status": "success", "is_verified": job.is_verified}

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"status": "success", "message": "Job deleted"}

# --- COMPANY ENDPOINTS ---
@app.get("/api/companies")
def get_companies(db: Session = Depends(get_db)):
    return db.query(Company).order_by(Company.name.asc()).all()

@app.post("/api/companies")
def add_company(company_in: CompanyCreate, db: Session = Depends(get_db)):
    existing = db.query(Company).filter(Company.name.ilike(company_in.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")
    new_co = Company(name=company_in.name, domain=company_in.domain)
    db.add(new_co)
    db.commit()
    db.refresh(new_co)
    return new_co

@app.delete("/api/companies/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
    return {"status": "success", "message": f"Company {company.name} deleted"}

# --- SETTINGS ENDPOINTS ---
@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@app.post("/api/settings")
def save_settings(settings_in: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(id=1)
        db.add(settings)
        
    settings.telegram_enabled = settings_in.telegram_enabled
    settings.telegram_token = settings_in.telegram_token
    settings.telegram_chat_id = settings_in.telegram_chat_id
    
    settings.discord_enabled = settings_in.discord_enabled
    settings.discord_webhook_url = settings_in.discord_webhook_url
    
    settings.email_enabled = settings_in.email_enabled
    settings.email_smtp_server = settings_in.email_smtp_server
    settings.email_smtp_port = settings_in.email_smtp_port
    settings.email_sender = settings_in.email_sender
    settings.email_password = settings_in.email_password
    settings.email_recipient = settings_in.email_recipient
    
    old_interval = settings.scraper_interval_hours
    settings.scraper_interval_hours = settings_in.scraper_interval_hours
    
    db.commit()
    
    # Update scheduler if interval changed
    if old_interval != settings_in.scraper_interval_hours:
        update_scheduler_interval(settings_in.scraper_interval_hours)
        
    return settings

@app.post("/api/settings/test-notification")
def test_notification(req: TestNotificationRequest, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not configured")
        
    success, message = test_channel_notification(settings, req.channel)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "success", "message": message}

# --- SCRAPER STATUS & LOGS ---
@app.get("/api/scraper/status")
def get_scraper_status():
    return scraper_status

@app.post("/api/scraper/run")
def trigger_scraper(background_tasks: BackgroundTasks):
    global scraper_status
    if scraper_status["is_running"]:
        return {"status": "running", "message": "Scraper is already running in background."}
        
    # Trigger as non-blocking background task
    background_tasks.add_task(run_scraper_task)
    return {"status": "started", "message": "Scraper execution launched in background."}

@app.get("/api/scraper/logs")
def get_scraper_logs(db: Session = Depends(get_db)):
    return db.query(ScraperLog).order_by(ScraperLog.timestamp.desc()).limit(50).all()
