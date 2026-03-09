"""Notification client — HTTP client to the cloud notification microservice."""

import httpx

from app.config import settings


class NotificationClient:
    """Sends notification scheduling requests to the cloud notification service."""

    def __init__(self):
        self.base_url = settings.NOTIFICATION_SERVICE_URL
        self.api_key = settings.NOTIFICATION_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=10.0,
            )
        return self._client

    async def schedule_notification(
        self,
        notification_id: str,
        telegram_chat_id: str,
        title: str,
        body: str,
        trigger_at: str,
    ) -> dict | None:
        """Schedule a Telegram notification on the cloud service."""
        if not self.base_url or not self.api_key:
            return None

        try:
            client = await self._get_client()
            response = await client.post(
                "/notify/schedule",
                json={
                    "id": notification_id,
                    "telegram_chat_id": telegram_chat_id,
                    "title": title,
                    "body": body,
                    "trigger_at": trigger_at,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            # Notification service is optional — fail silently
            return None

    async def cancel_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification."""
        if not self.base_url:
            return False

        try:
            client = await self._get_client()
            response = await client.delete(f"/notify/{notification_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def snooze_notification(
        self, notification_id: str, new_trigger_at: str
    ) -> bool:
        """Reschedule a notification to a new time."""
        if not self.base_url:
            return False

        try:
            client = await self._get_client()
            response = await client.put(
                f"/notify/{notification_id}/snooze",
                json={"trigger_at": new_trigger_at},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def register_subscription(
        self, endpoint: str, p256dh: str, auth: str
    ) -> dict | None:
        """Register a browser push subscription with the cloud service."""
        if not self.base_url:
            return None

        try:
            client = await self._get_client()
            response = await client.post(
                "/subscribe",
                json={
                    "endpoint": endpoint,
                    "p256dh": p256dh,
                    "auth": auth,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
