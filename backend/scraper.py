import datetime
import hashlib
import re
import time
import requests
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from database import Company, Job, ScraperLog, SessionLocal
from jobspy import scrape_jobs
from concurrent.futures import ThreadPoolExecutor

# Whitelist of trusted ATS portals and platforms
TRUSTED_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "smartrecruiters.com",
    "myworkdayjobs.com",
    "workdayjobs.com",
    "workday.com",
    "bamboohr.com",
    "recruitee.com",
    "ashbyhq.com",
    "jobs.ashbyhq.com",
    "zoho.com",
    "freshworks.com",
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "unstop.com"
]

# Negative title keywords indicating senior or non-dev roles
EXCLUDE_TITLE_KEYWORDS = [
    r"\bsenior\b", r"\bsr\b", r"\blead\b", r"\bprincipal\b", r"\barchitect\b",
    r"\bstaff\b", r"\bmanager\b", r"\bdirector\b", r"\bhead\b", r"\btech lead\b",
    r"\bsde[- ]?2\b", r"\bsde[- ]?3\b", r"\bsde[- ]?ii\b", r"\bsde[- ]?iii\b",
    r"\bii\b", r"\biii\b", r"\b2\b", r"\b3\b", r"\b4\b", r"\b5\b",
    r"\b[2-9]\s*\+\s*(years?|yrs?)\b", r"\b[2-9]\s*-\s*[2-9]\s*(years?|yrs?)\b",
    r"\bqa lead\b", r"\btest lead\b", r"\bconsultant\b", r"\bhr\b", r"\brecruiter\b",
    r"\bsales\b", r"\bmarketing\b"
]

INCLUDE_TITLE_KEYWORDS = [
    "software", "developer", "engineer", "sde", "frontend", "backend",
    "full stack", "fullstack", "android", "ios", "qa", "test", "testing",
    "data analyst", "data engineer", "cloud", "devops", "support",
    "intern", "analyst", "trainee", "graduate", "associate", "2026"
]
def scrape_greenhouse_board(board_token: str, company_name: str) -> list[dict]:
    """Fetch jobs directly from Greenhouse public API"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    jobs = []
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            raw_jobs = data.get("jobs", [])
            for rj in raw_jobs:
                title = rj.get("title", "")
                apply_url = rj.get("absolute_url", "")
                location_dict = rj.get("location", {})
                location = location_dict.get("name", "India") if location_dict else "India"
                desc = rj.get("content", "")
                
                if title and apply_url:
                    jobs.append({
                        "title": title,
                        "company": company_name,
                        "location": location,
                        "url": apply_url,
                        "source": "careers page",
                        "description": desc
                    })
    except Exception as e:
        print(f"Error fetching Greenhouse board {board_token}: {e}")
    return jobs

def scrape_lever_board(company_id: str, company_name: str) -> list[dict]:
    """Fetch jobs directly from Lever public API"""
    url = f"https://api.lever.co/v0/postings/{company_id}"
    jobs = []
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            raw_jobs = r.json()
            for rj in raw_jobs:
                title = rj.get("text", "")
                apply_url = rj.get("hostedUrl", "")
                categories = rj.get("categories", {})
                location = categories.get("location", "India") if categories else "India"
                desc = rj.get("description", "") + " " + rj.get("lists", {}).get("requirements", "")
                
                if title and apply_url:
                    jobs.append({
                        "title": title,
                        "company": company_name,
                        "location": location,
                        "url": apply_url,
                        "source": "careers page",
                        "description": desc
                    })
    except Exception as e:
        print(f"Error fetching Lever board {company_id}: {e}")
    return jobs

def clean_company_name(name) -> str:
    """Simplify company name for matching (e.g. 'Razorpay Software' -> 'razorpay')"""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"\b(software|private|limited|ltd|india|inc|technologies|tech|solutions|corp|corporation)\b", "", name)
    return name.strip()

def matches_company(job_company, target_companies: list[Company]) -> Company | None:
    """Check if the job's company matches one of our targets"""
    if not job_company or not isinstance(job_company, str):
        return None
    cleaned_job = clean_company_name(job_company)
    for company in target_companies:
        cleaned_target = clean_company_name(company.name)
        # Check for substring match or word match
        if cleaned_target in cleaned_job or cleaned_job in cleaned_target:
            return company
    return None

