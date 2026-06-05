import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Auto-detect if a Render persistent disk is mounted at /data
    if os.path.exists("/data") and os.access("/data", os.W_OK):
        DATABASE_URL = "sqlite:////data/jobs.db"
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'jobs.db')}"

# SQLAlchemy requires postgresql:// instead of postgres:// scheme for connection
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL)
    # Test connection to ensure the host is resolvable and accessible
    with engine.connect() as conn:
        pass
except Exception as e:
    print(f"Database connection failed: {e}")
    print("Falling back to local SQLite database.")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'jobs.db')}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, nullable=True)
    ats_type = Column(String, nullable=True) # greenhouse, lever, etc.
    ats_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    
    # Custom string ID (e.g. md5 hash of company + title + url) to avoid duplicate entries
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    url = Column(String, nullable=False)
    source = Column(String, nullable=True) # linkedin, indeed, google, glassdoor, unstop, etc.
    experience_level = Column(String, nullable=True) # e.g. "0-1 yoe"
    date_posted = Column(String, nullable=True)
    date_scraped = Column(DateTime, default=datetime.datetime.utcnow)
    is_notified = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True)

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, default=1)
    
    telegram_enabled = Column(Boolean, default=False)
    telegram_token = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    
    discord_enabled = Column(Boolean, default=False)
    discord_webhook_url = Column(String, nullable=True)
    
    email_enabled = Column(Boolean, default=False)
    email_smtp_server = Column(String, nullable=True)
    email_smtp_port = Column(Integer, default=587)
    email_sender = Column(String, nullable=True)
    email_password = Column(String, nullable=True)
    email_recipient = Column(String, nullable=True)
    
    scraper_interval_hours = Column(Integer, default=12)

