"""Exercise forms with real Home Assistant (optional runtime test dependency)."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
HAS_HA = importlib.util.find_spec("homeassistant") is not None
if HAS_HA:
    import jwt
    from homeassistant.helpers.data_entry_flow import _BaseFlowManagerView
    from custom_components.enable_banking.config_flow import BankingFlow

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
