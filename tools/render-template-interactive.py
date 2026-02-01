#!/usr/bin/env python3
"""
Универсальный интерактивный рендерер Jinja2-шаблонов с поддержкой YAML-docstring.
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from typing import Any, Dict, Optional, Set

import yaml
from jinja2 import Environment, FileSystemLoader, meta, nodes
from ipaddress import ip_address, ip_network


class VarMeta:
    def __init__(self, desc: str = "", type: str = "str", required: bool = False,
                 default: Any = None, example: str = ""):
        self.desc = desc
        self.type = type.lower()
        self.required = required
        self.default = default
        self.example = example


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Интерактивный рендерер Jinja2-шаблонов с поддержкой YAML-docstring"
    )
    parser.add_argument("template", help="Путь к шаблону")
    parser.add_argument("-o", "--output", help="Файл вывода")
    parser.add_argument("--dump-context", help="Сохранить контекст в JSON")
    parser.add_argument("--context", help="Загрузить контекст из JSON")
    return parser.parse_args()

def load_template_env(template_path: str):
    template_abs = os.path.abspath(template_path)
    template_dir = os.path.dirname(template_abs)
    template_name = os.path.basename(template_abs)
    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env, template_dir, template_name

def extract_yaml_header(source: str) -> Optional[Dict[str, Any]]:
    """Ищет блок {#--- ... ---#} в начале шаблона."""
    pattern = re.compile(r"{#---\n(.*?)\n---#}", re.DOTALL)
    match = pattern.search(source)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        print(f"Warning: Ошибка парсинга YAML-header: {e}", file=sys.stderr)
        return None

def get_template_defaults(env: Environment, template_name: str) -> Dict[str, Any]:
    """Извлекает значения из | default(...) — оставляем как fallback."""
    source = env.loader.get_source(env, template_name)[0]
    parsed = env.parse(source)
    defaults: Dict[str, Any] = {}

    def walk(node: nodes.Node):
        if isinstance(node, nodes.Filter) and node.name == "default":
            if isinstance(node.node, nodes.Name) and node.args and isinstance(node.args[0], nodes.Const):
                defaults[node.node.name] = node.args[0].value
        for field in node.fields:
            value = getattr(node, field, None)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, nodes.Node):
                        walk(item)
            elif isinstance(value, nodes.Node):
                walk(value)

    walk(parsed)
    return defaults

def validate_and_cast(value: str, var_type: str) -> Any:
    """Простая валидация и приведение типов."""
    value = value.strip()
    if value == "" and var_type != "str":
        return None

    if var_type == "int":
        return int(value)
    elif var_type == "bool":
        return value.lower() in ("true", "yes", "y", "1", "on")
    elif var_type == "ip":
        return ip_address(value)
    elif var_type == "cidr":
        return ip_network(value)
    elif var_type.startswith("list"):
        return [item.strip() for item in value.split(",") if item.strip()]
    else:  # str и неизвестные
        return value

def prompt_with_meta(name: str, meta: VarMeta) -> Any:
    example = f" (пример: {meta.example})" if meta.example else ""
    default_hint = f" [{meta.default!r}]" if meta.default is not None else ""
    prompt = f"{meta.desc or name}{example}{default_hint}: "

    while True:
        raw = input(prompt).strip()
        if raw == "" and meta.default is not None:
            return meta.default
        if raw == "" and not meta.required:
            return None

        try:
            value = validate_and_cast(raw, meta.type)
            return value
        except Exception as e:
            print(f"Некорректное значение для типа '{meta.type}': {e}")

def prompt_auto_fallback(name: str, default: Optional[Any] = None):
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

def main() -> None:
    args = parse_args()
    env, template_dir, template_name = load_template_env(args.template)

    source = env.loader.get_source(env, template_name)[0]
    yaml_meta = extract_yaml_header(source)
    template_defaults = get_template_defaults(env, template_name)

    # Загружаем внешний контекст
    context: Dict[str, Any] = {}
    if args.context:
        with open(args.context, "r", encoding="utf-8") as f:
            context = json.load(f)

    # Определяем переменные и их метаданные
    vars_meta: OrderedDict[str, VarMeta] = OrderedDict()
    undeclared = meta.find_undeclared_variables(env.parse(source))

    if yaml_meta and "vars" in yaml_meta:
        print("Обнаружен YAML-docstring → используем расширенный режим")
        for var_name, var_info in yaml_meta["vars"].items():
            vars_meta[var_name] = VarMeta(
                desc=var_info.get("desc", ""),
                type=var_info.get("type", "str"),
                required=var_info.get("required", False),
                default=var_info.get("default"),
                example=var_info.get("example", "")
            )
        # Добавляем переменные, которые есть в шаблоне, но не описаны в YAML
        for v in undeclared:
            if v not in vars_meta:
                vars_meta[v] = VarMeta()
    else:
        print("YAML-docstring не найден → старый режим")
        for v in sorted(undeclared):
            vars_meta[v] = VarMeta(default=template_defaults.get(v))

    # Интерактивный ввод
    for var_name, var_meta in vars_meta.items():
        if var_name in context:
            print(f"'{var_name}' уже задан в --context → пропуск")
            continue

        default_val = context.get(var_name) or var_meta.default or template_defaults.get(var_name)

        if yaml_meta and "vars" in yaml_meta:
            value = prompt_with_meta(var_name, var_meta)
        else:
            value, _ = prompt_auto_fallback(var_name, default=default_val)

        if value is not None or var_meta.required:
            context[var_name] = value

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