# Запуск NaturalAGI на Windows і слабкому ноутбуці

Для машин рівня: 8 ГБ RAM, Intel i3 (2 ядра / 4 потоки), 8–15 ГБ вільного диска, Windows 10/11.
Відеокарта не використовується взагалі.

Коротко: проєкт запускається **тільки через WSL2** (Linux всередині Windows). `nuctl`, яким деплояться функції,
не має Windows-версії. Усе інше робить профіль `lowspec` у Makefile: один інстанс кожної функції, урізана пам'ять
Neo4j і Kafka, без Nuclio dashboard / Postgres / MLflow, збірка образів по одному і на `python:3.12-slim`.

## 0. Скільки це займе

| що | диск | RAM під час роботи |
|---|---|---|
| Ubuntu у WSL2 + інструменти | ~2 ГБ | ~0.3 ГБ |
| Образи Neo4j + Kafka | ~1.5 ГБ | ~1.9 ГБ |
| Базовий образ + 5 функцій | ~2.5 ГБ | ~1.5–2 ГБ |
| Репозиторій + датасет | ~0.5 ГБ | — |
| **Разом** | **~7 ГБ** | **~4–4.5 ГБ** |

Перша збірка на i3 триває 20–40 хвилин. Далі старт займає 1–2 хвилини.

Якщо на диску C: менше 10 ГБ вільного, перенесіть WSL на інший диск (крок 1.3) або почистіть C: перед стартом.

## 1. Одноразове налаштування Windows

### 1.1. Встановити WSL2 з Ubuntu

PowerShell від адміністратора:

```powershell
wsl --install -d Ubuntu-24.04
```

Перезавантажити комп'ютер, відкрити «Ubuntu» з меню Пуск, задати ім'я користувача і пароль.

### 1.2. Обмежити пам'ять WSL

Створити файл `C:\Users\<ваше_ім'я>\.wslconfig`:

```ini
[wsl2]
memory=5GB
processors=4
swap=4GB
```

При 8 ГБ фізичної пам'яті це залишає Windows ~3 ГБ. Під час роботи з пайплайном **закрийте браузер з багатьма
вкладками**, інакше система почне свопитись і «фризити». Застосувати налаштування:

```powershell
wsl --shutdown
```

### 1.3. (Якщо мало місця на C:) Перенести Ubuntu на інший диск

```powershell
wsl --shutdown
wsl --manage Ubuntu-24.04 --move D:\wsl\ubuntu
```

Якщо команда `--manage` не підтримується (старий WSL), спершу `wsl --update`.

### 1.4. Docker Desktop не потрібен

Скрипт нижче ставить Docker Engine всередину Ubuntu. Це економить ~1.5 ГБ RAM порівняно з Docker Desktop. Якщо
Docker Desktop уже встановлено, закрийте його (іконка в треї → Quit), щоб не було двох Docker одночасно.

## 2. Одноразове налаштування всередині Ubuntu

Усі команди далі виконуються у вікні Ubuntu, **не** в PowerShell.

```bash
cd ~
git clone https://github.com/kbokh/NaturalAG.git NaturalAGI
cd NaturalAGI
bash scripts/setup_wsl.sh
```

Важливо: клонуйте в домашню теку Ubuntu (`~`), а не в `/mnt/c/...`. Робота з диском Windows у 5–10 разів
повільніша і ламає переноси рядків.

Скрипт встановлює Docker, `nuctl`, `uv`, `make`, вмикає systemd і створює файл `local.mk` з рядком
`PROFILE = lowspec`. Після цього всі `make`-команди автоматично працюють у легкому режимі.

Якщо скрипт у кінці попросить, виконайте в PowerShell `wsl --shutdown`, знову відкрийте Ubuntu і
`cd ~/NaturalAGI`.

## 3. Перевірка

```bash
make doctor
```

Має показати `PROFILE=lowspec`, знайдений `HOST_IP`, `docker daemon: running`, `compose config: valid`,
RAM ≥ 5 ГБ і достатньо місця. Якщо `HOST_IP` не знайдено: `hostname -I`, взяти першу адресу і додати в
`local.mk` рядок `HOST_IP = <адреса>`.

## 4. Запуск

```bash
make unpack_dataset       # один раз
make start_services       # Neo4j + Kafka (~1 хв)
make create_kafka_topics
make deploy               # збирає і деплоїть 5 функцій по одній (перший раз 20–40 хв)
```

Або все одразу: `make`.

Перевірити, що функції живі: `nuctl get functions --platform local`. Neo4j Browser: http://localhost:7474.

## 5. Python-оточення для ноутбуків

```bash
uv venv natural-agi --python 3.12
source natural-agi/bin/activate
uv sync --extra dev
```

Групу `ml` (PyTorch) не ставте без потреби. На Linux `pip install torch` за замовчуванням тягне CUDA-збірку
на ~2.5 ГБ. Якщо PyTorch потрібен, ставте CPU-версію:

```bash
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

MLflow-сервер у цьому профілі не запускається. Скрипти оцінки пишуть результати в локальну теку `mlruns/`
(змінна `MLFLOW_TRACKING_URI=file:./mlruns` вже додана скриптом у `~/.bashrc`).

## 6. Що реально можна робити на такій машині

- Прогнати скелетизацію й аналіз контуру на окремих картинках і подивитись графи в Neo4j.
- Навчити концепти на малій вибірці і класифікувати **десятки–сотні** зображень.
- Не варто: повний тест EMNIST (20 800 зображень) — на одному інстансі класифікації це години.

## 7. Зупинка і звільнення пам'яті

```bash
docker compose -f docker-compose.yaml -f docker-compose.lowspec.yaml stop   # зупинити Neo4j + Kafka
docker stop $(docker ps -q --filter name=nuclio-)                          # зупинити функції
```

Повністю звільнити RAM Windows: у PowerShell `wsl --shutdown`.

Звільнити диск після експериментів: `make docker_clean`.

## 8. Якщо щось пішло не так

| симптом | причина і що робити |
|---|---|
| Система «фризить» під час `make deploy` | Мало RAM. Закрити браузер, перевірити `.wslconfig`, `DEPLOY_PARALLELISM` має бути 1 (`make doctor`). |
| `nuctl: command not found` | Не відпрацював `scripts/setup_wsl.sh`, або команда запущена в PowerShell замість Ubuntu. |
| `permission denied ... docker.sock` | Закрити й відкрити термінал Ubuntu після setup (група `docker`). |
| `Cannot connect to the Docker daemon` | `sudo systemctl start docker` (або `sudo service docker start`). |
| Функції не бачать Kafka / Neo4j після перезапуску | Змінилась IP-адреса WSL. `make doctor`, потім `make deploy` заново. |
| `/bin/bash^M: bad interpreter` | Репозиторій склоновано у Windows. Клонувати заново всередині Ubuntu. |
| `no space left on device` | `make docker_clean`, `docker system df`; перенести WSL на інший диск (крок 1.3). |

Будь-яке налаштування профілю можна перевизначити без зміни файлів, наприклад:

```bash
make deploy INSTANCES_CLASSIFICATION=2
```
