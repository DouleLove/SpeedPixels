__all__ = (
    'Menu',
)

import os
import sys
from typing import Never, TypeVar

from PyQt5.QtCore import Qt, QEvent, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QPalette, QBrush, QPixmap, QMouseEvent, QCloseEvent, QMovie, QIcon, QTransform
from PyQt5.QtWidgets import (QWidget, QGridLayout, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                             QScrollArea, QSpacerItem, QSizePolicy, QLayout)

from arts import CustomArt, SavedArt
from constants import MEDIA_URL, PREVIEWS_NUM_PER_ROW, Theme
from utils import DataBase, set_text_color, update_stylesheet

T = TypeVar('T')

db = DataBase()


class BasePreview(QWidget):

    def __init__(self, parent: QWidget, path: str) -> None:
        super().__init__(parent)
        self.parent = lambda: parent

        self._images = {
            'dark': QPixmap(path.format('dark')),
            'light': QPixmap(path.format('light'))
        }

        self._preview_img = QLabel(self)
        mrg = self.parent().width() // (PREVIEWS_NUM_PER_ROW * 3)
        self._image_width = self.parent().width() // PREVIEWS_NUM_PER_ROW - mrg
        self._image_height = round(self._image_width / 1.5)
        self._preview_img.resize(self._image_width, self._image_height)

        self._theme: Theme = ...  # will be set in set_theme method

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._preview_img.setPixmap(self._images[theme.theme].scaled(self._image_width, self._image_height))
        self.leaveEvent()  # forcing color setting on widget run
        self.setFixedSize(self._preview_img.sizeHint() if self.sizeHint().isEmpty() else self.sizeHint())

    def enterEvent(self, *e: QEvent) -> None:
        self.setStyleSheet(f'background-color: {self._theme.HOVERED_PREVIEW_BACKGROUND_COLOR.name()}; padding: 10px;')

    def leaveEvent(self, *e: QEvent) -> None:
        self.setStyleSheet(f'background-color: {self._theme.PREVIEW_BACKGROUND_COLOR.name()}; padding: 10px;')

    def mousePressEvent(self, *e: QMouseEvent, art: CustomArt | SavedArt) -> None:
        self.parent().close()
        art.show()


class PreparedArtPreview(BasePreview):

    def __init__(self, name: str, parent: QWidget) -> None:
        super().__init__(parent, path=os.path.join(MEDIA_URL, '{}/%s_preview_img.png' % name))

        self._name = name

        self._info_layout = QVBoxLayout(self)
        self._info_layout.setSpacing(0)
        self._info_layout.addWidget(self._preview_img)
        try:
            pb = db.get_art_row(name)[1]
        except TypeError:
            pb = '-'
        self._info_layout.addWidget(QLabel(f'Name: {name}\n\nBest time: {pb}', self))

    def set_theme(self, theme: Theme, *args: Never, **kwargs: Never) -> None:
        super().set_theme(theme)
        set_text_color(self._info_layout, theme.FONT_COLOR)

    def mousePressEvent(self, *e: QMouseEvent) -> None:
        super().mousePressEvent(*e, art=SavedArt(self._name))


class CustomArtPreview(BasePreview):

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, path=os.path.join(MEDIA_URL, '{}/custom_preview_img.svg'))

    def set_theme(self, theme: Theme, *args: Never, **kwargs: Never) -> None:
        super().set_theme(theme)

    def mousePressEvent(self, *e: QMouseEvent) -> None:
        super().mousePressEvent(*e, art=CustomArt())


