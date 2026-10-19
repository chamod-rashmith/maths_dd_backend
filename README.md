# Maths DD Backend Service (Google Cloud Run)

This is the backend microservice for the **Maths DD** ecosystem. It handles content management, automation crons, and AI-driven mathematical question processing.

## 📁 Directory Structure
```
backend/
├── main.py            # FastAPI Application Entrypoint
├── requirements.txt   # Python Dependencies
├── Dockerfile         # Container Recipe for Cloud Run
├── .dockerignore      # Ignored files during container build
└── README.md          # Setup and Deployment Guide
```

---

## 💻 1. Running Locally

### Step 1: Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Start the server
```bash
python main.py
```
Or with Uvicorn:
```bash
uvicorn main:app --reload --port 8080
```

### Step 3: Test endpoints
- **Root:** [http://localhost:8080/](http://localhost:8080/)
- **Health Check:** [http://localhost:8080/health](http://localhost:8080/health)
- **Interactive Swagger Docs:** [http://localhost:8080/docs](http://localhost:8080/docs)

---

## ☁️ 2. Deploying to Google Cloud Run

### Option A: From Google Cloud Console (GUI)
1. Go to [Google Cloud Console -> Cloud Run](https://console.cloud.google.com/run).
2. Click **Create Service**.
3. Select **"Continuously deploy from a repository"** (connect GitHub repo and point to `backend/Dockerfile`), or upload the source folder.
4. Set **Port** to `8080`.
5. Under **Authentication**, check **"Allow unauthenticated invocations"** (if testing publicly).
6. Click **Create / Deploy**.

### Option B: Using Google Cloud SDK (`gcloud`)
```bash
cd backend
gcloud run deploy maths-dd-backend \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated
```
Google Cloud Build will automatically build the container from `Dockerfile` and give you a live HTTPS link!
