"""Portable, validated backups for SimpleNotes.

The backup format is versioned and uses only the Python standard library.
Imports are merged; existing notes are never silently overwritten.
"""

import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Dict, List, Tuple

FORMAT_NAME = "simplenotes.backup"
FORMAT_VERSION = 1
MAX_BACKUP_BYTES = 20 * 1024 * 1024
MAX_NOTE_BYTES = 2 * 1024 * 1024
MAX_NOTES = 50000
MAX_ARCHIVE_FILES = MAX_NOTES + 1

_NOTE_FIELDS = ("id", "title", "content", "created", "updated")


def _normalise_note(note: dict, index: int) -> Dict[str, object]:
    if not isinstance(note, dict):
        raise ValueError("Заметка №{} имеет неверный формат".format(index + 1))

    note_id = note.get("id")
    if isinstance(note_id, bool) or not isinstance(note_id, int) or note_id < 1:
        raise ValueError("У заметки №{} неверный идентификатор".format(index + 1))

    title = note.get("title", "Без названия")
    content = note.get("content", "")
    created = note.get("created", note.get("updated", ""))
    updated = note.get("updated", created)

    if not all(isinstance(value, str) for value in (title, content, created, updated)):
        raise ValueError("У заметки №{} неверные текстовые поля".format(index + 1))
    if len(title) > 500 or len(content.encode("utf-8")) > MAX_NOTE_BYTES:
        raise ValueError("Заметка №{} слишком большая".format(index + 1))
    if len(created) > 100 or len(updated) > 100:
        raise ValueError("У заметки №{} неверная дата".format(index + 1))

    return {
        "id": note_id,
        "title": title,
        "content": content,
        "created": created,
        "updated": updated,
    }


def encode_backup(notes: List[dict]) -> bytes:
    if not isinstance(notes, list) or len(notes) > MAX_NOTES:
        raise ValueError("Недопустимое количество заметок")

    normalised = [_normalise_note(note, i) for i, note in enumerate(notes)]
    ids = [note["id"] for note in normalised]
    if len(ids) != len(set(ids)):
        raise ValueError("В заметках повторяются идентификаторы")

    document = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": normalised,
    }
    payload = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    if len(payload) > MAX_BACKUP_BYTES:
        raise ValueError("Резервная копия превышает 20 МБ")
    return payload


