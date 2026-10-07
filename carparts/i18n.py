"""Строки интерфейса на английском и русском."""
from __future__ import annotations

LANGS = {"en": "English", "ru": "Русский"}
DEFAULT_LANG = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # привязки клавиш (нижняя строка)
        "b.cancel": "Cancel", "b.no": "No", "b.yes": "Yes", "b.ok": "OK",
        "b.add_car": "Add car", "b.delete_car": "Delete car", "b.quit": "Quit",
        "b.back": "Back to cars", "b.repeat": "Re-replace", "b.replace": "New replacement",
        "b.delete": "Delete", "b.history": "History", "b.stats": "Stats", "b.menu": "Menu",
        "b.car": "Car", "b.mileage": "Mileage", "b.lang": "Language", "b.sort": "Sort",
        "sort.label": "o: sort by {mode}", "sort.life": "life", "sort.name": "name",
        "sort.date": "replacement date",
        # ошибки ввода
        "err.required": "{field}: required",
        "err.int": "{field}: must be a whole number",
        "err.range": "{field}: out of range",
        "err.less": "mileage is below current ({km} km)",
        "err.negative": "mileage cannot be negative",
        "err.part_name": "Part: enter a name",
        "err.thresholds": "red threshold must be ≤ yellow",
        "err.brand": "enter make and model",
        "err.engine": "Engine: a number, e.g. 1.6",
        "err.engine_range": "Engine: out of range",
        "f.mileage": "Mileage", "f.warn": "Yellow %", "f.crit": "Red %",
        "f.interval_km": "Interval km", "f.interval_days": "Interval days", "f.year": "Year",
        # кнопки
        "btn.save": "Save", "btn.cancel": "Cancel", "btn.yes": "Yes", "btn.no": "No",
        "btn.ack": "Got it",
        # заголовки
        "t.mileage": "ENTER MILEAGE", "t.correct": "CORRECT MILEAGE",
        "t.replace": "REPLACE PART", "t.repeat": "REPEAT REPLACEMENT",
        "t.new_car": "NEW CAR", "t.export": "EXPORT HISTORY",
        "t.expired": "⚠ REPLACEMENT REQUIRED ⚠", "t.cars": "SELECT CAR",
        "t.parts": "PART LIFE", "t.history": "HISTORY", "t.stats": "STATS", "t.menu": "MENU",
        "t.delete_part": "DELETE PART", "t.delete_car": "DELETE CAR",
        "t.clear": "CLEAR HISTORY", "t.lang": "LANGUAGE / ЯЗЫК",
        # подписи полей
        "l.current_km": "Current mileage: {km} km", "u.km": "km",
        "l.odo_now": "Odometer now: {km} km",
        "l.correct_note": "Plain mileage entries above the new value will be removed "
                          "from history. Part replacements are kept.",
        "l.correct_km": "Correct mileage, km",
        "l.prev_replace": "Previous replacement: {km} km · {date}",
        "l.replace_km": "Mileage at replacement, km",
        "l.part": "Part (→ accept suggestion)", "l.part_ph": "Engine oil",
        "l.interval_km": "Interval, km (empty = ignore)",
        "l.interval_days": "Interval, days (empty = ignore)",
        "l.warn": "Yellow, %", "l.crit": "Red, %",
        "l.brand": "Make", "l.model": "Model", "l.year": "Year", "l.engine": "Engine, L",
        "l.odometer": "Current mileage, km",
        "l.format": "Format (↑↓/jk choose, Enter select, Tab next)",
        "l.folder": "Folder (empty = current)",
        "l.overrun": "over by {km} km", "l.overdue_days": "overdue by {d} days",
        # стартовое меню
        "m.plain": "1. Just open", "m.mileage": "2. Enter mileage",
        "m.replace": "3. Enter mileage and replaced part",
        # дашборд
        "d.odometer": "ODOMETER {km} km",
        "d.no_parts": "No parts yet. Press r to add a replacement.",
        "col.part": "Part", "col.life": "Life", "col.left_km": "Left km",
        "col.left_days": "Left d", "col.installed": "Installed",
        "h.empty": "empty",
        "s.parts": "Parts: {n}", "s.avg": "Avg mileage: ", "s.per_day": "{n} km/day",
        "s.few": "not enough data", "s.records": "Records: ",
        "s.records_val": "{n}, replacements: {r}", "s.next": "Next replacement:",
        "s.now": "now", "s.in_days": "~{date} ({d} d)",
        "lv.ok": "ok", "lv.warn": "soon", "lv.crit": "critical", "lv.expired": "overdue",
        "lv.off": "no interval",
        # уведомления и вопросы
        "n.saved": "Saved: {path}", "n.export": "Export", "n.cleared": "History cleared",
        "n.deleted": "Deleted: {name}", "n.corrected": "Mileage corrected: {km} km",
        "n.no_parts": "No parts yet", "n.car_deleted": "Deleted: {car}",
        "n.max_cars": "Maximum {n} cars", "n.car_added": "Added: {car}",
        "q.clear": "Delete all mileage and replacement history of “{car}”?\n"
                   "Parts and their life are kept.",
        "q.delete_car": "Delete “{car}” with all parts and history?\nThis cannot be undone.",
        "q.delete_part": "Delete “{name}”?\nPast replacement records stay in history.",
        # меню x
        "x.replace": "Replace part (new or existing)", "x.repeat": "Repeat replacement…",
        "x.delete": "Delete part…", "x.odometer": "Correct car mileage",
        "x.export": "Export history (Markdown / JSON)   h+e",
        "x.clear": "Clear history                      h+c",
        "x.add": "Add car", "x.delete_car": "Delete this car", "x.lang": "Language / Язык",
        # прочее
        "logo.tag": "parts life · service terminal",
        "md.date": "Date", "md.km": "Mileage, km", "md.replaced": "Replaced",
    },
    "ru": {
        "b.cancel": "Отмена", "b.no": "Нет", "b.yes": "Да", "b.ok": "OK",
        "b.add_car": "Добавить машину", "b.delete_car": "Удалить машину", "b.quit": "Выход",
        "b.back": "К выбору машины", "b.repeat": "Повтор. замена", "b.replace": "Новая замена",
        "b.delete": "Удалить", "b.history": "История", "b.stats": "Статистика",
        "b.menu": "Меню", "b.car": "Машина", "b.mileage": "Пробег", "b.lang": "Язык",
        "b.sort": "Сортировка",
        "sort.label": "o: сортировка — {mode}", "sort.life": "ресурс",
        "sort.name": "название", "sort.date": "дата замены",
        "err.required": "{field}: обязательное поле",
        "err.int": "{field}: нужно целое число",
        "err.range": "{field}: вне диапазона",
        "err.less": "пробег меньше текущего ({km} км)",
        "err.negative": "пробег не может быть отрицательным",
        "err.part_name": "Деталь: укажите название",
        "err.thresholds": "красный порог должен быть ≤ жёлтого",
        "err.brand": "укажите марку и модель",
        "err.engine": "Объём: число, например 1.6",
        "err.engine_range": "Объём: вне диапазона",
        "f.mileage": "Пробег", "f.warn": "Жёлтый %", "f.crit": "Красный %",
        "f.interval_km": "Интервал км", "f.interval_days": "Интервал дней", "f.year": "Год",
        "btn.save": "Сохранить", "btn.cancel": "Отмена", "btn.yes": "Да", "btn.no": "Нет",
        "btn.ack": "Принято",
        "t.mileage": "ВВОД ПРОБЕГА", "t.correct": "ИСПРАВИТЬ ПРОБЕГ",
        "t.replace": "ЗАМЕНА ДЕТАЛИ", "t.repeat": "ПОВТОРНАЯ ЗАМЕНА",
        "t.new_car": "НОВАЯ МАШИНА", "t.export": "ЭКСПОРТ ИСТОРИИ",
        "t.expired": "⚠ ТРЕБУЕТСЯ ЗАМЕНА ⚠", "t.cars": "ВЫБОР МАШИНЫ",
        "t.parts": "РЕСУРС ДЕТАЛЕЙ", "t.history": "ИСТОРИЯ", "t.stats": "СТАТИСТИКА",
        "t.menu": "МЕНЮ", "t.delete_part": "УДАЛЕНИЕ ДЕТАЛИ", "t.delete_car": "УДАЛЕНИЕ МАШИНЫ",
        "t.clear": "ОЧИСТКА ИСТОРИИ", "t.lang": "ЯЗЫК / LANGUAGE",
        "l.current_km": "Текущий пробег: {km} км", "u.km": "км",
        "l.odo_now": "Сейчас на одометре: {km} км",
        "l.correct_note": "Записи «просто пробег» выше нового значения будут удалены "
                          "из истории. Замены деталей сохранятся.",
        "l.correct_km": "Правильный пробег, км",
        "l.prev_replace": "Предыдущая замена: {km} км · {date}",
        "l.replace_km": "Пробег при замене, км",
        "l.part": "Деталь (→ принять подсказку)", "l.part_ph": "Моторное масло",
        "l.interval_km": "Интервал, км (пусто = не учитывать)",
        "l.interval_days": "Интервал, дней (пусто = не учитывать)",
        "l.warn": "Жёлтый, %", "l.crit": "Красный, %",
        "l.brand": "Марка", "l.model": "Модель", "l.year": "Год", "l.engine": "Объём, л",
        "l.odometer": "Текущий пробег, км",
        "l.format": "Формат (↑↓/jk выбрать, Enter отметить, Tab — дальше)",
        "l.folder": "Папка (пусто = текущая)",
        "l.overrun": "перепробег {km} км", "l.overdue_days": "просрочено на {d} дн",
        "m.plain": "1. Простой запуск", "m.mileage": "2. Ввести пробег",
        "m.replace": "3. Ввести пробег и заменённую деталь",
        "d.odometer": "ОДОМЕТР {km} км",
        "d.no_parts": "Деталей пока нет. Нажмите r, чтобы добавить замену.",
        "col.part": "Деталь", "col.life": "Ресурс", "col.left_km": "Ост. км",
        "col.left_days": "Ост. дн", "col.installed": "Установлено",
        "h.empty": "пусто",
        "s.parts": "Деталей: {n}", "s.avg": "Средний пробег: ", "s.per_day": "{n} км/день",
        "s.few": "мало данных", "s.records": "Записей: ",
        "s.records_val": "{n}, замен: {r}", "s.next": "Ближайшая замена:",
        "s.now": "сейчас", "s.in_days": "~{date} ({d} дн)",
        "lv.ok": "норма", "lv.warn": "скоро", "lv.crit": "критично", "lv.expired": "просрочено",
        "lv.off": "без интервала",
        "n.saved": "Сохранено: {path}", "n.export": "Экспорт", "n.cleared": "История очищена",
        "n.deleted": "Удалено: {name}", "n.corrected": "Пробег исправлен: {km} км",
        "n.no_parts": "Деталей пока нет", "n.car_deleted": "Удалена: {car}",
        "n.max_cars": "Максимум {n} машин", "n.car_added": "Добавлена: {car}",
        "q.clear": "Удалить всю историю пробега и замен «{car}»?\n"
                   "Детали и их ресурс останутся.",
        "q.delete_car": "Удалить «{car}» со всеми деталями и историей?\nЭто нельзя отменить.",
        "q.delete_part": "Удалить «{name}»?\nЗаписи о прошлых заменах в истории останутся.",
        "x.replace": "Заменить деталь (новая или любая)", "x.repeat": "Повторная замена детали…",
        "x.delete": "Удалить деталь…", "x.odometer": "Исправить пробег машины",
        "x.export": "Экспорт истории (Markdown / JSON)   h+e",
        "x.clear": "Очистить историю                   h+c",
        "x.add": "Добавить машину", "x.delete_car": "Удалить эту машину",
        "x.lang": "Язык / Language",
        "logo.tag": "ресурс запчастей · терминал обслуживания",
        "md.date": "Дата", "md.km": "Пробег, км", "md.replaced": "Что заменено",
    },
}

_lang = DEFAULT_LANG


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else DEFAULT_LANG


def get_lang() -> str:
    return _lang


def t(key: str, **kw) -> str:
    text = STRINGS[_lang].get(key) or STRINGS[DEFAULT_LANG][key]
    return text.format(**kw) if kw else text
