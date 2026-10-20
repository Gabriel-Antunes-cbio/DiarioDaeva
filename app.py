"""Ponto de entrada do Diário de Daeva."""
import sys

from PySide6.QtCore import QLockFile, QDir
from PySide6.QtWidgets import QApplication, QMessageBox

from daeva import theme
from daeva.main_window import MainWindow
from daeva.store import Store, data_dir


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Diário de Daeva")
    app.setQuitOnLastWindowClosed(False)  # continua na bandeja para os alertas
    theme.load_fonts()

    lock = QLockFile(QDir(str(data_dir())).filePath("app.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "Diário de Daeva",
                                "O Diário de Daeva já está aberto. Procure o ícone na bandeja, perto do relógio.")
        return 0

    store = Store()
    theme.apply(app, store.settings)
    win = MainWindow(store)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
