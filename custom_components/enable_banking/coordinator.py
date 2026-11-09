from datetime import timedelta, datetime
from decimal import Decimal
import logging
from aiohttp import ClientError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .api import Client, ApiError
from .counting import count

class BankingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, logging.getLogger(__name__), name=entry.title,
                         config_entry=entry, update_interval=timedelta(hours=8))
        self.entry = entry
        self.client = Client(hass, async_get_clientsession(hass), entry.data["app_id"], entry.data["key_path"])

    async def _async_update_data(self):
        expiry = datetime.fromisoformat(self.entry.data["valid_until"].replace("Z", "+00:00"))
        if dt_util.utcnow() >= expiry:
            raise ConfigEntryAuthFailed("Zgoda bankowa wygasla")
        today = dt_util.now().date()
        start = today.replace(day=1)
        totals = dict(card=0, blik=0, unknown=0, excluded=0)
        amounts = {}
        unknown_details = []
        try:
            for uid in self.entry.data["accounts"]:
                rows = await self.client.transactions(uid, start.isoformat(), today.isoformat())
                currency = self.entry.data.get("account_currencies", {}).get(uid)
                counts = count(rows, start, today, default_currency=currency)
                for key in totals:
                    totals[key] += counts[key]
                for currency, amount in counts["amounts"].items():
                    amounts[currency] = amounts.get(currency, Decimal("0")) + amount
                unknown_details.extend(counts["unknown_details"])
        except ApiError as err:
            if err.status in (401, 403, 404):
                raise ConfigEntryAuthFailed("Odnów autoryzację lub sprawdź klucz aplikacji") from err
            raise UpdateFailed(str(err)) from err
        except (ClientError, TimeoutError, OSError, ValueError, KeyError) as err:
            raise UpdateFailed("Nie udalo sie pobrac kompletnej historii") from err
        return {**totals, "amounts": amounts, "unknown_details": unknown_details, "month": start.strftime("%Y-%m"), "valid_until": self.entry.data["valid_until"]}
