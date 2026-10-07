from __future__ import annotations

import dataclasses
import time
from datetime import date, timedelta
from pathlib import Path

from rich import box
from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.color import Color
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.geometry import Region
from textual.screen import ModalScreen, Screen
from textual.suggester import SuggestFromList
from textual.theme import Theme
from textual.widget import Widget
from textual.widgets import (Button, Footer, Input, Label, ListItem, ListView, OptionList,
                             RadioButton, RadioSet, Static)
from textual.widgets.option_list import Option

from . import catalog, core, i18n
from .core import Car, MAX_CARS
from .i18n import t

GREEN, WARN, CRIT = "#33ff33", "#ffd000", "#ff3030"
DEFAULT_THEME = "isolation"
BAR_WIDTH = 20
CHORD_TIMEOUT = 2.0  # секунды на вторую клавишу после h

ISOLATION = Theme(
    name="isolation",
    primary=GREEN, secondary=GREEN, accent=GREEN,
    foreground=GREEN, background="#000000", surface="#000000", panel="#001a00",
    warning=WARN, error=CRIT, success=GREEN,
    dark=True,
)


class Palette:
    """Цвета для Rich-разметки, вычисленные из активной темы Textual."""

    def __init__(self) -> None:
        self.update({})

    def update(self, variables: dict[str, str]) -> None:
        def get(name: str, default: str) -> Color:
            try:
                return Color.parse(variables.get(name, default))
            except Exception:
                return Color.parse(default)

        bg = get("background", "#000000")
        fg = get("foreground", GREEN)
        primary = get("primary", GREEN)
        self.fg, self.primary = fg.hex6, primary.hex6
        self.ok = get("success", GREEN).hex6
        self.warn = get("warning", WARN).hex6
        self.crit = get("error", CRIT).hex6
        self.dim = fg.blend(bg, 0.45).hex6
        self.dark = primary.blend(bg, 0.7).hex6
        self.cursor = primary.blend(bg, 0.85).hex6

    def level(self, lv: str) -> str:
        return {"ok": self.ok, "warn": self.warn, "crit": self.crit,
                "expired": self.crit, "off": self.dim}[lv]


C = Palette()


def bar(pct: float | None, level: str) -> Text:
    if pct is None:
        return Text("·" * BAR_WIDTH, style=C.dark)
    filled = round(max(0.0, min(100.0, pct)) / 100 * BAR_WIDTH)
    text = Text()
    text.append("■" * filled, style=C.level(level))
    text.append("■" * (BAR_WIDTH - filled), style=C.dark)
    return text


def parse_int(value: str, field: str, *, optional: bool = False,
              lo: int = 0, hi: int | None = None) -> int | None:
    value = value.strip().replace(" ", "")
    if not value:
        if optional:
            return None
        raise ValueError(t("err.required", field=field))
    try:
        n = int(value)
    except ValueError:
        raise ValueError(t("err.int", field=field)) from None
    if n < lo or (hi is not None and n > hi):
        raise ValueError(t("err.range", field=field))
    return n


# ───────────────────────────── локализация и навигация ─────────────────────────────

