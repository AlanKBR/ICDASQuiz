# ICDAS Educacional

A production-deployed visual learning platform for the **International Caries Detection and Assessment System (ICDAS)**. It combines concise theory, a clinical image gallery, an interactive quiz, and instructor analytics in one responsive web application.

**Live application:** [www.icdasquiz.tech](https://www.icdasquiz.tech/)  
**Language:** Portuguese  
**Academic context:** Dentistry capstone project at UFJF-GV

## Project snapshot

| | |
|---|---|
| **Audience** | Dentistry students and instructors |
| **Problem** | ICDAS criteria are easier to memorize than to recognize consistently in clinical images |
| **Product** | Guided theory, visual examples, image-based practice, immediate feedback, and performance analytics |
| **Delivery** | Server-rendered Flask application, portable database layer, containerized production deployment |
| **Status** | Live and actively maintained |

## What the product does

Learners can review the ICDAS 0–6 criteria, browse labeled clinical examples, and practice classifying lesions in random or sequential quiz modes. Each answer receives immediate feedback and an explanation of the relevant clinical signs.

For instructors, the restricted dashboard turns quiz activity into useful teaching data:

- performance by ICDAS code
- confusion matrix between submitted and correct classifications
- images with the highest error rate
- attempt history and learner progression
- quiz mode and content-version comparisons
- CSV export for further analysis

## Engineering highlights

This project goes beyond a static educational page. It includes product, data, reliability, privacy, and deployment decisions that support real use:

- **Portable persistence:** the same application runs with embedded SQLite locally or PostgreSQL in production through SQLAlchemy.
- **Versioned schema:** Alembic controls database changes across both supported backends.
- **Structured analytics:** the data model separates participants, attempts, and individual answers, including response order and timing.
- **Content-aware versioning:** quiz versions are derived from the image and description set, keeping historical results interpretable as content changes.
- **Replay-safe forms:** each submission is bound to the attempt and question actually shown, so stale or forged responses are rejected.
- **Shared-device support:** declared learner identity is separate from the network signal, allowing multiple people to use the same computer or Wi-Fi.
- **Scale-to-zero friendly lifecycle:** expired active attempts are handled lazily without requiring a resident scheduler.
- **Production hardening:** secure headers, trusted-host validation, protected instructor access, rate limiting, and non-root container execution.

## Technology

| Layer | Technology |
|---|---|
| Language | Python 3.10+; Python 3.13 in the production image |
| Web framework | Flask 3.1 + Jinja2 |
| Persistence | SQLAlchemy 2 + Alembic |
| Databases | SQLite or PostgreSQL |
| UI | Tailwind CSS 4, local CSS, minimal vanilla JavaScript |
| Application server | Gunicorn |
| Testing | pytest |
| Packaging | Docker |

The application deliberately favors server-rendered pages and small JavaScript modules. This keeps the interaction model understandable, the deployment compact, and the core quiz behavior testable on the server.

## Data and privacy model

The main relationship is:

```text
participant -> attempt -> answers
```

A participant is an identity declared for the current learning session, not proof of civil identity. Each answer records the displayed image, submitted code, correct code, correctness, position, and response time.

The original IP address is not stored in clear text. When needed as a technical signal, it is retained only as an HMAC. It does not populate names or merge people into a single identity.

## Run locally

### Requirements

- Python 3.10+
- `pip`

### Setup

```bash
git clone https://github.com/AlanKBR/ICDASQuiz.git
cd ICDASQuiz

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://localhost:5000`.

When neither `DATABASE_URL` nor the PostgreSQL component variables are configured, the application uses an embedded SQLite database. Pointing it to PostgreSQL requires no application-code changes.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `FLASK_DEBUG` | Development mode; never enable in production | `0` |
| `SECRET_KEY` | Session-signing key | Required in production |
| `ADMIN_PASSWORD` | Instructor dashboard password | Required for dashboard access |
| `DATABASE_URL` | Complete SQLAlchemy database URL | Empty |
| `DB_PATH` | SQLite file path | `icdas.db` |
| `POSTGRES_HOST` | Enables URL assembly from PostgreSQL components | Empty |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | PostgreSQL database | Required with `POSTGRES_HOST` |
| `POSTGRES_USER` | PostgreSQL user | Required with `POSTGRES_HOST` |
| `POSTGRES_PASSWORD` | PostgreSQL password | Required with `POSTGRES_HOST` |
| `TRUSTED_HOSTS` | Allowed production hosts | Environment-specific |

Generate a development secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Tests

```bash
python -m pytest tests.py -v
```

The suite covers:

- core routes and error handling
- random and sequential quiz flows
- score, queue, reset, and mode-switch behavior
- persistence and migrations on isolated temporary databases
- idempotency, stale-form rejection, and concurrent interactions
- shared-device and name-normalization cases
- attempt expiration and historical preservation
- restricted analytics and CSV formula-injection protection
- invalid input handling and security headers

## Production model

The repository owns application code. Runtime infrastructure, secrets, routing, backups, and rollback remain outside the repository.

The production image runs the app with Gunicorn as a non-root user and uses PostgreSQL. Database files, local SQLite state, and `.env` files must never be committed. Deployments use an explicit Git SHA rather than automatically deploying every change to `main`.

## Adding clinical images

Clinical images are loaded from `static/imagens/`.

1. Name the source using `ICDAS_<code>_<description>.<ext>`.
2. Normalize it with `tools/convert_images.py`.
3. Add the generated WebP asset and matching description.
4. Run the test suite before publishing the new content version.

## Security controls

- restrictive Content Security Policy
- `X-Content-Type-Options`, `X-Frame-Options`, and Referrer Policy
- production-only HSTS and secure session cookies
- `HttpOnly` and `SameSite=Lax` cookies
- server-side validation for every quiz submission
- trusted-host validation in production
- rate limiting based on the validated edge address
- HMAC-only retention of the original IP signal
- Post/Redirect/Get flow to prevent browser resubmission
- question-to-attempt binding to reject replayed forms
- CSV export protection against spreadsheet formula injection

## Academic context

**Author:** Alan Anjos Miranda  
**Advisor:** Prof. Dr. Rodrigo Varella de Carvalho  
**Institution:** Federal University of Juiz de Fora — Governador Valadares campus (UFJF-GV)

Selected references:

- Ismail AI, Sohn W, Tellez M, et al. *The International Caries Detection and Assessment System: an integrated system for measuring dental caries.* Community Dentistry and Oral Epidemiology. 2007;35(3):170–178.
- Pitts NB. *ICDAS — a foundation for innovation in caries management.* Dental Update. 2009;36(5):268–272.
- Diniz MB, et al. *Validity of ICDAS clinical criteria for caries detection in occlusal surfaces in vitro.* Caries Research. 2009;43(5):405–409.

## Use and licensing

This repository is published for academic review and portfolio evaluation. No open-source license is granted. Contact the author before reusing the application or its clinical content.
