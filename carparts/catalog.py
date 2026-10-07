"""Справочник типовых заменяемых деталей и расходников для автоподсказки.

Только названия: интервалы зависят от машины и задаются пользователем.
Порядок важен — при совпадении начала подсказывается первая подходящая.
"""

PARTS = {
    "ru": [
        # двигатель и фильтры
        "Моторное масло", "Масляный фильтр", "Воздушный фильтр", "Салонный фильтр",
        "Топливный фильтр", "Свечи зажигания", "Свечи накаливания", "Катушка зажигания",
        "Высоковольтные провода", "Прокладка клапанной крышки", "Регулировка клапанов",
        "Подушки двигателя", "Сальники коленвала", "Дроссельная заслонка (чистка)",
        "Форсунки (чистка)", "Топливный насос", "Лямбда-зонд",
        # ГРМ и ремни
        "Ремень ГРМ", "Ролик натяжителя ГРМ", "Цепь ГРМ", "Помпа",
        "Приводной ремень", "Ролик натяжителя приводного ремня", "Ремень генератора",
        # охлаждение и жидкости
        "Антифриз", "Термостат", "Радиатор", "Патрубки системы охлаждения",
        "Тормозная жидкость", "Жидкость ГУР", "Омывающая жидкость", "AdBlue",
        # трансмиссия
        "Масло КПП", "Масло АКПП", "Фильтр АКПП", "Масло вариатора", "Масло в раздатке",
        "Масло в редукторе моста", "Сцепление", "Выжимной подшипник", "Маховик",
        "Подушка КПП", "Пыльники ШРУС", "ШРУС наружный", "ШРУС внутренний",
        "Крестовины кардана", "Подвесной подшипник кардана",
        # тормоза
        "Тормозные колодки передние", "Тормозные колодки задние",
        "Тормозные диски передние", "Тормозные диски задние", "Тормозные барабаны",
        "Колодки стояночного тормоза", "Тросы стояночного тормоза", "Тормозные шланги",
        # подвеска и рулевое
        "Амортизаторы передние", "Амортизаторы задние", "Опоры амортизаторов",
        "Пружины подвески", "Сайлентблоки", "Шаровые опоры", "Стойки стабилизатора",
        "Втулки стабилизатора", "Рулевые тяги", "Рулевые наконечники",
        "Ступичный подшипник", "Развал-схождение",
        # шины, электрика, прочее
        "Шины летние", "Шины зимние", "Сезонная смена шин", "Аккумулятор",
        "Щётки стеклоочистителя", "Лампы фар", "Стартер", "Генератор",
        "Заправка кондиционера", "Фильтр-осушитель кондиционера",
        "Гофра глушителя", "Глушитель", "Катализатор", "Сажевый фильтр",
    ],
    "en": [
        # engine and filters
        "Engine oil", "Oil filter", "Air filter", "Cabin filter", "Fuel filter",
        "Spark plugs", "Glow plugs", "Ignition coil", "Spark plug wires",
        "Valve cover gasket", "Valve adjustment", "Engine mounts", "Crankshaft seals",
        "Throttle body (cleaning)", "Fuel injectors (cleaning)", "Fuel pump",
        "Oxygen sensor",
        # timing and belts
        "Timing belt", "Timing belt tensioner", "Timing chain", "Water pump",
        "Serpentine belt", "Serpentine belt tensioner", "Alternator belt",
        # cooling and fluids
        "Coolant", "Thermostat", "Radiator", "Coolant hoses", "Brake fluid",
        "Power steering fluid", "Washer fluid", "AdBlue",
        # drivetrain
        "Manual transmission oil", "Automatic transmission fluid",
        "Automatic transmission filter", "CVT fluid", "Transfer case oil",
        "Differential oil", "Clutch", "Clutch release bearing", "Flywheel",
        "Transmission mount", "CV boots", "Outer CV joint", "Inner CV joint",
        "Driveshaft U-joints", "Driveshaft center bearing",
        # brakes
        "Front brake pads", "Rear brake pads", "Front brake discs", "Rear brake discs",
        "Brake drums", "Parking brake shoes", "Parking brake cables", "Brake hoses",
        # suspension and steering
        "Front shock absorbers", "Rear shock absorbers", "Strut mounts", "Coil springs",
        "Control arm bushings", "Ball joints", "Sway bar links", "Sway bar bushings",
        "Tie rods", "Tie rod ends", "Wheel bearing", "Wheel alignment",
        # tires, electrical, other
        "Summer tires", "Winter tires", "Seasonal tire change", "Battery",
        "Wiper blades", "Headlight bulbs", "Starter", "Alternator",
        "A/C recharge", "A/C receiver drier", "Exhaust flex pipe", "Muffler",
        "Catalytic converter", "Diesel particulate filter",
    ],
}


def suggestions(lang: str, own: list[str]) -> list[str]:
    """Сначала детали пользователя, затем справочник без повторов."""
    seen = {name.casefold() for name in own}
    return list(own) + [n for n in PARTS.get(lang, PARTS["en"]) if n.casefold() not in seen]
