from __future__ import annotations

__all__ = (
    'DB_URL',
    'MEDIA_URL',
    'PIXELARTS_DB_TABLE_NAME',
    'SETTINGS_DB_TABLE_NAME',
    'CELLS_NUM',
    'FIELD_SIZE',
    'BORDER_SIZE',
    'CUSTOM',
    'NOT_PROVIDED',
    'PREVIEWS_NUM_PER_ROW',
    'Theme'
)

import os
from pathlib import Path

from PyQt5.QtGui import QColor

BASE_DIR = Path(__file__).parent.parent

DB_URL = os.path.join(BASE_DIR, 'db.sqlite3')
MEDIA_URL = os.path.join(BASE_DIR, 'media')

PIXELARTS_DB_TABLE_NAME = 'ArtsInfo'
SETTINGS_DB_TABLE_NAME = 'Settings'

CELLS_NUM = (12, 12)  # horizontal, vertical
FIELD_SIZE = (60, 100)  # horizontal, vertical (in percents)
BORDER_SIZE = ((100 - FIELD_SIZE[0]) // 2, FIELD_SIZE[1])  # horizontal, vertical (in percents)

CUSTOM = '\0'
NOT_PROVIDED = '-'

PREVIEWS_NUM_PER_ROW = 4


class Theme:

    def __init__(self, theme: str) -> None:
        if theme == 'light':
            self.FONT_COLOR = QColor(0, 0, 0)
            self.ART_BACKGROUND_COLOR = QColor(255, 248, 248)
            self.ACTION_BUTTONS_BACKGROUND_COLOR = QColor(255, 245, 248)
            self.CELL_DEFAULT_COLOR = QColor(184, 184, 184)
            self.PREVIEW_BACKGROUND_COLOR = QColor(234, 244, 244)
            self.HOVERED_PREVIEW_BACKGROUND_COLOR = QColor(200, 215, 210)
        else:
            self.FONT_COLOR = QColor(189, 189, 189)
            self.ART_BACKGROUND_COLOR = QColor(84, 84, 84)
            self.ACTION_BUTTONS_BACKGROUND_COLOR = QColor(100, 100, 100)
            self.CELL_DEFAULT_COLOR = QColor(64, 64, 64)
            self.PREVIEW_BACKGROUND_COLOR = QColor(34, 44, 44)
            self.HOVERED_PREVIEW_BACKGROUND_COLOR = QColor(74, 84, 84)
        self.MENU_BACKGROUND_IMAGE_URL = os.path.join(MEDIA_URL, f'{theme}/bgmenu.jpg')

        self._theme = theme

    @property
    def theme(self) -> str:
        return self._theme

    def switch(self) -> Theme:
        return Theme('dark' if self.theme == 'light' else 'light')
