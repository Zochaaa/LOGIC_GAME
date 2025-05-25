import tkinter as tk
from PIL import Image, ImageTk
import uuid
import schemdraw
import schemdraw.logic as logic
import matplotlib
import os
import atexit

matplotlib.use('Agg')

def cleanup_temp_images():
    for file in os.listdir():
        if file.startswith("tmp_") and file.endswith(".png"):
            try:
                os.remove(file)
            except:
                pass

atexit.register(cleanup_temp_images)

def generate_gate_image(gate_type, filepath):
    with schemdraw.Drawing() as d:
        if gate_type == "AND":
            d += logic.And()
        elif gate_type == "OR":
            d += logic.Or()
        elif gate_type == "NOT":
            d += logic.Not()
        else:
            d += logic.And()
        d.save(filepath)

class GateImage:
    def __init__(self, canvas, x, y, gate_type, output_label, editor):
        self.canvas = canvas
        self.editor = editor
        self.gate_type = gate_type
        self.x = x
        self.y = y
        self.id = str(uuid.uuid4())
        self.output_label = output_label

        self.filepath = f"tmp_{self.id}.png"
        generate_gate_image(gate_type, self.filepath)
        self.image = Image.open(self.filepath)
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.image_id = canvas.create_image(x, y, image=self.tk_image, anchor="nw")
        self.inputs_expected = 1 if gate_type == "NOT" else 2
        self.input_connected_flags = [False] * self.inputs_expected
        self.outputs = []

        self.input_points = []
        self.input_circles = []
        self.input_labels = []
        gap = self.image.height / (self.inputs_expected + 1)
        for i in range(self.inputs_expected):
            px = self.x - 10
            py = self.y + (i + 1) * gap
            circle = canvas.create_oval(px-8, py-8, px+8, py+8, fill="blue", tags=("input", f"input_{i}", self.id))
            canvas.tag_bind(circle, "<Button-1>", lambda e, idx=i: self.editor.try_finish_connection(self, idx))
            self.input_points.append((px, py))
            self.input_circles.append(circle)
            label = canvas.create_text(px - 10, py, text=chr(65 + i), anchor="e")
            self.input_labels.append(label)

        px_out = self.x + self.image.width + 10
        py_out = self.y + self.image.height / 2
        self.output_point = (px_out, py_out)
        self.output_circle = canvas.create_oval(px_out-8, py_out-8, px_out+8, py_out+8, fill="red", tags=("output", self.id))
        canvas.tag_bind(self.output_circle, "<Button-1>", self.on_output_click)
        self.output_label_id = canvas.create_text(px_out + 15, py_out, text=output_label, anchor="w")

    def on_output_click(self, event):
        self.editor.start_connection(self)

class CircuitEditor:
    def __init__(self, canvas):
        self.canvas = canvas
        self.gates = []
        self.connections = []
        self.output_counter = 1
        self.source_gate = None
        self.temp_line = None
        self.drawing_connection = False
        self.canvas.bind("<Motion>", self.update_temp_line)

    def add_gate(self, gate_type):
        output_label = f"F{self.output_counter}"
        self.output_counter += 1
        gate = GateImage(self.canvas, 100 + 80 * len(self.gates), 100, gate_type, output_label, self)
        self.gates.append(gate)

    def start_connection(self, gate):
        self.source_gate = gate
        self.drawing_connection = True
        x, y = gate.output_point
        if self.temp_line:
            self.canvas.delete(self.temp_line)
        self.temp_line = self.canvas.create_line(x, y, x, y, fill="gray", dash=(4, 2), width=2)

    def update_temp_line(self, event):
        if self.drawing_connection and self.temp_line:
            x0, y0 = self.source_gate.output_point
            self.canvas.coords(self.temp_line, x0, y0, event.x, event.y)

    def try_finish_connection(self, dest_gate, input_index):
        if not self.drawing_connection or dest_gate == self.source_gate:
            self.cancel_connection()
            return

        if dest_gate.input_connected_flags[input_index]:
            self.cancel_connection()
            return

        src_x, src_y = self.source_gate.output_point
        dst_x, dst_y = dest_gate.input_points[input_index]

        if self.temp_line:
            self.canvas.delete(self.temp_line)
        line_id = self.canvas.create_line(src_x, src_y, dst_x, dst_y, arrow=tk.LAST, width=2, tags="connection")

        self.connections.append((self.source_gate, dest_gate, line_id, input_index))
        dest_gate.input_connected_flags[input_index] = True
        self.source_gate.outputs.append(dest_gate)

        self.source_gate = None
        self.temp_line = None
        self.drawing_connection = False

    def cancel_connection(self):
        if self.temp_line:
            self.canvas.delete(self.temp_line)
        self.temp_line = None
        self.source_gate = None
        self.drawing_connection = False

def main():
    root = tk.Tk()
    root.title("Edytor bramek logicznych")

    canvas = tk.Canvas(root, width=1000, height=700, bg="white")
    canvas.pack()

    frame = tk.Frame(root)
    frame.pack()

    editor = CircuitEditor(canvas)

    for gate in ["AND", "OR", "NOT"]:
        tk.Button(frame, text=gate, command=lambda g=gate: editor.add_gate(g)).pack(side=tk.LEFT)

    root.mainloop()

if __name__ == "__main__":
    main()