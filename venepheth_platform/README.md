# Venepheth SAYAVONG Academic Platform

A Django-based Professional Academic Platform built for Lecturer Venepheth SAYAVONG. 
Features a Zero-Cost Enterprise architecture, Modern UI (Tailwind + HTMX), and a Security-by-Design approach.

## 🚀 Features

- **Academic Profile & CV Management**: Centralized academic identity
- **Course Management**: Modules, resources, visibility controls
- **Research & Publications**: DOI tracking, citations, project statuses
- **Digital Resource Library**: Secure file hosting with MIME/size validation
- **Role-Based Access Control**: Superadmin, Admin, Lecturer, Editor, Researcher, Student
- **Audit Logging**: Immutable tracking of all state-changing actions
- **Modern UI**: Tailwind CSS, HTMX, Alpine.js, Lucide Icons

## 🛠 Tech Stack

- **Backend**: Django 5, Django REST Framework, Celery
- **Database**: PostgreSQL 16
- **Cache & Queue**: Redis 7
- **Frontend**: Django Templates, HTMX, Tailwind CSS, Alpine.js
- **Infrastructure**: Docker, Nginx, Gunicorn

## 🏃‍♂️ Quick Start (Development)

1. **Clone & Setup Environment**
   ```bash
   git clone <repo-url>
   cd venepheth_platform
   cp .env.example .env
   # Edit .env and change default passwords
   ```

2. **Start Infrastructure (DB & Redis)**
   ```bash
   docker-compose up -d db redis
   ```

3. **Install Dependencies & Migrate**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements/development.txt
   
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run Server**
   ```bash
   python manage.py runserver
   ```
   Or use the full Docker Compose stack:
   ```bash
   docker-compose up --build
   ```

## Import Verified CV Data

After confirming the target database and taking a backup, import the profile,
education, BBA teaching subjects, and publications present in the supplied CV:

```bash
docker compose exec -T web python manage.py backup_platform --output-dir /app/backups --keep-days 0 --encrypt
docker compose exec -T web python manage.py import_cv_data --remove-demo-data
```

Provision `BACKUP_ENCRYPTION_KEY` or the ignored `backup_key.bin` before the
backup command; it refuses to create an encrypted archive without a persistent
key.
The option removes only exact sample records created by the retired
`seed_data` command; it does not clear user-created courses, articles, research,
or resources. Imported records intentionally omit details absent from the CV,
such as course credits, publication abstracts, and language proficiency.

## 🔒 Security

This platform employs strict security measures:
- Immutable audit trails for all sensitive actions.
- Django-axes for brute force protection.
- Forced MFA for Admin/Superadmin roles.
- File upload scanning (MIME types via `python-magic`, strict extension whitelists).
- Object-level permissions via `django-guardian`.

## 🏗 Project Structure

Following a Modular Monolith architecture:
- `apps/core`: Shared models and utilities.
- `apps/accounts`: Custom user and RBAC.
- `apps/audit` & `apps/security`: System monitoring and logs.
- `apps/profiles`, `courses`, `research`, `resources`: The academic core.