def decode_backup(data: bytes) -> List[dict]:
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("Файл резервной копии должен быть двоичным")
    if len(data) > MAX_BACKUP_BYTES:
        raise ValueError("Резервная копия превышает 20 МБ")

    try:
        document = json.loads(bytes(data).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Файл не является корректной JSON-резервной копией") from exc

    if not isinstance(document, dict) or document.get("format") != FORMAT_NAME:
        raise ValueError("Это не резервная копия SimpleNotes")
    version = document.get("version")
    if isinstance(version, bool) or version != FORMAT_VERSION:
        raise ValueError("Версия резервной копии не поддерживается")

    raw_notes = document.get("notes")
    if not isinstance(raw_notes, list) or len(raw_notes) > MAX_NOTES:
        raise ValueError("В резервной копии неверный список заметок")

    notes = [_normalise_note(note, i) for i, note in enumerate(raw_notes)]
    ids = [note["id"] for note in notes]
    if len(ids) != len(set(ids)):
        raise ValueError("В резервной копии повторяются идентификаторы")
    return notes


def create_markdown_archive(notes: List[dict]) -> bytes:
    backup = encode_backup(notes)
    normalised = decode_backup(backup)
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("notes.json", backup)
        for note in normalised:
            safe_title = note["title"].replace("\r", " ").replace("\n", " ").strip()
            slug = re.sub(r"[^\w.-]+", "-", safe_title, flags=re.UNICODE).strip("-.")
            slug = (slug or "note")[:60]
            filename = "markdown/{}-{}.md".format(note["id"], slug)
            markdown = "# {}\n\n{}".format(safe_title or "Без названия", note["content"])
            archive.writestr(filename, markdown.encode("utf-8"))

    payload = buffer.getvalue()
    if len(payload) > MAX_BACKUP_BYTES:
        raise ValueError("Архив превышает 20 МБ")
    return payload


def _read_markdown_archive(data: bytes) -> List[dict]:
    if len(data) > MAX_BACKUP_BYTES:
        raise ValueError("Архив превышает 20 МБ")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("Файл не является корректным ZIP-архивом") from exc

    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ValueError("В архиве слишком много файлов")

        total_size = sum(info.file_size for info in infos)
        if total_size > MAX_BACKUP_BYTES:
            raise ValueError("Распакованный архив превышает 20 МБ")

        names = set()
        for info in infos:
            name = info.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("В архиве обнаружен небезопасный путь")
            if name in names:
                raise ValueError("В архиве повторяется имя файла")
            names.add(name)

        if "notes.json" in names:
            return decode_backup(archive.read("notes.json"))

        candidates = [
            info for info in infos
            if PurePosixPath(info.filename.replace("\\", "/")).suffix.lower()
            in (".md", ".markdown", ".txt")
            and not info.filename.replace("\\", "/").startswith("__MACOSX/")
        ]
        if not candidates:
            raise ValueError("В архиве нет заметок Markdown или TXT")

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        imported = []
        for index, info in enumerate(candidates):
            if info.file_size > MAX_NOTE_BYTES:
                raise ValueError("Файл {} превышает 2 МБ".format(info.filename))
            raw = archive.read(info)
            if len(raw) > MAX_NOTE_BYTES:
                raise ValueError("Файл {} превышает 2 МБ".format(info.filename))
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValueError("Файл {} должен быть в UTF-8".format(info.filename)) from exc

            path = PurePosixPath(info.filename.replace("\\", "/"))
            suffix = path.suffix.lower()
            lines = text.splitlines()
            if suffix in (".md", ".markdown") and lines:
                match = re.match(r"^#\s+(.+?)\s*$", lines[0])
                if match:
                    title = match.group(1).strip()
                    content = "\n".join(lines[1:]).lstrip("\n")
                else:
                    title = path.stem
                    content = text
            elif suffix == ".txt" and lines:
                title = lines[0].strip() or path.stem
                content = "\n".join(lines[1:]).lstrip("\n")
            else:
                title = path.stem
                content = text

            imported.append({
                "id": index + 1,
                "title": title[:500],
                "content": content,
                "created": now,
                "updated": now,
            })

    return imported


def decode_import(data: bytes, filename: str) -> List[dict]:
    if filename.lower().endswith(".zip"):
        return _read_markdown_archive(data)
    return decode_backup(data)


def merge_notes(existing: List[dict], imported: List[dict]) -> Tuple[List[dict], int, int, int]:
    """Merge an import without replacing existing notes.

    Returns (merged_notes, added, skipped_identical, id_conflicts).
    """
    merged = [dict(note) for note in existing]
    by_id = {note.get("id"): note for note in merged}
    reserved_ids = set(by_id)
    reserved_ids.update(
        note.get("id") for note in imported
        if isinstance(note.get("id"), int) and not isinstance(note.get("id"), bool)
    )
    next_id = max(
        (note_id for note_id in reserved_ids if isinstance(note_id, int) and not isinstance(note_id, bool)),
        default=0,
    ) + 1
    added = 0
    skipped = 0
    conflicts = 0

    for index, raw_note in enumerate(imported):
        note = _normalise_note(raw_note, index)
        current = by_id.get(note["id"])
        if current is not None:
            if all(current.get(field) == note[field] for field in _NOTE_FIELDS):
                skipped += 1
                continue
            while next_id in reserved_ids or next_id in by_id:
                next_id += 1
            note["id"] = next_id
            reserved_ids.add(next_id)
            next_id += 1
            conflicts += 1

        merged.append(note)
        by_id[note["id"]] = note
        added += 1

    return merged, added, skipped, conflicts
