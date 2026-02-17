import random
from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.entities import AuditLog, Campaign, Contact, Message, OptOut


def eligible_contacts(db: Session, segment_query: dict):
    stmt = select(Contact).where(Contact.blocked.is_(False))
    tags = segment_query.get("tags")
    language = segment_query.get("language")
    if language:
        stmt = stmt.where(Contact.language == language)
    contacts = db.execute(stmt).scalars().all()
    filtered = []
    for c in contacts:
        if tags and not set(tags).intersection(set(c.tags or [])):
            continue
        if c.opt_in_status or c.last_inbound_time:
            if not db.execute(select(OptOut).where(OptOut.contact_id == c.id)).first():
                filtered.append(c)
    return filtered


def build_template_components(variables: dict, contact: Contact):
    merged = {**variables, "name": contact.name or "Customer", "branch": variables.get("branch", "Main branch")}
    body_params = [{"type": "text", "text": str(v)} for _, v in merged.items()]
    return [{"type": "body", "parameters": body_params}]


def queue_campaign_messages(db: Session, campaign: Campaign, contacts: list[Contact]):
    greetings = ["Hello", "Hi", "Dear"]
    closings = ["Thank you", "Regards", "Team"]
    for contact in contacts:
        payload = {
            "variables": campaign.variables_json,
            "greeting": random.choice(greetings),
            "closing": random.choice(closings),
            "language": contact.language,
        }
        jitter_minutes = random.randint(0, 45)
        msg = Message(
            campaign_id=campaign.id,
            contact_id=contact.id,
            direction="out",
            template_name=campaign.template_name,
            payload_json=payload,
            status="pending",
            send_after=(campaign.scheduled_at or datetime.utcnow()) + timedelta(minutes=jitter_minutes),
        )
        db.add(msg)
    db.add(AuditLog(event_type="campaign_queued", details={"campaign_id": campaign.id, "count": len(contacts)}))
    db.commit()


def auto_pause_needed(db: Session, campaign_id: int, threshold: float = 0.3):
    msgs = db.execute(select(Message).where(Message.campaign_id == campaign_id)).scalars().all()
    if not msgs:
        return False
    fails = len([m for m in msgs if m.status in {"failed", "blocked"}])
    return (fails / len(msgs)) >= threshold


def campaign_status_counts(db: Session, campaign_id: int):
    msgs = db.execute(select(Message).where(Message.campaign_id == campaign_id)).scalars().all()
    out = {"pending": 0, "sent": 0, "failed": 0, "delivered": 0, "read": 0}
    for m in msgs:
        out[m.status] = out.get(m.status, 0) + 1
    return out
