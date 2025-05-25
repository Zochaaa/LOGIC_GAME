from tkinter import *
from PIL import Image, ImageTk
import schemdraw
import schemdraw.logic as logic
import os
import cairosvg

# 1. Utwórz obrazy tylko jeśli jeszcze ich nie ma (żeby nie nadpisywać za każdym razem)
def create_gate_image(gate_type, filename):
    if not os.path.exists(filename):
        with schemdraw.Drawing() as d:
            if gate_type == 'AND':
                d += logic.And()
            elif gate_type == 'OR':
                d += logic.Or()
            d.save(filename)

create_gate_image('AND', 'and_gate.png')
create_gate_image('OR', 'or_gate.png')

# 2. Funkcje przeciągania
def drag_start(event):
    widget = event.widget
    widget.startX = event.x
    widget.startY = event.y

def drag_motion(event):
    widget = event.widget
    x = widget.winfo_x() - widget.startX + event.x
    y = widget.winfo_y() - widget.startY + event.y
    widget.place(x=x, y=y)

# 3. Okno tkinter
window = Tk()
window.geometry("1200x800")
window.title("Logic Gates - Drag & Drop")

# 4. Wczytaj obrazy i zmień rozmiar
and_img = Image.open("and_gate.png").resize((100, 100))
or_img = Image.open("or_gate.png").resize((100, 100))

and_photo = ImageTk.PhotoImage(and_img)
or_photo = ImageTk.PhotoImage(or_img)

# 5. Dodaj etykiety z obrazami
label_and = Label(window, image=and_photo, bg="white")
label_and.image = and_photo
label_and.place(x=50, y=50)
label_and.bind("<Button-1>", drag_start)
label_and.bind("<B1-Motion>", drag_motion)

label_or = Label(window, image=or_photo, bg="white")
label_or.image = or_photo
label_or.place(x=200, y=50)
label_or.bind("<Button-1>", drag_start)
label_or.bind("<B1-Motion>", drag_motion)

window.mainloop()
