"""Enable Banking payment counters."""
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import Platform
from .const import DOMAIN, CALLBACK

class CallbackView(HomeAssistantView):
    url = CALLBACK
    name = "api:enable_banking:callback"
    requires_auth = False

    async def get(self, request):
        return web.Response(text="Skopiuj caly adres tej strony z paska przegladarki. Wroc do formularza integracji Enable Banking w Home Assistant i wklej adres. Nie udostepniaj go innym.",
                            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

def register_view(hass):
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("view"):
        hass.http.register_view(CallbackView())
        data["view"] = True

async def async_setup(hass, config):
    register_view(hass)
    return True

async def async_setup_entry(hass, entry):
    from .coordinator import BankingCoordinator
    register_view(hass)
    coordinator = BankingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True

async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
