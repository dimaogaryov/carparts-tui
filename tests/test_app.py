import os
import asyncio
from datetime import date, timedelta

import pytest

from carparts import core
from carparts.app import (CarPartsApp, CarSelectScreen, Dashboard, ExpiredModal,
                          StartMenuScreen)
from carparts.core import Car, Part


@pytest.fixture(autouse=True)
def data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    core.save_config({"lang": "ru"})  # первый запуск с выбором языка — отдельный тест
    return tmp_path


def seed():
    car = Car("Lada", "Vesta", 2020, 1.6, odometer=100_000)
    old = (date.today() - timedelta(days=400)).isoformat()
    car.parts = [
        Part("Моторное масло", 93_500, date.today().isoformat(), interval_km=8000),
        Part("Антифриз", 99_000, old, interval_km=60_000, interval_days=365),
        Part("Воздушный фильтр", 90_000, date.today().isoformat(), interval_km=30_000),
    ]
    core.save([car])


async def type_text(pilot, text):
    for ch in text:
        await pilot.press(ch)


def test_first_run_add_car():
    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await type_text(pilot, "Toyota")
            await pilot.press("enter")
            await type_text(pilot, "Corolla")
            await pilot.press("enter")
            await type_text(pilot, "2015")
            await pilot.press("enter")
            await type_text(pilot, "1,6")
            await pilot.press("enter")
            await type_text(pilot, "150000")
            await pilot.press("enter")
            await pilot.pause()
            assert core.load()[0].title == "Toyota Corolla 2015 1.6L"
            assert isinstance(app.screen, CarSelectScreen)
    asyncio.run(run())


def test_mileage_flow_shows_expired_and_dashboard():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter")              # выбор машины
            await pilot.pause()
            assert isinstance(app.screen, StartMenuScreen)
            await pilot.press("down", "enter")      # 2. ввод пробега
            await pilot.pause()
            await type_text(pilot, "101000")
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ExpiredModal)
            await pilot.press("enter")
            await pilot.pause()
            dash = app.screen
            assert isinstance(dash, Dashboard)
            assert core.load()[0].odometer == 101_000

            # мигание: проходит 6 тиков и возвращается к видимому состоянию
            await pilot.pause(2.2)
            assert dash.blink_step == 6 and not dash.blink_hidden

            # панели
            await pilot.press("h")
            assert not dash.query_one("#history-panel").display
            await pilot.press("s")
            assert not dash.query_one("#side").display
            await pilot.press("s", "h")
            assert dash.query_one("#side").display
            if shot := os.environ.get("CARPARTS_SCREENSHOT"):
                app.save_screenshot(shot)
    asyncio.run(run())


def test_replace_and_quick_mileage_and_export(tmp_path):
    seed()
    out = tmp_path / "out.md"

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")    # машина → простой запуск
            await pilot.pause()
            assert isinstance(app.screen, Dashboard)

            await pilot.press("r")
            await pilot.press("enter")              # пробег по умолчанию
            await type_text(pilot, "Антифриз")
            await pilot.pause()
            # настройки подтянулись из существующей детали
            assert app.screen.query_one("#interval_days").value == "365"
            await pilot.press("enter", "enter", "enter", "enter", "enter")
            await pilot.pause()
            car = core.load()[0]
            assert car.part("Антифриз").percent(car.odometer) == 100
            assert car.history[-1].replaced == ["Антифриз"]

            await pilot.press("m")
            await pilot.pause()
            await type_text(pilot, "99")            # меньше текущего — ошибка
            await pilot.press("enter")
            assert "меньше" in str(app.screen.query_one("#error").render())
            app.screen.query_one("#km").value = ""
            await type_text(pilot, "102000")
            await pilot.press("enter")
            await pilot.pause()
            assert core.load()[0].odometer == 102_000
            assert isinstance(app.screen, ExpiredModal)   # масло: 93500 + 8000 < 102000
            await pilot.press("enter")

            await pilot.press("x", *["down"] * 4, "enter")
            await pilot.pause()
            app.screen.query_one("#dir").value = str(tmp_path)
            await pilot.press("tab", "enter")       # Markdown по умолчанию
            await pilot.pause()
            md = next(tmp_path.glob("carparts_lada_vesta_*.md"))
            assert "| Антифриз |" in md.read_text(encoding="utf-8")
    asyncio.run(run())


