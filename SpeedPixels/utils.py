from __future__ import annotations

__all__ = (
    'Countdown',
    'DataBase',
    'Timer',
    'update_stylesheet',
    'load_menu'
)

import sqlite3
from typing import Callable, Iterable, Iterator, TypeVar, Any

from PyQt5.QtCore import QTimer, QTime, Qt, QSize
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout

from constants import DB_URL, PIXELARTS_DB_TABLE_NAME, SETTINGS_DB_TABLE_NAME, NOT_PROVIDED

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')
SupportsStylesheet = TypeVar('SupportsStylesheet')
SupportsCloseAndShow = TypeVar('SupportsCloseAndShow')


def load_menu(current_widget: SupportsCloseAndShow = None) -> None:
    from menu import Menu

    w = Menu()
    w.show()

    if current_widget is None:
        return

    while hasattr(current_widget, 'parent') and current_widget.parent():
        current_widget = current_widget.parent()
    current_widget.close()


def update_stylesheet(obj: SupportsStylesheet, styles: str) -> None:
    obj.setStyleSheet(_remove_styles_repeat(f'{obj.styleSheet()} {styles}'.strip()))


def _remove_styles_repeat(styles: str) -> str:
    dct = {}
    for style in filter(lambda x: x, styles.split(';')):
        k, v = map(str.strip, style.split(':'))
        dct[k] = v
    return '; '.join(map(lambda item: ': '.join(item), dct.items())) + ';'