def is_fresher_job(title: str, description: str = "") -> bool:
    """Filter out senior roles and verify it targets entry-level / freshers (0-1 yoe)"""
    title_lower = title.lower()
    
    # 1. Check negative keywords in title
    for kw in EXCLUDE_TITLE_KEYWORDS:
        if re.search(kw, title_lower):
            return False
            
    # 2. Check positive keywords in title
    has_pos_keyword = False
    for kw in INCLUDE_TITLE_KEYWORDS:
        if kw in title_lower:
            has_pos_keyword = True
            break
    if not has_pos_keyword:
        return False
        
    # 3. Check experience constraints in description if available
    if description:
        desc_lower = description.lower()
        # Look for things like "3+ years", "5+ years", "3-5 years" of experience
        exp_patterns = [
            r"\b([3-9]|\d{2})\+?\s*(years?|yrs?)\b",
            r"\b([3-9]|\d{2})\s*-\s*([3-9]|\d{2})\s*(years?|yrs?)\b",
            r"\b(minimum|at least|requried)\s+([3-9]|\d{2})\s*(years?|yrs?)\b",
        ]
        for pattern in exp_patterns:
            if re.search(pattern, desc_lower):
                # But allow if it also explicitly mentions "0-2 years", "freshers", or "2026" as a secondary option
                if not ("0-2" in desc_lower or "0-1" in desc_lower or "fresher" in desc_lower or "2026" in desc_lower):
                    return False
                    
    return True

def verify_and_resolve_url(url: str, company_domain: str | None) -> tuple[str, bool]:
    """Resolve redirect links and verify they point to trusted domains or company domain"""
    if not url:
        return "", False
        
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # 1. Simple domain check (e.g. is it a greenhouse/lever or company domain?)
    is_trusted = False
    if company_domain and company_domain.lower() in domain:
        is_trusted = True
    else:
        for trusted in TRUSTED_DOMAINS:
            if trusted in domain:
                is_trusted = True
                break
                
    # 2. If it is already a direct trusted link, we can skip resolving
    if is_trusted and not ("doubleclick" in domain or "ad" in domain or "clickserv" in domain):
        return url, True
        
    # 3. If it looks like a redirect link, perform HEAD request to find the final URL
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        final_url = res.url
        final_parsed = urlparse(final_url)
        final_domain = final_parsed.netloc.lower()
        
        is_final_trusted = False
        if company_domain and company_domain.lower() in final_domain:
            is_final_trusted = True
        else:
            for trusted in TRUSTED_DOMAINS:
                if trusted in final_domain:
                    is_final_trusted = True
                    break
                    
        return final_url, is_final_trusted
    except Exception as e:
        # If requests fails (e.g. SSL error, timeout), fall back to original url if it matches trusted domain
        return url, is_trusted

def generate_job_id(company: str, title: str, url: str) -> str:
    """Generate a stable, unique ID for a job to prevent duplicate inserts"""
    cleaned_url = url.split("?")[0] # remove query parameters for consistency
    unique_str = f"{company.lower()}_{title.lower()}_{cleaned_url}"
    return hashlib.md5(unique_str.encode('utf-8')).hexdigest()

def check_job_active(job: Job) -> tuple[str, bool]:
    """Check if a single job is still active by sending a request to its URL"""
    url = job.url
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        if res.status_code == 404:
            return job.id, False
            
        body_lower = res.text.lower()
        closed_indicators = [
            "no longer accepting applications",
            "no longer active",
            "job posting has expired",
            "job is no longer available",
            "this position has been filled",
            "page not found",
            "invalid job id",
            "job not found"
        ]
        for indicator in closed_indicators:
            if indicator in body_lower:
                return job.id, False
                
        return job.id, True
    except Exception:
        # On connection errors or timeouts, assume active to avoid false deletions
        return job.id, True

def prune_expired_jobs(db: Session):
    """Scan stored jobs and remove any that are no longer active on their career portals"""
    jobs = db.query(Job).all()
    if not jobs:
        return
        
    print(f"Checking active status for {len(jobs)} stored jobs...")
    inactive_ids = []
    
    # Check jobs in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_job_active, jobs)
        for job_id, is_active in results:
            if not is_active:
                inactive_ids.append(job_id)
                
    if inactive_ids:
        print(f"Pruning {len(inactive_ids)} expired/outdated jobs from database.")
        db.query(Job).filter(Job.id.in_(inactive_ids)).delete(synchronize_session=False)
        db.commit()
    else:
        print("All stored jobs are active.")

