#!/usr/bin/env python3
"""
Универсальный интерактивный рендерер Jinja2-шаблонов.

Примеры:
  python tools/render-template-interactive.py templates/cisco/ios-xe/ipsec-to-mikrotik.j2
  python tools/render-template-interactive.py templates/mikrotik/routeros-7.x/bootstrap.rsc.j2 -o out.rsc
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Optional, Set

from jinja2 import Environment, FileSystemLoader, meta, nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Интерактивный рендерер Jinja2-шаблонов "
                    "(спрашивает значения переменных и генерирует вывод)"
    )
    parser.add_argument(
        "template",
        help="Путь к Jinja2-шаблону (например templates/cisco/ios-xe/ipsec-to-mikrotik.j2)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Файл для записи результата. Если не указан — печать в stdout.",
    )
    parser.add_argument(
        "--dump-context",
        help="Сохранить введённые переменные в JSON-файл (для повторного использования).",
    )
    parser.add_argument(
        "--context",
        help="Загрузить контекст из JSON-файла (частично/полностью заполнить переменные).",
    )
    return parser.parse_args()


def load_template_env(template_path: str) -> tuple[Environment, str, str]:
    """
    Возвращает:
      env         - Jinja2 Environment
      template_dir- каталог с шаблоном
      template_name - имя шаблона внутри каталога
    """
    template_abs = os.path.abspath(template_path)
    template_dir = os.path.dirname(template_abs)
    template_name = os.path.basename(template_abs)

    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env, template_dir, template_name


def get_undeclared_variables(env: Environment, template_name: str) -> Set[str]:
    """
    Возвращает множество имен переменных, которые используются в шаблоне
    и не имеют значений по умолчанию в самом шаблоне.
    """
    source = env.loader.get_source(env, template_name)[0]
    parsed_ast = env.parse(source)
    return meta.find_undeclared_variables(parsed_ast)

def get_default_values(env: Environment, template_name: str) -> Dict[str, Any]:
    """
    Проходит по AST шаблона и пытается найти конструкции вида:
      {{ var | default(123) }}
      {{ var | default("text") }}
      {{ var | default(true) }}

    Возвращает dict: { 'var_name': default_value, ... }

    Ограничения:
      - работает для простых случаев: Name|default(Const)
      - игнорирует сложные выражения.
    """
    source = env.loader.get_source(env, template_name)[0]
    parsed = env.parse(source)

    defaults: Dict[str, Any] = {}

    def walk(node: nodes.Node):
        # ищем фильтры (Filter node)
        if isinstance(node, nodes.Filter):
            if node.name == "default":
                # node.node — то, к чему применяется фильтр,
                # ожидаем Name (переменная)
                if isinstance(node.node, nodes.Name):
                    var_name = node.node.name

                    # args[0] — первый аргумент default(...)
                    if node.args and isinstance(node.args[0], nodes.Const):
                        defaults[var_name] = node.args[0].value

        # рекурсивный обход всех полей-children
        for field_name in node.fields:
            value = getattr(node, field_name, None)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, nodes.Node):
                        walk(item)
            elif isinstance(value, nodes.Node):
                walk(value)

    walk(parsed)
    return defaults

def prompt_scalar(name: str) -> Any:
    """
    Спрашивает у пользователя простое значение (строка/число/bool),
    пытается аккуратно привести тип.
    """
    while True:
        raw = input(f"Значение для '{name}' (строка/число/bool): ").strip()

        # Пустую строку считаем пустой строкой (а не None)
        if raw == "":
            return ""

        # bool
        lower = raw.lower()
        if lower in ("true", "false", "yes", "no", "y", "n"):
            return lower in ("true", "yes", "y")

        # int
        try:
            return int(raw)
        except ValueError:
            pass

        # float
        try:
            return float(raw)
        except ValueError:
            pass

        # строка
        return raw


def prompt_list(name: str) -> Any:
    """
    Запрос списка значений: либо простых, либо словарей.
    Простейший интерактивный формат:
      - сначала спросим, список чего: 'scalar' или 'dict'
    """
    print(f"\n=== Ввод списка для переменной '{name}' ===")
    item_type = ""
    while item_type not in ("scalar", "dict"):
        item_type = input(
            "Тип элементов списка ('scalar' или 'dict') [scalar]: "
        ).strip().lower() or "scalar"

    items = []
    idx = 1
    while True:
        cont = input(f"Добавить элемент #{idx}? [y/N]: ").strip().lower()
        if cont not in ("y", "yes"):
            break

        if item_type == "scalar":
            items.append(prompt_scalar(f"{name}[{idx - 1}]"))
        else:
            # dict
            print(f"Ввод полей словаря для элемента #{idx}. "
                  "Пустое имя ключа — завершить ввод этого словаря.")
            obj: Dict[str, Any] = {}
            while True:
                key = input("  Имя поля (пусто — закончить этот элемент): ").strip()
                if key == "":
                    break
                value = prompt_scalar(f"{name}[{idx - 1}].{key}")
                obj[key] = value
            items.append(obj)

        idx += 1

    return items


def prompt_value(name: str) -> Any:
    """
    Предлагает ввести тип: scalar | list | json
    - scalar: единичное значение
    - list:   список
    - json:   произвольная структура в формате JSON одной строкой
    """
    print(f"\nПеременная: {name}")
    while True:
        mode = input(
            "Тип значения ('scalar', 'list', 'json') [scalar]: "
        ).strip().lower() or "scalar"

        if mode == "scalar":
            return prompt_scalar(name)
        if mode == "list":
            return prompt_list(name)
        if mode == "json":
            raw = input(
                "Введите JSON-значение (одной строкой, например "
                "'{\"a\": 1, \"b\": [1,2]}' ): "
            )
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"Ошибка JSON: {e}")
                continue

        print("Неизвестный тип. Разрешены: scalar, list, json.")

def prompt_auto(name: str, default: Optional[Any] = None):
    """
    Просит одно значение, пытается понять тип автоматически.
    Спец-префиксы:
      :json  <JSON>
      :list  a,b,c
      :dict  k1=val1 k2=val2

    Если default не None, показываем его пользователю.
    Пустой ввод -> (None, True) — переменная не попадает в контекст.
    """
    if default is not None:
        prompt = f"Значение для '{name}' [{default!r}]: "
    else:
        prompt = f"Значение для '{name}': "

    raw = input(prompt).strip()

    # 1. user pressed Enter -> пустое значение
    if raw == "":
        return None, True      # is_empty=True

    # 2. forced modes
    if raw.startswith(":json "):
        return json.loads(raw[6:].strip()), False
    if raw.startswith(":list "):
        return [x.strip() for x in raw[6:].split(",") if x.strip()], False
    if raw.startswith(":dict "):
        kv = [p.split("=", 1) for p in raw[6:].split()]
        return {k: v for k, v in kv}, False

    # 3. auto detect (bool/int/float/list/json/str)
    lower = raw.lower()
    if lower in ("true", "false", "yes", "no", "on", "off"):
        return lower in ("true", "yes", "on"), False

    if re.fullmatch(r"\d+", raw):
        return int(raw), False

    if re.fullmatch(r"\d+\.\d+", raw):
        return float(raw), False

    if "," in raw:
        return [x.strip() for x in raw.split(",") if x.strip()], False

    if (raw.startswith("{") and raw.endswith("}")) or \
       (raw.startswith("[") and raw.endswith("]")):
        try:
            return json.loads(raw), False
        except json.JSONDecodeError:
            pass

    return raw, False          # default → str

def load_context_from_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    args = parse_args()

    env, template_dir, template_name = load_template_env(args.template)
    undeclared = get_undeclared_variables(env, template_name)
    template_defaults = get_default_values(env, template_name)

    # Базовый контекст (из файла, если указан)
    context: Dict[str, Any] = {}
    if args.context:
        if not os.path.isfile(args.context):
            print(f"Файл контекста не найден: {args.context}", file=sys.stderr)
            sys.exit(1)
        print(f"Загружаю контекст из {args.context}")
        context = load_context_from_file(args.context)

    print(f"Шаблон:        {args.template}")
    print(f"Переменные:    {', '.join(sorted(undeclared)) or '(нет)'}")

    # Спросим только те переменные, у которых нет значения в context
    for var in sorted(undeclared):
        if var in context:
            print(
                f"\nПеременная '{var}' уже задана в context, "
                f"пропускаю (значение: {context[var]!r})"
            )
            continue
        
        default_val = template_defaults.get(var)  # может быть None

        val, is_empty = prompt_auto(var, default=default_val)
        if is_empty:
            # пользователь нажал Enter → не добавляем в context
            # Jinja2 сможет взять default из шаблона
            continue
        context[var] = val

    # Можно сохранить контекст на будущее
    if args.dump_context:
        with open(args.dump_context, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
        print(f"\nКонтекст сохранён в {args.dump_context}")

    # Рендер
    template = env.get_template(template_name)
    result = template.render(**context)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\nРезультат записан в {args.output}")
    else:
        print("\n===== Сгенерированный вывод =====\n")
        print(result)


if __name__ == "__main__":
    main()