from PyQt5.QtWidgets import QMainWindow, QDialog, QLabel, QWidget, QVBoxLayout, QApplication, QMainWindow, QAction, QToolBar, QWidget, QVBoxLayout
from PyQt5.QtGui import QIcon, QFont
import sys
from login_screen import LoginScreen
from PyQt5.QtCore import Qt

# Import other necessary Qt modules and classes


# Create a class that inherits from QMainWindow. Initialize the object. No parameters. No return value.

class BankManagementSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Bank Management System")
        self.setGeometry(100, 100, 800, 600)
        
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        new_action = QAction(QIcon("icons/new.png"), "New", self)
        file_menu.addAction(new_action)

        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        toolbar.addAction(new_action)

        # Create central widget
        central_widget = QWidget()
        central_layout = QVBoxLayout()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        welcome_label = QLabel("Welcome to the Bank Management System!")
        welcome_label.setFont(QFont("Arial", 24))  # Set the font and size
        welcome_label.setAlignment(Qt.AlignCenter)  # Center the label text

        # Add the welcome label to the layout
        central_layout.addWidget(welcome_label, alignment=Qt.AlignTop)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    bank_management_system = BankManagementSystem()
    bank_management_system.show()
    sys.exit(app.exec_())
