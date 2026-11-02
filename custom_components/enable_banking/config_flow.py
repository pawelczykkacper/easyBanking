from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import logging
from urllib.parse import urlsplit, parse_qs
try:
    import probatio as vol
except ImportError:  # Home Assistant versions that still use voluptuous
    import voluptuous as vol
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from . import register_view
from .api import Client, ApiError, InvalidKey
from .const import DOMAIN, CALLBACK

_LOGGER = logging.getLogger(__name__)

class BankingFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.settings = {}
        self.banks = {}
        self.session_data = {}
        self.target_entry = None
        self.error_detail = ""

    def _connection_error(self, err, stage):
        if isinstance(err, ApiError):
            self.error_detail = f"HTTP {err.status}, {err.code}"
            _LOGGER.warning("Enable Banking %s failed: HTTP %s (%s)", stage, err.status, err.code)
            if err.code == "REDIRECT_URI_NOT_ALLOWED":
                return "redirect_not_allowed"
            if err.status == 401:
                return "invalid_auth"
            if err.status == 403:
                return "access_denied"
            if err.status == 429:
                return "rate_limited"
            return "api_error"
        # Never log exception text, key paths, request URLs, tokens or bodies.
        _LOGGER.warning("Enable Banking %s failed: %s", stage, type(err).__name__)
        if isinstance(err, InvalidKey):
            return "invalid_key_format"
        if isinstance(err, TimeoutError):
            return "request_timeout"
        if isinstance(err, ClientError):
            return "network_error"
        if isinstance(err, OSError):
            return "invalid_key"
        return "unexpected_response"

    async def async_step_reauth(self, entry_data):
        self.target_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self.settings = {key: entry_data[key] for key in ("app_id", "key_path", "base_url")}
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}
        register_view(self.hass)
        if user_input is not None:
            self.settings = user_input
            base = urlsplit(user_input["base_url"])
            if base.scheme != "https" or not base.hostname or base.username or base.password or base.path not in ("", "/") or base.query or base.fragment:
                errors["base"] = "invalid_url"
            elif not Path(user_input["key_path"]).is_absolute():
                errors["base"] = "invalid_key"
            else:
                self.settings["base_url"] = user_input["base_url"].rstrip("/")
                self.client = Client(self.hass, async_get_clientsession(self.hass), user_input["app_id"].strip(), user_input["key_path"])
                try:
                    response = await self.client.request("GET", "/aspsps", params={"country": "PL", "service": "AIS", "psu_type": "personal"})
                    # ASPSPData has no services field; filter AIS on the API request.
                    self.banks = {b["name"]: b for b in response["aspsps"]}
                    if not self.banks:
                        errors["base"] = "no_banks"
                    else:
                        return await self.async_step_bank()
                except (ApiError, ClientError, TimeoutError, OSError, ValueError, KeyError, TypeError) as err:
                    errors["base"] = self._connection_error(err, "list_banks")
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("app_id", default=self.settings.get("app_id", "")): str,
            vol.Required("key_path", default=self.settings.get("key_path", "/config/enable_banking.pem")): str,
            vol.Required("base_url", default=self.settings.get("base_url", "https://ha.twoja-domena.pl")): str,
        }), errors=errors, description_placeholders={"error_detail": self.error_detail})

    async def async_step_bank(self, user_input=None):
        errors = {}
        if user_input is not None:
            name = user_input["bank"]
            if self.target_entry and name != self.target_entry.data["bank"]:
                errors["base"] = "wrong_bank"
            else:
                self.bank = name
                self.state = secrets.token_urlsafe(32)
                self.redirect = self.settings["base_url"] + CALLBACK
                maximum = int(self.banks[name].get("maximum_consent_validity", 86400))
                self.valid_until = (datetime.now(timezone.utc) + timedelta(seconds=min(maximum, 180*86400)-60)).isoformat()
                try:
                    data = await self.client.request("POST", "/auth", json={
                        "access": {"valid_until": self.valid_until},
                        "aspsp": {"name": name, "country": "PL"},
                        "state": self.state, "redirect_url": self.redirect, "psu_type": "personal"})
                    self.auth_url = data["url"]
                    return await self.async_step_authorize()
                except (ApiError, ClientError, TimeoutError, ValueError, KeyError, OSError, TypeError) as err:
                    errors["base"] = self._connection_error(err, "start_authorization")
        return self.async_show_form(step_id="bank", data_schema=vol.Schema({
            vol.Required("bank"): selector.SelectSelector(selector.SelectSelectorConfig(options=sorted(self.banks), mode=selector.SelectSelectorMode.DROPDOWN))
        }), errors=errors, description_placeholders={"error_detail": self.error_detail})

    async def async_step_authorize(self, user_input=None):
        errors = {}
        if user_input is not None:
            value = user_input["callback_url"]
            try:
                parts, expected = urlsplit(value), urlsplit(self.redirect)
                params = parse_qs(parts.query)
                if (parts.scheme, parts.netloc, parts.path) != (expected.scheme, expected.netloc, expected.path):
                    raise ValueError("Invalid callback")
                if not secrets.compare_digest(params.get("state", [""])[0], self.state):
                    raise ValueError("Invalid state")
                code = params["code"][0]
            except (ValueError, KeyError, IndexError):
                errors["base"] = "invalid_callback"
            else:
                try:
                    self.session_data = await self.client.request("POST", "/sessions", json={"code": code})
                    if not self.session_data.get("accounts"):
                        return self.async_abort(reason="no_accounts")
                    return await self.async_step_accounts()
                except (ApiError, ClientError, TimeoutError, ValueError, KeyError, OSError):
                    return self.async_abort(reason="authorization_failed")
        return self.async_show_form(step_id="authorize", data_schema=vol.Schema({
            vol.Optional("authorization_url", default=self.auth_url): str,
            vol.Required("callback_url"): str,
        }), description_placeholders={"auth_url": self.auth_url}, errors=errors)

    async def async_step_accounts(self, user_input=None):
        options = []
        for number, account in enumerate(self.session_data["accounts"], 1):
            account_id = account.get("account_id") or {}
            iban = account_id.get("iban", "")
            label = f"Rachunek {number} · {account.get('currency', '')} · …{iban[-4:]}"
            options.append({"value": account["uid"], "label": label})
        errors = {}
        if user_input is not None:
            allowed = {option["value"] for option in options}
            selected = user_input["accounts"]
            if not selected or not set(selected) <= allowed:
                errors["base"] = "select_accounts"
            else:
                # Do not persist account numbers, balances, descriptions or authorization URLs.
                data = {**self.settings, "bank": self.bank, "accounts": selected,
                        "session_id": self.session_data["session_id"], "valid_until": (self.session_data.get("access") or {}).get("valid_until", self.valid_until)}
                if self.target_entry:
                    return self.async_update_reload_and_abort(self.target_entry, data_updates=data)
                await self.async_set_unique_id(f"{self.settings['app_id']}:{self.bank}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=self.bank, data=data)
        return self.async_show_form(step_id="accounts", data_schema=vol.Schema({
            vol.Required("accounts"): selector.SelectSelector(selector.SelectSelectorConfig(options=options, multiple=True))
        }), errors=errors, description_placeholders={"error_detail": self.error_detail})
