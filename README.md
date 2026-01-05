# Acad AI – Mini Assessment Engine

A Django-based **REST API** backend for managing exams, questions, and student submissions.  
This project simulates the core functionality of an academic assessment engine, including secure student submissions, automated grading, and admin management of exams and questions.


## Features

- **Admin Panel**  
  - Create, update, delete exams  
  - Create, update, delete questions  
  - Bulk upload multiple-choice questions  

- **Student API**  
  - List available exams  
  - Start exams and submit answers securely  
  - Receive automated grading feedback  

  # Acad AI – Mini Assessment Engine

  A Django-based REST API backend that models exams, questions, and student
  submissions. This repository contains a small, production-minded assessment
  engine used for evaluating automated grading, secure submissions, and
  authentication flows.

  ## Table of contents

  - [Features](#features)
  - [Tech stack](#tech-stack)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment variables](#environment-variables)
  - [Database & migrations](#database--migrations)
  - [Authentication & email verification](#authentication--email-verification)
  - [API documentation](#api-documentation)
  - [Testing](#testing)
  - [License](#license)

  ## Features

  - Admin UI for managing exams and questions
  - Student endpoints to start exams, submit answers, and retrieve graded
    results
  - Modular grading engine (mock grader + pluggable LLM adapter)
  - Secure registration with email verification, login using email, and
    expiring tokens (24h)
  - OpenAPI (drf-spectacular) documentation available (Swagger / ReDoc)

  ## Tech stack

  - Python 3.10+
  - Django 4.x
  - Django REST Framework
  - PostgreSQL (recommended for production) / SQLite (development)
  - drf-spectacular for OpenAPI schema

  ## Prerequisites

  - Python 3.10+ installed
  - pip
  - A virtual environment tool (venv, pipenv, poetry)
  - (Optional) PostgreSQL for production

  ## Installation

  Clone and prepare the project:

  ```bash
  git clone https://github.com/Darrey1/Acad-AI-Backend.git
  cd "Acad-AI-Backend"
  cd "acad_engine"
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

  Create the Django settings environment (see next section) and run migrations:

  ```bash
  python manage.py migrate
  python manage.py createsuperuser
  python manage.py runserver
  ```

  ## Environment variables

  Set these at minimum for local development (for example via a .env file):

  - SECRET_KEY
  - DEBUG (True/False)
  - DOMAIN (optional)
  - GRADER (defaults to `mock`)  supported 'mock' | 'llm'
  - OPENAI_API_KEY  (optional only if you choose llm for the GRADER)

  For production, configure DATABASE settings for PostgreSQL and ensure
  EMAIL settings are set so verification emails can be sent.

  ## Database & migrations

  By default the project includes SQLite for convenience. For production switch
  to PostgreSQL and run migrations as shown above. Example (Postgres):

  ```bash
  # export DATABASE_URL or set env vars used by settings
  # then:
  python manage.py migrate
  ```

  ## Authentication & email verification

  This project implements a secure registration + email verification flow and
  login by email. Important details:

  - Register: POST /api/auth/register/  (creates inactive user and an email
    verification token)
  - Verify: POST /api/auth/verify/  (accepts a verification token; activates
    the user)
  - Login: POST /api/auth/login/  (email + password). On success returns an
    expiring token (valid for 24 hours). The token must be sent on subsequent
    requests as:

  ```
  Authorization: Token <token>
  ```

  Example register (curl):

  ```bash
  curl -s -X POST http://127.0.0.1:8000/api/auth/register/ \
    -H 'Content-Type: application/json' \
    -d '{"username": "student1", "email": "s1@example.com", "password": "S3cureP@ssw0rd"}'
  ```

  Example verify (curl) — in production the token is emailed; during local
  testing the token is returned in the register response:


  Example login (curl):

  ```bash
  curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
    -H 'Content-Type: application/json' \
    -d '{"email": "s1@example.com", "password": "S3cureP@ssw0rd"}'
  ```

  The login response contains the token and the configured expiry window
  (24 hours by default).

  Security notes

  - The registration endpoint is rate-limited (ScopedRateThrottle).
  - Passwords are validated using Django's password validators — configure
    `AUTH_PASSWORD_VALIDATORS` in `settings.py`.
  - In production: send verification emails asynchronously (Celery / background
    task) and never return verification tokens in API responses.



  ## API documentation

  OpenAPI schema and interactive docs are available at:

  - Swagger UI: /api/docs/
  - ReDoc: /api/redoc/
  - Raw schema: /api/schema/

  These endpoints are enabled when `drf-spectacular` is installed and the
  project settings include `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS']` pointing to
  `drf_spectacular.openapi.AutoSchema`.

  ## Testing

  Run the project's test suite (once tests are added):

  ```bash
  python manage.py test
  ```

  ## License

  This repository is provided for assessment purposes.

