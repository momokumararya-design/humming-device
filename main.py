import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.ui import App
if __name__ == "__main__":
    App().mainloop()
