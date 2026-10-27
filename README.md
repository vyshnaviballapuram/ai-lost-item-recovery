# AI-Based Campus Lost-Item Recovery System with Admin Approval Workflow

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Django 5.x/6.x](https://img.shields.io/badge/django-6.1-green.svg)](https://www.djangoproject.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.8.0-orange.svg)](https://scikit-learn.org/)
[![Deployment](https://img.shields.io/badge/deploy-Render%20Ready-violet.svg)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent, secure, database-backed web application engineered for university campuses. Designed as an industry-standard B.Tech Computer Science final-year engineering capstone project.

---

## 1. System Philosophy & Critical Privacy Invariant

> **CRITICAL ARCHITECTURAL REQUIREMENT:**  
> **Submitted reports NEVER appear automatically on the public catalog.**  
> Every submission is saved with a `PENDING` approval status. The embedded AI matching engine evaluates compatibility against counter-reports privately. Campus administrators inspect AI match suggestions, contact reporters, verify evidence against confidential item markings, and approve reports before any sanitized data is published publicly.

---

## 2. Key Capabilities & Workflow Architecture

```
   [ Student A: Reports Lost Item ]            [ Student B: Turns In Found Item ]
                 │                                              │
                 ▼                                              ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ 1. PRIVATE SUBMISSION: Saved with PENDING status (Not public)          │
   │    Confidential details (serials, marks, private contacts) secured     │
   └───────────────────────────────────┬────────────────────────────────────┘
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ 2. AI MATCHING ENGINE (items/services/ai_matching.py)                 │
   │    • Scikit-Learn TF-IDF N-gram Lexical Cosine Similarity (45%)        │
   │    • Category & Subcategory Classification Compatibility (20%)         │
   │    • Distinctive Brand & Color Token Attribute Overlap (15%)           │
   │    • Campus Landmark & Zone Spatial Proximity (10%)                    │
   │    • Chronological Timeline Coherence Analysis (10%)                  │
   └───────────────────────────────────┬────────────────────────────────────┘
                                       │
                                       ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ 3. CUSTOM ADMIN DASHBOARD & APPROVAL CONSOLE                          │
   │    • Inspect AI Similarity Score (0-100) and Justification Reasons     │
   │    • Compare Lost vs Found reports side-by-side                       │
   │    • Conduct and log student contact attempts (Email, Phone, Desk)     │
   │    • Action decision: APPROVE, REJECT, or REQUEST INFORMATION         │
   └───────────────────┬────────────────────────────────────────────────────┘
                       │
         ┌─────────────┴────────────────────────┐
         ▼                                      ▼
[ Approved: Eligible for              [ Rejected / Needs Info:
  Sanitized Public Listing ]            Remains strictly hidden; student notified ]
         │
         ▼
[ Student Claims Ownership on Found Item ]
         │
         ▼
[ Admin Compares Claim Evidence vs Confidential Markings ]
         │
         ▼
[ Verified Physical Hand-Off -> Recovery Record & Auto-Archival ]
```

---

## 3. Technology Stack

- **Backend:** Python 3.11+, Django 5.x/6.x, Django ORM, Django REST Framework.
- **Machine Learning / NLP:** Scikit-Learn (`TfidfVectorizer`, `cosine_similarity`), NumPy.
- **Database:** SQLite (local development), PostgreSQL (production on Render via `dj-database-url`).
- **Frontend:** HTML5, Vanilla CSS3 with custom Dark SaaS theme, Bootstrap 5.3, Bootstrap Icons, Chart.js 4.4.
- **Security:** Strict IDOR protection, CSRF protection, server-side permission decorators, database constraints preventing duplicate match pairs, immutable audit logging.
- **Production Serving:** WhiteNoise for static assets, Gunicorn for WSGI application serving.

---

## 4. Default Seed Accounts

The system comes equipped with a `seed_data` management command providing pre-configured test users across all roles:

| Role | Username | Password | Email | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin12345` | `admin@campus.edu` | Full Administrator & Superuser access |
| **Staff** | `security_officer` | `officer12345` | `security@campus.edu` | Campus Security Desk Officer |
| **Student A** | `arjun_patel` | `student12345` | `arjun.p@campus.edu` | Roll No: `CS-2023-042` |
| **Student B** | `priya_sharma` | `student12345` | `priya.s@campus.edu` | Roll No: `EC-2024-118` |
| **Student C** | `rahul_verma` | `student12345` | `rahul.v@campus.edu` | Roll No: `ME-2023-089` |

---

## 5. Local Setup & Quickstart Guide

### Prerequisites
- Python 3.11+ installed
- Git installed

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd ai-lost-item-recovery
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Seed demo data (Users, categories, reports, AI matches):**
   ```bash
   python manage.py seed_data
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   Open your browser at `http://127.0.0.1:8000/`.

---

## 6. Running Automated Tests

The application includes an extensive automated test suite covering all security boundaries, ML calculations, and workflow lifecycles:

```bash
python manage.py test items
```

**Verified Test Scenarios (18/18 passing):**
- Student registration, password hashing, and authentication redirects.
- Lost and found report creation defaulting to `PENDING` approval status.
- Verification that pending and rejected reports are excluded from public listings.
- Insecure Direct Object Reference (IDOR) protection: unapproved reports return `404 Not Found` for unauthorized viewers.
- AI TF-IDF vectorization and multi-factor similarity score calculation.
- Validation that AI rejects same-type comparisons (Lost-Lost, Found-Found, or self-comparison).
- Database unique constraints preventing duplicate report-pair match records.
- Role-based authorization: regular students accessing admin console receive `403 Permission Denied`.
- Report approval, rejection, and request-information state-machine transitions.
- Student contact logger and system audit logging.
- Ownership claim submission, verification against confidential markings, and physical hand-off recovery creation.

---

## 7. Render Deployment Guide

The codebase is pre-configured for deployment on [Render](https://render.com/).

### Step 1: Push Code to GitHub
Push this project to a GitHub repository.

### Step 2: Create a PostgreSQL Database on Render
1. In the Render Dashboard, click **New +** > **PostgreSQL**.
2. Name the database (e.g., `campus-recovery-db`).
3. Copy the **Internal Database URL**.

### Step 3: Create a Web Service on Render
1. Click **New +** > **Web Service** and connect your GitHub repository.
2. Select runtime: **Python 3**.
3. Set the build and start commands:
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3`
4. Set Environment Variables:
   - `DEBUG`: `False`
   - `DJANGO_SECRET_KEY`: `<Generate a random 50+ character string>`
   - `ALLOWED_HOSTS`: `.onrender.com`
   - `DATABASE_URL`: `<Your Render PostgreSQL connection URL>`
   - `CSRF_TRUSTED_ORIGINS`: `https://your-service-name.onrender.com`
   - `PUBLIC_REPORTS_ENABLED`: `True`

### Step 4: Persistent Disk for Media Files (Optional but Recommended)
On Render free web services, the local file system is ephemeral. For production persistent image storage:
1. Under **Disks**, add a Persistent Disk with Mount Path: `/opt/render/project/src/media`.
2. Or configure AWS S3 / Cloudinary using `django-storages`.

### Step 5: Create Initial Superuser on Render
In the Render Web Service Shell tab, run:
```bash
python manage.py createsuperuser
```
Or execute the automated seed script:
```bash
python manage.py seed_data
```

---

## 8. End-to-End Acceptance Scenario Walkthrough

Follow these steps to demonstrate the complete lifecycle:

1. **Submit a Lost Item Report:**
   - Log in as `arjun_patel` (`student12345`).
   - Go to **Report Lost Item**. Submit a report for a lost *Space Gray iPad Pro* in *Central Library*.
   - Add confidential marks: *Serial ending in 948; wallpaper is Mountain Lake*.
   - Confirm the report is created with status `PENDING`.
2. **Verify Public Privacy:**
   - Log out or open an incognito window. Visit the public **Home Page** and **Approved Listings**.
   - Confirm that Arjun's report does **NOT** appear on the public page.
   - Attempt to access the report URL directly: confirm you receive a `404 Not Found` (IDOR blocked).
3. **Submit a Compatible Found Item Report:**
   - Log in as `priya_sharma` (`student12345`).
   - Submit a found report: *Found Apple iPad in Central Library reading hall*.
   - Set confidential marks: *Serial ending in 948; mountain wallpaper*.
4. **AI Matching & Admin Review:**
   - Log in as `admin` (`admin12345`).
   - Navigate to the **Admin Console** (`/admin-dashboard/`).
   - Under **Approval Queue**, inspect Arjun's lost report.
   - Under **AI Match Review**, observe that the AI engine automatically paired Arjun's and Priya's reports with high similarity score (~85%+), displaying detailed reasons.
5. **Admin Contact Verification:**
   - In the report review console, log a contact attempt confirming details with Arjun.
   - Approve Arjun's and Priya's reports with verified notes.
6. **Public Visibility Transition:**
   - Check the public listings again: only approved reports appear now, with confidential marks and private phone numbers stripped.
7. **Claim & Recovery Completion:**
   - File an ownership claim on the item.
   - In the admin console, verify the claim against the confidential marks.
   - Finalize physical hand-off using the Recovery Form.
   - The reports transition to `ARCHIVED`, an immutable `RecoveryRecord` is created, and both parties receive notifications.

---

## 9. License

Developed for academic and engineering excellence. Released under the MIT License.
