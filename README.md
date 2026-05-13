# English Learning Telegram Bot

Telegram бот для заучування англійських слів методом флеш-карток.

## Як користуватися

1. `/start` — почати
2. Надіслати Excel файл (.xlsx) з двома колонками: A — англійське слово, B — переклад
3. Натиснути **Почати**
4. Для кожного слова натискати **✅ Знаю** або **❌ Не знаю**
   - **Знаю** → слово отримує +1 до лічильника і показується наступне
   - **Не знаю** → показується переклад і одразу нове слово (без штрафу)
5. Слова показуються від найменш відомих до найбільш відомих (за лічильником)
6. `/stats` — переглянути статистику

## Встановлення на Ubuntu

### Вимоги
- Python 3.10+
- MySQL 8+

### 1. Клонувати репозиторій
```bash
git clone git@github.com:kramar-alexandr/english_bot.git /opt/english_bot
cd /opt/english_bot
```

### 2. Встановити залежності
```bash
pip3 install -r requirements.txt
```

### 3. Налаштувати .env
```bash
cp .env.example .env
nano .env  # заповнити BOT_TOKEN і DB_PASSWORD
```

### 4. Налаштувати базу даних
```bash
chmod +x scripts/*.sh
./scripts/setup_db.sh
```

### 5. Встановити як системний сервіс
```bash
sudo cp scripts/english_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable english_bot
sudo systemctl start english_bot
```

### Перевірити статус
```bash
sudo systemctl status english_bot
journalctl -u english_bot -f
```

## Скрипти

| Скрипт | Опис |
|--------|------|
| `scripts/setup_db.sh` | Створити БД та користувача MySQL (один раз) |
| `scripts/clean_db.sh` | Очистити дані (всіх або одного користувача) |
| `scripts/deploy.sh` | Оновити код і перезапустити сервіс |

## Змінні середовища (.env)

| Змінна | Опис | За замовчуванням |
|--------|------|-----------------|
| `BOT_TOKEN` | Токен Telegram бота (від @BotFather) | — |
| `DB_HOST` | Хост MySQL | `localhost` |
| `DB_USER` | Користувач MySQL | `root` |
| `DB_PASSWORD` | Пароль MySQL | — |
| `DB_NAME` | Назва бази даних | `english_bot` |
| `RANDOMIZER_POOL` | Кількість слів у пулі рандомайзера | `10` |
