from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()   

BASE_DIR = Path(__file__).resolve().parent.parent

domain = os.getenv("DOMAIN")

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG") or False

ALLOWED_HOSTS = ["*"] #[domain]  # use ["*"] to allow all in development


CORS_ALLOW_ALL_ORIGINS = True



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',  # for GinIndex & SearchVectorField
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular', 
    'acad_core',
]



REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':[
        'acad_core.authenticator.CustomTokenAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES':[
        'rest_framework.throttling.ScopedRateThrottle',
    ],

    'DEFAULT_THROTTLE_RATES':{
        'auth_register': '5/hour',
        'auth_login': '20/hour',
        'auth_verify': '10/hour',
    },

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}



SPECTACULAR_SETTINGS = {
    "TITLE": "Acad AI – Mini Assessment Engine API",
    "VERSION": "1.0.0",
    "DESCRIPTION": """
### Overview
Acad AI is a backend-driven assessment engine designed to simulate real-world academic
examinations. The system allows students to securely take exams, submit answers, and
receive automated grading feedback through a well-structured REST API.

This API is built with Django and Django REST Framework, following industry best practices
for security, data integrity, and scalability.

---

### Core Features
- Exam creation and management (admin-only)
- Secure student exam participation
- Automated grading and result generation
- Optimized data retrieval for student results
- Fully documented REST endpoints for frontend integration

---

### Assessment Engine Scope
This API implements the requirements of the **Mini Assessment Engine (Acad AI Backend Test Task)**,
including:

#### 1. Database Modeling
The system models the complete assessment lifecycle using a normalized relational schema:
- **Exams**: title, course, duration, metadata, availability window
- **Questions**: linked to exams, question type (MCQ, short answer, essay), expected answers
- **Submissions**: student, exam, submitted answers, timestamps, and computed grades

Indexes, foreign keys, and constraints are applied to ensure data consistency and efficient queries.

---

#### 2. Secure Student Submissions
- Students can only submit and access **their own exam submissions**
- Authentication is required for all student-related endpoints
- Permissions and validation prevent unauthorized access or duplicate submissions

---

#### 3. Automated Grading
The grading logic is modular and extensible. Depending on configuration, the system supports:
- **Mock grading logic** (keyword matching, similarity scoring, rule-based evaluation)
- **Optional LLM-based grading** (e.g., OpenAI, Gemini, Claude), abstracted behind a service layer

This design allows future grading strategies to be introduced without modifying core logic.

---


### Student Exam Flow
The following illustrates how a student interacts with the system:

```mermaid
Flow:

1. UI displays all available exams (ENDPOINT: GET /api/user/exams/)  ----> PAGE 1
2. Student selects the exam they want to take 
3. UI displays exam details with Start button (ENDPOINT: GET /api/user/exams/{exam_id}/) ----> PAGE 2
4. Student clicks Start button 
5. Frontend fetches questions from backend and randomizes them (ENDPOINT: POST /api/user/exams/{exam_id}/start/) ----> PAGE 3
6. Student answers questions one by one (Next/Previous button to navigate each question) ----> PAGE 4
7. Student clicks Submit button to submit answers for grading (ENDPOINT: POST /api/user/exams/{exam_id}/submit/) ----> PAGE 5
8. Backend immediately stores the submission and returns a response with submission status = SUBMITTED, while grading runs asynchronously in the background
9. Frontend displays a waiting state (timer / loading screen) while grading is in progress
10.Frontend periodically checks if grading is completed (ENDPOINT: GET /api/user/exams/{exam_id}/results/)

Once grading is completed, backend returns final score, per-question feedback, and grading details, which are displayed to the student

```




### Authentication & Authorization
This API uses **Bearer Token Authentication**.

#### How to authenticate
1. Obtain an access token by logging in via the authentication endpoint.
2. Include the token in every authenticated request using the `Authorization` header.

**Header format:**
`Authorization: Bearer <your_access_token>`

#### Notes
- Requests without a valid token will receive `401 Unauthorized`
- Admin-only endpoints require an authenticated user with admin privileges
- Students can only access resources they own

---

### API Documentation
- Interactive API documentation is available via **Swagger UI**
- All endpoints include:
  - Required authentication details
  - Request and response examples
  - Clear validation and error responses

This documentation is intended to support seamless frontend and third-party integrations.

---

### Evaluation Focus
This project demonstrates:
- Clean and maintainable backend architecture
- Effective use of Django & Django REST Framework
- Strong security and permission enforcement
- Efficient database querying and result retrieval

Optimized access patterns for student results are implemented to reflect production-grade backend design.
""",
}



MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acad_engine.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'acad_engine.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# For PostgreSQL configuration using environment variables, uncomment and set the following:
# DATABASES = {
#     'default': {
#         'ENGINE': os.getenv("ENGINE"),
#         'NAME': os.getenv("NAME"),
#         'USER': os.getenv("USER"),
#         'PASSWORD': os.getenv("PASSWORD"),
#         'HOST': os.getenv("HOST"),
#         'PORT': os.getenv("PORT"),
#         'OPTIONS': {
#             'sslmode': 'require',
#         },
#     }
# }


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')



DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
GRADER_BACKEND = os.getenv("GRADER") or "mock"
TOKEN_EXPIRE_HOURS = 24
