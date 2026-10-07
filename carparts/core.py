from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .i18n import t

MAX_CARS = 5
SORT_MODES = ("life", "name", "date")
LEVELS = ("expired", "crit", "warn", "ok", "off")


def _app_dir(xdg_var: str, linux_default: str) -> Path:
    """Папка приложения по правилам ОС; явно заданная XDG-переменная главнее везде."""
    if xdg := os.environ.get(xdg_var):
        return Path(xdg) / "carparts"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        return (Path(appdata) if appdata else Path.home() / "AppData" / "Roaming") / "carparts"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "carparts"
    return Path.home() / linux_default / "carparts"


def data_path() -> Path:
    return _app_dir("XDG_DATA_HOME", ".local/share") / "data.json"


def config_path() -> Path:
    return _app_dir("XDG_CONFIG_HOME", ".config") / "config.json"


def load_config() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class Part:
    name: str
    installed_km: int
    installed_on: str
    interval_km: int | None = None
    interval_days: int | None = None
    warn_pct: float = 40
    crit_pct: float = 15

    def remaining_km(self, odo: int) -> int | None:
        if not self.interval_km:
            return None
        return self.interval_km - (odo - self.installed_km)

    def remaining_days(self, today: date | None = None) -> int | None:
        if not self.interval_days:
            return None
        today = today or date.today()
        return self.interval_days - (today - date.fromisoformat(self.installed_on)).days

    def percent(self, odo: int, today: date | None = None) -> float | None:
        ratios = []
        km = self.remaining_km(odo)
        if km is not None:
            ratios.append(km / self.interval_km)
        days = self.remaining_days(today)
        if days is not None:
            ratios.append(days / self.interval_days)
        return min(ratios) * 100 if ratios else None

    def level(self, odo: int, today: date | None = None) -> str:
        p = self.percent(odo, today)
        if p is None:
            return "off"
        if p <= 0:
            return "expired"
        if p <= self.crit_pct:
            return "crit"
        if p <= self.warn_pct:
            return "warn"
        return "ok"

    def days_left(self, odo: int, km_per_day: float | None,
                  today: date | None = None) -> float | None:
        """Прогноз дней до замены: по календарю и по среднему пробегу в день."""
        options = []
        days = self.remaining_days(today)
        if days is not None:
            options.append(days)
        km = self.remaining_km(odo)
        if km is not None and km_per_day:
            options.append(km / km_per_day)
        return min(options) if options else None


@dataclass
class HistoryEntry:
    date: str
    km: int
    replaced: list[str] = field(default_factory=list)


@dataclass
class Car:
    brand: str
    model: str
    year: int
    engine_l: float
    odometer: int = 0
    parts: list[Part] = field(default_factory=list)
    history: list[HistoryEntry] = field(default_factory=list)

    @property
    def title(self) -> str:
        return f"{self.brand} {self.model} {self.year} {self.engine_l:.1f}L"

    def log_mileage(self, km: int, replaced: list[str] | None = None) -> None:
        if km < self.odometer:
            raise ValueError(t("err.less", km=self.odometer))
        self.odometer = km
        self.history.append(HistoryEntry(date.today().isoformat(), km, replaced or []))

    def replace_part(self, name: str, interval_km=None, interval_days=None,
                     warn=40, crit=15, km: int | None = None) -> None:
        km = self.odometer if km is None else km
        if km < self.odometer:
            raise ValueError(t("err.less", km=self.odometer))
        self.parts = [p for p in self.parts if p.name != name]
        self.parts.append(Part(name, km, date.today().isoformat(),
                               interval_km, interval_days, warn, crit))
        self.log_mileage(km, [name])

    def correct_odometer(self, km: int) -> None:
        """Исправление ошибочного пробега: одометр можно опустить, ошибочные
        записи «просто пробег» выше нового значения удаляются из истории."""
        if km < 0:
            raise ValueError(t("err.negative"))
        self.odometer = km
        self.history = [h for h in self.history if h.replaced or h.km <= km]

    def remove_part(self, name: str) -> None:
        self.parts = [p for p in self.parts if p.name != name]

    def part(self, name: str) -> Part | None:
        return next((p for p in self.parts if p.name == name), None)

    def sorted_parts(self, today: date | None = None, by: str = "life") -> list[Part]:
        """life — по остатку ресурса (без критериев — в конце), name — по алфавиту,
        date — сначала последние замены."""
        if by == "name":
            return sorted(self.parts, key=lambda p: p.name.casefold())
        if by == "date":
            return sorted(self.parts, key=lambda p: (p.installed_on, p.installed_km),
                          reverse=True)

        def key(p: Part):
            pct = p.percent(self.odometer, today)
            return (pct is None, pct if pct is not None else 0, p.name)
        return sorted(self.parts, key=key)

    def expired(self, today: date | None = None) -> list[Part]:
        return [p for p in self.parts if p.level(self.odometer, today) == "expired"]

    def km_per_day(self) -> float | None:
        if len(self.history) < 2:
            return None
        first, last = self.history[0], self.history[-1]
        days = (date.fromisoformat(last.date) - date.fromisoformat(first.date)).days
        if days < 1 or last.km <= first.km:
            return None
        return (last.km - first.km) / days

    def clear_history(self) -> None:
        self.history = []

    def history_json(self) -> str:
        data = {
            "car": {k: getattr(self, k) for k in ("brand", "model", "year", "engine_l",
                                                   "odometer")},
            "history": [asdict(h) for h in self.history],
        }
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    def export_name(self, ext: str, today: date | None = None) -> str:
        slug = f"{self.brand}_{self.model}".replace(" ", "_").lower()
        return f"carparts_{slug}_{(today or date.today()).isoformat()}.{ext}"

    def history_md(self) -> str:
        rows = ["# " + self.title, "",
                f"| {t('md.date')} | {t('md.km')} | {t('md.replaced')} |", "|---|---|---|"]
        for h in reversed(self.history):
            rows.append(f"| {h.date} | {h.km} | {', '.join(h.replaced) or '—'} |")
        return "\n".join(rows) + "\n"


def load(path: Path | None = None) -> list[Car]:
    path = path or data_path()
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Car(**{**c,
                   "parts": [Part(**p) for p in c.get("parts", [])],
                   "history": [HistoryEntry(**h) for h in c.get("history", [])]})
            for c in raw]


def save(cars: list[Car], path: Path | None = None) -> None:
    path = path or data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps([asdict(c) for c in cars], ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(path)
