"""Prüft Daten auf Warnungen, meldet nur neue und schickt sie auf Wunsch als Push."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .alert_store import load_alert_state, save_alert_state
from .alerts import Alert, AlertSettings, carried_over, charging_status, evaluate, new_alerts
from .ntfy import NtfyError, mask_vin

Push = Callable[[str, list[str]], None]


class AlertWatcher:
    def __init__(self, settings: AlertSettings, state_file: Path, push: Push | None,
                 report: Callable[[str], None]) -> None:
        self.settings, self.state_file, self.push, self.report = settings, state_file, push, report
        self.snapshots: dict[str, dict[str, dict[str, Any]]] = {}

    def check(self, vin: str, data: dict[str, dict[str, Any]], merge: bool = False) -> list[Alert]:
        """merge: Live-Nachrichten enthalten nur Änderungen; sie ergänzen den letzten Stand."""
        snapshot = {**self.snapshots.get(vin, {}), **data} if merge else data
        if merge:
            self.snapshots = {**self.snapshots, vin: snapshot}
        current = evaluate(snapshot, self.settings)
        status = charging_status(snapshot)
        previous = load_alert_state(self.state_file, vin)
        fresh = new_alerts(current, previous, status)
        delivered = self._announce(vin, fresh)
        # Nicht zugestellte Warnungen gelten als noch nicht gemeldet: beim nächsten Mal erneut.
        undelivered = set() if delivered else {a.key for a in fresh}
        active = [a for a in current if a.key not in undelivered]
        kept = carried_over([k for k in previous.get("aktiv") or [] if k not in {a.key for a in current}], snapshot)
        status_to_keep = previous.get("ladestatus") if "laden_beendet" in undelivered else status
        save_alert_state(self.state_file, vin, (*active, *(Alert(k, "") for k in kept)), status_to_keep)
        return fresh

    def _announce(self, vin: str, fresh: list[Alert]) -> bool:
        """Meldet neue Warnungen; False, wenn der Push nicht zugestellt wurde."""
        for alert in fresh:
            self.report(f"Warnung: {alert.text}")
        if not fresh or self.push is None:
            return True
        title = f"BMW {mask_vin(vin)}: {len(fresh)} Warnung{'en' if len(fresh) > 1 else ''}"
        try:
            self.push(title, [alert.text for alert in fresh])
        except NtfyError as error:
            self.report(f"Hinweis: {error} Erneuter Versuch beim nächsten Mal.")
            return False
        return True
