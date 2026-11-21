import io
import json
import unittest
import zipfile

from backup import (
    FORMAT_NAME,
    create_markdown_archive,
    decode_backup,
    decode_import,
    encode_backup,
    merge_notes,
)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.notes = [
            {
                "id": 1,
                "title": "Покупки 🛒",
                "content": "Молоко\nХлеб",
                "created": "2026-11-20 10:00",
                "updated": "2026-11-21 09:00",
            },
            {
                "id": 2,
                "title": "Идея",
                "content": "Сделать приложение",
                "created": "2026-11-19 12:00",
                "updated": "2026-11-19 12:00",
            },
        ]

    def test_json_backup_round_trip_preserves_unicode_and_metadata(self):
        payload = encode_backup(self.notes)
        restored = decode_backup(payload)
        self.assertEqual(restored, self.notes)

    def test_markdown_archive_contains_readable_files_and_restores_exact_backup(self):
        payload = create_markdown_archive(self.notes)
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            names = archive.namelist()
            self.assertIn("notes.json", names)
            markdown_files = [name for name in names if name.endswith(".md")]
            self.assertEqual(len(markdown_files), 2)
            self.assertIn("# Покупки 🛒", archive.read(markdown_files[0]).decode("utf-8"))
        self.assertEqual(decode_import(payload, "backup.zip"), self.notes)

    def test_imports_markdown_only_zip(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("Заметки/План.md", "# План\n\nПервая строка\nВторая строка")
            archive.writestr("Черновик.txt", "Черновик\nТекст")
        imported = decode_import(buffer.getvalue(), "external.zip")
        self.assertEqual([note["title"] for note in imported], ["План", "Черновик"])
        self.assertEqual(imported[0]["content"], "Первая строка\nВторая строка")
        self.assertEqual(imported[1]["content"], "Текст")

    def test_rejects_wrong_format_and_unsupported_version(self):
        wrong_format = json.dumps({"format": "other", "version": 1, "notes": []}).encode("utf-8")
        with self.assertRaises(ValueError):
            decode_backup(wrong_format)

        unsupported = json.dumps({"format": FORMAT_NAME, "version": 2, "notes": []}).encode("utf-8")
        with self.assertRaises(ValueError):
            decode_backup(unsupported)

    def test_rejects_duplicate_ids_in_backup(self):
        document = {
            "format": FORMAT_NAME,
            "version": 1,
            "notes": [self.notes[0], dict(self.notes[0])],
        }
        with self.assertRaises(ValueError):
            decode_backup(json.dumps(document).encode("utf-8"))

    def test_merge_skips_identical_notes_and_preserves_conflicting_versions(self):
        existing = [dict(self.notes[0]), dict(self.notes[1])]
        incoming = [
            dict(self.notes[0]),
            dict(self.notes[1], content="Изменённый текст"),
            {
                "id": 3,
                "title": "Новая",
                "content": "Не потерять",
                "created": "2026-11-21 10:00",
                "updated": "2026-11-21 10:00",
            },
        ]

        merged, added, skipped, conflicts = merge_notes(existing, incoming)

        self.assertEqual((added, skipped, conflicts), (2, 1, 1))
        self.assertEqual([note["id"] for note in merged], [1, 2, 4, 3])
        self.assertEqual(merged[1]["content"], "Сделать приложение")
        self.assertEqual(merged[2]["content"], "Изменённый текст")
        self.assertEqual(merged[3]["title"], "Новая")
        self.assertEqual(existing, self.notes)

    def test_rejects_zip_path_traversal(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../outside.md", "# Не импортировать")
        with self.assertRaises(ValueError):
            decode_import(buffer.getvalue(), "unsafe.zip")


if __name__ == "__main__":
    unittest.main()
