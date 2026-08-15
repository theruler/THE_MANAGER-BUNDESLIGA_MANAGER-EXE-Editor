import sys
import os
import tkinter as tk

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))

from main_editor import DOSTranslationEditor

def main():
    root = tk.Tk()
    app = DOSTranslationEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
