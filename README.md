# WhatsApp Compliance CRM (Restaurant)

Production-oriented bulk messaging app built **only** on the official **Meta WhatsApp Cloud API**.

## Why this stack
- **Backend: FastAPI (Python)** for rapid development, async webhook/API handling, easy testability.
- **DB: PostgreSQL** (via Docker compose), with Alembic migrations.
- **Frontend: React + Vite** for fast, stable web UI.

## Compliance-first guardrails
- No unofficial WhatsApp automation, no scraping.
- Business-initiated sends rely on approved templates.
- Contact eligibility: requires `opt_in_status=true` or prior inbound conversation.
- Opt-out capture/import supported and enforced.
- Queue throttling with per-minute/per-hour limits and retry backoff.
- Audit logs for every sensitive operation.

## Repository structure
- `backend/app/main.py` API app + background dispatcher
- `backend/app/api/routes.py` Contacts, templates, campaigns, webhook, health
- `backend/app/services/whatsapp.py` Cloud API integration
- `backend/app/workers/dispatcher.py` queue worker, throttling, retries, pause rules
- `backend/app/utils/phone.py` E.164 validation and dedupe
- `backend/alembic/versions/0001_init.py` initial migration
- `frontend/src/App.jsx` compliance dashboard (EN/FA toggle)
- `sample_data/contacts_sample.csv` import sample

## Environment
Copy `.env.example` to `.env` and fill values:
- `WHATSAPP_TOKEN`
- `PHONE_NUMBER_ID`
- `WABA_ID`
- `VERIFY_TOKEN`
- `APP_SECRET` (optional, recommended)
- `BASE_URL`
- `DB_URL`

## Local run
```bash
docker compose up --build
```
Backend: http://localhost:8000
Frontend: http://localhost:5173

## Migrations
```bash
cd backend
alembic upgrade head
```

## Tests
```bash
cd backend
pytest
```

## WhatsApp Cloud API setup steps
1. Create Meta developer app and add WhatsApp product.
2. Connect your WABA and phone number.
3. Collect `WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`.
4. Set webhook callback to `https://<public-url>/api/webhook`.
5. Set verify token equal to `VERIFY_TOKEN`.
6. Subscribe to messages and statuses fields.
7. If signature validation is desired, set `APP_SECRET`.

## Template workflow
1. Create draft in app using `POST /api/templates`.
2. Submit matching text in Meta WhatsApp Manager > Message Templates.
3. After approval, store approved template id via `PATCH /api/templates/{name}`.
4. Campaign builder selects only approved templates in production process.

## Menu sending options
- Template with hosted PDF link.
- Interactive message endpoint (`POST /api/send/interactive`) for categories/buttons/lists.
- Catalog link inside template variable.

## Webhook local dev with tunnel
Use any tunnel (e.g. ngrok/cloudflared):
```bash
ngrok http 8000
```
Then set callback to generated HTTPS URL + `/api/webhook`.

## Safety controls implemented
- Auto-pause campaign when fail/blocked ratio exceeds threshold.
- Never send to opted-out contacts.
- Randomized send jitter inside business-hour window.
- Dry-run behavior when Cloud API credentials are unset.

## Notes
- Token security: keep env outside git, rotate periodically. For production, move token to OS keychain/secret manager.
- For click tracking, integrate short-link provider webhook into `messages`/`audit_logs`.
