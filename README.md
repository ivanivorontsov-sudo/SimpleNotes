# SimpleNotes — Простая программа для заметок

Лёгкая десктопная программа для создания и хранения заметок на Windows (и других ОС).

## Возможности

- Создание, редактирование и удаление заметок
- Поиск по заголовку и содержимому
- Автосохранение в JSON-файл в папке пользователя (`~/.simplenotes/notes.json`)
- Экспорт / импорт заметок в текстовый файл
- Горячие клавиши: `Ctrl+N`, `Ctrl+S`, `Ctrl+D` / `Delete`
- Современный простой интерфейс на Tkinter

## Скачать готовую версию (Windows)

Перейдите в раздел **[Releases](https://github.com/ivanivorontsov-sudo/SimpleNotes/releases)** и скачайте:

- `SimpleNotes.exe` — портативная версия (просто запустить)
- `SimpleNotes-Setup.exe` — установщик (рекомендуется)

> Релизы автоматически собираются через GitHub Actions при создании тега.

## Запуск из исходников

Требуется Python 3.8+.

```bash
git clone https://github.com/ivanivorontsov-sudo/SimpleNotes.git
cd SimpleNotes
python main.py
```

Никаких дополнительных зависимостей не нужно — используется только стандартная библиотека + Tkinter.

## Сборка EXE самостоятельно (Windows)

1. Установите Python 3.8+ и добавьте в PATH.
2. Установите PyInstaller:

```bash
pip install pyinstaller
```

3. Соберите:

```bash
pyinstaller --noconfirm --onefile --windowed --name SimpleNotes main.py
```

Готовый файл будет в папке `dist/SimpleNotes.exe`.

### Создание установщика (Inno Setup)

1. Установите [Inno Setup](https://jrsoftware.org/isinfo.php).
2. Откройте файл `installer.iss` и скомпилируйте его.
3. Установщик появится в папке `Output`.

## Структура проекта

```
SimpleNotes/
├── main.py              # Исходный код приложения
├── requirements.txt     # Зависимости для сборки
├── installer.iss        # Скрипт установщика Inno Setup
├── .github/
│   └── workflows/
│       └── build.yml    # Автоматическая сборка EXE и установщика
└── README.md
```

## Лицензия

MIT — используйте свободно.

---

Создано с помощью [Grok](https://x.ai)
