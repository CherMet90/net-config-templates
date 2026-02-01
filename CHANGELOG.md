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
<think>**Thinking about the user's request**

## [0.2.0] - 2026-02-01
### Added
- Шаблоны BGP для MikroTik RouterOS 7.x
- Шаблоны BGP для Cisco IOS-XE

## [0.2.1] - 2026-02-01
### Added
- Документация по настройке BGP для Cisco IOS-XE и Mikrotik ROS7

## [0.3.0] - 2026-02-01
### Added
- Поддержка **YAML-docstring** в шаблонах:
  - Все BGP-шаблоны (Cisco и MikroTik) переработаны с декларативным YAML-header в начале файла.
  - Формат позволяет описывать переменные, их типы, обязательность, значения по умолчанию, примеры и описания.
- Обновлён интерактивный рендерер `tools/render-template-interactive.py`:
  - Автоматический парсинг YAML-docstring.
  - Улучшенный UX: вывод описаний, примеров, валидация типов (int, ip, cidr, list и т.д.), проверка обязательных полей.
  - Полная обратная совместимость с шаблонами без YAML-header.

## [0.3.1] - 2026-02-01
### Added
- Обновлена документация по работе с интерактивным рендером
