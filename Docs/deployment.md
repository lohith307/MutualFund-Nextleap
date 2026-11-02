# Deployment & 24/7 Always-On Guide

This document describes how to deploy the **Groww Mutual Fund FAQ Assistant** to the cloud and ensure it stays awake 24/7 without incurring hosting costs.

---

## 1. Unified Architecture Advantage

The FastAPI backend (`src/api/main.py`) serves **both**:
- The **Stitch-grade Groww Web UI** at `GET /`
- The **RAG API endpoints** (`POST /query`, `GET /health`, `GET /schemes`, `GET /scheduler/status`)

This means you only need to deploy **one single service** to host both frontend and backend together!

---

## 2. Deploy on Render (Free + Never Sleeps)

Render offers a generous free tier for web services. Render normally spins down after 15 minutes of inactivity, but our automated keep-alive pinger prevents it from ever going to sleep.

### Step 1: Connect GitHub Repo to Render
1. Go to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** > **Web Service**.
3. Select your repository: `lohith307/MutualFund-Nextleap`.
4. Configure the settings (or let `render.yaml` auto-configure):
   - **Name:** `groww-mf-assistant`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

### Step 2: Add Environment Variables
In the Render dashboard under **Environment**:
| Key | Value | Description |
|---|---|---|
| `GROQ_API_KEY` | `gsk_...` | Your Groq API key |
| `LLM_PROVIDER` | `groq` | Model provider |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model |

Click **Deploy Web Service**. Render will build and deploy your app, giving you a public URL like:
`https://groww-mf-assistant.onrender.com`

---

## 3. Keep It Always Awake (Prevent Sleep Mode)

Choose either of these two free methods to prevent Render from going to sleep:

### Method A: GitHub Actions Keep-Alive (Built-in)
Our repository includes `.github/workflows/keep_alive.yml`, which pings the app every 12 minutes:
1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions** > **Variables** tab.
2. Click **New repository variable**.
3. Set Name: `APP_URL`
4. Set Value: Your Render URL (e.g. `https://groww-mf-assistant.onrender.com`).
5. Click **Add variable**.

### Method B: UptimeRobot (Free 5-Minute Pinger)
1. Sign up for free at [uptimerobot.com](https://uptimerobot.com).
2. Click **Add New Monitor**:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `Groww MF Assistant`
   - **URL (or IP):** `https://<your-render-app>.onrender.com/health`
   - **Monitoring Interval:** `Every 5 minutes`
3. Click **Create Monitor**.

Because traffic arrives every 5 to 12 minutes, Render will **never** enter sleep mode and your users will always get instant responses.

---

## 4. Deploying via Docker

To run on any Linux VPS (AWS EC2, GCP Compute Engine, DigitalOcean, Hetzner, etc.):

```bash
# Clone the repository
git clone https://github.com/lohith307/MutualFund-Nextleap.git
cd MutualFund-Nextleap

# Create your .env file with GROQ_API_KEY
echo "GROQ_API_KEY=gsk_your_key_here" > .env

# Start with Docker Compose
docker compose up -d --build
```
Your service will be live at `http://<your-server-ip>:8000`.
