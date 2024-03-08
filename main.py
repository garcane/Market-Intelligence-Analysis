#Serves as the entry point for the project
#importing libraries in main.py
# main.py
import sys
from PyQt5.QtWidgets import QApplication, QDialog
from bank_management_system import BankManagementSystem
from login_screen import LoginScreen

def main():
    app = QApplication(sys.argv)
    login_screen = LoginScreen()
    if login_screen.exec_() == QDialog.Accepted:
        # Login successful, create and show the main window
        bank_management_system = BankManagementSystem()
        bank_management_system.show()
    else:
        # Login failed, handle the failure case
        print("Login failed")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()