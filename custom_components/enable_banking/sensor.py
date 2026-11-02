from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

LABELS = {"card": "Płatności kartą", "blik": "Płatności BLIK", "total": "Płatności razem",
          "unknown": "Nierozpoznane obciążenia"}

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(Counter(entry.runtime_data, entry, key, label) for key, label in LABELS.items())

class Counter(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:credit-card-outline"
    _attr_native_unit_of_measurement = "transakcji"

    def __init__(self, coordinator, entry, key, label):
        super().__init__(coordinator)
        self.key = key
        self._attr_name = label
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {"identifiers": {("enable_banking", entry.entry_id)},
                                  "name": entry.title, "manufacturer": "Enable Banking"}

    @property
    def available(self):
        return super().available and self.coordinator.data["month"] == dt_util.now().strftime("%Y-%m")

    @property
    def native_value(self):
        return self.coordinator.data[self.key]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {"month": data["month"], "consent_valid_until": data["valid_until"],
                "classification": "description_heuristic", "unknown_debits": data["unknown"]}
