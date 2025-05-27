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

def generate_gate_image(gate_type, filepath, inputs=2):
    with schemdraw.Drawing() as d:
        if gate_type == "AND":
            d += logic.And(n=inputs)
        elif gate_type == "OR":
            d += logic.Or(n=inputs)
        elif gate_type == "NOT":
            d += logic.Not()
        elif gate_type == "NAND":
            d += logic.Nand(n=inputs)
        elif gate_type == "NOR":
            d += logic.Nor(n=inputs)
        else:
            d += logic.And()
        d.draw(show=False)
        d.save(filepath)

class GateImage:
    def __init__(self, canvas, x, y, gate_type, output_label, editor, inputs=2):
        self.canvas = canvas
        self.editor = editor
        self.gate_type = gate_type
        self.x = x
        self.y = y
        self.id = str(uuid.uuid4())
        self.output_label = output_label

        self.inputs_expected = 1 if gate_type == "NOT" else max(2, min(4, inputs))
        self.input_connected_flags = [False] * self.inputs_expected
        self.outputs = []

        self.input_names = []

        self.filepath = f"tmp_{self.id}.png"
        generate_gate_image(gate_type, self.filepath, self.inputs_expected)
        self.image = Image.open(self.filepath)

        # Skalowanie obrazu w zależności od liczby wejść
        scale_factor = 1.0 + 0.1 * (self.inputs_expected - 2)
        new_width = int(self.image.width * scale_factor)
        new_height = int(self.image.height * scale_factor)
        self.image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.image_id = canvas.create_image(x, y, image=self.tk_image, anchor="nw")

        self.input_points = []
        self.input_circles = []
        self.input_labels = []
        gap = new_height / (self.inputs_expected + 1)


        gate_number = ''.join(filter(str.isdigit, output_label)) or '1'

        for i in range(self.inputs_expected):
            px = self.x - 10
            py = self.y + (i + 1) * gap
            circle_radius = 5  # stały rozmiar kółek wejściowych
            circle = canvas.create_oval(px - circle_radius, py - circle_radius,
                                        px + circle_radius, py + circle_radius,
                                        fill="blue", tags=(f"input_{self.id}_{i}"))
            self.input_points.append((px, py))
            self.input_circles.append(circle)

            label_text = f"{chr(97 + i)}{gate_number}"
            label = canvas.create_text(px - 10, py, text=label_text, anchor="e")
            self.input_labels.append(label)
            self.input_names.append(label_text)

            def make_handler(gate, idx):
                def handler(event):
                    gate.editor.try_finish_connection(gate, idx)
                return handler

            canvas.tag_bind(f"input_{self.id}_{i}", "<Button-1>", make_handler(self, i))

        px_out = self.x + self.image.width + 10
        py_out = self.y + self.image.height / 2
        self.output_point = (px_out, py_out)
        self.output_circle = canvas.create_oval(px_out - 8, py_out - 8, px_out + 8, py_out + 8, fill="red", tags=("output", self.id))

        canvas.tag_bind(self.output_circle, "<ButtonPress-1>", self.on_output_press)
        canvas.tag_bind(self.output_circle, "<B1-Motion>", self.on_output_drag)
        canvas.tag_bind(self.output_circle, "<ButtonRelease-1>", self.on_output_release)

        self.output_label_id = canvas.create_text(px_out + 15, py_out, text=output_label, anchor="w")

    def on_output_press(self, event):
        self.editor.start_connection(self, event.x, event.y)

    def on_output_drag(self, event):
        self.editor.update_temp_line(event.x, event.y)

    def on_output_release(self, event):
        self.editor.try_finish_connection_at(event.x, event.y)

    def enable_drag(self):
        self.canvas.tag_bind(self.image_id, "<Button-1>", self.start_drag)
        self.canvas.tag_bind(self.image_id, "<B1-Motion>", self.on_drag)

    def start_drag(self, event):
        self.last_mouse_x = event.x_root
        self.last_mouse_y = event.y_root

    def on_drag(self, event):
        dx = event.x_root - self.last_mouse_x
        dy = event.y_root - self.last_mouse_y
        self.last_mouse_x = event.x_root
        self.last_mouse_y = event.y_root
        self.move(dx, dy)

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.canvas.move(self.image_id, dx, dy)
        for item in self.input_circles + self.input_labels:
            self.canvas.move(item, dx, dy)
        self.canvas.move(self.output_circle, dx, dy)
        self.canvas.move(self.output_label_id, dx, dy)
        self.input_points = [(x + dx, y + dy) for (x, y) in self.input_points]
        self.output_point = (self.output_point[0] + dx, self.output_point[1] + dy)

    def bind_right_click(self):
        self.canvas.tag_bind(self.image_id, "<Button-3>", self.on_right_click)

    def on_right_click(self, event):
        self.editor.delete_gate(self)

