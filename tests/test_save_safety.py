"""Regression tests for preserving editor data after failed writes."""

import unittest
from unittest.mock import Mock, patch

from main import NotesApp


class SaveFailureTests(unittest.TestCase):
    def make_app(self):
        app = NotesApp.__new__(NotesApp)
        app.current_note_id = 1
        app.notes = [
            {
                "id": 1,
                "title": "Старый заголовок",
                "content": "Старый текст",
                "created": "2026-11-20 10:00",
                "updated": "2026-11-20 10:00",
            }
        ]
        app.title_entry = Mock()
        app.title_entry.get.return_value = "Новый заголовок"
        app.text_area = Mock()
        app.text_area.get.return_value = "1.0"
        app.modified = True
        app.save_notes = Mock(return_value=False)
        return app

    def test_failed_write_rolls_back_model_but_keeps_editor_dirty(self):
        app = self.make_app()

        self.assertFalse(app.save_current())

        self.assertEqual(app.notes[0]["title"], "Старый заголовок")
        self.assertEqual(app.notes[0]["content"], "Старый текст")
        self.assertTrue(app.modified)
        self.assertEqual(app.title_entry.get(), "Новый заголовок")

    def test_failed_first_save_does_not_leave_phantom_note(self):
        app = self.make_app()
        app.current_note_id = None
        app.notes = []

        self.assertFalse(app.save_current())

        self.assertEqual(app.notes, [])
        self.assertTrue(app.modified)

    def test_selecting_another_note_is_aborted_when_save_fails(self):
        app = self.make_app()
        target = {"id": 2, "title": "Другая", "content": "", "created": "", "updated": ""}
        app.get_selected_index = Mock(return_value=target)
        app.save_current = Mock(return_value=False)

        with patch("main.messagebox.askyesno", return_value=True):
            app.on_select()

        self.assertEqual(app.current_note_id, 1)
        app.title_entry.delete.assert_not_called()

    def test_close_is_aborted_when_save_fails(self):
        app = self.make_app()
        app.root = Mock()
        app.save_current = Mock(return_value=False)

        with patch("main.messagebox.askyesno", return_value=True):
            app.on_close()

        app.root.destroy.assert_not_called()

    def test_new_note_is_aborted_when_current_note_cannot_be_saved(self):
        app = self.make_app()
        app.save_current = Mock(return_value=False)

        with patch("main.messagebox.askyesno", return_value=True):
            self.assertFalse(app.new_note())

        self.assertEqual(len(app.notes), 1)
        app.save_notes.assert_not_called()


if __name__ == "__main__":
    unittest.main()
