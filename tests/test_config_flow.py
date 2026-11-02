"""Exercise forms with real Home Assistant (optional runtime test dependency)."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
HAS_HA = importlib.util.find_spec("homeassistant") is not None
if HAS_HA:
    import jwt
    from homeassistant.helpers.data_entry_flow import _BaseFlowManagerView
    from custom_components.enable_banking.config_flow import BankingFlow
    from custom_components.enable_banking.api import ApiError, InvalidKey

@unittest.skipUnless(HAS_HA, "Install Home Assistant to run config flow tests")
class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    def flow(self):
        flow = BankingFlow()
        flow.hass = SimpleNamespace(data={}, http=SimpleNamespace(register_view=Mock()))
        return flow

    def serialize(self, result):
        return _BaseFlowManagerView(None)._prepare_result_json(result)

    async def test_initial_form_serializes_for_frontend(self):
        flow = self.flow()
        result = self.serialize(await flow.async_step_user())
        self.assertEqual(result["step_id"], "user")
        self.assertEqual([field["name"] for field in result["data_schema"]],
                         ["app_id", "key_path", "base_url"])
        flow.hass.http.register_view.assert_called_once()
        await flow.async_step_user()
        flow.hass.http.register_view.assert_called_once()

    async def test_documented_bank_response_without_services(self):
        flow = self.flow()
        bank = {"name": "Bank Millennium", "country": "PL",
                "maximum_consent_validity": 15552000, "auth_methods": []}
        request = AsyncMock(return_value={"aspsps": [bank]})
        with patch("custom_components.enable_banking.config_flow.async_get_clientsession"), \
             patch("custom_components.enable_banking.config_flow.Client") as client:
            client.return_value.request = request
            result = await flow.async_step_user({"app_id": "test-id",
                "key_path": "/config/key.pem", "base_url": "https://ha.example"})
        self.assertEqual(result["step_id"], "bank")
        self.assertEqual(flow.banks, {"Bank Millennium": bank})
        request.assert_awaited_once_with("GET", "/aspsps", params={
            "country": "PL", "service": "AIS", "psu_type": "personal"})
        self.serialize(result)

    async def test_empty_bank_response_shows_no_banks(self):
        flow = self.flow()
        with patch("custom_components.enable_banking.config_flow.async_get_clientsession"), \
             patch("custom_components.enable_banking.config_flow.Client") as client:
            client.return_value.request = AsyncMock(return_value={"aspsps": []})
            result = await flow.async_step_user({"app_id": "test-id",
                "key_path": "/config/key.pem", "base_url": "https://ha.example"})
        self.assertEqual(result["errors"], {"base": "no_banks"})

    async def test_authorization_url_is_visible_in_form_field(self):
        flow = self.flow()
        flow.settings = {"base_url": "https://ha.example"}
        flow.banks = {"Bank Millennium": {"maximum_consent_validity": 86400}}
        url = "https://auth.example/authorize/test"
        flow.client = SimpleNamespace(request=AsyncMock(return_value={"url": url}))
        result = await flow.async_step_bank({"bank": "Bank Millennium"})
        self.assertEqual(result["step_id"], "authorize")
        data = self.serialize(result)
        fields = {field["name"]: field for field in data["data_schema"]}
        self.assertEqual(fields["authorization_url"]["default"], url)
        self.assertIn("callback_url", fields)
        self.assertEqual(result["description_placeholders"]["auth_url"], url)

    async def test_authorization_reports_rejected_redirect(self):
        flow = self.flow()
        flow.settings = {"base_url": "https://ha.example"}
        flow.banks = {"Bank Millennium": {"maximum_consent_validity": 86400}}
        flow.client = SimpleNamespace(request=AsyncMock(side_effect=ApiError(400, "REDIRECT_URI_NOT_ALLOWED")))
        result = await flow.async_step_bank({"bank": "Bank Millennium"})
        self.assertEqual(result["errors"], {"base": "redirect_not_allowed"})
        self.assertEqual(result["description_placeholders"]["error_detail"], "HTTP 400, REDIRECT_URI_NOT_ALLOWED")
        self.serialize(result)

    def test_connection_failures_are_distinct_and_safe(self):
        from aiohttp import ClientConnectionError
        flow = self.flow()
        cases = [(ApiError(401), "invalid_auth"), (ApiError(403), "access_denied"),
                 (ApiError(429), "rate_limited"), (ApiError(500), "api_error"),
                 (InvalidKey("secret"), "invalid_key_format"),
                 (TimeoutError("secret"), "request_timeout"),
                 (ClientConnectionError("secret"), "network_error"),
                 (OSError("secret"), "invalid_key"), (ValueError("secret"), "unexpected_response")]
        for error, expected in cases:
            with self.subTest(expected=expected), self.assertLogs("custom_components.enable_banking.config_flow") as logs:
                self.assertEqual(flow._connection_error(error, "test"), expected)
            self.assertNotIn("secret", str(logs.output))

    def test_api_error_drops_unrecognized_body_codes(self):
        self.assertEqual(ApiError(400, "token-secret").code, "UNKNOWN")
        self.assertNotIn("token-secret", str(ApiError(400, "token-secret")))

    async def test_bank_selector_serializes(self):
        flow = self.flow()
        flow.banks = {"Bank Millennium": {}}
        self.assertEqual(self.serialize(await flow.async_step_bank())["step_id"], "bank")

    async def test_accounts_selector_serializes(self):
        flow = self.flow()
        flow.session_data = {"accounts": [{"uid": "example", "currency": "PLN"}]}
        self.assertEqual(self.serialize(await flow.async_step_accounts())["step_id"], "accounts")

    async def test_invalid_state_is_rejected_without_api_request(self):
        flow = self.flow()
        flow.redirect = "https://ha.example/api/enable_banking/callback"
        flow.auth_url = "https://auth.example"
        flow.state = "expected"
        result = await flow.async_step_authorize({"callback_url": flow.redirect + "?code=x&state=wrong"})
        self.assertEqual(result["errors"], {"base": "invalid_callback"})
        self.serialize(result)

    def test_core_jwt_is_available(self):
        self.assertTrue(callable(jwt.encode))
        self.assertTrue(issubclass(jwt.PyJWTError, Exception))

if __name__ == "__main__":
    unittest.main()
