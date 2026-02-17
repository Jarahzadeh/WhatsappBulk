import csv
import io
import json
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AuditLog, Campaign, Contact, Message, OptOut, Template
from app.schemas.schemas import CampaignCreate, OptOutImport, PauseResumeRequest, TemplateDraft
from app.services.campaigns import campaign_status_counts, eligible_contacts, queue_campaign_messages
from app.services.whatsapp import WhatsAppClient
from app.utils.phone import PhoneValidationError, dedupe_contacts, normalize_phone
from app.utils.security import verify_webhook_signature

router = APIRouter()
wa_client = WhatsAppClient()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Contact.id)))
    opted_out = db.scalar(select(func.count(OptOut.id)))
    sent = db.scalar(select(func.count(Message.id)).where(Message.status.in_(["sent", "delivered", "read"])))
    failed = db.scalar(select(func.count(Message.id)).where(Message.status == "failed"))
    return {
        "contacts": total,
        "opt_outs": opted_out,
        "delivery_success_rate": 0 if not sent else round(sent / max(1, sent + failed), 3),
        "failed": failed,
        "tier_warning": "Approaching cap" if failed > 50 else "ok",
    }


@router.post("/contacts/import")
async def import_contacts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    if file.filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(content))
        rows = df.to_dict(orient="records")
    else:
        text = content.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
    rows = dedupe_contacts(rows)
    created = 0
    for row in rows:
        try:
            phone = normalize_phone(row.get("phone") or row.get("phone_e164"))
        except PhoneValidationError:
            continue
        existing = db.execute(select(Contact).where(Contact.phone_e164 == phone)).scalar_one_or_none()
        tags = row.get("tags") or []
        if isinstance(tags, str):
            tags = [x.strip() for x in tags.split("|") if x.strip()]
        payload = {
            "name": row.get("name"),
            "language": row.get("language") or "en",
            "tags": tags,
            "opt_in_status": str(row.get("opt_in_status", "false")).lower() == "true",
            "opt_in_source": row.get("opt_in_source"),
            "opt_in_time": datetime.fromisoformat(row["opt_in_time"]) if row.get("opt_in_time") else None,
            "opt_in_text": row.get("opt_in_text"),
        }
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
        else:
            db.add(Contact(phone_e164=phone, **payload))
            created += 1
    db.add(AuditLog(event_type="contacts_imported", details={"filename": file.filename, "count": created}))
    db.commit()
    return {"created": created, "received": len(rows)}


@router.get("/contacts")
def list_contacts(db: Session = Depends(get_db)):
    rows = db.execute(select(Contact)).scalars().all()
    return rows


@router.post("/opt-outs/import")
def import_opt_outs(req: OptOutImport, db: Session = Depends(get_db)):
    count = 0
    for phone in req.phones:
        try:
            normalized = normalize_phone(phone)
        except PhoneValidationError:
            continue
        contact = db.execute(select(Contact).where(Contact.phone_e164 == normalized)).scalar_one_or_none()
        if not contact:
            continue
        contact.opt_in_status = False
        db.add(OptOut(contact_id=contact.id, reason=req.reason))
        count += 1
    db.add(AuditLog(event_type="opt_outs_imported", details={"count": count}))
    db.commit()
    return {"opted_out": count}


@router.post("/templates")
def create_template_draft(req: TemplateDraft, db: Session = Depends(get_db)):
    tmpl = Template(**req.model_dump())
    db.add(tmpl)
    db.add(
        AuditLog(
            event_type="template_draft_created",
            details={
                "name": req.name,
                "meta_submission_hint": "Submit in Meta Business Manager > WhatsApp Manager > Message Templates, then set approved_template_id via PATCH /templates/{name}.",
            },
        )
    )
    db.commit()
    return {"status": "draft_saved", "next": "submit_in_meta"}


@router.patch("/templates/{name}")
def approve_template(name: str, body: dict, db: Session = Depends(get_db)):
    tmpl = db.execute(select(Template).where(Template.name == name)).scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="template not found")
    tmpl.approved_template_id = body.get("approved_template_id")
    tmpl.status = body.get("status", "approved")
    db.add(AuditLog(event_type="template_updated", details={"name": name, "status": tmpl.status}))
    db.commit()
    return {"ok": True}


@router.post("/campaigns")
def create_campaign(req: CampaignCreate, db: Session = Depends(get_db)):
    c = Campaign(**req.model_dump(), status="scheduled" if req.scheduled_at else "draft")
    db.add(c)
    db.commit()
    db.refresh(c)
    contacts = eligible_contacts(db, req.segment_query)
    queue_campaign_messages(db, c, contacts)
    return {"campaign_id": c.id, "eligible": len(contacts)}


@router.post("/campaigns/{campaign_id}/preview")
def preview_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    contacts = eligible_contacts(db, campaign.segment_query)
    sample = contacts[:10]
    previews = [
        {
            "to": c.phone_e164,
            "name": c.name,
            "language": c.language,
            "template": campaign.template_name,
            "variables": campaign.variables_json,
        }
        for c in sample
    ]
    return {"sample_count": len(previews), "previews": previews}


@router.post("/campaigns/{campaign_id}/status")
def pause_resume_campaign(campaign_id: int, req: PauseResumeRequest, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="not found")
    campaign.status = req.status
    db.add(AuditLog(event_type="campaign_status_changed", details={"campaign_id": campaign_id, "status": req.status}))
    db.commit()
    return {"ok": True}


@router.get("/campaigns/{campaign_id}/queue")
def queue_dashboard(campaign_id: int, db: Session = Depends(get_db)):
    return campaign_status_counts(db, campaign_id)


@router.post("/send/interactive")
async def send_interactive(body: dict):
    return await wa_client.send_interactive(body["to"], body["body_text"], body["action"])


@router.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.verify_token:
        return JSONResponse(content=int(challenge))
    raise HTTPException(status_code=403, detail="forbidden")


@router.post("/webhook")
async def webhook_events(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.app_secret and not verify_webhook_signature(body, signature, settings.app_secret):
        raise HTTPException(status_code=401, detail="invalid signature")
    event = json.loads(body.decode("utf-8"))
    entries = event.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                phone = normalize_phone(message.get("from"))
                contact = db.execute(select(Contact).where(Contact.phone_e164 == phone)).scalar_one_or_none()
                if contact:
                    contact.last_inbound_time = datetime.utcnow()
                    db.add(Message(contact_id=contact.id, direction="in", payload_json=message, status="received"))
                    text = (((message.get("text") or {}).get("body") or "").strip().lower())
                    if text in {"stop", "unsubscribe", "optout", "إلغاء", "لغو", "انصراف"}:
                        contact.opt_in_status = False
                        db.add(OptOut(contact_id=contact.id, reason="user_message_opt_out"))
            for status in value.get("statuses", []):
                wa_id = status.get("id")
                msg = db.execute(select(Message).where(Message.wa_message_id == wa_id)).scalar_one_or_none()
                if msg:
                    msg.status = status.get("status", msg.status)
                    if msg.status == "delivered":
                        msg.delivered_at = datetime.utcnow()
                    if msg.status == "read":
                        msg.read_at = datetime.utcnow()
    db.add(AuditLog(event_type="webhook_received", details={"entries": len(entries)}))
    db.commit()
    return {"ok": True}


@router.get("/audit-logs")
def list_audit_logs(db: Session = Depends(get_db)):
    return db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).scalars().all()
