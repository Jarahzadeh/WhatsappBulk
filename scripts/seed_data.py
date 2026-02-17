from datetime import datetime

from app.db.session import SessionLocal
from app.models.entities import Contact, Template


def run():
    db = SessionLocal()
    if db.query(Contact).count() == 0:
        db.add_all([
            Contact(name='Ali', phone_e164='+971501111111', language='ar', tags=['dubai'], opt_in_status=True, opt_in_source='web_form', opt_in_time=datetime.utcnow()),
            Contact(name='Sara', phone_e164='+971502222222', language='en', tags=['fujairah'], opt_in_status=True, opt_in_source='pos_receipt', opt_in_time=datetime.utcnow()),
        ])
    if db.query(Template).count() == 0:
        db.add(Template(name='menu_offer_v1', language='en', category='marketing', body_draft='Hi {{1}}, check menu {{2}}'))
    db.commit()
    db.close()


if __name__ == '__main__':
    run()
