from __future__ import annotations

__all__ = (
    'CustomArt',
    'SavedArt'
)

import os
from typing import ParamSpec, Generator

import keyboard
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QColor, QIcon, QResizeEvent
from PyQt5.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QInputDialog, QColorDialog, QLabel,
                             QGridLayout, QSizePolicy, QHBoxLayout, QMessageBox)

from constants import BORDER_SIZE, CUSTOM, CELLS_NUM, MEDIA_URL, NOT_PROVIDED, Theme
from utils import Countdown, DataBase, Timer, update_stylesheet, load_menu

P = ParamSpec('P')

db = DataBase()
theme = Theme(db.get_setting_value('theme'))


class Cell(QPushButton):

    def __init__(self, field: Field) -> None:
        super().__init__(field.parent())
        self.parent = lambda: field
        self._position = field.count() - 1

        self._color = theme.CELL_DEFAULT_COLOR
        self._saved_color = theme.CELL_DEFAULT_COLOR
        self.save()  # shortcut for setting up border

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.released.connect(self._callback)

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, value: QColor) -> None:
        self._color = value
        self._draw()

    @property
    def saved_color(self) -> QColor:
        return self._saved_color

    def is_painted(self) -> bool:
        return self._color != theme.CELL_DEFAULT_COLOR

    def is_saved(self) -> bool:
        return self._saved_color != theme.CELL_DEFAULT_COLOR

    def save(self) -> None:
        self._saved_color = self.color
        self.color = theme.CELL_DEFAULT_COLOR
        if self.is_saved():
            update_stylesheet(self, f'border: 3px solid {self._saved_color.name()};')
        else:
            update_stylesheet(self, 'border: 1px solid black')

    def _draw(self) -> None:
        update_stylesheet(self, f'background-color: {self.color.name()};')

    # color validation lies on PixelArt class
    def _callback(self) -> None:
        if self.is_painted():
            self.color = theme.CELL_DEFAULT_COLOR
            return
        current_color = self.parent().parent().user_color
        if self.is_saved() and current_color != self._saved_color:
            return
        self.color = current_color


