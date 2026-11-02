from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

LABELS = {"card": "Płatności kartą", "blik": "Płatności BLIK",
          "unknown": "Nierozpoznane obciążenia"}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = [Counter(coordinator, entry, key, label) for key, label in LABELS.items()]
    entities.append(UnknownDetailsSensor(coordinator, entry))
    currencies = set(entry.data.get("account_currencies", {}).values())
    currencies.update(coordinator.data.get("amounts", {}))
    entities.extend(AmountSensor(coordinator, entry, currency) for currency in sorted(currencies))
    async_add_entities(entities)
    added_currencies = set(currencies)

    def add_new_currency_sensors():
        new_currencies = set(coordinator.data.get("amounts", {})) - added_currencies
        if new_currencies:
            added_currencies.update(new_currencies)
            async_add_entities(AmountSensor(coordinator, entry, currency)
                               for currency in sorted(new_currencies))

    coordinator.async_add_listener(add_new_currency_sensors)

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

class AmountSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator, entry, currency):
        super().__init__(coordinator)
        self.currency = currency
        self._attr_name = f"Suma płatności ({currency})"
        self._attr_native_unit_of_measurement = currency
        self._attr_unique_id = f"{entry.entry_id}_amount_{currency.lower()}"
        self._attr_device_info = {"identifiers": {("enable_banking", entry.entry_id)},
                                  "name": entry.title, "manufacturer": "Enable Banking"}

    @property
    def available(self):
        return super().available and self.coordinator.data["month"] == dt_util.now().strftime("%Y-%m")

    @property
    def native_value(self):
        return self.coordinator.data["amounts"].get(self.currency, 0)

    @property
    def extra_state_attributes(self):
        return {"month": self.coordinator.data["month"],
                "consent_valid_until": self.coordinator.data["valid_until"],
                "includes": "zaksięgowane płatności kartą i BLIK"}


class UnknownDetailsSensor(CoordinatorEntity, SensorEntity):
    """Text summary plus detailed attributes for unclassified debits."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:text-box-search-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Szczegóły nierozpoznanych obciążeń"
        self._attr_unique_id = f"{entry.entry_id}_unknown_details"
        self._attr_device_info = {"identifiers": {("enable_banking", entry.entry_id)},
                                  "name": entry.title, "manufacturer": "Enable Banking"}

    @property
    def available(self):
        return super().available and self.coordinator.data["month"] == dt_util.now().strftime("%Y-%m")

    @property
    def native_value(self):
        details = self.coordinator.data.get("unknown_details", [])
        if not details:
            return "Brak nierozpoznanych obciążeń"
        snippets = [f"{item['date']} {item['description']}" for item in details[:3]]
        summary = f"{len(details)} operacji: " + " | ".join(snippets)
        return summary[:250]

    @property
    def extra_state_attributes(self):
        details = self.coordinator.data.get("unknown_details", [])
        return {
            "month": self.coordinator.data["month"],
            "count": len(details),
            "transactions": details[:100],
            "truncated": len(details) > 100,
        }
