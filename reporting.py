class ReportingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Create buttons
        report_button = QPushButton("View Reports")
        report_button.clicked.connect(self.show_report_window)
        transaction_button = QPushButton("Manage Transactions")
        transaction_button.clicked.connect(self.show_transaction_window)

        # Add buttons to the layout
        layout.addWidget(report_button)
        layout.addWidget(transaction_button)

        self.setLayout(layout)

    def show_report_window(self):
        report_window = ReportWindow()