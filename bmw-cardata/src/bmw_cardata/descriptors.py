"""Welche Datenpunkte der Status-Befehl abfragt, wie sie heißen und wie sie gruppiert sind.

Die Namen der Datenpunkte stammen aus BMWs CarData-Katalog (abgeglichen mit der
Titeltabelle der Home-Assistant-Integration kvanbiesen/bmw-cardata-ha). Welche davon
ein Auto wirklich liefert, hängt von Modell und Ausstattung ab; fehlende bleiben leer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

CONTAINER_NAME = "bmw-cardata-cli Status"
CONTAINER_PURPOSE = "Fahrzeugstatus fuer den Kommandozeilen-Client"
# Wartungsdaten (vehicle.status.*) liegen in einem eigenen Container, der höchstens einmal
# am Tag gelesen wird: Am 20.10.2026 ließen sie laut Home-Assistant-Integration jeden
# Abruf ihres Containers mit CU-400 scheitern. So kostet ein solcher Fehler nur sie.
SERVICE_CONTAINER_NAME = "bmw-cardata-cli Wartung"
SERVICE_CONTAINER_PURPOSE = "Wartungstermine fuer den Kommandozeilen-Client"
SERVICE_DESCRIPTORS = ("vehicle.status.serviceDistance.next", "vehicle.status.serviceTime.inspectionDateLegal")

LATITUDE = "vehicle.cabin.infotainment.navigation.currentLocation.latitude"
LONGITUDE = "vehicle.cabin.infotainment.navigation.currentLocation.longitude"


@dataclass(frozen=True)
class Field:
    label: str
    descriptors: tuple[str, ...]  # der erste vorhandene Wert wird angezeigt
    raw_unit: str = ""  # Einheit der Rohwerte, wo sie feststeht (für den CSV-Kopf)


@dataclass(frozen=True)
class Group:
    title: str
    fields: tuple[Field, ...]
    map_link: bool = False  # nach den Feldern einen Kartenlink zeigen


def _f(label: str, *descriptors: str) -> Field:
    return Field(label, descriptors)


def _tire(position: str, axle: str, side: str, target: bool = False) -> Field:
    label, suffix = ("Solldruck", "pressureTarget") if target else ("Reifendruck", "pressure")
    return Field(f"{label} {position}", (f"vehicle.chassis.axle.{axle}.wheel.{side}.tire.{suffix}",), "kPa")


TIRES = (("vorne links", "row1", "left"), ("vorne rechts", "row1", "right"),
         ("hinten links", "row2", "left"), ("hinten rechts", "row2", "right"))


STATUS_GROUPS: tuple[Group, ...] = (
    Group("Fahren und Reichweite", (
        _f("Kilometerstand", "vehicle.vehicle.travelledDistance"),
        _f("Gesamtreichweite", "vehicle.drivetrain.lastRemainingRange"),
        _f(
            "Elektrische Reichweite",
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            "vehicle.drivetrain.electricEngine.remainingElectricRange",
        ),
        _f("Kraftstoffreichweite", "vehicle.drivetrain.fuelSystem.remainingFuelRange"),
        _f("Tankfüllstand", "vehicle.drivetrain.fuelSystem.level"),
        _f("Restkraftstoff", "vehicle.drivetrain.fuelSystem.remainingFuel"),
        _f("In Bewegung", "vehicle.isMoving"),
    )),
    Group("Laden", (
        _f(
            "Ladestand Hochvoltbatterie",
            "vehicle.drivetrain.batteryManagement.header",
            "vehicle.powertrain.electric.battery.stateOfCharge.displayed",
        ),
        _f("Ladeziel", "vehicle.powertrain.electric.battery.stateOfCharge.target"),
        _f("Ladestatus", "vehicle.drivetrain.electricEngine.charging.status"),
        _f("Restladezeit", "vehicle.drivetrain.electricEngine.charging.timeRemaining"),
        _f("Ladeleistung", "vehicle.powertrain.electric.battery.charging.power"),
        _f("Ladekabel eingesteckt", "vehicle.powertrain.tractionBattery.charging.port.anyPosition.isPlugged"),
        _f("Ladeklappe offen", "vehicle.powertrain.tractionBattery.charging.port.anyPosition.flap.isOpen"),
        _f("Batteriegesundheit", "vehicle.powertrain.electric.battery.stateOfHealth.displayed"),
    )),
    Group("Türen, Fenster und Klappen", (
        _f("Türschloss", "vehicle.cabin.door.lock.status"),
        _f("Türen", "vehicle.cabin.door.status"),
        _f("Fahrertür offen", "vehicle.cabin.door.row1.driver.isOpen"),
        _f("Beifahrertür offen", "vehicle.cabin.door.row1.passenger.isOpen"),
        _f("Tür hinten Fahrerseite offen", "vehicle.cabin.door.row2.driver.isOpen"),
        _f("Tür hinten Beifahrerseite offen", "vehicle.cabin.door.row2.passenger.isOpen"),
        _f("Fenster Fahrer", "vehicle.cabin.window.row1.driver.status"),
        _f("Fenster Beifahrer", "vehicle.cabin.window.row1.passenger.status"),
        _f("Fenster hinten Fahrerseite", "vehicle.cabin.window.row2.driver.status"),
        _f("Fenster hinten Beifahrerseite", "vehicle.cabin.window.row2.passenger.status"),
        _f("Heckklappe offen", "vehicle.body.trunk.isOpen"),
        _f("Heckklappe verriegelt", "vehicle.body.trunk.isLocked"),
        _f("Motorhaube offen", "vehicle.body.hood.isOpen"),
        _f("Schiebedach", "vehicle.cabin.sunroof.status"),
        _f("Licht an", "vehicle.body.lights.isRunningOn"),
        _f("Alarmanlage", "vehicle.vehicle.antiTheftAlarmSystem.alarm.armStatus"),
    )),
    Group("Reifen", (
        *(_tire(*tire, target=target) for tire in TIRES for target in (False, True)),
        _f("Reifendiagnose", "vehicle.chassis.axle.wheel.tire.diagnosis"),
    )),
    Group("Wartung und Bordnetz", (
        _f("12-V-Batterie", "vehicle.electricalSystem.battery.stateOfCharge"),
        _f("12-V-Spannung", "vehicle.electricalSystem.battery.voltage"),
        _f("Nächster Service in", SERVICE_DESCRIPTORS[0]),
        _f("Nächste Hauptuntersuchung", SERVICE_DESCRIPTORS[1]),
    )),
    Group("Position", (
        _f("Breitengrad", LATITUDE),
        _f("Längengrad", LONGITUDE),
    ), map_link=True),
)

STATUS_FIELDS: tuple[Field, ...] = tuple(field for group in STATUS_GROUPS for field in group.fields)


def all_descriptors() -> tuple[str, ...]:
    return tuple(d for field in STATUS_FIELDS for d in field.descriptors)


def polled_descriptors() -> tuple[str, ...]:
    """Die Datenpunkte des Status-Containers: alle außer den Wartungsdaten."""
    return tuple(d for d in all_descriptors() if d not in SERVICE_DESCRIPTORS)


def descriptor_signature(descriptors: tuple[str, ...] | None = None) -> str:
    """Kurzer Fingerabdruck der Datenpunkte; ändert er sich, braucht es einen neuen Container."""
    chosen = polled_descriptors() if descriptors is None else descriptors
    return hashlib.sha256("\n".join(sorted(chosen)).encode("utf-8")).hexdigest()[:16]
