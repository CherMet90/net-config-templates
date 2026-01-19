# Changelog

Все значимые изменения этого проекта будут документироваться в этом файле.

## [0.1.0] - 2026-01-19
### Added
- Начальная структура проекта:
  - `templates/mikrotik/routeros-7.x/*` — шаблоны для bootstrap-конфига и WAN-вариантов.
  - `templates/cisco/ios-xe/ipsec-to-mikrotik.j2` — шаблон IPsec-туннеля к MikroTik.
  - `inventory/sites.yml` — заготовка под инвентарь площадок.
  - `docs/` — базовая документация.
- Скрипт `tools/render-template-interactive.py`:
  - интерактивный рендер Jinja2-шаблонов;
  - автоопределение типов вводимых значений (int/float/bool/list/json/str);
  - поддержка префиксов `:json`, `:list`, `:dict`;
  - чтение default-значений из фильтра `| default(...)` в шаблонах и вывод их пользователю;
  - сохранение (`--dump-context`) и загрузка (`--context`) JSON-контекста.
- Документация по использованию интерактивного рендера:  
  `docs/how-to-use-interactive-renderer.md`.
