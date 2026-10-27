"""Focused presentation checks; the existing integration suite covers business behaviour."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QLineEdit

from client.gui.admin.users_tab import UserEditDialog
from client.gui.conversation_view import MessageHistory
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow
from client.gui.styles import PALETTE, apply_application_theme, display_time
from tests.test_gui import wait_idle


def test_history_escapes_markup_wraps_long_words_and_preserves_selection(qtbot):
    view = MessageHistory()
    qtbot.addWidget(view)
    view.resize(360, 400)
    view.show()
    messages = [
        {
            "id": 1,
            "sender": "alex",
            "created_at": "2026-10-27T14:00:00+00:00",
            "content": '<img src="file:///private.png"><b>copy me</b>\nFirst  line\tkept\n'
            + "x" * 10000,
        }
    ]
    view.render_messages(messages, "alex")
    assert '<img src="file:///private.png">' in view.toPlainText()
    assert "<b>copy me</b>" in view.toPlainText()
    assert "First  line\tkept" in view.toPlainText()
    assert view.document().size().width() <= view.viewport().width()
    cursor = view.document().find("copy me")
    view.setTextCursor(cursor)
    view.render_messages(messages, "alex")
    assert view.textCursor().selectedText() == "copy me"
    view.clear()
    view.render_messages(messages, "alex")
    assert "copy me" in view.toPlainText()


def test_login_tab_order_and_dialog_labels(qtbot, client_factory, qapp):
    apply_application_theme(qapp)
    network = client_factory()
    dialog = LoginWindow(network)
    qtbot.addWidget(dialog)
    dialog.resize(dialog.minimumSize())
    dialog.show()
    dialog.activateWindow()
    qtbot.waitUntil(dialog.isActiveWindow)
    dialog.username_edit.setFocus()
    qtbot.waitUntil(dialog.username_edit.hasFocus)
    qtbot.keyClick(dialog.username_edit, Qt.Key_Tab)
    assert dialog.password_edit.hasFocus()
    qtbot.keyClick(dialog.password_edit, Qt.Key_Tab)
    assert dialog.login_btn.hasFocus()
    assert dialog.username_edit.accessibleName() == "Username"
    for child in [
        dialog.username_edit,
        dialog.password_edit,
        dialog.login_btn,
        dialog.transport_label,
    ]:
        assert dialog.rect().contains(child.mapTo(dialog, child.rect().bottomRight()))
    editor = UserEditDialog("create", ["employee", "guest"], parent=dialog)
    qtbot.addWidget(editor)
    assert editor.password_edit.echoMode() == QLineEdit.Password
    buddies = {label.buddy() for label in editor.findChildren(QLabel)}
    assert {editor.username_edit, editor.password_edit, editor.role_combo} <= buddies
    dialog.close()
    wait_idle(qtbot)


def test_narrow_messenger_handles_long_titles_and_keeps_composer_visible(qtbot, client_factory):
    network = client_factory("alice")
    network.create_chat("A long conversation title " * 3)
    info = {**network.user_info, "username": "a_long_synthetic_username_1234567"}
    window = MainWindow(network, info)
    qtbot.addWidget(window)
    window.resize(window.minimumSize())
    window.show()
    qtbot.waitUntil(lambda: window.chats_list.count() == 1, timeout=5000)
    window.chats_list.setCurrentRow(0)
    wait_idle(qtbot)
    assert window.width() == window.minimumWidth()
    assert window.status_label.toolTip().startswith(info["username"])
    assert window.conversation_label.toolTip() == "A long conversation title " * 3
    for child in [window.chats_list, window.message_edit, window.send_btn]:
        assert window.rect().contains(child.mapTo(window, child.rect().bottomRight()))
    assert not window.splitter.childrenCollapsible()
    window.close()
    wait_idle(qtbot)


def test_text_palette_contrast():
    def luminance(color):
        rgb = QColor(color).getRgbF()[:3]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in rgb
        ]
        return sum(
            value * weight for value, weight in zip(linear, [0.2126, 0.7152, 0.0722], strict=True)
        )

    for foreground in [PALETTE["text"], PALETTE["secondary"], PALETTE["muted"]]:
        for background in [
            PALETTE["background"],
            PALETTE["panel"],
            PALETTE["surface"],
            PALETTE["own_message"],
        ]:
            first, second = sorted([luminance(foreground), luminance(background)])
            assert (second + 0.05) / (first + 0.05) >= 4.5


def test_legacy_and_aware_timestamps_display_the_same_in_local_time():
    assert display_time("2026-10-27T14:00:00") == display_time("2026-10-27T14:00:00+00:00")
    assert display_time("not a timestamp") == "not a timestamp"