class UserArtsOverview(QWidget):

    class ScrollableAreaItem(QLabel):

        def __init__(self, theme: Theme, parent: QWidget = None, *args: T, **kwargs: T):
            super().__init__(*args, **kwargs, parent=parent)
            self.parent = lambda: parent
            self._theme = theme

            self.setStyleSheet('padding-top: 4px; padding-bottom: 4px;')

        def enterEvent(self, *e: QEvent) -> None:
            update_stylesheet(self, f'background-color: {self._theme.HOVERED_PREVIEW_BACKGROUND_COLOR.name()};')

        def leaveEvent(self, *e: QEvent) -> None:
            update_stylesheet(self, f'background-color: {self._theme.PREVIEW_BACKGROUND_COLOR.name()};')

        def mousePressEvent(self, *e: QMouseEvent) -> None:
            art = SavedArt(self.text())
            art.show()
            self.parent().close()

    def __init__(self, theme: Theme, limit: int, offset: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent = lambda: parent
        self.resize(self.parent().size())

        self._theme = theme
        self._limit = limit
        self._offset = offset

        self._view = QWidget(self)
        self._view.setStyleSheet(f'background-color: {theme.PREVIEW_BACKGROUND_COLOR.name()};')
        self._view.resize(self.width() // 4, self.height() // 4 * 3)
        self._view.move((self.width() - self._view.width()) // 2, (self.height() - self._view.height()) // 2)
        self._view.setLayout(QVBoxLayout(self))
        self._view.layout().setSpacing(0)

        self._header = QWidget(self._view)
        self._header.setStyleSheet('background-color: rgb(182, 191, 183);')
        self._header_layout = QHBoxLayout(self._header)
        self._header_layout.addWidget(QLabel('My arts', self._header))
        self._close_widget = QLabel(self._header)
        self._close_widget.mousePressEvent = self.closeEvent
        self._close_widget.setPixmap(QPixmap(os.path.join(MEDIA_URL, 'general/close_user_arts_overview.svg')))
        self._header_layout.addWidget(self._close_widget, alignment=Qt.AlignRight)

        self._scrollable = QScrollArea(self._view)
        self._items_layout = QVBoxLayout(self._view)
        self._items_layout.setSpacing(0)
        self._items_layout.addStretch()
        self._load_items()
        area = QWidget()
        area.setLayout(self._items_layout)
        self._scrollable.setWidget(area)
        self._scrollable.setWidgetResizable(True)
        self._scrollable.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._view.layout().addWidget(self._header)
        self._view.layout().addWidget(self._scrollable)

    def _on_scroll(self) -> None:
        if self._scrollable.verticalScrollBar().value() > self._scrollable.verticalScrollBar().maximum() // 100 * 80:
            self._load_items()

    def _load_items(self) -> None:
        for art_name in db.get_art_names(limit=self._limit, offset=self._offset, is_prepared=0):
            item = self.ScrollableAreaItem(self._theme, self.parent(), art_name)
            self._items_layout.insertWidget(self._items_layout.count() - 1, item)
        self._offset += self._limit
        if self._items_layout.count() == 1:  # if only spacer added
            self._items_layout.insertWidget(0, QLabel("There's nothing here yet", self), alignment=Qt.AlignHCenter)
        set_text_color(self._items_layout, self._theme.FONT_COLOR)

    def closeEvent(self, e: QCloseEvent) -> None:
        self.parent().setEnabled(True)
        self.close()


class ThemeSwitcher(QLabel):
    switched = pyqtSignal(Theme)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._theme = Theme(db.get_setting_value('theme'))

        size = self.parent().height() // 5 // 3   # 1/3 height from _user_utils layout
        self.setPixmap(QPixmap(os.path.join(MEDIA_URL, 'general/switch_theme.svg')).scaled(size, size))
        self.setMaximumSize(size + 15, size)  # 15px is an extra space for animation
        self.mousePressEvent = lambda e: self._animate()

        self._pixmap = self.pixmap().copy()
        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0)
        self._animation.setEndValue(180)
        self._animation.setDuration(1000)
        self._animation.valueChanged.connect(lambda value: self._rotate(value))
        self._is_signal_emitted = False

    @property
    def theme(self) -> Theme:
        return self._theme

    def _rotate(self, value: int) -> None:
        self.setPixmap(self._pixmap.transformed(QTransform().rotate(value)))
        if self._is_signal_emitted is False and value > self._animation.endValue() // 2:
            self._is_signal_emitted = True
            self._theme = self._theme.switch()
            self.switched.emit(self._theme)
        if value == self._animation.endValue():
            self._is_signal_emitted = False
            self._pixmap = self.pixmap().copy()

    def _animate(self) -> None:
        self._animation.start()


class Menu(QWidget):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle('SpeedPixels')
        self.setWindowIcon(QIcon(os.path.join(MEDIA_URL, 'general/icon.svg')))

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(self.screen().geometry())
        self._bg = QPalette()

        self._main_layout = QVBoxLayout(self)

        self._prepared_previews_layout = QGridLayout(self)
        self._prepared_previews_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self._prepared_previews_layout.setSpacing(0)
        prepared_art_names = db.get_art_names(is_prepared=1)
        for idx in range(len(prepared_art_names)):
            self._prepared_previews_layout.addWidget(
                PreparedArtPreview(prepared_art_names[idx], self),
                idx // PREVIEWS_NUM_PER_ROW,
                idx % PREVIEWS_NUM_PER_ROW
            )

        self._user_utils = QHBoxLayout(self)

        self._add_custom = CustomArtPreview(self)
        self._theme_switcher = ThemeSwitcher(self)
        self._theme_switcher.switched.connect(lambda theme: self._set_theme(theme))
        self._user_utils.addWidget(self._theme_switcher, alignment=Qt.AlignBottom | Qt.AlignLeft)
        self._user_utils.addWidget(self._add_custom)
        self._actions_layout = QVBoxLayout(self)
        self._show_user_arts_btn = QPushButton('My arts', self)
        self._show_user_arts_btn.clicked.connect(self._show_user_arts)
        self._exit_btn = QPushButton('Exit', self)
        self._exit_btn.clicked.connect(sys.exit)
        self._exit_btn.setMaximumWidth(self._show_user_arts_btn.sizeHint().width() * 2)
        self._actions_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self._actions_layout.addWidget(self._show_user_arts_btn)
        self._actions_layout.addWidget(self._exit_btn)
        self._actions_layout.setAlignment(Qt.AlignRight)
        self._user_utils.addLayout(self._actions_layout)

        self._logo_layout = QVBoxLayout(self)
        self._logo = QMovie(os.path.join(MEDIA_URL, 'general/logo.gif'))
        self._logo.start()
        self._logo_label = QLabel(self)
        self._logo_label.setMovie(self._logo)
        self._logo_layout.addWidget(self._logo_label, alignment=Qt.AlignHCenter)

        self._main_layout.addLayout(self._logo_layout, stretch=1)  # 20% of window height
        self._main_layout.addLayout(self._prepared_previews_layout, stretch=3)  # 60% of window height
        self._main_layout.addLayout(self._user_utils, stretch=1)  # 20% of window height

        self._backgrounds = {
            'dark': QPixmap(Theme('dark').MENU_BACKGROUND_IMAGE_URL),
            'light': QPixmap(Theme('light').MENU_BACKGROUND_IMAGE_URL)
        }
        self._set_theme(self._theme_switcher.theme)

    def _show_user_arts(self) -> None:
        self.setEnabled(False)
        area = UserArtsOverview(self._theme_switcher.theme, limit=50, parent=self)
        area.show()

    def _set_theme(self, theme: Theme) -> None:
        self._bg.setBrush(QPalette.Background, QBrush(self._backgrounds[theme.theme].scaled(self.size())))
        self.setPalette(self._bg)
        self._show_user_arts_btn.setStyleSheet(f'background-color: {theme.PREVIEW_BACKGROUND_COLOR.name()};')
        self._exit_btn.setStyleSheet(f'background-color: {theme.PREVIEW_BACKGROUND_COLOR.name()};')
        set_text_color(self._actions_layout, theme.FONT_COLOR)
        for idx in range(self._prepared_previews_layout.count()):
            self._prepared_previews_layout.itemAt(idx).widget().set_theme(theme)
        self._add_custom.set_theme(theme)
        db.set_settings(theme=theme.theme)

    def setEnabled(self, value: bool) -> None:
        for child in self.children():
            child.setEnabled(value)  # type: ignore
        self._logo.setPaused(not value)
