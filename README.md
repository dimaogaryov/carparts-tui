# CarParts TUI

Terminal app for tracking the service life of car parts and consumables, styled after retro terminals 

TUI-приложение для контроля ресурса запчастей и расходников автомобиля. English and Russian UI.

![dashboard](docs/dashboard.svg)

## Features

- You log what was replaced and set the interval: kilometres, days, or both.
  Remaining life is computed per criterion; the one that runs out first wins
  (e.g. coolant is due after a year even with low mileage).
- Yellow / red thresholds per part (40 % / 15 % by default). Critical parts blink
  ⚠⚠ three times every 10 seconds; overdue parts pop up a modal after a mileage entry.
- Up to 5 cars, mileage and replacement history, stats with a forecast of the next replacement.
- Part name autocomplete from a built-in catalogue (~80 common parts, EN/RU).
- Sort parts by remaining life, name or replacement date.
- Export history to Markdown or JSON.
- Follows any Textual theme (`Ctrl+P` → theme); the default is a green phosphor theme.
- Vim keys (`hjkl`), and all hotkeys also work in the Russian keyboard layout.

## Install

Requires Python 3.11+ and Linux (other platforms are untested).

```sh
git clone https://github.com/dimaogaryov/carparts-tui.git
cd carparts-tui
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/carparts
```

## Keys

| Key | Action |
|---|---|
| `↑↓` / `jk` | move between parts |
| `Enter` | repeat replacement of the selected part (new mileage, same intervals) |
| `r` | new replacement |
| `d` | delete part |
| `m` | quick mileage entry |
| `o` | sort: life → name → replacement date |
| `h` / `s` | toggle history / stats panel |
| `h` then `e` | export history (Markdown / JSON) |
| `h` then `c` | clear history |
| `x` | menu: correct mileage, add/delete car, language… |
| `c` | switch car |
| `Ctrl+P` | command palette (themes) |
| `q` | quit |

In dialogs: `←→` / `hl` switch buttons, `↑↓` move between fields, `Esc` cancels.

## Data

- Cars and history: `$XDG_DATA_HOME/carparts/data.json` (`~/.local/share/carparts/data.json`)
- Settings (language, theme, sort): `$XDG_CONFIG_HOME/carparts/config.json`

## Development

```sh
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

## License

[MIT](LICENSE)