class CircuitEditor:
    def __init__(self, canvas):
        self.canvas = canvas
        self.gates = []
        self.connections = []
        self.output_counter = 1

        self.source_gate = None
        self.temp_line = None
        self.drawing_connection = False

        self.canvas.tag_bind("connection", "<Button-3>", self.delete_connection)

    def add_gate(self, gate_type, inputs=2):
        output_label = f"F{self.output_counter}"
        self.output_counter += 1
        gate = GateImage(self.canvas, 100 + 80 * len(self.gates), 100, gate_type, output_label, self, inputs)
        self.gates.append(gate)
        gate.enable_drag()
        gate.bind_right_click()

    def start_connection(self, gate, x, y):
        self.source_gate = gate
        self.drawing_connection = True
        if self.temp_line:
            self.canvas.delete(self.temp_line)
        self.temp_line = self.canvas.create_line(x, y, x, y, fill="gray", dash=(4, 2), width=2)

    def update_temp_line(self, x, y):
        if self.drawing_connection and self.temp_line:
            x0, y0 = self.source_gate.output_point
            self.canvas.coords(self.temp_line, x0, y0, x, y)

    def try_finish_connection_at(self, x, y):
        if not self.drawing_connection:
            return

        # Szukamy najbliższego wejścia do punktu (x, y) ze wszystkich bramek
        found_gate = None
        found_input_idx = None
        min_dist = float('inf')
        tolerance = 25

        for gate in self.gates:
            for idx, (ix, iy) in enumerate(gate.input_points):
                dist = ((ix - x) ** 2 + (iy - y) ** 2) ** 0.5
                if dist <= tolerance and dist < min_dist:
                    found_gate = gate
                    found_input_idx = idx
                    min_dist = dist

        if not found_gate or found_gate == self.source_gate or found_gate.input_connected_flags[found_input_idx]:
            self.cancel_connection()
            return

        src_x, src_y = self.source_gate.output_point
        dst_x, dst_y = found_gate.input_points[found_input_idx]

        if self.temp_line:
            self.canvas.delete(self.temp_line)

        line_id = self.canvas.create_line(src_x, src_y, dst_x, dst_y, arrow=tk.LAST, width=2, tags="connection")

        self.connections.append((self.source_gate, found_gate, line_id, found_input_idx))
        found_gate.input_connected_flags[found_input_idx] = True
        self.source_gate.outputs.append(found_gate)

        self.source_gate = None
        self.temp_line = None
        self.drawing_connection = False


        if not found_gate or found_gate == self.source_gate or found_gate.input_connected_flags[found_input_idx]:
            self.cancel_connection()
            return

        src_x, src_y = self.source_gate.output_point
        dst_x, dst_y = found_gate.input_points[found_input_idx]

        if self.temp_line:
            self.canvas.delete(self.temp_line)

        line_id = self.canvas.create_line(src_x, src_y, dst_x, dst_y, arrow=tk.LAST, width=2, tags="connection")

        self.connections.append((self.source_gate, found_gate, line_id, found_input_idx))
        found_gate.input_connected_flags[found_input_idx] = True
        self.source_gate.outputs.append(found_gate)

        self.source_gate = None
        self.temp_line = None
        self.drawing_connection = False


    def cancel_connection(self):
        if self.temp_line:
            self.canvas.delete(self.temp_line)
        self.temp_line = None
        self.source_gate = None
        self.drawing_connection = False

    def delete_connection(self, event):
        item = self.canvas.find_withtag("current")
        if not item:
            return
        line_id = item[0]

        for conn in self.connections:
            if conn[2] == line_id:
                source_gate, dest_gate, _, input_idx = conn
                self.canvas.delete(line_id)
                dest_gate.input_connected_flags[input_idx] = False
                if dest_gate in source_gate.outputs:
                    source_gate.outputs.remove(dest_gate)
                self.connections.remove(conn)
                break

    def delete_gate(self, gate):
        to_delete = [conn for conn in self.connections if conn[0] == gate or conn[1] == gate]
        for conn in to_delete:
            src, dst, line_id, input_idx = conn
            self.canvas.delete(line_id)
            if dst.input_connected_flags[input_idx]:
                dst.input_connected_flags[input_idx] = False
            if dst in src.outputs:
                src.outputs.remove(dst)
            self.connections.remove(conn)

        self.canvas.delete(gate.image_id)
        for item in gate.input_circles + gate.input_labels:
            self.canvas.delete(item)
        self.canvas.delete(gate.output_circle)
        self.canvas.delete(gate.output_label_id)

        self.gates.remove(gate)

    def clear_all(self):
        for gate in self.gates[:]:
            self.delete_gate(gate)
        self.gates.clear()
        self.connections.clear()
        self.output_counter = 1

    def generate_expression(self):
        expressions = {}

        def dfs(gate):
            if gate.id in expressions:
                return expressions[gate.id]

            inputs = []
            used_idxs = []

            for src, dst, _, input_idx in self.connections:
                if dst == gate:
                    inputs.append(dfs(src))
                    used_idxs.append(input_idx)

            for i in range(gate.inputs_expected):
                if i not in used_idxs:
                    inputs.append(gate.input_names[i])

            if gate.gate_type == "AND":
                expr = f"({' & '.join(inputs)})"
            elif gate.gate_type == "OR":
                expr = f"({' | '.join(inputs)})"
            elif gate.gate_type == "NOT":
                expr = f"(~{inputs[0]})"
            elif gate.gate_type == "NAND":
                expr = f"~({' & '.join(inputs)})"
            elif gate.gate_type == "NOR":
                expr = f"~({' | '.join(inputs)})"
            else:
                expr = gate.output_label

            expressions[gate.id] = expr
            return expr

        output_exprs = []
        for gate in self.gates:
            is_output = all(gate != conn[0] for conn in self.connections)
            if is_output:
                output_exprs.append(f"{gate.output_label} = {dfs(gate)}")

        result = "\n".join(output_exprs)
        self.show_expression_window(result)

    def show_expression_window(self, text):
        win = tk.Toplevel()
        win.title("Wygenerowana funkcja logiczna")
        text_widget = tk.Text(win, width=60, height=15)
        text_widget.pack(padx=10, pady=10)
        text_widget.insert(tk.END, text)
        text_widget.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    root.title("Edytor bramek logicznych")

    canvas = tk.Canvas(root, width=1000, height=700, bg="pink")
    canvas.pack()

    frame = tk.Frame(root)
    frame.pack()

    editor = CircuitEditor(canvas)

    tk.Label(frame, text="Liczba wejść (2-4):").pack(side=tk.LEFT)
    entry_inputs = tk.Spinbox(frame, from_=2, to=4, width=5)
    entry_inputs.pack(side=tk.LEFT)

    def make_add_gate(gate_type):
        return lambda: editor.add_gate(gate_type, int(entry_inputs.get()))

    for gate in ["AND", "OR", "NOT", "NAND", "NOR"]:
        tk.Button(frame, text=gate, command=make_add_gate(gate)).pack(side=tk.LEFT)

    tk.Button(frame, text="Generuj funkcję", command=editor.generate_expression).pack(side=tk.LEFT)
    tk.Button(frame, text="Wyczyść", command=editor.clear_all).pack(side=tk.LEFT)

    root.mainloop()

if __name__ == "__main__":
    main()
