## Подготовка головного MikroTik к новой площадке (MGMT-only)

---

## 1. Сгенерировать WireGuard-ключи для филиала

На любом Linux/WSL/Unix‑хосте с установленным WireGuard:

```bash
wg genkey | tee SITE123.private | wg pubkey > SITE123.public
```

### Краткая таблица

| Сторона | Тип ключа   | Где генерим / берём                     | Куда подставляем                       |
|--------|-------------|-----------------------------------------|----------------------------------------|
| Филиал | private key | `wg genkey` → `SITE123.branch.priv`    | `BR_WG_PRIV` → `private-key` wg-mgmt   |
| Филиал | public key  | `wg pubkey` → `SITE123.branch.pub`     | `public-key` peer на HQ (wg-hub)       |
| HQ     | private key | Уже на HQ, в интерфейсе `wg-hub`       | НИКОГДА не уходит в шаблоны филиала    |
| HQ     | public key  | `interface wireguard print` (wg-hub)   | `HQ_WG_PUB` → `public-key` peer на филиале |

---

## 2. Добавить peer филиала на головном MikroTik

```routeros
/interface wireguard peers
add interface=wg-hub \
    public-key="SITE123_PUBLIC_KEY" \
    allowed-address=10.255.0.123/32 \
    comment="SITE123 MGMT-only"
```

Где:
- `interface=wg-hub` — существующий WireGuard-интерфейс на HQ (шлюз MGMT).
- `public-key` — содержимое файла `SITE123.public`.
- `allowed-address=10.255.0.123/32` — **WG IP роутера филиала**.
- `comment="SITE123 MGMT-only"` — для быстрых поисков и аудита.

Проверка, что peer добавлен корректно:

```routeros
/interface wireguard peers print detail where comment~"SITE123"
```

---

## 3. Алгоритм для сотрудника на новой площадке

1. Ноут → LAN-порт MikroTik.
2. WinBox Neighbors → MAC → admin/пустой пароль.
3. Files → drag `.rsc`.
4. Terminal: `/import file-name=SITE123_DHCP.rsc`
5. Кабель провайдера → ether1.
6. Пинг 1.1.1.1 (проверить интернет).

**Инженер HQ**: Подключиться с WinBox по WG-IP → настроить IPsec → отключить WG-пир на роутере HQ