import sys
from PyQt5.QtWidgets import QApplication
from client.network import NetworkClient
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    network = NetworkClient()
    
    login_window = LoginWindow(network)
    if login_window.exec_() == LoginWindow.Accepted:
        main_window = MainWindow(network)
        main_window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
