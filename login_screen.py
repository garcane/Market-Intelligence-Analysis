from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

class LoginScreen(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Create UI components
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.login)

        # Add components to the layout
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(login_button)

        self.setLayout(layout)
        self.setWindowTitle("Login")

    def login(self):
        # Implement login logic here
        username = self.username_input.text()
        password = self.password_input.text()
        # Perform authentication and handle successful or failed login

        # Example: Print the entered credentials
        print(f"Username: {username}, Password: {password}")