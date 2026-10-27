"""Presentation helpers for conversation lists and safely formatted message rows."""

from html import escape

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QTextOption
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTextEdit

from client.gui.styles import PALETTE, display_time

ROW_PRESENTATION = Qt.UserRole + 1


class ConversationDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(180, 70)

    def paint(self, painter, option, index):
        presentation = index.data(ROW_PRESENTATION) or {}
        base = QStyleOptionViewItem(option)
        self.initStyleOption(base, index)
        base.text = ""
        base.widget.style().drawControl(QStyle.CE_ItemViewItem, base, painter, base.widget)
        painter.save()
        rect = option.rect.adjusted(14, 12, -14, -10)
        font = QFont(option.font)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(PALETTE["text"]))
        title = presentation.get("title", index.data(Qt.DisplayRole) or "")
        painter.drawText(
            QRect(rect.x(), rect.y(), rect.width(), 24),
            Qt.AlignVCenter,
            painter.fontMetrics().elidedText(title, Qt.ElideRight, rect.width()),
        )
        font.setWeight(QFont.Normal)
        font.setPointSizeF(max(9, font.pointSizeF() - 1))
        painter.setFont(font)
        painter.setPen(QColor(PALETTE["secondary"]))
        painter.drawText(
            QRect(rect.x(), rect.y() + 27, rect.width(), 20),
            Qt.AlignVCenter,
            painter.fontMetrics().elidedText(
                presentation.get("subtitle", ""), Qt.ElideRight, rect.width()
            ),
        )
        painter.restore()


class MessageHistory(QTextEdit):
    """Selectable, accessible rich-text rows with every user-provided value escaped."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("history")
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAccessibleName("Conversation messages")
        self.setAccessibleDescription(
            "Sender, local date and time, then message text. Select text to copy."
        )
        self.document().setDocumentMargin(8)
        self._rendered = None

    def clear(self):
        self._rendered = None
        super().clear()

    def render_messages(self, messages, username: str) -> None:
        signature = (
            username,
            tuple((m["id"], m["sender"], m["created_at"], m["content"]) for m in messages),
        )
        if signature == self._rendered:
            return  # Preserve text selection and avoid a layout pass on unchanged polling results.
        rows = []
        for message in messages:
            own = message["sender"] == username
            sender = escape(message["sender"])
            stamp = escape(display_time(message["created_at"]))
            content = escape(message["content"]).replace("\n", "<br>")
            color = PALETTE["own_message"] if own else PALETTE["surface"]
            cell = (
                f'<td width="84%" bgcolor="{color}" style="padding:12px 16px;">'
                f'<p style="margin:0 0 8px 0;"><b style="color:#edf2f8;">{sender}</b>'
                f' &nbsp; <span style="color:#bbc8d9;font-size:9pt;">{stamp}</span></p>'
                f'<p style="margin:0;line-height:125%;white-space:pre-wrap;color:#edf2f8;">{content}</p></td>'
            )
            spacer = '<td width="16%"></td>'
            rows.append(
                '<table width="100%" cellspacing="0" cellpadding="0"><tr>'
                + (spacer + cell if own else cell + spacer)
                + '</tr></table><p style="margin:0;font-size:5pt;">&nbsp;</p>'
            )
        self.setHtml("".join(rows))
        self._rendered = signature
