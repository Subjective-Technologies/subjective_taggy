#!/usr/bin/env python3
import sys
import os
import sqlite3
import io

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QScrollArea, QFileDialog, QColorDialog, QMenu, QAction,
    QStatusBar, QSplitter, QFontComboBox, QSpinBox, QLayout, QSizePolicy, QLayoutItem, QCheckBox
)
from PyQt5.QtGui import (
    QPainter, QColor, QPixmap, QImage, QDrag, QCursor, QFont, QPen
)
from PyQt5.QtCore import (
    Qt, QMimeData, QByteArray, QBuffer, QIODevice, QSize, QRect
)

from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtWidgets import QTextEdit

from datetime import datetime  # Ensure this import is present at the top

from PyQt5.QtWidgets import QGraphicsDropShadowEffect

from PyQt5.QtWidgets import QTextEdit, QGraphicsDropShadowEffect

from PyQt5.QtCore import pyqtSignal

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtGui import QPixmap
import base64
from PyQt5.QtGui import QPixmap, QBrush, QPalette


from PyQt5.QtWidgets import QPushButton, QInputDialog, QMenu, QAction, QSizePolicy, QColorDialog, QFileDialog
from PyQt5.QtGui import QFont, QColor, QPixmap
from PyQt5.QtCore import QByteArray, Qt, QMimeData

from PyQt5.QtWidgets import QVBoxLayout, QGridLayout
from PyQt5.QtWidgets import QComboBox

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit, QGraphicsDropShadowEffect, QMenu, QAction, QApplication
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit, QGraphicsDropShadowEffect, QMenu, QAction, QApplication
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTextEdit, QGraphicsDropShadowEffect, QMenu, QAction, QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton

from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap, QImage, QDrag, QCursor
from PyQt5.QtCore import QMimeData, Qt, QSize, QRect, pyqtSignal

from datetime import datetime
import os
import re
import re
from PyQt5.QtGui import QPixmap, QImage


import re
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QTextEdit, QGraphicsDropShadowEffect, QMenu, QAction,
                             QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton)
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap, QImage, QDrag, QCursor
from PyQt5.QtCore import QMimeData, Qt, QSize, QRect, pyqtSignal

from datetime import datetime



class TaskInputTextEdit(QTextEdit):
    # This signal is emitted when the user submits (Enter without Shift).
    submitSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        # If Enter or Return is pressed without Shift, emit submitSignal.
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and not (event.modifiers() & Qt.ShiftModifier):
            self.submitSignal.emit()
            event.accept()
        else:
            # For Shift+Enter or other keys, perform default behavior.
            super().keyPressEvent(event)



# =============================================================================
# Helper Class: ColorHelper
# =============================================================================
class ColorHelper:
    @staticmethod
    def isColorLight(color):
        """Determine if a QColor (or hex string) is light."""
        if isinstance(color, str):
            qcolor = QColor(color)
        else:
            qcolor = color
        r, g, b = qcolor.red(), qcolor.green(), qcolor.blue()
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance > 186

    @staticmethod
    def getDistinctColor(existing_colors):
        """Return a hex color string distinct from the ones in existing_colors."""
        candidates = [
            "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
            "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080"
        ]
        for candidate in candidates:
            if candidate not in existing_colors:
                return candidate
        return "#000000"
    

