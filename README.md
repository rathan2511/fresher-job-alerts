# 🚀 Tier 2 Fresher Job Alerts Dashboard

A premium, full-stack job aggregation and notification system tailored for **2026 graduates** and **freshers (0-1 YOE)** looking for opportunities in **Tier 2 Indian product companies/startups**.

It directly scrapes Greenhouse, Lever, and other official sources, validates job listings to ensure they are **100% active and legit** (no outdated or dead postings), and delivers instant notifications to email (customized for `rathan.gangishetty@gmail.com`), Telegram, or Discord.

---

## ✨ Features
- **Direct Careers Page Scrapers**: Built-in support for Greenhouse and Lever API boards to get direct listings without scraping intermediary job portals.
- **Batched 2026/Fresher Filters**: Built-in experience filters (0-1 YOE) specifically optimized to prioritize the 2026 graduating batch and reject senior roles.
- **Legit Link Verification**: Resolves redirects and checks domain whitelists to ensure application links go directly to the official portal.
- **Active Postings Enforcement (Anti-Outdated)**: A background verification routine checks all stored jobs regularly, automatically pruning and removing closed or expired listings.
- **Multiple Notification Channels**: Support for SMTP email alerts, Telegram bot alerts, and Discord webhooks.
- **Premium Glassmorphic Dashboard**: A clean, responsive React SPA containing:
  - **Job Feed**: Real-time matching jobs list with direct apply links and verification badges.
  - **Target Companies**: Admin view to manage company tracking database.
  - **Notifications Configuration**: Quick settings to toggle notification dispatchers.
  - **Scraper Logs**: Live inspection of scraping operations.

---

## 🛠️ Architecture & Tech Stack
- **Frontend**: React (Vite), Tailwind/Vanilla CSS (Premium Glassmorphism), Lucide React.
- **Backend**: FastAPI (Python), SQLAlchemy ORM, APScheduler (automated scraping & pruning background loop).
- **Database**: SQLite (`backend/jobs.db`).

---

## 📂 Project Structure
```text
fresher-job-alerts/
├── backend/
│   ├── database.py       # SQLite database configuration and models
│   ├── main.py           # FastAPI application endpoints & background scheduler
│   ├── notifier.py       # Notification dispatchers (SMTP, Telegram, Discord)
│   ├── scraper.py        # Scraper engine (Greenhouse, Lever, validation, active-check)
│   └── requirements.txt  # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Main Dashboard UI & Frontend state logic
│   │   ├── index.css     # Premium styling stylesheet
│   │   └── main.jsx
│   ├── package.json      # React Vite dependencies
│   └── index.html
└── README.md             # This guide
```

---

## 🚀 Setup and Run Guide

### 1. Backend Setup
1. Open a terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux**:
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```
   The backend will be running on `http://127.0.0.1:8000`.

### 2. Frontend Setup
1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev -- --host 127.0.0.1 --port 5173
   ```
   The dashboard will be running on `http://127.0.0.1:5173`.

---

## 🌍 Hosting & Multi-Device Access

### 1. Frontend Hosting (Vercel)
You can deploy the frontend directly to Vercel:
1. Initialize a Git repository if not already done, commit the changes, and push them to your GitHub:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```
2. Sign in to your [Vercel Dashboard](https://vercel.com/) and click **Add New Project**.
3. Select your `fresher-job-alerts` repository.
4. **Root Directory**: Set this to `frontend`.
5. **Framework Preset**: Select **Vite**.
6. Set the **Build Command** to `npm run build` and **Output Directory** to `dist`.
7. Click **Deploy**.

### 2. Backend Hosting & Cross-Device Access
Since the database uses local SQLite, running the backend locally is recommended for testing. To access the app on multiple devices simultaneously (e.g. phone and laptop) while running the backend locally:

#### Option A: Local Network Sharing (Wi-Fi)
1. Find your computer's local IP address (e.g., `192.168.1.15`).
   - On Windows, run `ipconfig` in CMD or PowerShell.
   - On macOS/Linux, run `ifconfig` or `ip a`.
2. Change the `API_BASE` variable at the top of `frontend/src/App.jsx` from `http://localhost:8000/api` to:
   ```javascript
   const API_BASE = "http://<YOUR-PC-IP>:8000/api";
   ```
3. Run both backend and frontend servers with `--host 0.0.0.0` to allow incoming traffic.
4. Access the dashboard from any device on the same Wi-Fi network using `http://<YOUR-PC-IP>:5173`.

#### Option B: Ngrok Tunnel (Easiest & Worldwide Access)
1. Install [ngrok](https://ngrok.com/) on your computer.
2. In a terminal, run:
   ```bash
   ngrok http 8000
   ```
3. Copy the public HTTPS forwarding URL provided by ngrok (e.g., `https://xxxx.ngrok-free.app`).
4. Update `API_BASE` in `frontend/src/App.jsx` with the ngrok URL:
   ```javascript
   const API_BASE = "https://xxxx.ngrok-free.app/api";
   ```
5. Deploy or rebuild the frontend, and you can now open the app on **any device anywhere**!

---

## ⚡ Active Postings Validation Details
To prevent outdated job posts from crowding the dashboard:
1. When the scraper executes, it first pulls fresh jobs and adds new matching roles to the local database.
2. At the end of every scrape loop, it fires a parallelized status check (`prune_expired_jobs`) on all stored job listings using a thread pool.
3. It validates each job page for `404 Not Found` statuses or keywords indicating the opening is closed (e.g., *"No longer accepting applications"*, *"posting has expired"*, etc.).
4. If a listing is closed, it is instantly deleted from the database so only active roles remain visible on the dashboard.
