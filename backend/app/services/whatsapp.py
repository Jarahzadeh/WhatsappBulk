from datetime import datetime

import httpx

from app.core.config import settings


class WhatsAppClient:
    def __init__(self):
        self.base = "https://graph.facebook.com/v20.0"

    async def send_template(self, to: str, template_name: str, language: str, components: list[dict]):
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }
        return await self._post(payload)

    async def send_interactive(self, to: str, body_text: str, action: dict):
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": action.get("type", "list"),
                "body": {"text": body_text},
                "action": action,
            },
        }
        return await self._post(payload)

    async def _post(self, payload: dict):
        if not settings.whatsapp_token or not settings.phone_number_id:
            return {"dry_run": True, "payload": payload, "timestamp": datetime.utcnow().isoformat()}
        url = f"{self.base}/{settings.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {settings.whatsapp_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