def test_repeat_replacement_from_cursor_and_menu():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            if shot := os.environ.get("CARPARTS_SCREENSHOT_SELECT"):
                app.save_screenshot(shot)
            await pilot.press("enter", "enter")    # машина → простой запуск
            await pilot.pause()
            dash = app.screen
            # сортировка: антифриз (просрочен), масло, фильтр
            assert dash.cursor_name == "Антифриз"
            await pilot.press("down")
            assert dash.cursor_name == "Моторное масло"
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen.query_one("#name").value == "Моторное масло"
            assert app.screen.query_one("#interval_km").value == "8000"
            await type_text(pilot, "100500")        # поле пробега выделено целиком
            await pilot.press("enter", "enter", "enter", "enter", "enter", "enter")
            await pilot.pause()
            oil = core.load()[0].part("Моторное масло")
            assert oil.installed_km == 100_500 and oil.interval_km == 8000
            assert core.load()[0].odometer == 100_500
            if isinstance(app.screen, ExpiredModal):  # антифриз всё ещё просрочен
                await pilot.press("enter")
            assert dash.cursor_name == "Моторное масло"
            if shot := os.environ.get("CARPARTS_SCREENSHOT"):
                app.save_screenshot(shot)

            # через меню x → повторная замена → антифриз
            await pilot.press("x", "down", "enter")
            await pilot.pause()
            await pilot.press("enter")              # первый в списке — антифриз
            await pilot.pause()
            assert app.screen.query_one("#interval_days").value == "365"
            await pilot.press("enter", "enter", "enter", "enter", "enter", "enter")
            await pilot.pause()
            car = core.load()[0]
            assert car.part("Антифриз").percent(car.odometer) == 100
            assert car.history[-1].replaced == ["Антифриз"]
            assert not car.expired()
    asyncio.run(run())


def test_delete_part_and_correct_odometer():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            dash = app.screen

            # ошибочный пробег → исправление без окна просрочки
            await pilot.press("m")
            await pilot.pause()
            await type_text(pilot, "190000")
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")              # закрыть окно просрочки
            await pilot.press("x", "down", "down", "down", "enter")
            await pilot.pause()
            await type_text(pilot, "100200")
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is dash
            car = core.load()[0]
            assert car.odometer == 100_200 and car.history == []
            assert car.part("Моторное масло").level(car.odometer) == "warn"  # 1300/8000

            # удаление выбранной детали: «Нет» по умолчанию, затем «y»
            assert dash.cursor_name == "Антифриз"
            await pilot.press("d", "enter")
            await pilot.pause()
            assert core.load()[0].part("Антифриз") is not None
            await pilot.press("d", "y")
            await pilot.pause()
            names = [p.name for p in core.load()[0].parts]
            assert names == ["Моторное масло", "Воздушный фильтр"]
            assert dash.cursor_name == "Моторное масло"
    asyncio.run(run())



def test_theme_switch_recolors_and_persists():
    seed()
    from carparts.app import C

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert app.theme == "isolation" and C.fg.lower() == "#33ff33"
            for name in sorted(app.available_themes):  # на экране выбора машины
                app.theme = name
            await pilot.pause()
            app.theme = "isolation"
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            for name in sorted(app.available_themes):  # ни одна тема не ломает отрисовку
                app.theme = name
                await pilot.pause()
            app.theme = "gruvbox"
            await pilot.pause()
            assert C.crit.lower() == app.theme_variables["error"].lower()
            if shot := os.environ.get("CARPARTS_SCREENSHOT_THEME"):
                app.save_screenshot(shot)
        assert core.load_config()["theme"] == "gruvbox"

        app = CarPartsApp()                          # тема восстанавливается при запуске
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert app.theme == "gruvbox"
    asyncio.run(run())


def test_history_chords_export_json_and_clear(tmp_path):
    seed()
    import json

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            dash = app.screen
            app.log_mileage(100_100)

            await pilot.press("e")                  # без h — ничего
            await pilot.pause()
            assert app.screen is dash

            await pilot.press("h", "e")             # h+e → экспорт, панель видна
            await pilot.pause()
            assert dash.query_one("#history-panel").display
            await pilot.press("down", "enter")      # JSON
            app.screen.query_one("#dir").value = str(tmp_path / "exp")
            await pilot.press("tab", "enter")
            await pilot.pause()
            data = json.loads(next((tmp_path / "exp").glob("*.json")).read_text(encoding="utf-8"))
            assert data["car"]["brand"] == "Lada" and data["history"][0]["km"] == 100_100

            await pilot.press("h", "c", "n")        # h+c → подтверждение → нет
            await pilot.pause()
            assert core.load()[0].history
            await pilot.press("h", "c", "y")
            await pilot.pause()
            assert core.load()[0].history == []
            assert app.screen is dash               # c из аккорда не сменил машину

            await pilot.press("c")                  # просто c — к выбору машины
            await pilot.pause()
            assert isinstance(app.screen, CarSelectScreen)
    asyncio.run(run())


def test_delete_car_from_select_and_menu():
    seed()
    cars = core.load()
    cars.append(Car("Honda", "Integra", 1999, 1.6, odometer=200_000))
    core.save(cars)

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("d", "n")
            await pilot.pause()
            assert len(core.load()) == 2
            await pilot.press("d", "y")             # удаляем первую (Lada)
            await pilot.pause()
            assert [c.brand for c in core.load()] == ["Honda"]

            await pilot.press("enter", "enter")     # Honda → дашборд
            await pilot.pause()
            await pilot.press("x", *["down"] * 7, "enter", "y")
            await pilot.pause()
            assert core.load() == []
            assert isinstance(app.screen.app.screen_stack[1], CarSelectScreen)
    asyncio.run(run())


