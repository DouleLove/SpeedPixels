__all__ = ()
__author__ = 'Doule'
__license__ = 'MIT'
__title__ = 'SpeedPixel'
__version__ = '3.11'

import sys

from PyQt5.QtWidgets import QApplication

from utils import load_menu


def main():
    app = QApplication(sys.argv)
    load_menu()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
