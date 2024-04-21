from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from account_management import AccountManagementWindow

class BankManagementSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Bank Management System")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget
        central_widget = QWidget()
        central_layout = QVBoxLayout()
        central_widget.setLayout(central_layout)

        # Add the AccountManagementWindow to the central layout
        account_management_window = AccountManagementWindow()
        central_layout.addWidget(account_management_window)

        self.setCentralWidget(central_widget)