class ScraperLog(Base):
    __tablename__ = "scraper_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    jobs_scraped = Column(Integer, default=0)
    jobs_added = Column(Integer, default=0)
    status = Column(String, default="Success") # Success / Failed
    log_message = Column(Text, nullable=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# List of pre-seeded Tier 2 Indian product/growth companies
INITIAL_COMPANIES = [
    {"name": "PhonePe", "domain": "phonepe.com", "ats_type": "greenhouse", "ats_token": "phonepe"},
    {"name": "Paytm", "domain": "paytm.com", "ats_type": "greenhouse", "ats_token": "paytm"},
    {"name": "CRED", "domain": "cred.club", "ats_type": "greenhouse", "ats_token": "cred"},
    {"name": "Razorpay", "domain": "razorpay.com", "ats_type": "greenhouse", "ats_token": "razorpaysoftwareprivatelimited"},
    {"name": "Swiggy", "domain": "swiggy.com", "ats_type": "greenhouse", "ats_token": "swiggy"},
    {"name": "Zomato", "domain": "zomato.com", "ats_type": None, "ats_token": None},
    {"name": "Zoho", "domain": "zoho.com", "ats_type": None, "ats_token": None},
    {"name": "Freshworks", "domain": "freshworks.com", "ats_type": "greenhouse", "ats_token": "freshworks"},
    {"name": "Groww", "domain": "groww.in", "ats_type": "greenhouse", "ats_token": "groww"},
    {"name": "Zerodha", "domain": "zerodha.com", "ats_type": None, "ats_token": None},
    {"name": "InMobi", "domain": "inmobi.com", "ats_type": "greenhouse", "ats_token": "inmobi"},
    {"name": "Meesho", "domain": "meesho.com", "ats_type": "greenhouse", "ats_token": "meesho"},
    {"name": "Delhivery", "domain": "delhivery.com", "ats_type": "greenhouse", "ats_token": "delhivery"},
    {"name": "Nykaa", "domain": "nykaa.com", "ats_type": None, "ats_token": None},
    {"name": "Blinkit", "domain": "blinkit.com", "ats_type": None, "ats_token": None},
    {"name": "Zepto", "domain": "zepto.com", "ats_type": None, "ats_token": None},
    {"name": "Dream11", "domain": "dream11.com", "ats_type": None, "ats_token": None},
    {"name": "ShareChat", "domain": "sharechat.com", "ats_type": "greenhouse", "ats_token": "sharechat"},
    {"name": "BrowserStack", "domain": "browserstack.com", "ats_type": "greenhouse", "ats_token": "browserstack"},
    {"name": "Postman", "domain": "postman.com", "ats_type": "greenhouse", "ats_token": "postman"},
    {"name": "Chargebee", "domain": "chargebee.com", "ats_type": "greenhouse", "ats_token": "chargebee"},
    {"name": "Urban Company", "domain": "urbancompany.com", "ats_type": "greenhouse", "ats_token": "urbancompany"},
    {"name": "MPL", "domain": "mpl.live", "ats_type": None, "ats_token": None},
    {"name": "Gameskraft", "domain": "gameskraft.com", "ats_type": None, "ats_token": None},
    {"name": "Unacademy", "domain": "unacademy.com", "ats_type": "greenhouse", "ats_token": "unacademy"},
    {"name": "UpGrad", "domain": "upgrad.com", "ats_type": "greenhouse", "ats_token": "upgrad"},
    {"name": "PolicyBazaar", "domain": "policybazaar.com", "ats_type": None, "ats_token": None},
    {"name": "Hasura", "domain": "hasura.io", "ats_type": None, "ats_token": None},
    {"name": "Druva", "domain": "druva.com", "ats_type": None, "ats_token": None},
    {"name": "Pine Labs", "domain": "pinelabs.com", "ats_type": "greenhouse", "ats_token": "pinelabs"},
    {"name": "Ola", "domain": "olaelectric.com", "ats_type": None, "ats_token": None},
    {"name": "Ather Energy", "domain": "atherenergy.com", "ats_type": "greenhouse", "ats_token": "atherenergy"},
    {"name": "Licious", "domain": "licious.in", "ats_type": None, "ats_token": None},
    {"name": "Shiprocket", "domain": "shiprocket.in", "ats_type": None, "ats_token": None},
    {"name": "Ninjacart", "domain": "ninjacart.in", "ats_type": None, "ats_token": None},
    {"name": "BlackBuck", "domain": "blackbuck.com", "ats_type": None, "ats_token": None},
    {"name": "BillDesk", "domain": "billdesk.com", "ats_type": None, "ats_token": None},
    {"name": "CarDekho", "domain": "cardekho.com", "ats_type": None, "ats_token": None},
    {"name": "Spinny", "domain": "spinny.com", "ats_type": None, "ats_token": None},
    {"name": "Darwinbox", "domain": "darwinbox.com", "ats_type": "lever", "ats_token": "darwinbox"},
    {"name": "Amagi", "domain": "amagi.com", "ats_type": None, "ats_token": None},
    {"name": "Fractal Analytics", "domain": "fractal.ai", "ats_type": None, "ats_token": None},
    {"name": "Gupshup", "domain": "gupshup.io", "ats_type": None, "ats_token": None}
]

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    # Check if companies are seeded
    if db.query(Company).count() == 0:
        for c in INITIAL_COMPANIES:
            company = Company(
                name=c["name"], 
                domain=c["domain"],
                ats_type=c.get("ats_type"),
                ats_token=c.get("ats_token")
            )
            db.add(company)
        db.commit()
        print("Database initialized and companies pre-seeded.")
        
    # Check if settings are initialized
    if db.query(Settings).count() == 0:
        default_settings = Settings(
            id=1,
            email_enabled=True,
            email_recipient="rathan.gangishetty@gmail.com",
            telegram_enabled=False,
            discord_enabled=False
        )
        db.add(default_settings)
        db.commit()
        print("Default settings initialized.")
        
    db.close()

if __name__ == "__main__":
    init_db()