class Countdown(QTimer):

    def __init__(self, parent: QWidget, before: Iterable[Callable] = ..., after: Iterable[Callable] = ...) -> None:
        super().__init__()

        self._bg = QWidget(parent)
        self._bg.setStyleSheet('background-color: transparent;')
        self._bg.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._layout = QHBoxLayout(self._bg)
        self._surface = QLabel(self._bg)
        self._layout.addWidget(self._surface, alignment=Qt.AlignHCenter)

        self._before = before if before != Ellipsis else ()
        self._after = after if after != Ellipsis else ()
        self._frames: Iterator = ...  # will be set in start method

        self.timeout.connect(self._callback)
        self.resize(parent.size())

    @staticmethod
    def _invoke(*callbacks: Callable) -> None:
        for callback in callbacks:
            callback()

    def _callback(self) -> None:
        try:
            self._surface.setPixmap(next(self._frames).scaled(self._bg.height() // 3, self._bg.height() // 3))
        except StopIteration:
            self._invoke(*self._after)
            self.stop()

    def start(self, delay: int, *frames: QPixmap) -> None:
        self.stop()
        self._invoke(*self._before)
        self._frames = iter(frames)
        self._callback()  # skips delay at the beginning
        super().start(delay)

    def stop(self) -> None:
        super().stop()
        self._surface.setPixmap(QPixmap())

    def resize(self, size: QSize) -> None:
        self._bg.resize(size)


class Timer(QLabel):

    def __init__(self, widget: QWidget, text: str = None, update_delay: int = 50) -> None:
        super().__init__(widget)

        self._text = text or ''

        self._update_delay = update_delay
        self._view = QTime(0, 0, 0)
        self._timer = QTimer()
        self._timer.timeout.connect(self._update)

    @property
    def milliseconds(self) -> int:
        return self._view.msecsSinceStartOfDay()

    def run(self) -> None:
        self._timer.start(self._update_delay)

    def pause(self) -> None:
        self._timer.stop()

    def drop(self, save_text: bool = False) -> None:
        self.setText(f'{self._text}0.00' if save_text else '')
        self.pause()
        self._view = QTime(0, 0, 0)

    @staticmethod
    def to_str(milliseconds: int, separator: str = ...) -> str:
        if not isinstance(separator, str):
            separator = '.'
        return f'{milliseconds // 1000}{separator}{str(milliseconds % 1000).rstrip("0"):0<2}'

    def _to_str(self) -> str:
        return f'{self._text}{self.to_str(self.milliseconds)}'

    def _update(self) -> None:
        self._view = self._view.addMSecs(self._update_delay)
        self.setText(self._to_str())


class DataBase:

    def __init__(self, template_cells_table: str = ...) -> None:
        if not isinstance(template_cells_table, str):
            template_cells_table = '{}_cells'
        self._cursor = self._get_cursor()
        self._tpl = template_cells_table

    @staticmethod
    def _get_cursor() -> sqlite3.Cursor:
        try:
            with sqlite3.connect(DB_URL) as connection:
                return connection.cursor()
        except sqlite3.Error:
            raise ConnectionAbortedError(f'Could not connect to "{DB_URL}" database') from None

    @staticmethod
    def _to_db_format(s: str) -> str:
        return s.title().replace(' ', '')

    def get_setting_value(self, setting: str) -> T:  # shortcut to get specified value from settings dictionary
        return next(iter(self.get_settings(setting).values()))

    def get_settings(self, *settings: str) -> dict[str, T]:
        settings = tuple(map(str.lower, settings))
        rows = self._cursor.execute(f'SELECT * FROM {SETTINGS_DB_TABLE_NAME}').fetchall()

        for row in rows:
            setting_name = row[0].lower()
            if setting_name not in settings:
                rows.remove(row)

        return dict(rows)

    def set_settings(self, **settings: T) -> None:
        db_settings = self.get_settings(*settings.keys())

        for setting, value in settings.items():
            if value == db_settings[setting.lower()]:
                continue
            self._cursor.execute(f'UPDATE {SETTINGS_DB_TABLE_NAME} SET value = ? '
                                 f'WHERE setting = "{setting.lower()}" COLLATE NOCASE',
                                 (settings[setting].lower(),))
        self._cursor.connection.commit()

    def get_art_row(self, name: str) -> tuple[str, int, dict[int, QColor], bool] | None:
        row = self._cursor.execute(f'SELECT * FROM {PIXELARTS_DB_TABLE_NAME} WHERE name = "{name}"').fetchone()

        if row is None:
            return

        try:
            fetched = self._cursor.execute(f'SELECT * FROM {self._tpl.format(self._to_db_format(name))}').fetchall()
            cells = dict((index, QColor(color)) for index, color in fetched)
        except sqlite3.OperationalError:
            raise SystemError(f'Could not get cells data for "{name}" art. Most likely it have been lost') from None

        return name, row[1], cells, bool(row[2])

    def get_art_names(self, limit: int = None, offset: int = 0, **conditions: Any) -> tuple[str]:
        limit = f' LIMIT {limit}' if limit else ''
        offset = f' OFFSET {offset}' if offset else ''
        conditions = ' WHERE ' + ' AND '.join(map(lambda item: f'{item[0]} = {item[1]}', conditions.items())) \
            if conditions else ''
        query = f'SELECT name FROM {PIXELARTS_DB_TABLE_NAME}{conditions}{limit}{offset}'
        return tuple(map(lambda x: x[0], self._cursor.execute(query).fetchall()))  # type: ignore

    def save_art_row(self, name: str, time: float, fill: dict[int, QColor] = ...) -> None:
        row = self.get_art_row(name)

        if fill == Ellipsis:
            try:
                fill = row[2]
            except TypeError:
                raise ValueError('fill argument must be provided to save new arts') from None

        try:
            self._delete_cells_table(name)
            self._create_cells_table(name, fill)
            if row is None:
                self._create_art_row(name, time)
            else:
                self._update_art_row(row, time)
        except sqlite3.Error:
            raise ValueError('Invalid data')
        self._cursor.connection.commit()

    def delete_art_row(self, name: str) -> None:
        self._cursor.execute(f'DELETE FROM {PIXELARTS_DB_TABLE_NAME} WHERE name = "{name}"')
        self._delete_cells_table(name)
        self._cursor.connection.commit()

    def _update_art_row(self, row: tuple[str, float, dict[int, QColor], bool], time: float) -> None:
        query = f'UPDATE {PIXELARTS_DB_TABLE_NAME} SET time = ? WHERE name = "{row[0]}"'
        self._cursor.execute(query, (time if time != NOT_PROVIDED else row[1],))

    def _create_art_row(self, name: str, time: float) -> None:
        query = f'INSERT INTO {PIXELARTS_DB_TABLE_NAME} (name, time, is_prepared) VALUES (?, ?, ?)'
        self._cursor.execute(query, (name, time, False))

    def _delete_cells_table(self, name: str) -> None:
        self._cursor.execute(f'DROP TABLE IF EXISTS {self._tpl.format(self._to_db_format(name))}')

    def _create_cells_table(self, name: str, fill: dict[int, QColor]) -> None:
        name = self._tpl.format(self._to_db_format(name))
        self._cursor.execute(f'''CREATE TABLE {name} (
                                    cell_index INTEGER NOT NULL,
                                    color TEXT NOT NULL
                                 );''')
        values = ', '.join([f'({idx}, "{clr.name()}")' for idx, clr in fill.items()])
        self._cursor.execute(f'INSERT INTO {name} (cell_index, color) VALUES {values}')