def test_first_run_asks_language_and_translates(tmp_path):
    from carparts import i18n
    from carparts.app import LanguageScreen
    core.config_path().unlink()
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, LanguageScreen)
            await pilot.press("enter")                 # English — первый пункт
            await pilot.pause()
            assert isinstance(app.screen, CarSelectScreen)
            assert core.load_config()["lang"] == "en"
            assert app.screen.query_one("#cars").border_title == "SELECT CAR"
            descs = {b.description for b in app.screen.active_bindings.values()
                     if b.binding.show for b in [b.binding]}
            assert "Add car" in descs

            await pilot.press("L", "j", "enter")       # смена на русский
            await pilot.pause()
            assert i18n.get_lang() == "ru"
            assert app.screen.query_one("#cars").border_title == "ВЫБОР МАШИНЫ"
    asyncio.run(run())
    from carparts import i18n as _i
    _i.set_lang("ru")


def test_arrows_and_vim_keys_in_popups():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            dash = app.screen
            app.log_mileage(100_100)

            # подтверждение: фокус на «Нет», ← / h переводит на «Да»
            await pilot.press("h", "c")
            await pilot.pause()
            assert app.focused.id == "no"
            await pilot.press("left")
            assert app.focused.id == "yes"
            await pilot.press("right")
            assert app.focused.id == "no"
            await pilot.press("h")
            assert app.focused.id == "yes"
            await pilot.press("enter")
            await pilot.pause()
            assert core.load()[0].history == []

            # меню: j/k по пунктам
            await pilot.press("x", "j", "j", "k")
            await pilot.pause()
            assert app.screen.query_one("OptionList").highlighted == 1
            await pilot.press("escape")
            await pilot.pause()

            # форма: ↓ по полям и до кнопок, ← → между кнопками
            await pilot.press("m")
            await pilot.pause()
            await pilot.press("down")
            assert app.focused.id == "ok"
            await pilot.press("right")
            assert app.focused.id == "cancel"
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is dash
    asyncio.run(run())


def test_russian_layout_keys_hidden_in_footer_and_palette_kept():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert "ctrl+p" in app._bindings.key_to_bindings     # палитра на месте
            await pilot.press("enter", "enter")
            await pilot.pause()
            dash = app.screen
            shown = [k for k, ab in dash.active_bindings.items() if ab.binding.show]
            assert all(not ("а" <= k.lower() <= "я") for k in shown), shown
            assert {"r", "h", "x", "m"} <= set(shown)

            await pilot.press("р")                     # h → история
            assert not dash.query_one("#history-panel").display
            await pilot.press("о")                     # j → вниз
            assert dash.cursor_name == "Моторное масло"
            await pilot.press("к")                     # r → новая замена
            await pilot.pause()
            assert app.screen.query_one("#name").value == ""
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("ч", "о", "л")           # x → меню, j, k
            await pilot.pause()
            assert app.screen.query_one("OptionList").highlighted == 0
            await pilot.press("escape")
            await pilot.pause()
            app.log_mileage(100_100)
            await pilot.press("р", "с")               # h+c → очистка
            await pilot.pause()
            await pilot.press("р")                     # h на кнопках → «Да»
            assert app.focused.id == "yes"
            await pilot.press("н")                     # y
            await pilot.pause()
            assert core.load()[0].history == []
            await pilot.press("ь")                     # m → пробег
            await pilot.pause()
            assert app.screen.query_one("#km").value == "100100"
    asyncio.run(run())


def test_part_name_suggestions_from_catalog():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            await pilot.press("r", "enter")          # к полю «Деталь»
            await type_text(pilot, "сал")
            await pilot.pause(0.3)
            await pilot.press("right")              # принять подсказку
            assert app.screen.query_one("#name").value == "Салонный фильтр"
            app.screen.query_one("#name").value = ""
            await type_text(pilot, "мот")            # своя деталь важнее справочника
            await pilot.pause(0.3)
            await pilot.press("right")
            assert app.screen.query_one("#name").value == "Моторное масло"
    asyncio.run(run())


def test_dashboard_sort_cycle():
    seed()

    async def run():
        app = CarPartsApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            dash = app.screen
            order = lambda: [p.name for p in dash.parts_in_order()]
            assert order() == ["Антифриз", "Моторное масло", "Воздушный фильтр"]
            await pilot.press("o")
            assert dash.sort_mode == "name"
            assert order() == ["Антифриз", "Воздушный фильтр", "Моторное масло"]
            assert "название" in dash.query_one("#parts-panel").border_subtitle
            await pilot.press("щ")                  # русская раскладка
            assert dash.sort_mode == "date"
            assert order()[-1] == "Антифриз"        # поставлен раньше всех
            assert core.load_config()["sort"] == "date"
            await pilot.press("o")
            assert dash.sort_mode == "life"
    asyncio.run(run())