# =============================================================================
# Database Manager
# =============================================================================
class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self.connect()
        self.initializeSchema()

    def connect(self):
        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def initializeSchema(self):
        cursor = self.conn.cursor()
        # Create tags table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                color TEXT,
                background_image BLOB
            )
        """)
        # Create tasks table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT
            )
        """)
        # Create task_tags table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                tag_id INTEGER,
                UNIQUE(task_id, tag_id)
            )
        """)
        self.conn.commit()

    def getTasks(self, filters=None):
        """
        Retrieves tasks from the database.
        If filters contains tag IDs, only returns tasks that have ALL the specified tags (using AND logic).
        If filters contains text, tasks must match the search text.
        """
        cursor = self.conn.cursor()
        params = []
        
        # Build the base query.
        query = "SELECT * FROM tasks t"
        conditions = []
        
        # Add text filtering if provided.
        if filters and 'text' in filters and filters['text']:
            conditions.append("t.text LIKE ?")
            params.append("%{}%".format(filters['text']))
        
        # Add tag filtering using a subquery.
        if filters and 'tags' in filters and filters['tags']:
            tag_ids = filters['tags']
            # This subquery returns task_ids that have all of the specified tags.
            subquery = (
                "SELECT task_id FROM task_tags "
                "WHERE tag_id IN (" + ",".join(["?"] * len(tag_ids)) + ") "
                "GROUP BY task_id HAVING COUNT(DISTINCT tag_id) = ?"
            )
            conditions.append("t.id IN (" + subquery + ")")
            params.extend(tag_ids)
            params.append(len(tag_ids))
        
        # If any conditions exist, add them to the query.
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        tasks = []
        for row in rows:
            task = Task.load_from_db(row)
            # Retrieve associated tags for the task.
            tag_cursor = self.conn.cursor()
            tag_cursor.execute("""
                SELECT tags.* FROM tags
                JOIN task_tags ON tags.id = task_tags.tag_id
                WHERE task_tags.task_id = ?
            """, (task.id,))
            tag_rows = tag_cursor.fetchall()
            for tag_row in tag_rows:
                tag = Tag.load_from_db(tag_row)
                task.tags.append(tag)
            tasks.append(task)
        return tasks


    def getTags(self, search=""):
        """
        Retrieves tags from the database.
        Optionally filters by tag name.
        """
        cursor = self.conn.cursor()
        if search:
            cursor.execute("SELECT * FROM tags WHERE name LIKE ?", ("%{}%".format(search),))
        else:
            cursor.execute("SELECT * FROM tags")
        rows = cursor.fetchall()
        tags = [Tag.load_from_db(row) for row in rows]
        return tags

    def saveTask(self, task):
        """
        Inserts or updates a task record and its tag assignments.
        """
        cursor = self.conn.cursor()
        if task.id is None:
            cursor.execute("INSERT INTO tasks (text) VALUES (?)", (task.text,))
            task.id = cursor.lastrowid
        else:
            cursor.execute("UPDATE tasks SET text=? WHERE id=?", (task.text, task.id))
            # For simplicity, delete all tag assignments and reinsert.
            cursor.execute("DELETE FROM task_tags WHERE task_id=?", (task.id,))
        # Insert tag assignments.
        for tag in task.tags:
            cursor.execute("INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?,?)", (task.id, tag.id))
        self.conn.commit()

    def saveTag(self, tag):
        """
        Inserts or updates a tag record.
        """
        cursor = self.conn.cursor()
        if tag.id is None:
            cursor.execute("INSERT INTO tags (name, color, background_image) VALUES (?,?,?)",
                           (tag.name, tag.color, tag.background_image))
            tag.id = cursor.lastrowid
        else:
            cursor.execute("UPDATE tags SET name=?, color=?, background_image=? WHERE id=?",
                           (tag.name, tag.color, tag.background_image, tag.id))
        self.conn.commit()

    def assignTagToTask(self, task_id, tag_id):
        """
        Creates a task-tag assignment.
        """
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?,?)", (task_id, tag_id))
        self.conn.commit()

# =============================================================================
# Domain Classes: Tag and Task
# =============================================================================
class Tag:
    def __init__(self, name, color=None, background_image=None, id=None):
        self.id = id
        self.name = name
        self.color = color if color else "#000000"
        self.background_image = background_image  # stored as binary data

    def save(self, db_manager: DatabaseManager):
        db_manager.saveTag(self)

    @staticmethod
    def load_from_db(data):
        return Tag(
            name=data["name"],
            color=data["color"],
            background_image=data["background_image"],
            id=data["id"]
        )

    def setColor(self, new_color):
        self.color = new_color

    def setBackgroundImage(self, image_data):
        self.background_image = image_data



class Task:
    def __init__(self, text, tags=None, id=None, timestamp=""):
        self.id = id
        self.text = text
        self.tags = tags if tags else []
        self.timestamp = timestamp  # timestamp is a string in ISO format

    def save(self, db_manager: DatabaseManager):
        db_manager.saveTask(self)

    def addTag(self, tag: 'Tag', db_manager: DatabaseManager):
        if tag not in self.tags:
            self.tags.append(tag)
            if db_manager and self.id:
                db_manager.assignTagToTask(self.id, tag.id)

    def removeTag(self, tag: 'Tag'):
        if tag in self.tags:
            self.tags.remove(tag)

    @staticmethod
    def load_from_db(data):
        # Check if "timestamp" exists, is not None, and is not empty.
        if "timestamp" in data.keys() and data["timestamp"] is not None and data["timestamp"].strip() != "":
            ts = data["timestamp"]
        else:
            # Use current timestamp as fallback.
            ts = datetime.now().isoformat()
        return Task(
            text=data["text"],
            id=data["id"],
            tags=[],
            timestamp=ts
        )


# =============================================================================
# UI Widget Classes
# =============================================================================

# (Assume ColorHelper and other necessary classes/imports are already defined)

class TagWidget(QPushButton):
    def __init__(self, tag, parent=None, db_manager=None):
        super().__init__(tag.name, parent)
        self.tag = tag
        self.db_manager = db_manager
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        font = self.font()
        font.setBold(True)
        self.setFont(font)
        self.updateStyle()
        self.deleteButton = QPushButton("×", self)
        self.deleteButton.setStyleSheet("""
            QPushButton {
                background-color: black;
                color: white;
                font-weight: bold;
                border: none;
            }
        """)
        self.deleteButton.setFixedSize(12, 12)
        self.deleteButton.clicked.connect(self.deleteTag)

    def updateStyle(self):
        bg_color = self.tag.color
        # For the Completed tag, force text to black; otherwise use luminance.
        if self.tag.name == "Completed":
            text_color = "#000000"
        else:
            text_color = "#000000" if ColorHelper.isColorLight(bg_color) else "#FFFFFF"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        self.setText(self.tag.name)
        self.adjustSize()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # For tags other than the protected ones, add options.
        if self.tag.name not in ["Completed", "Doing"]:
            changeColorAction = QAction("Change Color", self)
            changeColorAction.triggered.connect(self.changeColor)
            menu.addAction(changeColorAction)
            renameAction = QAction("Rename Tag", self)
            renameAction.triggered.connect(self.renameTag)
            menu.addAction(renameAction)
        assignImageAction = QAction("Assign Background Image", self)
        assignImageAction.triggered.connect(self.assignBackgroundImage)
        menu.addAction(assignImageAction)
        menu.exec_(event.globalPos())

    def renameTag(self):
        new_name, ok = QInputDialog.getText(self, "Rename Tag", "New tag name:")
        if ok and new_name.strip():
            self.tag.name = new_name.strip()
            if self.db_manager:
                self.tag.save(self.db_manager)
            self.updateStyle()

    def changeColor(self):
        if self.tag.name in ["Completed", "Doing"]:
            return
        color = QColorDialog.getColor()
        if color.isValid():
            self.tag.setColor(color.name())
            if self.db_manager:
                self.tag.save(self.db_manager)
            self.updateStyle()

    def assignBackgroundImage(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Select Background Image", "",
                                                  "Images (*.png *.jpg *.bmp)", options=options)
        if fileName:
            with open(fileName, "rb") as f:
                image_data = f.read()
            self.tag.setBackgroundImage(image_data)
            if self.db_manager:
                self.tag.save(self.db_manager)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setData("application/x-tag", QByteArray(str(self.tag.id).encode()))
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction)
        super().mousePressEvent(event)

    def deleteTag(self):
        if self.db_manager:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("DELETE FROM tags WHERE id=?", (self.tag.id,))
            cursor.execute("DELETE FROM task_tags WHERE tag_id=?", (self.tag.id,))
            self.db_manager.conn.commit()
        self.deleteLater()
        main_window = self.window()
        if hasattr(main_window, "updateTagList"):
            main_window.updateTagList()
        if hasattr(main_window, "updateTaskList"):
            main_window.updateTaskList()

    def sizeHint(self):
        fm = self.fontMetrics()
        rect = fm.boundingRect(self.text())
        width = rect.width() + 8
        height = rect.height() + 8
        return QSize(width, height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.deleteButton.move(self.width() - self.deleteButton.width(), 0)


# Custom QTextEdit to help with key handling (if desired)
class EditableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
    def keyPressEvent(self, event):
        # If Enter (Return) is pressed without Shift, finish editing.
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and not (event.modifiers() & Qt.ShiftModifier):
            if self.parent() is not None and hasattr(self.parent(), "finishEditing"):
                self.parent().finishEditing(event)
            event.accept()
        else:
            super().keyPressEvent(event)




# (Assume that TagWidget, Tag, and DatabaseManager classes are defined elsewhere.)

import re
from PyQt5.QtCore import Qt, QMimeData, QSize, QRect
from PyQt5.QtGui import QFont, QColor, QPixmap, QImage, QDrag, QCursor, QPainter
from PyQt5.QtWidgets import QWidget, QTextEdit, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsDropShadowEffect, QMenu, QAction, QApplication
from datetime import datetime

# Assume that TagWidget, Tag, and DatabaseManager classes are defined elsewhere.

class TaskBubble(QWidget):
    current_filter_tag = None
    # Balanced card body height range (text area only).
    TEXT_MIN_H = 64
    TEXT_MAX_H = 168

    def __init__(self, task, db_manager=None, font=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.db_manager = db_manager
        self.taskBubbleFont = font if font is not None else QFont("Noto Sans", 13)
        self._card_width = 320
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)
        self.initUI()
        self.setupButtons()

    def applyCardWidth(self, width):
        """Lock card to a consistent grid/list width and reflow text."""
        self._card_width = max(220, int(width))
        self.setFixedWidth(self._card_width)
        self.adjustTextEditHeight()
        self._placeChromeButtons()

    def initUI(self):
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 28, 12, 10)
        self.layout.setSpacing(8)
        self.setLayout(self.layout)

        # Create a QTextEdit to display (and later edit) the task text.
        self.textEdit = QTextEdit(self)
        self.textEdit.setText(self.task.text)
        self.textEdit.setFont(self.taskBubbleFont)
        self.textEdit.setFrameStyle(QTextEdit.NoFrame)
        self.textEdit.setReadOnly(True)
        self.textEdit.setStyleSheet(
            "background: transparent; color: #F3F4F6; padding: 2px 2px 0 2px; border: none;"
        )
        self.textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.addWidget(self.textEdit)

        # Create a dedicated thumbnail container (for image/PDF thumbnails).
        self.thumbnailContainer = QWidget(self)
        self.thumbnailLayout = QHBoxLayout(self.thumbnailContainer)
        self.thumbnailLayout.setContentsMargins(0, 0, 0, 0)
        self.thumbnailLayout.setSpacing(5)
        self.thumbnailContainer.setLayout(self.thumbnailLayout)
        self.thumbnailContainer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.insertWidget(1, self.thumbnailContainer)

        # Create the timestamp label (chrome overlay).
        ts = self.task.timestamp if self.task.timestamp else ""
        self.timestampLabel = QLabel(ts, self)
        self.timestampLabel.setStyleSheet(
            "background-color: rgba(0,0,0,160); color: #D1D5DB; font-size: 9pt;"
            "padding: 2px 6px; border-radius: 4px;"
        )
        self.timestampLabel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.timestampLabel.adjustSize()

        # Create a horizontal layout for tag buttons.
        self.tagLayout = QHBoxLayout()
        self.tagLayout.setSpacing(4)
        self.tagLayout.addStretch()  # Right-align tag buttons.
        for tag in self.task.tags:
            tag_button = TagWidget(tag, db_manager=self.db_manager)
            tag_button.setFixedHeight(max(22, tag_button.sizeHint().height()))
            if tag.name in ["Doing", "Completed", "Note"]:
                tag_button.deleteButton.hide()
            self.tagLayout.addWidget(tag_button)
        self.layout.addLayout(self.tagLayout)

        # Compact card chrome.
        self.setStyleSheet(
            "TaskBubble {"
            "  background-color: #141414;"
            "  border: 1px solid #3F3F46;"
            "  border-radius: 10px;"
            "}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        self.timestampLabel.setText(ts)
        self.adjustTextEditHeight()

    def setupButtons(self):
        btn_css = """
            QPushButton {
                background-color: #27272A;
                color: #E5E7EB;
                font-weight: bold;
                border: 1px solid #3F3F46;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
        """
        self.deleteButton = QPushButton("×", self)
        self.deleteButton.setStyleSheet(btn_css)
        self.deleteButton.setFixedSize(20, 20)
        self.deleteButton.setToolTip("Delete task")
        self.deleteButton.clicked.connect(self.deleteTask)

        self.editButton = QPushButton("✎", self)
        self.editButton.setStyleSheet(btn_css)
        self.editButton.setFixedSize(20, 20)
        self.editButton.setToolTip("Edit task")
        self.editButton.clicked.connect(self.startEditing)

        self.copyButton = QPushButton("⧉", self)
        self.copyButton.setStyleSheet(btn_css)
        self.copyButton.setFixedSize(20, 20)
        self.copyButton.setToolTip("Copy text")
        self.copyButton.clicked.connect(lambda: QApplication.clipboard().setText(self.task.text))
        self._placeChromeButtons()

    def _placeChromeButtons(self):
        if not hasattr(self, "deleteButton"):
            return
        margin = 6
        gap = 4
        x = self.width() - margin
        for btn in (self.deleteButton, self.editButton, self.copyButton):
            x -= btn.width()
            btn.move(x, margin)
            x -= gap
        if hasattr(self, "timestampLabel"):
            self.timestampLabel.adjustSize()
            self.timestampLabel.move(margin, margin)

    def adjustTextEditHeight(self):
        self.textEdit.document().setTextWidth(max(40, self._card_width - 28))
        self.textEdit.document().adjustSize()
        doc_height = self.textEdit.document().size().height() + 12
        if doc_height <= 0:
            fm = self.textEdit.fontMetrics()
            doc_height = self.textEdit.document().blockCount() * fm.lineSpacing() + 12
        threshold = self.TEXT_MAX_H
        if doc_height < threshold:
            self.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.textEdit.setFixedHeight(max(self.TEXT_MIN_H, int(doc_height)))
        else:
            self.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.textEdit.setFixedHeight(int(threshold))
        self.updateGeometry()

    def startEditing(self):
        print("startEditing called", flush=True)
        self.textEdit.setReadOnly(False)
        self.textEdit.setFocus()
        self.textEdit.selectAll()

    def finishEditing(self, event):
        print("finishEditing called", flush=True)
        new_text = self.textEdit.toPlainText().strip()
        print("New text:", new_text, flush=True)
        if new_text:
            self.task.text = new_text
            self.task.save(self.db_manager)
            self.setTask(self.task)
        self.textEdit.setReadOnly(True)
        self.adjustTextEditHeight()
        QTextEdit.focusOutEvent(self.textEdit, event)

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and not (event.modifiers() & Qt.ShiftModifier):
            if not self.textEdit.isReadOnly():
                print("Enter pressed while editing; finishing editing", flush=True)
                self.finishEditing(event)
                event.accept()
                return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        print("mouseDoubleClickEvent called; starting editing", flush=True)
        self.startEditing()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        print("contextMenuEvent: showing context menu", flush=True)
        menu = QMenu(self)
        copyAction = QAction("Copy Task Text", self)
        copyAction.triggered.connect(lambda: QApplication.clipboard().setText(self.task.text))
        menu.addAction(copyAction)
        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-tag"):
            print("dragEnterEvent: Accepting drop", flush=True)
            event.acceptProposedAction()
        else:
            print("dragEnterEvent: Ignoring drop", flush=True)
            event.ignore()

    def dropEvent(self, event):
        print("dropEvent called", flush=True)
        if event.mimeData().hasUrls():
            print("dropEvent: Detected file drop", flush=True)
            for url in event.mimeData().urls():
                local_file = url.toLocalFile()
                print("Dropped file:", local_file, flush=True)
                if local_file:
                    ext = os.path.splitext(local_file)[1].lower()
                    print("File extension:", ext, flush=True)
                    if ext in ['.png', '.jpg', '.jpeg']:
                        print("Processing image file drop", flush=True)
                        image = QImage(local_file)
                        if image.isNull():
                            print("Failed to load image from", local_file, flush=True)
                        else:
                            print("Image loaded successfully from", local_file, flush=True)
                            thumbnail = image.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            thumb_label = QLabel(self)
                            thumb_label.setProperty("isThumbnail", True)
                            thumb_label.setFixedSize(64, 64)
                            thumb_label.setPixmap(QPixmap.fromImage(thumbnail))
                            print("Thumbnail created, size:", thumbnail.size(), flush=True)
                            self.thumbnailLayout.addWidget(thumb_label)
                            thumb_label.show()
                            with open(local_file, "rb") as f:
                                binary_content = f.read()
                            mime_type = "png" if ext == ".png" else "jpg"
                            print("Inserting document record for", os.path.basename(local_file), flush=True)
                            cursor = self.db_manager.conn.cursor()
                            cursor.execute(
                                "INSERT INTO documents (name, binary_content, mime_type, text_caption) VALUES (?,?,?,?)",
                                (os.path.basename(local_file), binary_content, mime_type, "")
                            )
                            self.db_manager.conn.commit()
                            reference = f"[[{os.path.basename(local_file)}]]"
                            if reference not in self.task.text:
                                self.task.text += " " + reference
                                self.task.save(self.db_manager)
                                print("Task text updated with reference:", reference, flush=True)
                    elif ext == ".pdf":
                        print("Processing PDF file drop", flush=True)
                        pdf_icon = QPixmap("pdf_icon.png")
                        if pdf_icon.isNull():
                            print("pdf_icon.png not found; creating gray placeholder", flush=True)
                            pdf_icon = QPixmap(64, 64)
                            pdf_icon.fill(QColor("gray"))
                        thumb_label = QLabel(self)
                        thumb_label.setProperty("isThumbnail", True)
                        thumb_label.setFixedSize(64, 64)
                        thumb_label.setPixmap(pdf_icon.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        self.thumbnailLayout.addWidget(thumb_label)
                        thumb_label.show()
                        with open(local_file, "rb") as f:
                            binary_content = f.read()
                        mime_type = "pdf"
                        print("Inserting document record for PDF:", os.path.basename(local_file), flush=True)
                        cursor = self.db_manager.conn.cursor()
                        cursor.execute(
                            "INSERT INTO documents (name, binary_content, mime_type, text_caption) VALUES (?,?,?,?)",
                            (os.path.basename(local_file), binary_content, mime_type, "")
                        )
                        self.db_manager.conn.commit()
                        reference = f"[[{os.path.basename(local_file)}]]"
                        if reference not in self.task.text:
                            self.task.text += " " + reference
                            self.task.save(self.db_manager)
                            print("Task text updated with PDF reference:", reference, flush=True)
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-tag"):
            print("dropEvent: Detected tag drop", flush=True)
            try:
                tag_data = event.mimeData().data("application/x-tag")
                tag_id = int(bytes(tag_data).decode())
                print("Tag id dropped:", tag_id, flush=True)
            except Exception as e:
                print("Error decoding tag id:", e, flush=True)
                event.ignore()
                return
            if self.db_manager:
                all_tags = self.db_manager.getTags()
                new_tag = next((t for t in all_tags if t.id == tag_id), None)
                if new_tag:
                    if new_tag.name in ["Doing", "Completed", "Note"]:
                        self.task.tags = [t for t in self.task.tags if t.name not in ["Doing", "Completed", "Note"]]
                    self.task.tags = [t for t in self.task.tags if t.id != new_tag.id]
                    self.task.tags.append(new_tag)
                    unique = {}
                    for t in self.task.tags:
                        unique[t.id] = t
                    self.task.tags = list(unique.values())
                    self.task.save(self.db_manager)
                    self.setTask(self.task)
                    print("Tag drop processed; task updated", flush=True)
            event.acceptProposedAction()
        else:
            print("dropEvent: No supported format detected", flush=True)
            event.ignore()

    def setTask(self, task):
        print("=== setTask() called on reload ===", flush=True)
        self.task = task
        self.textEdit.setText(task.text)
        self.timestampLabel.setText(task.timestamp if task.timestamp else "")
        # Clear the thumbnail container.
        print("Clearing thumbnail container...", flush=True)
        while self.thumbnailLayout.count():
            item = self.thumbnailLayout.takeAt(0)
            if item is not None and item.widget() is not None:
                print("Deleting thumbnail widget", flush=True)
                item.widget().deleteLater()
        # Process document references.
        refs = re.findall(r'\[\[(.*?)\]\]', task.text)
        print("Found document references on reload:", refs, flush=True)
        for ref in refs:
            ref_clean = ref.strip()
            print("Reload processing reference:", ref_clean, flush=True)
            try:
                cursor = self.db_manager.conn.cursor()
                cursor.execute("SELECT * FROM documents WHERE lower(name)=lower(?)", (ref_clean,))
                doc_row = cursor.fetchone()
                if doc_row:
                    mime = doc_row["mime_type"].lower() if "mime_type" in doc_row.keys() else ""
                    print(f"Reload: Document record found for '{ref_clean}' with MIME type: {mime}", flush=True)
                    thumb_label = QLabel(self)
                    thumb_label.setProperty("isThumbnail", True)
                    thumb_label.setFixedSize(64, 64)
                    if mime in ["png", "jpg", "jpeg"]:
                        image = QImage.fromData(doc_row["binary_content"])
                        if image.isNull():
                            print(f"Reload: Failed to load image for '{ref_clean}'", flush=True)
                            continue
                        thumbnail = image.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb_label.setPixmap(QPixmap.fromImage(thumbnail))
                        print(f"Reload: Thumbnail for '{ref_clean}' created, size: {thumbnail.size()}", flush=True)
                    elif mime == "pdf":
                        pdf_icon = QPixmap("pdf_icon.png")
                        if pdf_icon.isNull():
                            print("Reload: pdf_icon.png not found; creating gray placeholder", flush=True)
                            pdf_icon = QPixmap(64, 64)
                            pdf_icon.fill(QColor("gray"))
                        thumbnail = pdf_icon.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb_label.setPixmap(thumbnail)
                        print(f"Reload: PDF thumbnail for '{ref_clean}' created", flush=True)
                    else:
                        print(f"Reload: Unsupported MIME type for '{ref_clean}': {mime}", flush=True)
                        continue
                    self.thumbnailLayout.addWidget(thumb_label)
                    thumb_label.show()
                else:
                    print(f"Reload: No document record found for '{ref_clean}'", flush=True)
            except Exception as e:
                print(f"Reload: Error processing document reference '{ref_clean}': {e}", flush=True)
        # Update the tag layout.
        print("Reload: Updating tag layout...", flush=True)
        while self.tagLayout.count() > 1:
            item = self.tagLayout.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()
        for tag in self.task.tags:
            tag_button = TagWidget(tag, db_manager=self.db_manager)
            tag_button.setFixedHeight(tag_button.sizeHint().height())
            if tag.name in ["Doing", "Completed", "Note"]:
                tag_button.deleteButton.hide()
            self.tagLayout.addWidget(tag_button)
        self.adjustTextEditHeight()
        self.update()
        print("=== setTask() completed on reload ===", flush=True)

    def deleteTask(self):
        print("deleteTask called", flush=True)
        if self.db_manager:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id=?", (self.task.id,))
            cursor.execute("DELETE FROM task_tags WHERE task_id=?", (self.task.id,))
            self.db_manager.conn.commit()
            print("Task deleted from database", flush=True)
        self.deleteLater()
        main_window = self.window()
        if hasattr(main_window, "updateTaskList"):
            main_window.updateTaskList()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._placeChromeButtons()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QColor("#3F3F46"))
        painter.setBrush(QColor("#141414"))
        painter.drawRoundedRect(rect, 10, 10)
        super().paintEvent(event)


class TaskListContainer(QWidget):
    DEFAULT_BG = "#1C1C1F"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_pixmap = None
        self.bg_color = self.DEFAULT_BG
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setBackgroundPixmap(self, pixmap):
        self.background_pixmap = pixmap
        self.bg_color = None
        self.update()

    def clearBackgroundPixmap(self):
        self.background_pixmap = None
        self.update()

    def setBackgroundColor(self, color):
        # Empty color restores the default panel background (not mid-grey).
        self.bg_color = color if color and color.strip() != "" else self.DEFAULT_BG
        self.background_pixmap = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.background_pixmap is not None:
            painter.drawPixmap(self.rect(), self.background_pixmap)
        elif self.bg_color is not None and self.bg_color.strip() != "":
            painter.fillRect(self.rect(), QColor(self.bg_color))
        else:
            painter.fillRect(self.rect(), QColor(self.DEFAULT_BG))



class TagFilterWidget(QWidget):
    """
    A designated area in the left pane where tags can be dropped to filter tasks.
    Each filter tag is rendered as a small button with bold font and 8px total padding.
    A small delete cross (a black square with a white bold '×') appears at the top-right of each tag.
    Clicking the cross removes the tag from the filter list.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout = FlowLayout(self, margin=4, spacing=6)
        self.setLayout(self.layout)
        self.filter_tags = []  # Holds Tag objects currently used as filters
        self._placeholder = QLabel("Drop tags here to filter")
        self._placeholder.setStyleSheet("color: #71717A; font-size: 11px; padding: 4px;")
        self.layout.addWidget(self._placeholder)

    class FilterTagButton(QPushButton):
        def __init__(self, tag, parent=None):
            super().__init__(tag.name, parent)
            self.tag = tag
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            font = self.font()
            font.setBold(True)
            self.setFont(font)
            self.updateStyle()
            # Create a small delete (cross) button.
            self.deleteButton = QPushButton("×", self)
            self.deleteButton.setStyleSheet("""
                QPushButton {
                    background-color: black;
                    color: white;
                    font-weight: bold;
                    border: none;
                }
            """)
            self.deleteButton.setFixedSize(12, 12)
            self.deleteButton.clicked.connect(self.deleteSelf)

        def updateStyle(self):
            bg_color = self.tag.color
            # For "Completed" tag force text to black; otherwise decide based on luminance.
            if self.tag.name == "Completed":
                text_color = "#000000"
            else:
                text_color = "#000000" if ColorHelper.isColorLight(bg_color) else "#FFFFFF"
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: {text_color};
                    border-radius: 4px;
                    padding: 0px;
                    margin: 0px;
                }}
            """)
            self.setText(self.tag.name)
            self.adjustSize()

        def sizeHint(self):
            fm = self.fontMetrics()
            text_rect = fm.boundingRect(self.text())
            width = text_rect.width() + 8  # 8px total padding
            height = text_rect.height() + 8
            return QSize(width, height)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.deleteButton.move(self.width() - self.deleteButton.width(), 0)

        def deleteSelf(self):
            parent = self.parent()
            if hasattr(parent, "removeFilterTag"):
                parent.removeFilterTag(self.tag)
            self.deleteLater()

    def _rebuildFilterButtons(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        if not self.filter_tags:
            self._placeholder = QLabel("Drop tags here to filter")
            self._placeholder.setStyleSheet("color: #71717A; font-size: 11px; padding: 4px;")
            self.layout.addWidget(self._placeholder)
            return
        for t in self.filter_tags:
            button = TagFilterWidget.FilterTagButton(t, parent=self)
            self.layout.addWidget(button)

    def addFilterTag(self, tag):
        if tag not in self.filter_tags:
            self.filter_tags.append(tag)
            self._rebuildFilterButtons()
            main_window = self.window()
            if hasattr(main_window, "updateTaskList"):
                main_window.updateTaskList()

    def removeFilterTag(self, tag):
        if tag in self.filter_tags:
            self.filter_tags.remove(tag)
        self._rebuildFilterButtons()
        main_window = self.window()
        if hasattr(main_window, "updateTaskList"):
            main_window.updateTaskList()

    def clearFilters(self):
        self.filter_tags = []
        self._rebuildFilterButtons()
        main_window = self.window()
        if hasattr(main_window, "updateTaskList"):
            main_window.updateTaskList()

    def getCurrentFilters(self):
        return self.filter_tags

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-tag"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-tag"):
            try:
                tag_id = int(bytes(event.mimeData().data("application/x-tag")).decode())
            except Exception as e:
                print("Error decoding tag id:", e)
                event.ignore()
                return
            main_window = self.window()
            # Instead of using self.db_manager (which does not exist on this widget),
            # we obtain it from the main window.
            if hasattr(main_window, "db_manager"):
                tags = main_window.db_manager.getTags()
                tag = next((t for t in tags if t.id == tag_id), None)
                if tag:
                    self.addFilterTag(tag)
        event.acceptProposedAction()




class TaskListWidget(QScrollArea):
    # Preferred card width for auto grid columns (px).
    GRID_MIN_CARD = 300
    GRID_GAP = 14
    LIST_MAX_FRAC = 0.72

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.layout_mode = "Grid"  # default: grid mode
        self._last_tasks = []
        self._last_font = None
        self._resize_refresh_pending = False
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.container = TaskListContainer()
        self.setLayoutMode(self.layout_mode)
        self.setWidget(self.container)
        self.setWidgetResizable(True)

    def gridColumnCount(self):
        vp_w = max(self.viewport().width(), self.GRID_MIN_CARD)
        cols = max(1, vp_w // (self.GRID_MIN_CARD + self.GRID_GAP))
        return min(cols, 6)

    def cardWidthForMode(self):
        vp_w = max(self.viewport().width(), 200)
        if self.layout_mode == "Grid":
            cols = self.gridColumnCount()
            usable = vp_w - self.GRID_GAP * (cols + 1)
            return max(240, usable // cols)
        return max(320, int(vp_w * self.LIST_MAX_FRAC))

    def setLayoutMode(self, mode):
        self.layout_mode = mode
        new_container = TaskListContainer()
        if mode == "Grid":
            new_layout = QGridLayout()
            new_layout.setSpacing(self.GRID_GAP)
            new_layout.setContentsMargins(12, 12, 12, 12)
            new_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        else:
            new_layout = QVBoxLayout()
            new_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            new_layout.setSpacing(self.GRID_GAP)
            new_layout.setContentsMargins(16, 12, 16, 12)
        new_container.setLayout(new_layout)
        self.container.deleteLater()
        self.container = new_container
        self.setWidget(self.container)

    def refreshTasks(self, tasks, font):
        self._last_tasks = list(tasks)
        self._last_font = font
        layout = self.container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        card_w = self.cardWidthForMode()
        if self.layout_mode == "Grid":
            grid_layout = layout
            col_count = self.gridColumnCount()
            for c in range(col_count):
                grid_layout.setColumnStretch(c, 1)
            row = 0
            col = 0
            for task in tasks:
                bubble = TaskBubble(task, db_manager=self.db_manager, font=font)
                bubble.applyCardWidth(card_w)
                grid_layout.addWidget(bubble, row, col, Qt.AlignTop)
                col += 1
                if col >= col_count:
                    col = 0
                    row += 1
            # Keep rows packed at the top (no vertical stretch of empty space).
            grid_layout.setRowStretch(row + 1, 1)
        else:
            for task in tasks:
                bubble = TaskBubble(task, db_manager=self.db_manager, font=font)
                bubble.applyCardWidth(card_w)
                layout.addWidget(bubble, 0, Qt.AlignHCenter | Qt.AlignTop)
            layout.addStretch(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Debounce reflow so continuous resize doesn't thrash the UI.
        if self._resize_refresh_pending:
            return
        self._resize_refresh_pending = True
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(80, self._onResizeSettle)

    def _onResizeSettle(self):
        self._resize_refresh_pending = False
        if self._last_font is None:
            return
        # Only reflow grid when column count would change; always update card widths.
        self.refreshTasks(self._last_tasks, self._last_font)



# =============================================================================
# Main Application Window
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Taggy Todo")
        self.resize(1280, 800)
        # Readable default for dense grid cards
        self.taskBubbleFont = QFont("Noto Sans", 13)
        # Default ordering: True means newest first, False means oldest first.
        self.orderNewestFirst = True
        # Initialize the default database (todos.db in the user's home folder)
        home = os.path.expanduser("~")
        default_db = os.path.join(home, "todos.db")
        self.db_manager = DatabaseManager(default_db)
        self.initUI()

    def initUI(self):
        # Start the application maximized.
        self.showMaximized()
        self.statusBar().showMessage("Ready to accept tasks and tags.")

        toolbar = self.addToolBar("File")
        toolbar.setMovable(False)
        openButton = QPushButton("Open")
        openButton.clicked.connect(self.openDatabase)
        toolbar.addWidget(openButton)

        # Font family control for task bubbles.
        self.fontCombo = QFontComboBox()
        self.fontCombo.setCurrentFont(self.taskBubbleFont)
        self.fontCombo.currentFontChanged.connect(self.changeTaskBubbleFont)
        toolbar.addWidget(self.fontCombo)

        # Font size control for task bubbles.
        self.fontSizeSpin = QSpinBox()
        self.fontSizeSpin.setMinimum(8)
        self.fontSizeSpin.setMaximum(72)
        self.fontSizeSpin.setValue(13)
        self.fontSizeSpin.valueChanged.connect(self.changeTaskBubbleFont)
        toolbar.addWidget(self.fontSizeSpin)

        # Ordering toggle button.
        self.orderToggleButton = QPushButton("Newest First")
        self.orderToggleButton.setCheckable(True)
        self.orderToggleButton.setChecked(True)
        self.orderToggleButton.clicked.connect(self.toggleOrder)
        toolbar.addWidget(self.orderToggleButton)

        self.darkModeButton = QPushButton("Light Mode")
        self.darkModeButton.setCheckable(True)
        self.darkModeButton.setChecked(True)
        self.darkModeButton.clicked.connect(self.toggleDarkMode)
        toolbar.addWidget(self.darkModeButton)

        # Default view: Grid
        self.layoutCombo = QComboBox()
        self.layoutCombo.addItem("Grid")
        self.layoutCombo.addItem("List")
        self.layoutCombo.setCurrentText("Grid")
        self.layoutCombo.currentTextChanged.connect(self.changeTaskLayout)
        toolbar.addWidget(self.layoutCombo)

        self.toggleDarkMode()  # Apply dark mode by default

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QHBoxLayout(centralWidget)
        mainLayout.setContentsMargins(8, 8, 8, 8)
        mainLayout.setSpacing(0)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        mainLayout.addWidget(self.splitter)

        self.leftPane = self.createLeftPane()
        self.splitter.addWidget(self.leftPane)
        self.rightPane = self.createRightPane()
        self.splitter.addWidget(self.rightPane)

        # Sidebar ~280px; tasks take the rest.
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([300, max(900, self.width() - 300)])


    def changeTaskBubbleFont(self):
        new_font = self.fontCombo.currentFont()
        new_font.setPointSize(self.fontSizeSpin.value())
        self.taskBubbleFont = new_font
        self.updateTaskList()

    def toggleOrder(self):
        self.orderNewestFirst = not self.orderNewestFirst
        self.orderToggleButton.setText("Newest First" if self.orderNewestFirst else "Oldest First")
        self.updateTaskList()

    def createLeftPane(self):
        leftWidget = QWidget()
        leftWidget.setObjectName("leftPane")
        layout = QVBoxLayout(leftWidget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        section_css = (
            "background-color: #121214; border: 1px solid #3F3F46;"
            "border-radius: 8px; padding: 6px;"
        )
        label_css = "color: #A1A1AA; font-size: 11px; font-weight: 600; padding: 2px 0;"

        # Tag search field.
        self.tagSearchField = QLineEdit()
        self.tagSearchField.setPlaceholderText("Search Tags")
        self.tagSearchField.setClearButtonEnabled(True)
        self.tagSearchField.textChanged.connect(self.updateTagList)
        layout.addWidget(self.tagSearchField)

        tags_label = QLabel("All Tags")
        tags_label.setStyleSheet(label_css)
        layout.addWidget(tags_label)

        # Scrollable tags list — this is the expanding section.
        tagListContainer = QWidget()
        tagListContainer.setStyleSheet(section_css)
        self.flowLayout = FlowLayout(tagListContainer, margin=4, spacing=6)
        tagListContainer.setLayout(self.flowLayout)
        tagScroll = QScrollArea()
        tagScroll.setWidgetResizable(True)
        tagScroll.setFrameShape(QScrollArea.NoFrame)
        tagScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tagScroll.setWidget(tagListContainer)
        tagScroll.setMinimumHeight(120)
        layout.addWidget(tagScroll, stretch=4)

        filter_label = QLabel("Filter Tags (drop tags here)")
        filter_label.setStyleSheet(label_css)
        layout.addWidget(filter_label)

        # Compact filter drop zone — does not steal vertical space.
        filterContainer = QWidget()
        filterContainer.setStyleSheet(section_css)
        filterContainer.setMaximumHeight(110)
        filterContainer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        filterLayout = QVBoxLayout(filterContainer)
        filterLayout.setContentsMargins(4, 4, 4, 4)
        filterLayout.setSpacing(4)
        self.tagFilterWidget = TagFilterWidget(filterContainer)
        filterLayout.addWidget(self.tagFilterWidget)
        sortLayout = QHBoxLayout()
        sortLabel = QLabel("Sort:")
        sortLabel.setStyleSheet("color: #A1A1AA;")
        sortLayout.addWidget(sortLabel)
        self.orderCheckBox = QCheckBox("Newest first")
        self.orderCheckBox.setChecked(True)
        self.orderCheckBox.stateChanged.connect(lambda _: self.updateTaskList())
        sortLayout.addWidget(self.orderCheckBox)
        sortLayout.addStretch()
        filterLayout.addLayout(sortLayout)
        layout.addWidget(filterContainer, stretch=0)

        status_label = QLabel("Task Status Tags")
        status_label.setStyleSheet(label_css)
        layout.addWidget(status_label)

        # Status tags: fixed compact row.
        statusContainer = QWidget()
        statusContainer.setStyleSheet(section_css)
        statusContainer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        statusContainer.setFixedHeight(52)
        self.statusTagLayout = QHBoxLayout(statusContainer)
        self.statusTagLayout.setContentsMargins(8, 6, 8, 6)
        self.statusTagLayout.setSpacing(8)
        self.statusTagLayout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        statusContainer.setLayout(self.statusTagLayout)
        layout.addWidget(statusContainer, stretch=0)

        # Populate Status Tags.
        existing_tags = self.db_manager.getTags()
        status_tags = {"Doing": None, "Completed": None}
        for tag in existing_tags:
            if tag.name in status_tags:
                status_tags[tag.name] = tag
        for status, tag in status_tags.items():
            if not tag:
                if status == "Doing":
                    tag = Tag(status, color="#FF0000")
                elif status == "Completed":
                    tag = Tag(status, color="#00FF00")
                tag.save(self.db_manager)
            btn = TagWidget(tag, db_manager=self.db_manager)
            if tag.name in ["Doing", "Completed"]:
                btn.deleteButton.hide()
            self.statusTagLayout.addWidget(btn)
        self.statusTagLayout.addStretch()

        # New Tag Input — pinned bottom.
        newTagContainer = QWidget()
        newTagLayout = QHBoxLayout(newTagContainer)
        newTagLayout.setContentsMargins(0, 4, 0, 0)
        newTagLayout.setSpacing(6)
        self.newTagField = QLineEdit()
        self.newTagField.setPlaceholderText("Add New Tag")
        self.newTagField.returnPressed.connect(self.addNewTag)
        newTagLayout.addWidget(self.newTagField, stretch=1)
        addTagButton = QPushButton("Add Tag")
        addTagButton.setFixedWidth(80)
        addTagButton.clicked.connect(self.addNewTag)
        newTagLayout.addWidget(addTagButton)
        layout.addWidget(newTagContainer, stretch=0)

        self.updateTagList()
        leftWidget.setMinimumWidth(260)
        leftWidget.setMaximumWidth(420)
        return leftWidget


    def updateTagList(self):
        search_text = self.tagSearchField.text()
        tags = self.db_manager.getTags(search_text)
        while self.flowLayout.count():
            item = self.flowLayout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        for tag in tags:
            btn = TagWidget(tag, db_manager=self.db_manager)
            if tag.name in ["Doing", "Completed"]:
                btn.deleteButton.hide()
            self.flowLayout.addWidget(btn)

    def createRightPane(self):
        rightWidget = QWidget()
        layout = QVBoxLayout(rightWidget)
        layout.setContentsMargins(4, 0, 4, 4)
        layout.setSpacing(8)

        # Task search field.
        self.taskSearchField = QLineEdit()
        self.taskSearchField.setPlaceholderText("Search Tasks")
        self.taskSearchField.setClearButtonEnabled(True)
        self.taskSearchField.textChanged.connect(self.updateTaskList)
        layout.addWidget(self.taskSearchField)

        # Task list takes almost all vertical space (no 50/50 split).
        self.taskListWidget = TaskListWidget(db_manager=self.db_manager)
        self.taskListWidget.setLayoutMode("Grid")
        layout.addWidget(self.taskListWidget, stretch=1)

        # Compact composer bar at the bottom.
        newTaskContainer = QWidget()
        newTaskContainer.setObjectName("newTaskBar")
        newTaskContainer.setStyleSheet(
            "#newTaskBar { background-color: #121214; border: 1px solid #3F3F46;"
            "border-radius: 10px; }"
        )
        newTaskContainer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        newTaskLayout = QHBoxLayout(newTaskContainer)
        newTaskLayout.setContentsMargins(10, 8, 10, 8)
        newTaskLayout.setSpacing(8)

        self.newTaskTextArea = TaskInputTextEdit()
        self.newTaskTextArea.setPlaceholderText("Create new task  (Enter to add · Shift+Enter for newline)")
        self.newTaskTextArea.setFont(self.taskBubbleFont)
        line_spacing = self.newTaskTextArea.fontMetrics().lineSpacing()
        default_text_area_height = line_spacing * 3 + 10
        self.newTaskTextArea.setFixedHeight(default_text_area_height)
        self.newTaskTextArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.newTaskTextArea.setStyleSheet(
            "QTextEdit { background: #1C1C1F; border: 1px solid #3F3F46;"
            "border-radius: 6px; padding: 6px; color: #F3F4F6; }"
        )
        self.newTaskTextArea.submitSignal.connect(self.addNewTask)
        newTaskLayout.addWidget(self.newTaskTextArea, stretch=1)

        self.sendTaskButton = QPushButton("New Task")
        self.sendTaskButton.setMinimumWidth(96)
        self.sendTaskButton.setFixedHeight(default_text_area_height)
        self.sendTaskButton.setStyleSheet(
            "QPushButton { background: #4F46E5; color: white; font-weight: 600;"
            "border: none; border-radius: 6px; padding: 0 14px; }"
            "QPushButton:hover { background: #6366F1; }"
            "QPushButton:pressed { background: #4338CA; }"
        )
        self.sendTaskButton.clicked.connect(self.addNewTask)
        newTaskLayout.addWidget(self.sendTaskButton, stretch=0)

        layout.addWidget(newTaskContainer, stretch=0)
        self.updateTaskList()
        return rightWidget


    def updateTaskList(self):
        search_text = self.taskSearchField.text()
        filters = {"text": search_text, "tags": [t.id for t in self.tagFilterWidget.getCurrentFilters()]}
        tasks = self.db_manager.getTasks(filters)
        orderNewestFirst = self.orderCheckBox.isChecked()
        try:
            tasks.sort(key=lambda t: t.id, reverse=orderNewestFirst)
        except Exception:
            pass

        # Update background of task list area remains unchanged…
        current_filters = self.tagFilterWidget.getCurrentFilters()
        container = self.taskListWidget.container
        if len(current_filters) == 1:
            tag = current_filters[0]
            TaskBubble.current_filter_tag = [tag]
            if tag.background_image and len(tag.background_image) > 0:
                pixmap = QPixmap()
                if pixmap.loadFromData(tag.background_image):
                    container.setBackgroundPixmap(pixmap)
                else:
                    container.setBackgroundColor(tag.color)
            else:
                container.setBackgroundColor(tag.color)
        else:
            TaskBubble.current_filter_tag = None
            container.clearBackgroundPixmap()
            container.setBackgroundColor("")
        
        self.taskListWidget.refreshTasks(tasks, font=self.taskBubbleFont)




    def addNewTag(self):
        tag_name = self.newTagField.text().strip()
        if tag_name:
            try:
                existing_tags = self.db_manager.getTags()
                existing_colors = [t.color for t in existing_tags]
                color = ColorHelper.getDistinctColor(existing_colors)
                tag = Tag(tag_name, color=color)
                tag.save(self.db_manager)
            except sqlite3.IntegrityError as e:
                print("Tag already exists:", e)
                pass
            finally:
                self.newTagField.clear()
                self.updateTagList()

    def addNewTask(self):
        task_text = self.newTaskTextArea.toPlainText().strip()
        if task_text:
            tags = self.db_manager.getTags()
            doing_tag = next((t for t in tags if t.name == "Doing"), None)
            new_task = Task(task_text, tags=[doing_tag] if doing_tag else [], timestamp=datetime.now().isoformat())
            new_task.save(self.db_manager)
            self.newTaskTextArea.clear()
            self.updateTaskList()


    def openDatabase(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Database", "", "SQLite Database Files (*.db)", options=options)
        if fileName:
            self.db_manager.disconnect()
            self.db_manager = DatabaseManager(fileName)
            self.updateTagList()
            self.updateTaskList()
            self.statusBar().showMessage(f"Switched to database: {fileName}")

    def toggleDarkMode(self):
        if self.darkModeButton.isChecked():
            dark_style = """
            QMainWindow, QWidget {
                background-color: #18181B;
                color: #F4F4F5;
            }
            QToolBar {
                background-color: #18181B;
                border-bottom: 1px solid #27272A;
                spacing: 8px;
                padding: 4px;
            }
            QStatusBar {
                background-color: #18181B;
                color: #A1A1AA;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox, QFontComboBox {
                background-color: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 4px 8px;
                selection-background-color: #4F46E5;
            }
            QPushButton {
                background-color: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
            QPushButton:checked {
                background-color: #3F3F46;
                border-color: #6366F1;
            }
            QCheckBox {
                color: #E4E4E7;
                spacing: 6px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QSplitter::handle {
                background: #27272A;
            }
            QScrollBar:vertical {
                background: #18181B;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3F3F46;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QToolTip {
                background-color: #27272A;
                color: #F4F4F5;
                border: 1px solid #52525B;
            }
            """
            QApplication.instance().setStyleSheet(dark_style)
            self.darkModeButton.setText("Light Mode")
        else:
            QApplication.instance().setStyleSheet("")
            self.darkModeButton.setText("Dark Mode")


    def changeTaskLayout(self, mode):
        # Set the new layout mode in the task list widget.
        self.taskListWidget.setLayoutMode(mode)
        # Refresh the task list so that tasks are re-added using the new layout.
        self.updateTaskList()


class FlowLayout(QLayout):
    """A simple flow layout that arranges widgets horizontally and wraps them to a new row."""
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        for item in self.itemList:
            widgetSize = item.sizeHint()
            nextX = x + widgetSize.width() + self.spacing()
            if nextX - self.spacing() > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + self.spacing()
                nextX = x + widgetSize.width() + self.spacing()
                lineHeight = 0
            if not testOnly:
                item.setGeometry(QRect(x, y, widgetSize.width(), widgetSize.height()))
            x = nextX
            lineHeight = max(lineHeight, widgetSize.height())
        return y + lineHeight - rect.y()


# =============================================================================
# Main Function
# =============================================================================
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
