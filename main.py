#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpleNotes - Простая программа для заметок
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
from datetime import datetime
from pathlib import Path


class NotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleNotes — Простые заметки")
        self.root.geometry("900x600")
        self.root.minsize(700, 450)

        # Путь к данным
        self.data_dir = Path.home() / ".simplenotes"
        self.data_dir.mkdir(exist_ok=True)
        self.notes_file = self.data_dir / "notes.json"
        self.notes = []
        self.current_note_id = None

        self.setup_ui()
        self.load_notes()
        self.refresh_list()

        # Горячие клавиши
        self.root.bind("<Control-n>", lambda e: self.new_note())
        self.root.bind("<Control-s>", lambda e: self.save_current())
        self.root.bind("<Control-d>", lambda e: self.delete_note())
        self.root.bind("<Delete>", lambda e: self.delete_note())

    def setup_ui(self):
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Левая панель — список заметок
        left_frame = ttk.Frame(main_frame, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Заметки", font=("", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # Поиск
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X)

        # Список
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.notes_listbox = tk.Listbox(
            list_frame,
            font=("", 10),
            activestyle="dotbox",
            selectmode=tk.SINGLE,
            exportselection=False
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.notes_listbox.yview)
        self.notes_listbox.configure(yscrollcommand=scrollbar.set)
        self.notes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_listbox.bind("<<ListboxSelect>>", self.on_select)
        self.notes_listbox.bind("<Double-Button-1>", lambda e: self.focus_editor())

        # Кнопки слева
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="＋ Новая", command=self.new_note).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame, text="🗑 Удалить", command=self.delete_note).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        # Правая панель — редактор
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Заголовок
        title_frame = ttk.Frame(right_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(title_frame, text="Заголовок:").pack(side=tk.LEFT)
        self.title_entry = ttk.Entry(title_frame, font=("", 12, "bold"))
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.title_entry.bind("<KeyRelease>", lambda e: self.mark_modified())

        # Текст
        text_frame = ttk.Frame(right_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            undo=True,
            padx=8,
            pady=8
        )
        text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=text_scroll.set)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.bind("<KeyRelease>", lambda e: self.mark_modified())

        # Нижняя панель
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))

        self.status_label = ttk.Label(bottom_frame, text="Готово", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        ttk.Button(bottom_frame, text="💾 Сохранить (Ctrl+S)", command=self.save_current).pack(side=tk.RIGHT)

        # Меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новая заметка", command=self.new_note, accelerator="Ctrl+N")
        file_menu.add_command(label="Сохранить", command=self.save_current, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт заметки...", command=self.export_note)
        file_menu.add_command(label="Импорт заметки...", command=self.import_note)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_close)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="Удалить заметку", command=self.delete_note, accelerator="Ctrl+D")

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.modified = False

    def mark_modified(self):
        self.modified = True
        self.status_label.config(text="Изменено*", foreground="orange")

    def load_notes(self):
        if self.notes_file.exists():
            try:
                with open(self.notes_file, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить заметки:\n{e}")
                self.notes = []
        else:
            self.notes = []

    def save_notes(self):
        try:
            with open(self.notes_file, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить заметки:\n{e}")

    def refresh_list(self):
        self.notes_listbox.delete(0, tk.END)
        query = self.search_var.get().lower().strip()
        for note in sorted(self.notes, key=lambda n: n.get("updated", ""), reverse=True):
            title = note.get("title", "Без названия")
            if query and query not in title.lower() and query not in note.get("content", "").lower():
                continue
            self.notes_listbox.insert(tk.END, title)

    def get_selected_index(self):
        sel = self.notes_listbox.curselection()
        if not sel:
            return None
        visible = []
        query = self.search_var.get().lower().strip()
        for note in sorted(self.notes, key=lambda n: n.get("updated", ""), reverse=True):
            title = note.get("title", "Без названия")
            if query and query not in title.lower() and query not in note.get("content", "").lower():
                continue
            visible.append(note)
        if sel[0] < len(visible):
            return visible[sel[0]]
        return None

    def on_select(self, event=None):
        note = self.get_selected_index()
        if note is None:
            return
        if self.modified:
            if not messagebox.askyesno("Несохранённые изменения", "Сохранить текущую заметку?"):
                pass
            else:
                self.save_current()
        self.current_note_id = note["id"]
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, note.get("title", ""))
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", note.get("content", ""))
        self.modified = False
        updated = note.get("updated", "")
        self.status_label.config(text=f"Обновлено: {updated}", foreground="gray")

    def focus_editor(self):
        self.text_area.focus_set()

    def new_note(self):
        if self.modified:
            if messagebox.askyesno("Несохранённые изменения", "Сохранить текущую заметку?"):
                self.save_current()
        new_id = max([n.get("id", 0) for n in self.notes] or [0]) + 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        note = {
            "id": new_id,
            "title": "Новая заметка",
            "content": "",
            "created": now,
            "updated": now
        }
        self.notes.append(note)
        self.save_notes()
        self.search_var.set("")
        self.refresh_list()
        # Выбрать новую
        self.notes_listbox.selection_clear(0, tk.END)
        self.notes_listbox.selection_set(0)
        self.notes_listbox.activate(0)
        self.on_select()
        self.title_entry.focus_set()
        self.title_entry.select_range(0, tk.END)
        self.modified = False

    def save_current(self):
        if self.current_note_id is None:
            self.new_note()
            return
        title = self.title_entry.get().strip() or "Без названия"
        content = self.text_area.get("1.0", tk.END).rstrip()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for note in self.notes:
            if note["id"] == self.current_note_id:
                note["title"] = title
                note["content"] = content
                note["updated"] = now
                break
        self.save_notes()
        self.refresh_list()
        # Восстановить выделение
        for i, note in enumerate(sorted(self.notes, key=lambda n: n.get("updated", ""), reverse=True)):
            if note["id"] == self.current_note_id:
                self.notes_listbox.selection_clear(0, tk.END)
                self.notes_listbox.selection_set(i)
                self.notes_listbox.activate(i)
                break
        self.modified = False
        self.status_label.config(text=f"Сохранено: {now}", foreground="green")

    def delete_note(self):
        note = self.get_selected_index()
        if note is None:
            messagebox.showinfo("Удаление", "Выберите заметку для удаления")
            return
        if not messagebox.askyesno("Подтверждение", f"Удалить заметку «{note.get('title', '')}»?"):
            return
        self.notes = [n for n in self.notes if n["id"] != note["id"]]
        self.save_notes()
        self.current_note_id = None
        self.title_entry.delete(0, tk.END)
        self.text_area.delete("1.0", tk.END)
        self.modified = False
        self.refresh_list()
        self.status_label.config(text="Заметка удалена", foreground="gray")

    def export_note(self):
        if self.current_note_id is None:
            messagebox.showinfo("Экспорт", "Сначала выберите или создайте заметку")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")],
            initialfile=self.title_entry.get() or "note"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.title_entry.get() + "\n\n")
                    f.write(self.text_area.get("1.0", tk.END))
                self.status_label.config(text=f"Экспортировано: {path}", foreground="green")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def import_note(self):
        path = filedialog.askopenfilename(
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.split("\n", 1)
            title = lines[0].strip() or Path(path).stem
            body = lines[1] if len(lines) > 1 else ""
            new_id = max([n.get("id", 0) for n in self.notes] or [0]) + 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            note = {
                "id": new_id,
                "title": title,
                "content": body.strip(),
                "created": now,
                "updated": now
            }
            self.notes.append(note)
            self.save_notes()
            self.refresh_list()
            self.status_label.config(text="Заметка импортирована", foreground="green")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def show_about(self):
        messagebox.showinfo(
            "О программе",
            "SimpleNotes v1.0\n\n"
            "Простая программа для заметок.\n"
            "Данные сохраняются локально в папке пользователя.\n\n"
            "Горячие клавиши:\n"
            "Ctrl+N — новая заметка\n"
            "Ctrl+S — сохранить\n"
            "Ctrl+D / Delete — удалить\n\n"
            "Создано с помощью Grok"
        )

    def on_close(self):
        if self.modified:
            if messagebox.askyesno("Выход", "Есть несохранённые изменения. Сохранить?"):
                self.save_current()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        pass
    except Exception:
        pass
    app = NotesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
