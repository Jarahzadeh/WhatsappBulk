import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.entities import AuditLog, Campaign, Contact, Message, OptOut
from app.services.campaigns import auto_pause_needed, build_template_components
from app.services.throttler import RateThrottler
from app.services.whatsapp import WhatsAppClient

throttler = RateThrottler(settings.per_minute_cap, settings.per_hour_cap)
wa_client = WhatsAppClient()


async def process_pending_messages():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            rows = db.execute(select(Message).where(Message.status == "pending").where((Message.send_after.is_(None)) | (Message.send_after <= now)).limit(20)).scalars().all()
            for msg in rows:
                campaign = db.get(Campaign, msg.campaign_id) if msg.campaign_id else None
                if campaign and campaign.status == "paused":
                    continue
                contact = db.get(Contact, msg.contact_id)
                if not contact or contact.blocked:
                    msg.status = "failed"
                    msg.error_code = "CONTACT_BLOCKED"
                    continue
                if db.execute(select(OptOut).where(OptOut.contact_id == contact.id)).first():
                    msg.status = "failed"
                    msg.error_code = "OPTED_OUT"
                    continue
                if not throttler.allow(now):
                    break
                if now.hour < settings.business_hours_start or now.hour >= settings.business_hours_end:
                    msg.send_after = now + timedelta(minutes=15)
                    continue
                try:
                    result = await wa_client.send_template(
                        to=contact.phone_e164,
                        template_name=msg.template_name,
                        language=msg.payload_json.get("language", "en"),
                        components=build_template_components(msg.payload_json.get("variables", {}), contact),
                    )
                    msg.status = "sent" if not result.get("dry_run") else "dry_run"
                    msg.sent_at = now
                    msg.wa_message_id = (result.get("messages") or [{}])[0].get("id") if isinstance(result, dict) else None
                    contact.last_outbound_time = now
                except Exception as exc:  # noqa: BLE001
                    msg.retry_count += 1
                    if msg.retry_count > 5:
                        msg.status = "failed"
                        msg.error_code = str(exc)
                    else:
                        msg.send_after = now + timedelta(minutes=2**msg.retry_count)
                db.add(AuditLog(event_type="message_dispatch_attempt", details={"message_id": msg.id, "status": msg.status}))

            if rows:
                for cid in set([m.campaign_id for m in rows if m.campaign_id]):
                    if auto_pause_needed(db, cid):
                        campaign = db.get(Campaign, cid)
                        if campaign:
                            campaign.status = "paused"
                            db.add(AuditLog(event_type="campaign_auto_paused", details={"campaign_id": cid}))
            db.commit()
        finally:
            db.close()
        await asyncio.sleep(3)
