import asyncio
import edge_tts
import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import shutil
from datetime import datetime
import requests
from io import BytesIO
from gtts import gTTS

# Проверяем совместимость с pydub
try:
    import audioop
    from pydub import AudioSegment
    USE_PYDUB = True
except ImportError:
    USE_PYDUB = False

class UniversalTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Универсальный TTS - Мультидвижковый")
        self.root.geometry("900x750")
        
        # Настройки по умолчанию
        self.engine_var = tk.StringVar(value="edge")  # edge, yandex, gtts
        self.voice_var = tk.StringVar(value="ru-RU-DmitryNeural")
        self.speed_var = tk.DoubleVar(value=0)
        
        # Настройки Yandex (ЗАМЕНИТЕ НА СВОИ!)
        self.yandex_api_key = "AQVNyif48miwPqHSoXIXojkLIsF9UHoRgYO-0AWl"
        self.yandex_folder_id = "b1gn31qp9dfj014m325m"
        self.yandex_voice = "alena"  # alena, filipp, ermil
        
        # Переменные для отслеживания прогресса
        self.current_chunk = 0
        self.total_chunks = 0
        self.chunk_texts = []
        self.is_synthesizing = False
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(header_frame, text="🎙️ Универсальный TTS (Мультидвижковый)", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        self.time_label = ttk.Label(header_frame, text="", font=('Arial', 10))
        self.time_label.pack(side=tk.RIGHT)
        
        # Текст для озвучки
        text_frame = ttk.LabelFrame(main_frame, text="Текст для озвучки", padding="5")
        text_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_area = tk.Text(text_frame, height=10, width=90, 
                                yscrollcommand=text_scroll.set,
                                wrap=tk.WORD, font=('Arial', 10))
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.text_area.yview)
        
        # Визуализация процесса
        self.visualization_frame = ttk.LabelFrame(main_frame, text="Визуализация процесса", padding="5")
        self.visualization_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.visualization_frame, 
                                           variable=self.progress_var,
                                           maximum=100,
                                           length=700)
        self.progress_bar.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_text = tk.StringVar(value="Готов к работе")
        ttk.Label(self.visualization_frame, textvariable=self.progress_text, 
                 font=('Arial', 10)).grid(row=1, column=0, columnspan=4, pady=5)
        
        # Детальная информация
        info_frame = ttk.Frame(self.visualization_frame)
        info_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        self.chunk_info = tk.StringVar(value="Частей: 0")
        ttk.Label(info_frame, textvariable=self.chunk_info).pack(side=tk.LEFT, padx=10)
        
        self.time_elapsed = tk.StringVar(value="Время: 0:00")
        ttk.Label(info_frame, textvariable=self.time_elapsed).pack(side=tk.LEFT, padx=10)
        
        self.chars_processed = tk.StringVar(value="Символов: 0")
        ttk.Label(info_frame, textvariable=self.chars_processed).pack(side=tk.LEFT, padx=10)
        
        # НАСТРОЙКИ: Выбор движка и голосов
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки синтеза", padding="10")
        settings_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Выбор движка TTS
        ttk.Label(settings_frame, text="Движок:").grid(row=0, column=0, sticky=tk.W)
        engines = [("Edge TTS", "edge"), ("Yandex SpeechKit", "yandex"), ("Google TTS", "gtts")]
        
        for i, (name, engine_id) in enumerate(engines):
            ttk.Radiobutton(settings_frame, text=name, variable=self.engine_var, 
                           value=engine_id, command=self.update_voice_options).grid(row=0, column=i+1, padx=10)
        
        # Голос (меняется в зависимости от движка)
        ttk.Label(settings_frame, text="Голос:").grid(row=1, column=0, sticky=tk.W, pady=(15, 0))
        self.voice_selector_frame = ttk.Frame(settings_frame)
        self.voice_selector_frame.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=(15, 0))
        
        # Изначальные голоса для Edge
        self.edge_voices = [
            ("Дмитрий (мужской)", "ru-RU-DmitryNeural"), 
            ("Светлана (женский)", "ru-RU-SvetlanaNeural")
        ]
        
        self.yandex_voices = [
            ("Алёна (женский)", "alena"),
            ("Филипп (мужской)", "filipp"),
            ("Ермил (мужской)", "ermil")
        ]
        
        self.gtts_voices = [
            ("Русский", "ru")
        ]
        
        # Скорость
        ttk.Label(settings_frame, text="Скорость:").grid(row=2, column=0, sticky=tk.W, pady=(15, 0))
        speed_frame = ttk.Frame(settings_frame)
        speed_frame.grid(row=2, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=(15, 0))
        
        ttk.Label(speed_frame, text="-50%").pack(side=tk.LEFT)
        speed_scale = ttk.Scale(speed_frame, from_=-50, to=50, variable=self.speed_var, 
                               orient=tk.HORIZONTAL, length=200)
        speed_scale.pack(side=tk.LEFT, padx=10)
        ttk.Label(speed_frame, text="+50%").pack(side=tk.LEFT)
        
        self.speed_label = ttk.Label(speed_frame, text=f"{self.speed_var.get():+.0f}%", 
                                    width=6, anchor=tk.CENTER)
        self.speed_label.pack(side=tk.LEFT, padx=10)
        speed_scale.configure(command=lambda v: self.speed_label.config(text=f"{float(v):+.0f}%"))
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        self.synthesize_button = ttk.Button(button_frame, text="🎵 Начать озвучивание", 
                                           command=self.start_synthesis, width=25)
        self.synthesize_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📁 Загрузить текст", 
                  command=self.load_text_file, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🧹 Очистить текст", 
                  command=self.clear_text, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="⏹ Остановить", 
                  command=self.cancel_synthesis, width=15).pack(side=tk.LEFT, padx=5)
        
        # Лог работы
        log_frame = ttk.LabelFrame(main_frame, text="Лог работы", padding="5")
        log_frame.grid(row=5, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_area = tk.Text(log_frame, height=8, width=90, 
                               yscrollcommand=log_scroll.set,
                               wrap=tk.WORD, font=('Arial', 9),
                               bg='#F5F5F5', relief=tk.SUNKEN)
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_area.yview)
        
        # Статусная строка
        status_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=6, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="✅ Готов к работе")
        ttk.Label(status_frame, textvariable=self.status_var, 
                 font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        
        # Таймер для обновления времени
        self.start_time = None
        self.update_time()
        
        # Инициализация голосов
        self.update_voice_options()
        self.add_log("Программа запущена")
        self.add_log(f"Используется движок: {self.engine_var.get()}")
    
    def update_voice_options(self):
        """Обновляет список голосов в зависимости от выбранного движка."""
        # Очищаем фрейм с выбором голоса
        for widget in self.voice_selector_frame.winfo_children():
            widget.destroy()
        
        engine = self.engine_var.get()
        
        if engine == "edge":
            voices = self.edge_voices
            self.voice_var.set("ru-RU-DmitryNeural")
        elif engine == "yandex":
            voices = self.yandex_voices
            self.voice_var.set("alena")
        else:  # gtts
            voices = self.gtts_voices
            self.voice_var.set("ru")
        
        # Создаем радиокнопки для голосов
        for i, (name, voice_id) in enumerate(voices):
            ttk.Radiobutton(self.voice_selector_frame, text=name, variable=self.voice_var, 
                           value=voice_id).grid(row=0, column=i, padx=10)
        
        self.add_log(f"Переключен на движок: {engine}")
    
    def add_log(self, message, level="INFO"):
        """Добавляет сообщение в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "INFO":
            prefix = "ℹ️"
        elif level == "WARNING":
            prefix = "⚠️"
        elif level == "ERROR":
            prefix = "❌"
        elif level == "SUCCESS":
            prefix = "✅"
        else:
            prefix = "📝"
        
        log_message = f"[{timestamp}] {prefix} {message}\n"
        self.log_area.insert("1.0", log_message)
        
        # Ограничиваем размер лога
        lines = int(self.log_area.index('end-1c').split('.')[0])
        if lines > 100:
            self.log_area.delete("100.0", "end")
        
        self.log_area.see("1.0")
    
    def update_time(self):
        """Обновление времени в интерфейсе."""
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=now)
        self.root.after(1000, self.update_time)
    
    def update_progress(self, chunk_num, total_chunks, text=""):
        """Обновление визуализации прогресса."""
        if total_chunks > 0:
            progress_percent = (chunk_num / total_chunks) * 100
            self.progress_var.set(progress_percent)
            self.progress_text.set(f"Озвучивается часть {chunk_num} из {total_chunks} ({progress_percent:.1f}%)")
            self.chunk_info.set(f"Частей: {chunk_num}/{total_chunks}")
            
            # Подсвечиваем текущую часть в основном тексте
            if text and chunk_num > 0:
                self.highlight_current_chunk(chunk_num - 1, text)
                if chunk_num == 1 or chunk_num % 5 == 0:
                    self.add_log(f"Обрабатывается часть {chunk_num}/{total_chunks} ({len(text)} символов)")
            
            # Обновляем время выполнения
            if self.start_time:
                elapsed = datetime.now() - self.start_time
                minutes = int(elapsed.total_seconds() // 60)
                seconds = int(elapsed.total_seconds() % 60)
                self.time_elapsed.set(f"Время: {minutes}:{seconds:02d}")
    
    def highlight_current_chunk(self, chunk_index, chunk_text):
        """Подсвечивает текущий фрагмент в основном тексте."""
        try:
            full_text = self.text_area.get(1.0, tk.END).strip()
            if chunk_text in full_text:
                start_pos = full_text.find(chunk_text)
                end_pos = start_pos + len(chunk_text)
                
                self.text_area.tag_remove("highlight", 1.0, tk.END)
                self.text_area.tag_add("highlight", f"1.0+{start_pos}c", f"1.0+{end_pos}c")
                self.text_area.tag_config("highlight", background="#FFFACD", foreground="black")
                self.text_area.see(f"1.0+{start_pos}c")
        except:
            pass
    
    def load_text_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите текстовый файл",
            filetypes=[("Текстовые файлы", "*.txt"), ("Документы", "*.docx"), ("Все файлы", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(1.0, content)
                
                chars = len(content)
                words = len(content.split())
                lines = content.count('\n') + 1
                
                status_msg = f"📄 Загружен: {os.path.basename(file_path)} | Символов: {chars:,} | Слов: {words:,} | Строк: {lines}"
                self.status_var.set(status_msg)
                self.chars_processed.set(f"Символов: {chars:,}")
                self.add_log(f"Загружен файл: {os.path.basename(file_path)} ({chars:,} символов, {words:,} слов)")
                
            except Exception as e:
                error_msg = f"Не удалось загрузить файл:\n{e}"
                messagebox.showerror("Ошибка", error_msg)
                self.add_log(f"Ошибка загрузки файла: {str(e)[:100]}", "ERROR")
    
    def clear_text(self):
        self.text_area.delete(1.0, tk.END)
        self.status_var.set("Текст очищен")
        self.chars_processed.set("Символов: 0")
        self.text_area.tag_remove("highlight", 1.0, tk.END)
        self.add_log("Текстовое поле очищено")
    
    def cancel_synthesis(self):
        """Остановка процесса синтеза."""
        if self.is_synthesizing:
            self.is_synthesizing = False
            self.status_var.set("⏹ Остановлено пользователем")
            self.add_log("Процесс синтеза остановлен пользователем", "WARNING")
    
    def start_synthesis(self):
        if self.is_synthesizing:
            self.add_log("Попытка запуска при уже работающем синтезе", "WARNING")
            return
            
        text = self.text_area.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Предупреждение", "Введите текст для озвучки.")
            self.add_log("Попытка запуска без текста", "WARNING")
            return
        
        engine = self.engine_var.get()
        voice_name = self.voice_var.get()
        speed = self.speed_var.get()
        
        self.add_log(f"Начало синтеза: движок={engine}, голос={voice_name}, скорость={speed:+.0f}%, символов={len(text):,}")
        
        self.is_synthesizing = True
        self.synthesize_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.start_time = datetime.now()
        
        threading.Thread(target=self.run_async_synthesis, args=(text,), daemon=True).start()
    
    def split_long_text(self, text, max_length=4000):
        """Разбивает текст на части для длинных текстов."""
        if len(text) <= max_length:
            self.add_log(f"Текст не требует разбиения ({len(text)} символов)")
            return [text]
        
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        self.root.after(0, lambda: self.chunk_info.set(f"Частей: 0/{len(chunks)}"))
        self.add_log(f"Текст разбит на {len(chunks)} частей по {max_length} символов")
        return chunks
    
    async def synthesize_chunk(self, text, voice, speed, output_file):
        """Озвучивает фрагмент текста в зависимости от выбранного движка."""
        engine = self.engine_var.get()
        
        try:
            if engine == "edge":
                # КОРРЕКТНЫЙ способ для edge-tts 7.x
                tts = edge_tts.Communicate(text, voice, rate=f"{speed:+.0f}%")
                await tts.save(output_file)
                
            elif engine == "yandex":
                # Синтез через Yandex SpeechKit API
                url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
                headers = {"Authorization": f"Api-Key {self.yandex_api_key}"}
                data = {
                    "text": text,
                    "voice": voice,
                    "folderId": self.yandex_folder_id,
                    "format": "mp3",
                    "sampleRateHertz": 48000,
                }
                
                response = requests.post(url, headers=headers, data=data, stream=True)
                if response.status_code == 200:
                    with open(output_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    raise Exception(f"Yandex API error: {response.status_code} - {response.text}")
                    
            elif engine == "gtts":
                # Синтез через Google TTS
                tts = gTTS(text=text, lang=voice, slow=False)
                tts.save(output_file)
            
            self.add_log(f"Фрагмент озвучен ({engine}): {len(text)} символов -> {os.path.basename(output_file)}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.add_log(f"Ошибка синтеза фрагмента ({engine}): {error_msg[:100]}", "ERROR")
            raise e
    
    def run_async_synthesis(self, text):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_synthesize_speech(text))
        except Exception as error:
            error_msg = str(error)
            self.root.after(0, lambda msg=error_msg: self.show_error(msg))
        finally:
            loop.close()
            self.root.after(0, lambda: self.set_synthesis_done())
    
    async def async_synthesize_speech(self, text):
        try:
            if not self.is_synthesizing:
                self.add_log("Синтез отменен перед началом", "WARNING")
                return
                
            self.root.after(0, lambda: self.status_var.set("🚀 Начинаю синтез..."))
            
            chunks = self.split_long_text(text)
            self.total_chunks = len(chunks)
            self.chunk_texts = chunks
            
            self.root.after(0, lambda: self.update_progress(0, self.total_chunks))
            
            temp_files = []
            for i, chunk in enumerate(chunks, 1):
                if not self.is_synthesizing:
                    self.add_log(f"Синтез остановлен на части {i-1}/{len(chunks)}", "WARNING")
                    break
                    
                self.current_chunk = i
                self.root.after(0, lambda idx=i, txt=chunk: 
                              self.update_progress(idx, self.total_chunks, txt))
                
                self.root.after(0, lambda s=f"Часть {i}/{len(chunks)}": 
                              self.status_var.set(f"🎙️ {s}"))
                
                temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_files.append(temp_mp3.name)
                temp_mp3.close()
                
                await self.synthesize_chunk(chunk, self.voice_var.get(), 
                                           self.speed_var.get(), temp_mp3.name)
                
                chars_done = sum(len(c) for c in chunks[:i])
                self.root.after(0, lambda cd=chars_done: 
                              self.chars_processed.set(f"Символов: {cd:,}/{len(text):,}"))
            
            if not self.is_synthesizing:
                self.root.after(0, lambda: self.add_log("Синтез прерван, удаляю временные файлы", "WARNING"))
                for f in temp_files:
                    try:
                        if os.path.exists(f):
                            os.unlink(f)
                    except:
                        pass
                return
            
            self.root.after(0, lambda: self.status_var.set("✅ Синтез завершён! Сохраняю результат..."))
            self.root.after(0, lambda: self.update_progress(self.total_chunks, self.total_chunks, ""))
            self.add_log(f"Синтез завершен успешно, создано {len(temp_files)} временных файлов", "SUCCESS")
            
            output_file = filedialog.asksaveasfilename(
                title="Сохранить аудиофайл",
                defaultextension=".mp3",
                filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")]
            )
            
            if output_file:
                self.add_log(f"Сохранение результата в: {os.path.basename(output_file)}")
                
                if len(temp_files) == 1:
                    shutil.copy2(temp_files[0], output_file)
                    self.root.after(0, lambda: self.show_success(output_file))
                else:
                    if USE_PYDUB:
                        try:
                            self.add_log(f"Объединение {len(temp_files)} файлов с помощью pydub")
                            combined = AudioSegment.empty()
                            for mp3_file in temp_files:
                                audio = AudioSegment.from_mp3(mp3_file)
                                combined += audio
                            combined.export(output_file, format="mp3", bitrate="192k")
                            self.root.after(0, lambda: self.show_success(output_file))
                        except Exception as e:
                            self.root.after(0, lambda: self.show_merge_instructions(temp_files, output_file))
                    else:
                        self.root.after(0, lambda: self.show_merge_instructions(temp_files, output_file))
            
            for f in temp_files:
                try:
                    if os.path.exists(f):
                        os.unlink(f)
                except:
                    pass
            
            self.root.after(0, lambda: self.text_area.tag_remove("highlight", 1.0, tk.END))
            
        except Exception as error:
            error_msg = str(error)
            self.root.after(0, lambda msg=error_msg: self.show_error(msg))
    
    def set_synthesis_done(self):
        """Сброс состояния после синтеза."""
        self.is_synthesizing = False
        self.synthesize_button.config(state=tk.NORMAL)
    
    def show_error(self, msg):
        self.status_var.set("❌ Ошибка")
        self.add_log(f"Критическая ошибка: {msg[:200]}", "ERROR")
        messagebox.showerror("Ошибка", msg)
        self.set_synthesis_done()
    
    def show_success(self, output_file):
        file_size = os.path.getsize(output_file) / 1024 / 1024 if os.path.exists(output_file) else 0
        
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            time_str = f"{minutes}:{seconds:02d}"
        else:
            time_str = "?"
        
        engine = self.engine_var.get()
        voice = self.voice_var.get()
        
        success_msg = (
            f"✅ Аудиофайл успешно создан!\n\n"
            f"📁 Файл: {os.path.basename(output_file)}\n"
            f"💾 Размер: {file_size:.2f} MB\n"
            f"🔧 Движок: {engine}\n"
            f"🎙️ Голос: {voice}\n"
            f"⏱️ Время обработки: {time_str}\n"
            f"📊 Частей: {self.total_chunks}"
        )
        
        messagebox.showinfo("Готово!", success_msg)
        
        status_msg = f"✅ Готово! Файл сохранён: {os.path.basename(output_file)} ({file_size:.2f} MB)"
        self.status_var.set(status_msg)
        
        self.add_log(f"Файл успешно сохранен: {os.path.basename(output_file)} ({file_size:.2f} MB, время: {time_str})", "SUCCESS")
        
        self.set_synthesis_done()
    
    def show_merge_instructions(self, temp_files, output_file):
        instruction = (
            "Текст разбит на несколько частей. Для объединения:\n\n"
            "1. Установите pydub: pip install pydub audioop-lts\n"
            "2. Перезапустите программу\n\n"
            "Или используйте аудио-редактор для объединения файлов."
        )
        
        messagebox.showinfo("Требуется объединение", instruction)
        self.status_var.set("⚠️ Требуется объединение файлов")
        self.add_log("Требуется установка pydub для объединения файлов", "WARNING")
        self.set_synthesis_done()

def main():
    root = tk.Tk()
    app = UniversalTTSApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
