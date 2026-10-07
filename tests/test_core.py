from datetime import date, timedelta
from pathlib import Path

import pytest

from carparts.core import Car, Part, load, save

D0 = date(2026, 1, 1)


def part(**kw) -> Part:
    return Part("x", installed_km=100_000, installed_on=D0.isoformat(), **kw)


# --- по пробегу ---

def test_check_example_oil():
    oil = part(interval_km=8000)
    assert oil.percent(103_000, D0) == pytest.approx(62.5)
    assert oil.level(103_000, D0) == "ok"
    assert oil.percent(106_900, D0) == pytest.approx(13.75)
    assert oil.level(106_900, D0) == "crit"


def test_fresh_part_is_100():
    assert part(interval_km=8000).percent(100_000, D0) == 100


@pytest.mark.parametrize("odo, level", [
    (104_799, "ok"),       # 40.01%
    (104_800, "warn"),     # ровно 40% → warn
    (106_800, "crit"),     # ровно 15% → crit
    (108_000, "expired"),  # 0%
    (110_000, "expired"),  # ушли в минус
])
def test_km_thresholds(odo, level):
    assert part(interval_km=8000).level(odo, D0) == level


def test_negative_percent():
    assert part(interval_km=8000).percent(112_000, D0) == pytest.approx(-50)


# --- по времени ---

def test_days_only():
    p = part(interval_days=365)
    assert p.percent(999_999, D0) == 100  # пробег игнорируется
    assert p.level(100_000, D0 + timedelta(days=219)) == "warn"   # 146/365 = 40%
    assert p.level(100_000, D0 + timedelta(days=311)) == "crit"   # 54/365 < 15%
    assert p.level(100_000, D0 + timedelta(days=365)) == "expired"


# --- смешанные ---

def test_mixed_takes_minimum_time_wins():
    # антифриз: год прошёл, пробег маленький → менять
    p = part(interval_km=60_000, interval_days=365)
    today = D0 + timedelta(days=366)
    assert p.remaining_km(101_000) == 59_000
    assert p.level(101_000, today) == "expired"


def test_mixed_takes_minimum_km_wins():
    p = part(interval_km=10_000, interval_days=365)
    assert p.percent(109_000, D0 + timedelta(days=10)) == pytest.approx(10)


def test_custom_thresholds():
    p = part(interval_km=1000, warn_pct=60, crit_pct=30)
    assert p.level(100_450, D0) == "warn"  # 55%
    assert p.level(100_750, D0) == "crit"  # 25%


def test_no_criteria_off():
    p = part()
    assert p.percent(100_000, D0) is None
    assert p.level(100_000, D0) == "off"


# --- Car ---

def make_car() -> Car:
    return Car("Lada", "Vesta", 2020, 1.6, odometer=50_000)


def test_replace_part_resets_and_logs():
    car = make_car()
    car.replace_part("Масло", interval_km=8000)
    car.log_mileage(57_000)
    car.replace_part("Масло", interval_km=8000, km=57_500)
    assert len(car.parts) == 1
    assert car.parts[0].percent(car.odometer) == 100
    assert car.odometer == 57_500
    assert [h.replaced for h in car.history] == [["Масло"], [], ["Масло"]]


def test_mileage_cannot_go_back():
    car = make_car()
    with pytest.raises(ValueError):
        car.log_mileage(49_000)


def test_sorted_and_expired():
    car = make_car()
    car.parts = [
        Part("a", 50_000, D0.isoformat(), interval_km=1000),
        Part("b", 40_000, D0.isoformat(), interval_km=1000),
        Part("c", 50_000, D0.isoformat()),
        Part("d", 49_500, D0.isoformat(), interval_km=1000),
    ]
    assert [p.name for p in car.sorted_parts(D0)] == ["b", "d", "a", "c"]
    assert [p.name for p in car.expired(D0)] == ["b"]


def test_save_load_roundtrip(tmp_path):
    car = make_car()
    car.replace_part("Антифриз", interval_km=60_000, interval_days=730, warn=30, crit=10)
    f = tmp_path / "carparts" / "data.json"
    save([car], f)
    assert load(f) == [car]
    assert load(tmp_path / "missing.json") == []


def test_history_md():
    car = make_car()
    car.log_mileage(51_000)
    car.replace_part("Масло", interval_km=8000)
    md = car.history_md()
    assert md.startswith("# Lada Vesta 2020 1.6L")
    lines = md.splitlines()
    assert lines[4].endswith("| 51000 | Масло |")
    assert lines[5].endswith("| 51000 | — |")


def test_correct_odometer_drops_bogus_mileage_only():
    car = make_car()
    car.log_mileage(51_000)
    car.replace_part("Масло", interval_km=8000)
    car.log_mileage(510_000)                  # опечатка
    car.correct_odometer(52_000)
    assert car.odometer == 52_000
    assert [h.km for h in car.history] == [51_000, 51_000]
    assert car.part("Масло").level(car.odometer) == "ok"
    with pytest.raises(ValueError):
        car.correct_odometer(-1)


def test_remove_part():
    car = make_car()
    car.replace_part("Масло", interval_km=8000)
    car.remove_part("Масло")
    assert car.parts == [] and car.history[-1].replaced == ["Масло"]


def test_catalog_suggestions():
    from carparts import catalog
    assert len(catalog.PARTS["ru"]) == len(catalog.PARTS["en"])
    for names in catalog.PARTS.values():
        assert len(names) == len({n.casefold() for n in names})
    got = catalog.suggestions("ru", ["Масло ДВС", "антифриз"])
    assert got[:2] == ["Масло ДВС", "антифриз"]
    assert "Антифриз" not in got


def test_sorted_parts_modes():
    car = make_car()
    car.parts = [
        Part("в", 50_000, "2026-03-01", interval_km=1000),
        Part("А", 49_900, "2026-05-01", interval_km=1000),
        Part("б", 49_000, "2026-05-01", interval_km=1000),
    ]
    assert [p.name for p in car.sorted_parts(D0, by="life")] == ["б", "А", "в"]
    assert [p.name for p in car.sorted_parts(D0, by="name")] == ["А", "б", "в"]
    assert [p.name for p in car.sorted_parts(D0, by="date")] == ["А", "б", "в"]


@pytest.mark.parametrize("platform, env, expected", [
    ("linux", {}, "{home}/.local/share/carparts/data.json"),
    ("darwin", {}, "{home}/Library/Application Support/carparts/data.json"),
    ("win32", {"APPDATA": "{home}/AppData/Roaming"}, "{home}/AppData/Roaming/carparts/data.json"),
    ("win32", {"XDG_DATA_HOME": "{home}/x"}, "{home}/x/carparts/data.json"),
])
def test_data_path_per_platform(monkeypatch, tmp_path, platform, env, expected):
    from carparts import core
    monkeypatch.setattr(core.sys, "platform", platform)
    monkeypatch.setattr(core.Path, "home", lambda: tmp_path)
    for var in ("XDG_DATA_HOME", "APPDATA"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v.format(home=tmp_path))
    assert core.data_path() == Path(expected.format(home=tmp_path))
