# 🎙️ Универсальный TTS Синтезатор (Мультидвижковый)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-stable-brightgreen)](https://github.com/Aendrous/SileroTTStoMp3)

Программа с графическим интерфейсом для синтеза речи из текста с использованием нескольких движков TTS. Поддерживает Edge TTS, Yandex SpeechKit и Google TTS.

## 📸 Скриншоты

### Главное окно программы
![Главное окно программы](screenshots/main_window.png)

### Процесс синтеза
![Процесс синтеза](screenshots/synthesis_process.png)

### Настройки Yandex SpeechKit
![Настройки Yandex](screenshots/yandex_settings.png)

## ✨ Возможности

- **Мультидвижковая архитектура**:
  - ✅ Edge TTS (Microsoft) — высокое качество, не требует ключей
  - ✅ Yandex SpeechKit — премиум голоса, лучшее качество для русского
  - ✅ Google TTS — простой и бесплатный
- **Графический интерфейс** на tkinter
- **Визуализация процесса**:
  - Прогресс-бар с процентом выполнения
  - Подсветка текущего обрабатываемого фрагмента
  - Детальная статистика (время, символы, части)
- **Поддержка длинных текстов** — автоматическое разбиение на части
- **Лог работы** с цветовой маркировкой сообщений
- **Экспорт в MP3** — сохранение результата в один файл

## 📦 Установка и запуск

### 1. Требования
- Python 3.8 или выше
- Установленные зависимости (см. ниже)

### 2. Установка зависимостей
```bash
# Клонируйте репозиторий
git clone https://github.com/Aendrous/SileroTTStoMp3.git
cd SileroTTStoMp3

# Установите зависимости
pip install -r requirements.txt
