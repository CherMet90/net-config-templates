# Интерактивный генератор конфигураций (render-template-interactive.py)

Инструмент позволяет быстро сгенерировать конфигурацию из любого Jinja2-шаблона,  
задавая значения переменных в интерактивном режиме.

## Основные возможности

- Автоматически определяет все переменные, которые используются в шаблоне
- Показывает значения по умолчанию, если они прописаны в шаблоне через `| default(...)`
- Пустой ввод (Enter) → переменная **не передаётся** в контекст → срабатывает default из шаблона
- Автоопределение типов значений (bool, int, float, list, dict/json, str)
- Поддержка форсированного ввода типов через префиксы `:json`, `:list`, `:dict`
- Возможность сохранить введённые значения в JSON для повторного использования
- Поддержка загрузки ранее сохранённого контекста (`--context`)

## Быстрый старт

```bash
# Самый простой запуск (всё в stdout)
python tools/render-template-interactive.py \
  templates/cisco/ios-xe/ipsec-to-mikrotik.j2
```

```bash
# Сохранить результат в файл + сохранить контекст для будущего использования
python tools/render-template-interactive.py \
  templates/mikrotik/routeros-7.x/bootstrap.rsc.j2 \
  -o output/SITE999_bootstrap.rsc \
  --dump-context inventory/SITE999_context.json
```

```bash
# Повторно использовать сохранённый контекст
python tools/render-template-interactive.py \
  templates/mikrotik/routeros-7.x/bootstrap.rsc.j2 \
  --context inventory/SITE999_context.json \
  -o output/SITE999_new.rsc
```

## Как отвечать на вопросы скрипта

| Ввод пользователя                                 | Что произойдёт                                      | Тип результата     |
|----------------------------------------------------|------------------------------------------------------|--------------------|
| `Enter` (пустая строка)                            | Переменная **не** попадёт в контекст                | — (default шаблона) |
| `1376`                                             | Целое число                                         | `int`              |
| `3.14`                                             | Число с плавающей точкой                            | `float`            |
| `true` / `yes` / `on`                              | Булево `true`                                       | `bool`             |
| `false` / `no` / `off`                             | Булево `false`                                      | `bool`             |
| `192.168.1.1,10.0.0.1,172.16.0.1`                 | Список строк через запятую                          | `list[str]`        |
| `{"peer": "MTK1", "prio": 100}`                    | JSON-объект (автоопределение)                       | `dict`             |
| `:json {"name":"SITE1", "id":42}`                  | Принудительный JSON                                 | `dict` / `list`    |
| `:list vlan10, vlan20, vlan777`                    | Принудительный список строк                         | `list[str]`        |
| `:dict role=core prio=100 location=KZ01`           | Принудительный словарь (пары ключ=значение)         | `dict[str,str]`    |

## Пример диалога

```text
Шаблон:        templates/cisco/ios-xe/ipsec-to-mikrotik.j2
Переменные:    description, fvrf_name, ipsec_profile_name, peer_ip, peer_public_ip, psk, tcp_mss, tunnel_if, tunnel_ip, tunnel_mask, tunnel_mtu, tunnel_source_if

Переменная: fvrf_name
Значение для 'fvrf_name' (Enter = оставить пустым / default из шаблона): FVRF-INET

Переменная: tunnel_mtu
Значение для 'tunnel_mtu' [default: 1376] (Enter = использовать default): 

  → пропуск (будет использован default из шаблона, если он есть)

Переменная: description
Значение для 'description' [default: 'IPsec to MikroTik SITE'] (Enter = использовать default): IPsec SITE999 → HQ

...
```

## Рекомендации по шаблонам

Чтобы интерактивный режим работал максимально удобно, в шаблонах рекомендуется:

```jinja
# Хорошо
ip mtu {{ tunnel_mtu | default(1376) }}
description {{ description | default("IPsec tunnel to remote site") }}

# Очень хорошо (самодокументирующийся шаблон)
{# tunnel_mtu — MTU туннельного интерфейса, обычно 1376–1400 #}
ip mtu {{ tunnel_mtu | default(1376) }}

# Плохо (без default пользователь будет вынужден вводить всегда)
ip mtu {{ tunnel_mtu }}
```

## Текущие ограничения

- Распознаются только простые `| default(константа)`  
  (сложные выражения типа `| default(another_var * 2)` пока не поддерживаются)
- Сложные вложенные структуры списков/словарей удобнее всего вводить через `:json`
