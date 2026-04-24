"""
events/bus.py — EventBus pub/sub interne Python
"""
import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    """Bus d'événements asynchrone pub/sub."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, handler: Callable):
        """Abonner un handler à un événement."""
        self._handlers.setdefault(event_name, []).append(handler)
        logger.info(f"[EventBus] Handler abonné: {event_name} → {handler.__name__}")

    async def publish(self, event_name: str, payload: dict, tenant_id: str = None):
        """Publier un événement — exécute tous les handlers abonnés."""
        handlers = self._handlers.get(event_name, [])
        if not handlers:
            logger.debug(f"[EventBus] Aucun handler pour: {event_name}")
            return

        logger.info(f"[EventBus] Publish: {event_name} ({len(handlers)} handlers)")
        full_payload = {"event": event_name, "tenant_id": tenant_id, **payload}

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(full_payload)
                else:
                    handler(full_payload)
            except Exception as e:
                logger.error(f"[EventBus] Erreur handler {handler.__name__}: {e}")
                from backend.modules.error_tracker.service import log_error
                await log_error(
                    module="event_bus",
                    message=f"Handler {handler.__name__} failed for {event_name}: {e}",
                    level="ERROR",
                    tenant_id=tenant_id
                )


# Singleton global
event_bus = EventBus()
