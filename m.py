import tkinter as tk

window = tk.Tk()
window.geometry("200x100")
window.title("Test Window")

tk.Label(window, text="Hello!").pack()

window.mainloop()
