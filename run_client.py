import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from client.network import NetworkClient
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    network = NetworkClient()
    if not network.connect():
        QMessageBox.critical(None, "Error", "Cannot connect to server")
        return

    login_dialog = LoginWindow(network)
    if login_dialog.exec_() != login_dialog.Accepted or not login_dialog.user_info:
        network.disconnect()
        return

    main_window = MainWindow(network, login_dialog.user_info)
    main_window.show()

    exit_code = app.exec_()
    network.disconnect()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
