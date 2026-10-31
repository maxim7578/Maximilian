"""Welche Datenpunkte der Status-Befehl abfragt und wie sie heißen."""

from __future__ import annotations

from dataclasses import dataclass

CONTAINER_NAME = "bmw-cardata-cli Status"
CONTAINER_PURPOSE = "Fahrzeugstatus fuer den Kommandozeilen-Client"


@dataclass(frozen=True)
class Field:
    label: str
    descriptors: tuple[str, ...]  # der erste vorhandene Wert wird angezeigt


STATUS_FIELDS: tuple[Field, ...] = (
    Field("Kilometerstand", ("vehicle.vehicle.travelledDistance",)),
    Field(
        "Ladestand Hochvoltbatterie",
        (
            "vehicle.drivetrain.batteryManagement.header",
            "vehicle.powertrain.electric.battery.stateOfCharge.displayed",
        ),
    ),
    Field("Ladeziel", ("vehicle.powertrain.electric.battery.stateOfCharge.target",)),
    Field("Elektrische Reichweite", ("vehicle.drivetrain.electricEngine.remainingElectricRange",)),
    Field("Ladestatus", ("vehicle.drivetrain.electricEngine.charging.status",)),
    Field("Restladezeit", ("vehicle.drivetrain.electricEngine.charging.timeRemaining",)),
    Field(
        "Ladekabel eingesteckt",
        ("vehicle.powertrain.tractionBattery.charging.port.anyPosition.isPlugged",),
    ),
    Field("Tankfüllstand", ("vehicle.drivetrain.fuelSystem.level",)),
    Field("Restkraftstoff", ("vehicle.drivetrain.fuelSystem.remainingFuel",)),
    Field("Türschloss", ("vehicle.cabin.door.lock.status",)),
    Field("12-V-Batterie", ("vehicle.electricalSystem.battery.stateOfCharge",)),
    Field("Nächster Service in", ("vehicle.status.serviceDistance.next",)),
    Field("Breitengrad", ("vehicle.cabin.infotainment.navigation.currentLocation.latitude",)),
    Field("Längengrad", ("vehicle.cabin.infotainment.navigation.currentLocation.longitude",)),
)


def all_descriptors() -> tuple[str, ...]:
    return tuple(d for field in STATUS_FIELDS for d in field.descriptors)