class Field(QGridLayout):
    filled = pyqtSignal()

    def __init__(self, art: QWidget) -> None:
        super().__init__(art)
        self.parent = lambda: art

        for row in range(1, CELLS_NUM[0] + 1):
            for col in range(1, CELLS_NUM[1] + 1):
                cell = Cell(self)
                cell.released.connect(self._child_on_click)
                self.addWidget(cell, row, col)

    def prepare(self, prep: dict[int, QColor]) -> None:
        for k, v in prep.items():
            self.itemAt(k).widget().color = v

    @property
    def used_colors(self) -> list[QColor]:
        used = []
        used_hex_codes = set()

        for color in self._get_saved_colors_and_positions().values():
            if color.name() not in used_hex_codes:
                used_hex_codes.add(color.name())
                used.append(color)

        return used

    def _cells(self) -> Generator[Cell]:
        for position in range(self.count()):
            yield self.itemAt(position).widget()

    def _get_saved_colors_and_positions(self) -> dict[int, QColor]:
        return dict((idx, cell.saved_color) for idx, cell in enumerate(self._cells()) if cell.is_saved())

    def _is_filled(self) -> bool:
        return self.is_saved() and all(cell.color == cell.saved_color for cell in self._cells())

    def _child_on_click(self):
        if self._is_filled():
            self.filled.emit()

    def is_saved(self) -> bool:
        return any(cell.is_saved() for cell in self._cells())

    def paint(self) -> None:
        for cell in self._cells():
            cell.save()

    def clear(self) -> None:
        for cell in self._cells():
            cell.color = theme.CELL_DEFAULT_COLOR
            cell.save()

    def save(self) -> tuple[str, dict[int, QColor]] | None:
        clrs = self._get_saved_colors_and_positions()
        if not clrs:
            QMessageBox.question(self.parent(), 'Error', 'To save pixel art, at least one color must be saved',
                                 QMessageBox.Ok, QMessageBox.Ok)
            return
        name = QInputDialog().getText(self.parent(), 'Action', 'Enter pixel art name')[0]
        if name == CUSTOM:
            QMessageBox.information(self.parent(), 'Error', 'Invalid data', QMessageBox.Ok, QMessageBox.Ok)
            return
        if not name:
            return
        if db.get_art_row(name) and QMessageBox.question(
                self.parent(), 'Warning', f'Pixel art with name "{name}" already exists. Remove previous pixel art?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.No:
            return

        return name, clrs  # process handling in parent class

    def setEnabled(self, value: bool) -> None:
        for cell in self._cells():
            cell.color = theme.CELL_DEFAULT_COLOR if value else cell.saved_color
            cell.setEnabled(value)


class PixelArt(QWidget):

    def __new__(cls, *args: P.args, **kwargs: P.kwargs) -> CustomArt | SavedArt:
        if cls == PixelArt:
            raise SystemError('Cannot create PixelArt object directly')
        return super().__new__(cls)

    def __init__(self, name: str, pb: int, parent: QWidget = None) -> None:
        global theme
        theme = Theme(db.get_setting_value('theme'))

        super().__init__(parent)

        self.setWindowTitle('SpeedPixels')
        self.setWindowIcon(QIcon(os.path.join(MEDIA_URL, 'general/icon.svg')))

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(*self.screen().geometry().getRect())

        self._name = name
        self._best_time = pb

        self._user_color = theme.CELL_DEFAULT_COLOR

        self.setLayout(QHBoxLayout(self))
        self.setStyleSheet(f'background-color: {theme.ART_BACKGROUND_COLOR.name()};')

        # art info
        self._art_name_label = QLabel(f'Name: {self.name if self.name != CUSTOM else NOT_PROVIDED}', self)
        self._best_time_label = QLabel(self)
        self._current_time_label = Timer(self, 'Current time: ')

        # right border
        self._right_border = QVBoxLayout(self)
        self._right_border.addWidget(self._art_name_label, alignment=Qt.AlignHCenter)
        self._right_border.addWidget(self._best_time_label, alignment=Qt.AlignHCenter)
        self._right_border.addWidget(self._current_time_label, alignment=Qt.AlignHCenter)
        self._right_border.addWidget(QLabel(self), alignment=Qt.AlignBottom)

        for i in range(self._right_border.count()):
            widget = self._right_border.itemAt(i).widget()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.setMaximumWidth(self.width() * BORDER_SIZE[0] // 100)

        # field
        self._field = Field(self)
        self._field.filled.connect(self._on_field_fill)

        # action buttons
        self._paint_btn = QPushButton('Paint', self)
        self._restart_btn = QPushButton('Restart', self)
        self._clear_btn = QPushButton('Clear', self)
        self._save_btn = QPushButton('Save', self)
        self._delete_btn = QPushButton('Delete', self)
        self._menu_btn = QPushButton('To menu', self)
        self._palette_layout = QVBoxLayout(self)
        self._palette_layout.setSpacing(25)
        # Hooks keyboard nums from 1 to 9 press using "keyboard" module.
        # Hook is enabled, when colors palette (not svg palette) is active. In other cases it is set to None.
        self._keyboard_hook = None

        self._paint_btn.clicked.connect(self._paint_btn_callback)
        self._restart_btn.clicked.connect(self._restart_btn_callback)
        self._clear_btn.clicked.connect(self._clear_btn_callback)
        self._save_btn.clicked.connect(self._save_btn_callback)
        self._delete_btn.clicked.connect(self._delete_btn_callback)
        self._menu_btn.clicked.connect(lambda: load_menu(self))

        for btn in (self._paint_btn, self._restart_btn, self._clear_btn,
                    self._save_btn, self._delete_btn, self._menu_btn):
            btn.setStyleSheet(f'background-color: {theme.ACTION_BUTTONS_BACKGROUND_COLOR.name()};')
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMaximumWidth(self.width() * BORDER_SIZE[0] // 100)

        # left border
        self._left_border = QVBoxLayout(self)
        self._left_border.addWidget(self._paint_btn)
        self._left_border.addWidget(self._restart_btn)
        self._left_border.addWidget(self._clear_btn)
        self._left_border.addWidget(self._save_btn)
        self._left_border.addWidget(self._delete_btn)
        self._left_border.addStretch()
        self._left_border.addItem(self._palette_layout)
        self._left_border.addStretch()
        self._left_border.addWidget(self._menu_btn, alignment=Qt.AlignBottom)

        # main window layout
        self.layout().addItem(self._left_border)
        self.layout().addItem(self._field)
        self.layout().addItem(self._right_border)

        # media preload/usage
        self._palette_svg = QLabel(self)
        palette_svg = QPixmap(os.path.join(MEDIA_URL, 'general/palette.svg'))
        im_size = self.width() * BORDER_SIZE[0] // 200  # 50 percents of border width
        self._palette_svg.setPixmap(palette_svg.scaled(im_size, im_size))
        self._palette_svg.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self._palette_svg.mousePressEvent = self._svg_palette_callback

        self._selected_icon = QIcon(os.path.join(MEDIA_URL, f'general/selected.png'))

        self._countdown_frames = (
            QPixmap(os.path.join(MEDIA_URL, 'general/gg.png')),
            QPixmap(os.path.join(MEDIA_URL, 'general/3.png')),
            QPixmap(os.path.join(MEDIA_URL, 'general/2.png')),
            QPixmap(os.path.join(MEDIA_URL, 'general/1.png'))
        )

        # countdown (Starts on paint/restart button callbacks. Clear button stops countdown)
        self._countdown = Countdown(
            self,
            before=[lambda: self._field.setEnabled(False)],
            after=[lambda: self._field.setEnabled(True), self._current_time_label.run]
        )

        # sets start palette (as svg) to left border
        self._switch_palette()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if self.name != CUSTOM:
            raise ReferenceError('Name can only be set for custom arts')
        if not isinstance(value, str):
            raise ValueError(
                f'Setter of property "name" expected "str" instance value, got "{value.__class__.__name__}" instead'
            )
        self._name = value

    @property
    def user_color(self) -> QColor:
        return self._user_color

    @user_color.setter
    def user_color(self, color: QColor) -> None:
        if not color.isValid():
            raise ValueError('Setter of property "user_color" got invalid color')
        self._user_color = color

    def _is_pb(self, time: int) -> bool:
        try:
            return time < float(self._best_time) * 1000
        except (ValueError, TypeError):
            return True

    def _paint_btn_callback(self) -> None:
        self._field.paint()
        if not self._field.used_colors:
            self._clear_btn_callback()
            return

        self._best_time_label.setText(f'Best time: {self._best_time}')
        self._best_time_label.setHidden(False)

        self._switch_palette()
        self._current_time_label.drop(save_text=True)
        self._countdown.start(1000, *self._countdown_frames[1:])

        if self.user_color not in self._field.used_colors:
            self.user_color = self._field.used_colors[0]

        for idx in range(self._palette_layout.count()):
            btn = self._palette_layout.itemAt(idx).layout().itemAt(1).widget()
            # original QPushButton doesn't have backgroundColor attribute. Check _set_colors_palette method
            if btn.backgroundColor == self.user_color:
                self._mark_as_selected(btn)

    def _save_btn_callback(self) -> None:
        self._current_time_label.pause()
        r = self._field.save()

        if r:
            try:
                self.name = r[0]
                db.save_art_row(self.name, self._best_time, r[1])
                art = SavedArt(self.name)
                art.show()
                self.close()
            except ValueError:
                QMessageBox.information(self, 'Error', 'Invalid data', QMessageBox.Ok, QMessageBox.Ok)

        if self._current_time_label.milliseconds:
            self._current_time_label.run()

    def _restart_btn_callback(self) -> None:
        if not self._field.used_colors:
            self._clear_btn_callback()
            return
        self._current_time_label.drop(save_text=True)
        self._countdown.start(1000, *self._countdown_frames[1:])

    def _clear_btn_callback(self) -> None:
        if self._field.used_colors:
            self.user_color = theme.CELL_DEFAULT_COLOR
        self._switch_palette()
        self._current_time_label.drop()
        self._countdown.stop()
        self._field.setEnabled(True)
        self._field.clear()
        if self.name == CUSTOM:
            self._best_time = NOT_PROVIDED
        self._best_time_label.setHidden(True)

    def _delete_btn_callback(self) -> None:
        if QMessageBox.question(self, 'Warning', 'Are you sure you want to delete this pixel art?',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            db.delete_art_row(self.name)
            load_menu(self)

    def _on_field_fill(self) -> None:
        if self._is_pb(self._current_time_label.milliseconds):
            self._best_time = self._current_time_label.to_str(self._current_time_label.milliseconds)
            self._best_time_label.setText(f'Best time: {self._best_time}')
            if self.name != CUSTOM:  # ignores saving for custom arts
                db.save_art_row(self.name, float(self._best_time))  # saves new pb
        self._current_time_label.drop(save_text=True)
        self._countdown.start(1000, *self._countdown_frames)

    def _mark_as_selected(self, color: QPushButton) -> None:
        for idx in range(self._palette_layout.count()):
            self._palette_layout.itemAt(idx).layout().itemAt(1).widget().setIcon(QIcon())
        color.setIcon(self._selected_icon)
        color.setIconSize(QSize(color.width() // 2, color.height() // 2))

    def _switch_palette(self) -> None:
        colors = self._field.used_colors

        self._clear_palette()
        if not colors or self.sender() == self._clear_btn:
            self._set_svg_palette()
        else:
            self._set_colors_palette(*colors)

    def _clear_palette(self) -> None:
        for _ in range(self._palette_layout.count()):
            item = self._palette_layout.itemAt(0)
            self._palette_layout.removeItem(item)

            if item.layout() is None:
                item.widget().hide()
                continue

            item = item.layout()
            for idx in range(item.count()):
                item.itemAt(idx).widget().deleteLater()

    def _set_colors_palette(self, *colors: QColor) -> None:
        for idx in range(len(colors)):
            lt = QHBoxLayout(self)
            lbl = QLabel(str(idx + 1), self)
            lbl.setVisible(True)
            btn = QPushButton(self)
            btn.setVisible(True)
            btn.setMaximumSize(50, 50)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            update_stylesheet(btn, f'background-color: {colors[idx].name()};')
            # palette fakes background color, so we will storage background color as button attribute
            btn.backgroundColor = colors[idx]
            lt.addWidget(lbl, alignment=Qt.AlignRight)
            lt.addWidget(btn, alignment=Qt.AlignLeft)
            self._palette_layout.addLayout(lt)
        self._keyboard_hook = keyboard.on_press(self._hook_keyboard_press)

    def _set_svg_palette(self) -> None:
        self._palette_layout.addWidget(self._palette_svg, alignment=Qt.AlignHCenter)
        self._palette_svg.setHidden(False)
        if self._keyboard_hook:
            keyboard.unhook(self._keyboard_hook)
            self._keyboard_hook = None

    def _svg_palette_callback(self, _: QEvent) -> None:
        # do not use QColorDialog.getColor method. It is static, so background color cannot be set
        dialog = QColorDialog(self)
        dialog.setStyleSheet(f'background-color: {theme.ART_BACKGROUND_COLOR.name()};')
        dialog.open()
        dialog.colorSelected.connect(lambda: setattr(self, 'user_color', dialog.selectedColor()))

    def _hook_keyboard_press(self, event: keyboard.KeyboardEvent) -> None:
        if event.event_type == 'down' and event.name.isdigit():
            try:
                self.user_color = self._field.used_colors[int(event.name) - 1]
                self._mark_as_selected(self._palette_layout.itemAt(int(event.name) - 1).layout().itemAt(1).widget())
            except IndexError:
                return  # should not change current color if index is invalid

    def resizeEvent(self, e: QResizeEvent) -> None:
        self._countdown.resize(e.size())


class ActionsCleanupMixin:

    @staticmethod
    def _delete(*buttons: QPushButton) -> None:
        for btn in buttons:
            btn.deleteLater()


class CustomArt(PixelArt, ActionsCleanupMixin):

    def __init__(self, **kwargs: str) -> None:
        super().__init__(CUSTOM, NOT_PROVIDED, **kwargs)

        self._delete(self._delete_btn)


class SavedArt(PixelArt, ActionsCleanupMixin):

    def __init__(self, name: str, **kwargs: str) -> None:
        row = db.get_art_row(name)

        if not row:
            raise NameError(f'Art with name "{name}" is not saved')

        super().__init__(row[0], row[1], **kwargs)
        self._field.prepare(row[2])
        self._paint_btn_callback()

        unavailable_btns = [self._paint_btn, self._save_btn, self._clear_btn]
        self._delete(*unavailable_btns + ([self._delete_btn] if name in db.get_art_names(is_prepared=1) else []))
