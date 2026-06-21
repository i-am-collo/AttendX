"""
main.py
-------
Entry point for AttendX.
"""
import sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.schema import initialize_database
initialize_database()

from gui.login_page import LoginPage

def main():
    app = LoginPage()
    app.run()           # blocks until root.mainloop() exits

if __name__ == "__main__":
    main()