def run_scraper(db: Session, hours_old: int = 48) -> list[Job]:
    """Main function to scrape job boards, filter, and save results"""
    start_time = datetime.datetime.utcnow()
    companies = db.query(Company).all()
    if not companies:
        print("No target companies configured in database.")
        return []
        
    print(f"Starting scrape for {len(companies)} target companies. Lookback: {hours_old} hours.")
    
    # Split companies into chunks of 15 to build boolean query
    chunk_size = 15
    company_chunks = [companies[i:i + chunk_size] for i in range(0, len(companies), chunk_size)]
    
    scraped_jobs_count = 0
    added_jobs = []
    
    # --- Part 1: Direct Careers Page Scraping ---
    direct_jobs = []
    for company in companies:
        if company.ats_type == "greenhouse" and company.ats_token:
            print(f"Direct scraping Greenhouse for {company.name}...")
            raw_jobs = scrape_greenhouse_board(company.ats_token, company.name)
            direct_jobs.extend(raw_jobs)
        elif company.ats_type == "lever" and company.ats_token:
            print(f"Direct scraping Lever for {company.name}...")
            raw_jobs = scrape_lever_board(company.ats_token, company.name)
            direct_jobs.extend(raw_jobs)
            
    scraped_jobs_count += len(direct_jobs)
    print(f"Direct careers pages yielded {len(direct_jobs)} raw jobs.")
    
    for rjob in direct_jobs:
        title = rjob["title"]
        company_name = rjob["company"]
        location = rjob["location"]
        url = rjob["url"]
        source = rjob["source"]
        desc = rjob["description"]
        
        # 1. Filter for fresher/0-1 yoe
        if not is_fresher_job(title, desc):
            continue
            
        # 2. Verify URL
        resolved_url, is_legit = verify_and_resolve_url(url, None)
        if not is_legit:
            continue
            
        # 3. Save to database
        job_id = generate_job_id(company_name, title, resolved_url)
        existing_job = db.query(Job).filter(Job.id == job_id).first()
        if not existing_job:
            source_name = source
            if "unstop.com" in resolved_url.lower():
                source_name = "unstop"
                
            new_job = Job(
                id=job_id,
                title=title,
                company=company_name,
                location=location,
                url=resolved_url,
                source=source_name,
                experience_level="0-1 yoe",
                date_posted=datetime.date.today().isoformat(),
                is_notified=False,
                is_verified=True
            )
            db.add(new_job)
            added_jobs.append(new_job)
    db.commit()
    print(f"Added {len(added_jobs)} verified fresher jobs from direct career pages.")
    
    # --- Part 2: Fallback Job Boards Scraping ---
    for idx, chunk in enumerate(company_chunks):
        companies_query = " OR ".join([f'"{c.name}"' for c in chunk])
        search_query = f"({companies_query}) (Software OR Developer OR Intern OR Engineer OR SDE)"
        
        print(f"Scraping chunk {idx+1}/{len(company_chunks)} with query: {search_query[:80]}...")
        
        try:
            # We scrape from LinkedIn and Indeed
            df = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=search_query,
                location="India",
                results_wanted=20,
                hours_old=hours_old,
                country_indeed='india',
                verbose=0
            )
            
            scraped_jobs_count += len(df)
            print(f"Found {len(df)} raw jobs in chunk {idx+1}.")
            
            for _, row in df.iterrows():
                # Extract fields
                job_title = str(row.get('title', ''))
                job_company_name = str(row.get('company', ''))
                job_location = str(row.get('location', ''))
                raw_url = str(row.get('job_url_direct', '') or row.get('job_url', ''))
                job_source = str(row.get('site', ''))
                job_desc = str(row.get('description', ''))
                date_posted_val = str(row.get('date_posted', ''))
                
                if not job_title or not job_company_name or not raw_url or raw_url.strip().lower() == "nan":
                    continue
                    
                # 1. Match company
                matched_co = matches_company(job_company_name, companies)
                if not matched_co:
                    continue
                    
                # 2. Filter for fresher/0-1 yoe
                if not is_fresher_job(job_title, job_desc):
                    continue
                    
                # 3. Verify and resolve URL legitimacy
                resolved_url, is_legit = verify_and_resolve_url(raw_url, matched_co.domain)
                if not is_legit:
                    continue
                    
                # 4. Generate stable ID
                job_id = generate_job_id(matched_co.name, job_title, resolved_url)
                
                # Check if job already exists in database
                existing_job = db.query(Job).filter(Job.id == job_id).first()
                if not existing_job:
                    source_name = job_source
                    if "unstop.com" in resolved_url.lower():
                        source_name = "unstop"
                        
                    new_job = Job(
                        id=job_id,
                        title=job_title,
                        company=matched_co.name,
                        location=job_location,
                        url=resolved_url,
                        source=source_name,
                        experience_level="0-1 yoe",
                        date_posted=date_posted_val,
                        is_notified=False,
                        is_verified=True
                    )
                    db.add(new_job)
                    added_jobs.append(new_job)
                    
            db.commit()
            
        except Exception as e:
            print(f"Error scraping chunk {idx+1}: {e}")
            
        # Sleep briefly between requests to prevent rate limiting
        time.sleep(2)
        
    # Write Log to database
    duration = (datetime.datetime.utcnow() - start_time).total_seconds()
    log_msg = f"Completed in {duration:.1f}s. Scraped {scraped_jobs_count} raw listings. Added {len(added_jobs)} new filtered fresher jobs."
    print(log_msg)
    
    log = ScraperLog(
        timestamp=start_time,
        jobs_scraped=scraped_jobs_count,
        jobs_added=len(added_jobs),
        status="Success" if len(added_jobs) > 0 or scraped_jobs_count > 0 else "Idle",
        log_message=log_msg
    )
    db.add(log)
    db.commit()
    
    # Prune outdated / expired jobs from the database
    prune_expired_jobs(db)
    
    return added_jobs

if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        run_scraper(db_session, hours_old=72)
    finally:
        db_session.close()
