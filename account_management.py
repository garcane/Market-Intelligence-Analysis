from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from reporting import ReportingWindow
from transaction_handling import TransactionHandlingWindow

class AccountManagementWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Create buttons
        report_button = QPushButton("View Reports")
        report_button.clicked.connect(self.show_reporting_window)
        transaction_button = QPushButton("Manage Transactions")
        transaction_button.clicked.connect(self.show_transaction_window)

        # Add buttons to the layout
        layout.addWidget(report_button)
        layout.addWidget(transaction_button)

        self.setLayout(layout)

    def show_reporting_window(self):
        reporting_window = ReportingWindow()
        reporting_window.show()

    def show_transaction_window(self):
        transaction_window = TransactionHandlingWindow()
        transaction_window.show()