class Localized:
    """Переводит подписи привязок (ключи вида "b.*") у экземпляра.

    BINDINGS собираются Textual на уровне класса, поэтому язык применяется
    к привязкам экземпляра; при смене языка экраны пересоздаются.
    Привязки переводятся на месте: Textual добавляет к приложению свои
    (например, Ctrl+P — палитра команд), и их нельзя потерять.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.localize_bindings()

    def localize_bindings(self) -> None:
        bindings = self._bindings.key_to_bindings
        if not hasattr(self, "_l10n_keys"):
            self._l10n_keys = {(b.key, b.action): b.description
                               for items in bindings.values() for b in items
                               if b.description.startswith("b.")}
        for key, items in bindings.items():
            bindings[key] = [
                dataclasses.replace(b, description=t(self._l10n_keys[b.key, b.action]))
                if (b.key, b.action) in self._l10n_keys else b
                for b in items
            ]


# Та же физическая клавиша в русской раскладке (ЙЦУКЕН)
RU_LAYOUT = dict(zip("qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM",
                     "йцукенгшщзфывапролдячсмитьЙЦУКЕНГШЩЗФЫВАПРОЛДЯЧСМИТЬ"))


def with_ru(bindings: list[Binding]) -> list[Binding]:
    """Добавляет скрытые копии буквенных привязок для русской раскладки:
    клавиши работают в любой раскладке, а в нижней строке видны только латинские."""
    extra = []
    for b in bindings:
        ru_keys = [RU_LAYOUT[k] for k in b.key.split(",") if k in RU_LAYOUT]
        if ru_keys:
            extra.append(Binding(",".join(ru_keys), b.action, b.description,
                                 show=False, priority=b.priority))
    return bindings + extra


class NavButton(Button):
    """Кнопка, между которыми можно ходить стрелками и hjkl."""

    BINDINGS = with_ru([
        Binding("left,h,up,k", "app.focus_previous", show=False),
        Binding("right,l,down,j", "app.focus_next", show=False),
    ])


class VimOptionList(OptionList):
    BINDINGS = with_ru([
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ])


class VimListView(ListView):
    BINDINGS = with_ru([
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ])


class VimRadioSet(RadioSet):
    BINDINGS = with_ru([
        Binding("j", "next_button", show=False),
        Binding("k", "previous_button", show=False),
    ])


# ───────────────────────────── модальные окна ─────────────────────────────

class FormModal(Localized, ModalScreen):
    """Форма: Enter переходит к следующему полю, на последнем — сохраняет.

    ↑↓ ходят по полям; в полях ввода j/k печатаются как буквы, поэтому vim-клавиши
    работают только на кнопках и в списках.
    """

    BINDINGS = with_ru([
        Binding("escape", "cancel", "b.cancel"),
        Binding("up", "app.focus_previous", show=False),
        Binding("down", "app.focus_next", show=False),
    ])
    TITLE_KEY = ""

    def title_text(self) -> str:
        return t(self.TITLE_KEY)

    def compose_fields(self) -> ComposeResult:
        yield from ()

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog") as d:
            d.border_title = self.title_text()
            yield from self.compose_fields()
            yield Label("", id="error", classes="error")
            with Horizontal(classes="buttons"):
                yield NavButton(t("btn.save"), id="ok")
                yield NavButton(t("btn.cancel"), id="cancel")

    def on_mount(self) -> None:
        # Textual вызывает on_mount каждого класса в MRO, поэтому подклассы
        # меняют начальный фокус через focus_first, а не через on_mount
        self.focus_first()

    def focus_first(self) -> None:
        first = self.query(Input).first()
        first.focus()
        first.select_all()

    @on(Input.Submitted)
    def next_field(self, event: Input.Submitted) -> None:
        inputs = list(self.query(Input))
        i = inputs.index(event.input)
        if i + 1 < len(inputs):
            inputs[i + 1].focus()
        else:
            self.submit()

    @on(Button.Pressed, "#ok")
    def submit(self) -> None:
        try:
            result = self.collect()
        except ValueError as e:
            self.query_one("#error", Label).update(f"⚠ {e}")
            return
        self.dismiss(result)

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    def val(self, id_: str) -> str:
        return self.query_one(f"#{id_}", Input).value

    def check_not_below(self, km: int, car: Car) -> int:
        if km < car.odometer:
            raise ValueError(t("err.less", km=car.odometer))
        return km

    def collect(self):
        raise NotImplementedError


class MileageModal(FormModal):
    TITLE_KEY = "t.mileage"

    def __init__(self, car: Car) -> None:
        super().__init__()
        self.car = car

    def compose_fields(self) -> ComposeResult:
        yield Label(t("l.current_km", km=self.car.odometer))
        yield Input(str(self.car.odometer), placeholder=t("u.km"), id="km", type="integer")

    def collect(self) -> int:
        return self.check_not_below(parse_int(self.val("km"), t("f.mileage")), self.car)


class CorrectOdometerModal(FormModal):
    TITLE_KEY = "t.correct"

    def __init__(self, car: Car) -> None:
        super().__init__()
        self.car = car

    def compose_fields(self) -> ComposeResult:
        yield Label(t("l.odo_now", km=self.car.odometer))
        yield Label(t("l.correct_note"))
        yield Label(t("l.correct_km"))
        yield Input(str(self.car.odometer), id="km", type="integer")

    def collect(self) -> int:
        return parse_int(self.val("km"), t("f.mileage"))


class ConfirmModal(Localized, ModalScreen):
    BINDINGS = with_ru([Binding("escape,n", "answer(False)", "b.no"),
                        Binding("y", "answer(True)", "b.yes")])

    def __init__(self, title: str, question: str) -> None:
        super().__init__()
        self.title_text, self.question = title, question

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog alarm") as d:
            d.border_title = self.title_text
            yield Static(self.question)
            with Horizontal(classes="buttons"):
                yield NavButton(t("btn.yes"), id="yes")
                yield NavButton(t("btn.no"), id="no")

    def on_mount(self) -> None:
        self.query_one("#no", Button).focus()

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_answer(self, yes: bool) -> None:
        self.dismiss(yes)


class ReplaceModal(FormModal):
    TITLE_KEY = "t.replace"

    def __init__(self, car: Car, preset: str | None = None) -> None:
        super().__init__()
        self.car = car
        self.preset = car.part(preset) if preset else None

    def title_text(self) -> str:
        if self.preset:
            return f"{t('t.repeat')} · {self.preset.name}"
        return super().title_text()

    def compose_fields(self) -> ComposeResult:
        names = catalog.suggestions(i18n.get_lang(), sorted(p.name for p in self.car.parts))
        if self.preset:
            yield Label(t("l.prev_replace", km=self.preset.installed_km,
                          date=self.preset.installed_on))
        yield Label(t("l.replace_km"))
        yield Input(str(self.car.odometer), id="km", type="integer")
        yield Label(t("l.part"))
        yield Input(self.preset.name if self.preset else "", id="name",
                    placeholder=t("l.part_ph"),
                    suggester=SuggestFromList(names, case_sensitive=False))
        yield Label(t("l.interval_km"))
        yield Input(id="interval_km", type="integer")
        yield Label(t("l.interval_days"))
        yield Input(id="interval_days", type="integer")
        with Horizontal(classes="pair"):
            with Vertical():
                yield Label(t("l.warn"))
                yield Input("40", id="warn", type="integer")
            with Vertical():
                yield Label(t("l.crit"))
                yield Input("15", id="crit", type="integer")

    def on_mount(self) -> None:
        if self.preset:
            self.prefill_from(self.preset.name)

    @on(Input.Changed, "#name")
    def prefill(self, event: Input.Changed) -> None:
        self.prefill_from(event.value)

    def prefill_from(self, name: str) -> None:
        """Для уже известной детали подставляем её прежние настройки."""
        p = self.car.part(name.strip())
        if p is None:
            return
        for id_, v in (("interval_km", p.interval_km), ("interval_days", p.interval_days),
                       ("warn", p.warn_pct), ("crit", p.crit_pct)):
            self.query_one(f"#{id_}", Input).value = "" if v is None else str(int(v))

    def collect(self) -> dict:
        km = self.check_not_below(parse_int(self.val("km"), t("f.mileage")), self.car)
        name = self.val("name").strip()
        if not name:
            raise ValueError(t("err.part_name"))
        warn = parse_int(self.val("warn"), t("f.warn"), hi=100)
        crit = parse_int(self.val("crit"), t("f.crit"), hi=100)
        if crit > warn:
            raise ValueError(t("err.thresholds"))
        return dict(
            name=name, km=km, warn=warn, crit=crit,
            interval_km=parse_int(self.val("interval_km"), t("f.interval_km"),
                                  optional=True, lo=1),
            interval_days=parse_int(self.val("interval_days"), t("f.interval_days"),
                                    optional=True, lo=1),
        )


class AddCarModal(FormModal):
    TITLE_KEY = "t.new_car"

    def compose_fields(self) -> ComposeResult:
        yield Label(t("l.brand"))
        yield Input(id="brand", placeholder="Toyota")
        yield Label(t("l.model"))
        yield Input(id="model", placeholder="Corolla")
        with Horizontal(classes="pair"):
            with Vertical():
                yield Label(t("l.year"))
                yield Input(id="year", type="integer")
            with Vertical():
                yield Label(t("l.engine"))
                yield Input(id="engine", placeholder="1.6")
        yield Label(t("l.odometer"))
        yield Input(id="odometer", type="integer")

    def collect(self) -> Car:
        brand, model = self.val("brand").strip(), self.val("model").strip()
        if not brand or not model:
            raise ValueError(t("err.brand"))
        year = parse_int(self.val("year"), t("f.year"), lo=1900, hi=date.today().year + 1)
        try:
            engine = float(self.val("engine").replace(",", "."))
        except ValueError:
            raise ValueError(t("err.engine")) from None
        if not 0 < engine < 20:
            raise ValueError(t("err.engine_range"))
        return Car(brand, model, year, engine, parse_int(self.val("odometer"), t("f.mileage")))


class ExportModal(FormModal):
    TITLE_KEY = "t.export"
    FORMATS = {"fmt-md": "md", "fmt-json": "json"}

    def __init__(self, car: Car) -> None:
        super().__init__()
        self.car = car

    def compose_fields(self) -> ComposeResult:
        yield Label(t("l.format"))
        with VimRadioSet(id="fmt"):
            yield RadioButton("Markdown (.md)", value=True, id="fmt-md")
            yield RadioButton("JSON (.json)", id="fmt-json")
        yield Label(t("l.folder"))
        yield Input(str(Path.cwd()), id="dir")
        yield Label("", id="target")

    def on_mount(self) -> None:
        self.update_target()

    def focus_first(self) -> None:
        self.query_one(RadioSet).focus()

    def ext(self) -> str:
        pressed = self.query_one(RadioSet).pressed_button
        return self.FORMATS[pressed.id] if pressed else "md"

    def target(self) -> Path:
        folder = self.val("dir").strip()
        base = Path(folder).expanduser() if folder else Path.cwd()
        return base / self.car.export_name(self.ext())

    @on(Input.Changed, "#dir")
    @on(RadioSet.Changed)
    def update_target(self) -> None:
        self.query_one("#target", Label).update(f"→ {self.target()}")

    def collect(self) -> Path:
        path = self.target()
        text = self.car.history_json() if self.ext() == "json" else self.car.history_md()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except OSError as e:
            raise ValueError(str(e)) from None
        return path


class MenuModal(Localized, ModalScreen):
    BINDINGS = with_ru([Binding("escape", "cancel", "b.cancel")])

    def __init__(self, title: str, options: list[tuple[str, str]]) -> None:
        super().__init__()
        self.title_text, self.options = title, options

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog") as d:
            d.border_title = self.title_text
            yield VimOptionList(*(Option(label, id=key) for key, label in self.options))

    def on_mount(self) -> None:
        self.query_one(OptionList).highlighted = 0

    @on(OptionList.OptionSelected)
    def chosen(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ExpiredModal(Localized, ModalScreen):
    BINDINGS = with_ru([Binding("escape,enter", "close", "b.ok")])

    def __init__(self, car: Car) -> None:
        super().__init__()
        self.car = car

    def compose(self) -> ComposeResult:
        text = Text()
        for p in self.car.expired():
            text.append("⚠⚠ ", style=f"bold {C.crit}")
            text.append(p.name, style=f"bold {C.crit}")
            over = []
            km = p.remaining_km(self.car.odometer)
            if km is not None and km <= 0:
                over.append(t("l.overrun", km=-km))
            days = p.remaining_days()
            if days is not None and days <= 0:
                over.append(t("l.overdue_days", d=-days))
            text.append(f"  {', '.join(over)}\n", style=C.warn)
        with Vertical(classes="dialog alarm") as d:
            d.border_title = t("t.expired")
            yield Static(text)
            yield NavButton(t("btn.ack"), id="ok")

    def on_mount(self) -> None:
        self.query_one(Button).focus()

    @on(Button.Pressed)
    def action_close(self) -> None:
        self.dismiss(None)


# ───────────────────────────── основные экраны ─────────────────────────────

class Logo(Widget):
    DEFAULT_CSS = "Logo { height: auto; }"

    def render(self) -> Text:
        return Text.assemble(
            ("▞▀▖▞▀▖▛▀▖▛▀▖▞▀▖▛▀▖▀▛▘▞▀▖\n", C.primary),
            ("▌  ▙▄▌▙▄▘▙▄▘▙▄▌▙▄▘ ▌ ▚▄ \n", C.primary),
            ("▚▄▘▌ ▌▌▚ ▌  ▌ ▌▌▚  ▌ ▄▄▘\n", C.primary),
            (t("logo.tag"), C.dim),
        )


class LanguageScreen(Screen):
    """Выбор языка: при первом запуске и из меню."""

    def compose(self) -> ComposeResult:
        yield Logo(id="logo")
        with Vertical(classes="panel", id="start") as v:
            v.border_title = t("t.lang")
            yield VimOptionList(*(Option(name, id=code) for code, name in i18n.LANGS.items()))

    def on_mount(self) -> None:
        ol = self.query_one(OptionList)
        ol.highlighted = list(i18n.LANGS).index(i18n.get_lang())
        ol.focus()

    @on(OptionList.OptionSelected)
    def chosen(self, event: OptionList.OptionSelected) -> None:
        self.app.set_language(event.option.id)
        self.dismiss(event.option.id)


class CarSelectScreen(Localized, Screen):
    BINDINGS = with_ru([Binding("a", "add_car", "b.add_car"),
                        Binding("d,delete", "delete_car", "b.delete_car"),
                        Binding("L", "language", "b.lang"),
                        Binding("q", "app.quit", "b.quit")])

    def compose(self) -> ComposeResult:
        yield Logo(id="logo")
        with Vertical(classes="panel", id="cars") as v:
            v.border_title = t("t.cars")
            yield VimListView()
        yield Footer()

    async def on_mount(self) -> None:
        await self.reload()
        if not self.app.cars:
            self.action_add_car()

    @staticmethod
    def car_line(car: Car) -> Text:
        levels = [p.level(car.odometer) for p in car.parts]
        worst = next((lv for lv in core.LEVELS if lv in levels), "ok")
        line = Text()
        line.append(f"{car.title:<36}", style=C.level(worst))
        line.append(f"{car.odometer:>9} {t('u.km')}  ", style=C.fg)
        if worst in ("crit", "expired"):
            line.append("⚠⚠", style=C.crit)
        return line

    async def reload(self) -> None:
        lv_ = self.query_one(ListView)
        await lv_.clear()
        await lv_.extend(ListItem(Static(self.car_line(car))) for car in self.app.cars)
        if self.app.cars:
            lv_.index = 0
        lv_.focus()

    @on(ListView.Selected)
    def chosen(self, event: ListView.Selected) -> None:
        self.app.car = self.app.cars[event.list_view.index]
        self.app.switch_screen(StartMenuScreen())

    def action_add_car(self) -> None:
        self.app.add_car(on_added=lambda _: self.run_worker(self.reload()))

    def action_delete_car(self) -> None:
        index = self.query_one(ListView).index
        if index is None or not self.app.cars:
            return
        car = self.app.cars[index]

        async def done(yes):
            if yes:
                self.app.delete_car(car)
                await self.reload()
                if not self.app.cars:
                    self.action_add_car()
        self.app.push_screen(ConfirmModal(t("t.delete_car"), t("q.delete_car", car=car.title)),
                             done)

    def action_language(self) -> None:
        self.app.push_screen(LanguageScreen(),
                             lambda _: self.app.switch_screen(CarSelectScreen()))

    def on_theme_change(self) -> None:
        # перекрашиваем строки на месте: пересборка списка при быстром
        # перелистывании тем в палитре приводит к гонке монтирования
        for item, car in zip(self.query(ListItem), self.app.cars):
            item.query_one(Static).update(self.car_line(car))


class StartMenuScreen(Localized, Screen):
    BINDINGS = with_ru([Binding("escape", "back", "b.back")])

    def compose(self) -> ComposeResult:
        yield Logo(id="logo")
        with Vertical(classes="panel", id="start") as v:
            v.border_title = self.app.car.title
            yield VimOptionList(
                Option(t("m.plain"), id="plain"),
                Option(t("m.mileage"), id="mileage"),
                Option(t("m.replace"), id="replace"),
            )
        yield Footer()

    def on_mount(self) -> None:
        ol = self.query_one(OptionList)
        ol.highlighted = 0
        ol.focus()

    @on(OptionList.OptionSelected)
    def chosen(self, event: OptionList.OptionSelected) -> None:
        car = self.app.car
        if event.option.id == "plain":
            self.app.switch_screen(Dashboard())
        elif event.option.id == "mileage":
            def done(km):
                if km is not None:
                    self.app.log_mileage(km)
                    self.app.switch_screen(Dashboard(check_expired=True))
            self.app.push_screen(MileageModal(car), done)
        else:
            def done(data):
                if data is not None:
                    self.app.replace_part(data)
                    self.app.switch_screen(Dashboard(check_expired=True))
            self.app.push_screen(ReplaceModal(car), done)

    def action_back(self) -> None:
        self.app.switch_screen(CarSelectScreen())


class Dashboard(Localized, Screen):
    BINDINGS = with_ru([
        Binding("up,k", "move(-1)", "↑↓", priority=True),
        Binding("down,j", "move(1)", show=False, priority=True),
        Binding("enter", "replace_selected", "b.repeat", priority=True),
        Binding("r", "replace", "b.replace"),
        Binding("d,delete", "delete_selected", "b.delete"),
        Binding("h", "toggle('history-panel')", "b.history"),
        Binding("s", "toggle('stats-panel')", "b.stats"),
        Binding("o", "cycle_sort", "b.sort"),
        Binding("x", "extra", "b.menu"),
        Binding("e", "history_export", show=False),
        Binding("c", "change_car", "b.car"),
        Binding("q", "app.quit", "b.quit"),
    ])

    def __init__(self, check_expired: bool = False) -> None:
        super().__init__()
        self.check_expired = check_expired
        self.blink_hidden = False
        self.blink_step = 0
        self.blink_timer = None
        self.cursor_name: str | None = None
        self.history_chord_until = 0.0
        mode = core.load_config().get("sort", "life")
        self.sort_mode = mode if mode in core.SORT_MODES else "life"

    def compose(self) -> ComposeResult:
        yield Static(id="topbar")
        with Horizontal(id="body"):
            with VerticalScroll(classes="panel", id="parts-panel") as v:
                v.border_title = t("t.parts")
                v.border_subtitle = self.sort_label()
                yield Static(id="parts")
            with Vertical(id="side"):
                with VerticalScroll(classes="panel", id="history-panel") as v:
                    v.border_title = t("t.history")
                    v.border_subtitle = "h+e export · h+c clear"
                    yield Static(id="history")
                with Vertical(classes="panel", id="stats-panel") as v:
                    v.border_title = t("t.stats")
                    yield Static(id="stats")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self.set_interval(10, self.start_blink)
        self.start_blink()
        if self.check_expired:
            self.app.show_expired()

    # ── мигание: 3 раза, затем горит постоянно; цикл каждые 10 с ──
    def start_blink(self) -> None:
        car = self.app.car
        if self.blink_timer:
            self.blink_timer.stop()
        if any(p.level(car.odometer) in ("crit", "expired") for p in car.parts):
            self.blink_step = 0
            self.blink_timer = self.set_interval(0.3, self.blink_tick)

    def blink_tick(self) -> None:
        self.blink_step += 1
        self.blink_hidden = self.blink_step % 2 == 1
        if self.blink_step >= 6:
            self.blink_timer.stop()
            self.blink_timer = None
        self.render_parts()

    # ── отрисовка ──
    def on_theme_change(self) -> None:
        self.refresh_all()

    def refresh_all(self) -> None:
        self.render_top()
        self.render_parts()
        self.render_history()
        self.render_stats()

    def render_top(self) -> None:
        car = self.app.car
        text = Text()
        text.append(f" {car.title} ", style=f"bold reverse {C.primary}")
        km = f"{car.odometer:,}".replace(",", " ")
        text.append(f"   {t('d.odometer', km=km)}", style=f"bold {C.fg}")
        text.append(f"   {date.today().isoformat()}", style=C.dim)
        self.query_one("#topbar", Static).update(text)

    def render_parts(self) -> None:
        car = self.app.car
        names = [p.name for p in self.parts_in_order()]
        if self.cursor_name not in names:
            self.cursor_name = names[0] if names else None
        if not car.parts:
            self.query_one("#parts", Static).update(Text(t("d.no_parts"), style=C.dim))
            return
        table = Table(box=box.SIMPLE_HEAD, expand=True, header_style=f"bold {C.primary}",
                      border_style=C.dark, pad_edge=False, padding=(0, 1, 0, 0))
        table.add_column("", width=2, no_wrap=True)
        table.add_column(t("col.part"), ratio=1, min_width=18, no_wrap=True,
                         overflow="ellipsis")
        table.add_column(t("col.life"), width=BAR_WIDTH, no_wrap=True)
        table.add_column("%", justify="right", width=5)
        table.add_column(t("col.left_km"), justify="right", width=8)
        table.add_column(t("col.left_days"), justify="right", width=7)
        table.add_column(t("col.installed"), justify="right", width=19, no_wrap=True,
                         style=C.dim)
        for p in self.parts_in_order():
            pct, lv = p.percent(car.odometer), p.level(car.odometer)
            color = C.level(lv)
            alarm = lv in ("crit", "expired")
            hidden = alarm and self.blink_hidden
            selected = p.name == self.cursor_name
            if hidden or not alarm:
                sign = Text("▶" if selected else "", style=f"bold {C.fg}")
            else:
                sign = Text("⚠⚠", style=f"bold {C.crit}")
            name = Text(" " * len(p.name) if hidden else p.name,
                        style=f"bold {color}" if alarm else color)
            km, days = p.remaining_km(car.odometer), p.remaining_days()
            table.add_row(
                sign, name, bar(pct, lv),
                Text("—" if pct is None else f"{pct:.0f}", style=color),
                Text("—" if km is None else str(km), style=color),
                Text("—" if days is None else str(days), style=color),
                f"{p.installed_km} · {p.installed_on}",
                style=f"on {C.cursor}" if selected else None,
            )
        self.query_one("#parts", Static).update(table)

    def render_history(self) -> None:
        car = self.app.car
        text = Text()
        for h in reversed(car.history):
            text.append(f"{h.date}  ", style=C.dim)
            text.append(f"{h.km:>8} {t('u.km')}", style=C.fg)
            if h.replaced:
                text.append(f"  ⟳ {', '.join(h.replaced)}", style=f"bold {C.fg}")
            text.append("\n")
        self.query_one("#history", Static).update(text or Text(t("h.empty"), style=C.dim))

    def render_stats(self) -> None:
        car = self.app.car
        levels = [p.level(car.odometer) for p in car.parts]
        text = Text()
        text.append(t("s.parts", n=len(car.parts)) + "\n", style=f"bold {C.fg}")
        for lv in ("ok", "warn", "crit", "expired", "off"):
            n = levels.count(lv)
            if n:
                text.append(f"  ■ {t('lv.' + lv):<14}{n}\n", style=C.level(lv))
        kpd = car.km_per_day()
        text.append("\n" + t("s.avg"), style=C.dim)
        text.append((t("s.per_day", n=f"{kpd:.0f}") if kpd else t("s.few")) + "\n",
                    style=C.fg)
        replacements = sum(len(h.replaced) for h in car.history)
        text.append(t("s.records"), style=C.dim)
        text.append(t("s.records_val", n=len(car.history), r=replacements) + "\n", style=C.fg)
        forecast = [(d, p) for p in car.parts
                    if (d := p.days_left(car.odometer, kpd)) is not None]
        if forecast:
            d, p = min(forecast, key=lambda x: x[0])
            text.append("\n" + t("s.next") + "\n", style=C.dim)
            text.append(f"  {p.name}\n", style=f"bold {C.level(p.level(car.odometer))}")
            when = date.today() + timedelta(days=max(0, int(d)))
            text.append("  " + (t("s.now") if d <= 0 else
                                t("s.in_days", date=when.isoformat(), d=int(d))) + "\n",
                        style=C.fg)
        self.query_one("#stats", Static).update(text)

    # ── сортировка ──
    def parts_in_order(self) -> list:
        return self.app.car.sorted_parts(by=self.sort_mode)

    def sort_label(self) -> str:
        return t("sort.label", mode=t("sort." + self.sort_mode))

    def action_cycle_sort(self) -> None:
        modes = core.SORT_MODES
        self.sort_mode = modes[(modes.index(self.sort_mode) + 1) % len(modes)]
        core.save_config({**core.load_config(), "sort": self.sort_mode})
        self.query_one("#parts-panel").border_subtitle = self.sort_label()
        self.render_parts()

    # ── действия ──
    def action_toggle(self, panel_id: str) -> None:
        panel = self.query_one(f"#{panel_id}")
        panel.display = not panel.display
        side = self.query_one("#side")
        side.display = any(c.display for c in side.children)
        if panel_id == "history-panel":
            # h — ещё и префикс аккордов h+e / h+c (как меню панелей в btop)
            self.history_chord_until = time.monotonic() + CHORD_TIMEOUT

    def take_history_chord(self) -> bool:
        """Сработал ли аккорд с h; панель истории при этом остаётся видимой."""
        if time.monotonic() > self.history_chord_until:
            return False
        self.history_chord_until = 0.0
        mode = core.load_config().get("sort", "life")
        self.sort_mode = mode if mode in core.SORT_MODES else "life"
        self.query_one("#history-panel").display = True
        self.query_one("#side").display = True
        return True

    def action_history_export(self) -> None:
        if self.take_history_chord():
            self.export_history()

    def export_history(self) -> None:
        self.app.push_screen(ExportModal(self.app.car), lambda path: path and
                             self.notify(t("n.saved", path=path), title=t("n.export")))

    def clear_history(self) -> None:
        def done(yes):
            if yes:
                self.app.car.clear_history()
                self.app.save()
                self.refresh_all()
                self.notify(t("n.cleared"))
        self.app.push_screen(ConfirmModal(t("t.clear"), t("q.clear", car=self.app.car.title)),
                             done)

    def delete_this_car(self) -> None:
        car = self.app.car

        def done(yes):
            if yes:
                self.app.delete_car(car)
                self.app.switch_screen(CarSelectScreen())
        self.app.push_screen(ConfirmModal(t("t.delete_car"), t("q.delete_car", car=car.title)),
                             done)

    def action_move(self, delta: int) -> None:
        names = [p.name for p in self.parts_in_order()]
        if not names:
            return
        i = names.index(self.cursor_name) if self.cursor_name in names else 0
        i = max(0, min(len(names) - 1, i + delta))
        self.cursor_name = names[i]
        self.render_parts()
        # шапка таблицы занимает 3 строки
        self.query_one("#parts-panel").scroll_to_region(Region(0, i + 3, 1, 1),
                                                         animate=False)

    def action_replace(self, preset: str | None = None) -> None:
        def done(data):
            if data is not None:
                self.app.replace_part(data)
                self.cursor_name = data["name"]
                self.refresh_all()
                self.app.show_expired()
        self.app.push_screen(ReplaceModal(self.app.car, preset), done)

    def action_replace_selected(self) -> None:
        if self.cursor_name:
            self.action_replace(self.cursor_name)
        else:
            self.action_replace()

    def action_delete_selected(self, name: str | None = None) -> None:
        name = name or self.cursor_name
        if not name:
            return

        def done(yes):
            if yes:
                self.app.car.remove_part(name)
                self.app.save()
                self.cursor_name = None
                self.refresh_all()
                self.notify(t("n.deleted", name=name))
        self.app.push_screen(ConfirmModal(t("t.delete_part"), t("q.delete_part", name=name)),
                             done)

    def correct_odometer(self) -> None:
        def done(km):
            if km is not None:
                self.app.car.correct_odometer(km)
                self.app.save()
                self.refresh_all()
                self.notify(t("n.corrected", km=km))
        self.app.push_screen(CorrectOdometerModal(self.app.car), done)

    def choose_part(self, title: str, then) -> None:
        parts = self.parts_in_order()
        if not parts:
            self.notify(t("n.no_parts"), severity="warning")
            return
        self.app.push_screen(MenuModal(title, [(p.name, p.name) for p in parts]),
                             lambda name: name and then(name))

    def choose_part_to_replace(self) -> None:
        self.choose_part(t("t.repeat"), self.action_replace)

    def action_extra(self) -> None:
        def done(choice):
            if choice == "replace":
                self.action_replace()
            elif choice == "repeat":
                self.choose_part_to_replace()
            elif choice == "delete":
                self.choose_part(t("t.delete_part"), self.action_delete_selected)
            elif choice == "odometer":
                self.correct_odometer()
            elif choice == "add":
                self.app.add_car()
            elif choice == "export":
                self.export_history()
            elif choice == "clear":
                self.clear_history()
            elif choice == "delete_car":
                self.delete_this_car()
            elif choice == "lang":
                self.app.push_screen(LanguageScreen(),
                                     lambda _: self.app.switch_screen(Dashboard()))
        self.app.push_screen(MenuModal(t("t.menu"), [
            (key, t("x." + key)) for key in (
                "replace", "repeat", "delete", "odometer", "export", "clear",
                "add", "delete_car", "lang")
        ]), done)

    def action_change_car(self) -> None:
        if self.take_history_chord():
            self.clear_history()
        else:
            self.app.switch_screen(CarSelectScreen())


# ───────────────────────────── приложение ─────────────────────────────

class CarPartsApp(Localized, App):
    CSS_PATH = "theme.tcss"
    TITLE = "CarParts"
    BINDINGS = with_ru([Binding("m", "quick_mileage", "b.mileage")])

    def __init__(self) -> None:
        config = core.load_config()
        i18n.set_lang(config.get("lang", i18n.DEFAULT_LANG))
        super().__init__()
        self.cars: list[Car] = core.load()
        self.car: Car | None = None
        self.saved_theme = config.get("theme", DEFAULT_THEME)
        self.first_run = "lang" not in config
        self.theme_ready = False

    def on_mount(self) -> None:
        self.register_theme(ISOLATION)
        self.theme = (self.saved_theme if self.saved_theme in self.available_themes
                      else DEFAULT_THEME)
        C.update(self.get_css_variables())
        self.theme_ready = True
        if self.first_run:
            self.push_screen(LanguageScreen(),
                             lambda _: self.push_screen(CarSelectScreen()))
        else:
            self.push_screen(CarSelectScreen())

    def set_language(self, lang: str) -> None:
        i18n.set_lang(lang)
        core.save_config({**core.load_config(), "lang": lang})
        self.localize_bindings()  # подписи привязок самого приложения

    def watch_theme(self, name: str) -> None:
        if not self.theme_ready:
            return
        C.update(self.get_css_variables())
        for screen in self.screen_stack:
            if hasattr(screen, "on_theme_change"):
                screen.on_theme_change()
        core.save_config({**core.load_config(), "theme": name})

    def save(self) -> None:
        core.save(self.cars)

    def log_mileage(self, km: int) -> None:
        self.car.log_mileage(km)
        self.save()

    def replace_part(self, data: dict) -> None:
        self.car.replace_part(**data)
        self.save()

    def delete_car(self, car: Car) -> None:
        self.cars.remove(car)
        if self.car is car:
            self.car = None
        self.save()
        self.notify(t("n.car_deleted", car=car.title))

    def show_expired(self) -> None:
        if self.car and self.car.expired():
            self.push_screen(ExpiredModal(self.car))

    def add_car(self, on_added=None) -> None:
        if len(self.cars) >= MAX_CARS:
            self.notify(t("n.max_cars", n=MAX_CARS), severity="warning")
            return

        def done(car):
            if car is not None:
                self.cars.append(car)
                self.save()
                self.notify(t("n.car_added", car=car.title))
                if on_added:
                    on_added(car)
        self.push_screen(AddCarModal(), done)

    def check_action(self, action: str, parameters) -> bool | None:
        if action == "quick_mileage":
            return self.car is not None and isinstance(self.screen, (Dashboard, StartMenuScreen))
        return True

    def action_quick_mileage(self) -> None:
        def done(km):
            if km is None:
                return
            self.log_mileage(km)
            if isinstance(self.screen, Dashboard):
                self.screen.refresh_all()
            else:
                self.switch_screen(Dashboard())
            self.show_expired()
        self.push_screen(MileageModal(self.car), done)


def self_test() -> int:
    """Запуск без терминала на временных данных: проверка собранного бинарника."""
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["XDG_DATA_HOME"] = os.environ["XDG_CONFIG_HOME"] = tmp
        car = Car("Test", "Car", 2020, 1.6, odometer=10_000)
        car.replace_part("Engine oil", interval_km=8000, km=10_000)
        core.save([car])
        core.save_config({"lang": "ru"})
        reached = []

        async def pilot(p) -> None:
            await p.pause()
            await p.press("enter", "enter")         # машина → дашборд
            await p.pause()
            reached.append(type(p.app.screen).__name__)
            p.app.exit()

        CarPartsApp().run(headless=True, auto_pilot=pilot, size=(120, 40))
    ok = reached == ["Dashboard"]
    print("self-test:", "ok" if ok else f"FAILED {reached}")
    return 0 if ok else 1


def main() -> None:
    import argparse
    import sys
    from importlib.metadata import PackageNotFoundError, version

    parser = argparse.ArgumentParser(prog="carparts")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.version:
        try:
            print("carparts", version("carparts"))
        except PackageNotFoundError:
            print("carparts", "unknown")
        return
    if args.self_test:
        sys.exit(self_test())
    CarPartsApp().run()


if __name__ == "__main__":
    main()
