#Serves as the entry point for the project
#importing libraries in main.py
import sys
from PyQt5.QtWidgets import QApplication
from bank_management_system import BankManagementSystem

if __name__ == "__main__":
    app = QApplication(sys.argv)
    bank_management_system = BankManagementSystem()
    bank_management_system.show()
    sys.exit(app.exec_())