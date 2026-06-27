# Frontend Modes

This branch now treats the UI layer as two entry points over one shared core:

## Desktop mode

- File: `desktop_app.py`
- Behavior: always-on-top desktop control window
- Goal: provider switching, rollback, status, and command bridge
- Suggested use: local operator control

Run:

```bash
python desktop_app.py
```

For a desktop launch without a console window, use `desktop_app.pyw`
or `pythonw.exe desktop_app.pyw` on Windows.

## QQ bot mode

- File: `qq_bot.py`
- Behavior: text-command message bridge
- Goal: receive short commands and forward them to the shared core
- Suggested use: remote control by message only

Run:

```bash
python qq_bot.py
```

## Shared command set

- `status`
- `rollback`
- `refresh`
- `history`
- `clear`
- `provider github`
- `provider deepseek`
- `uid <value>`

## Design rule

- Desktop handles richer interaction and configuration
- QQ bot stays command-only and does not try to own the UI
- Core state and rollback remain shared
