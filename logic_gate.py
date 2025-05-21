import tkinter as tk
from PIL import Image, ImageTk
import uuid
import schemdraw
import schemdraw.logic as logic

# === Generuj obraz bramki logicznej ===
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
    def __init__(self, canvas, x, y, gate_type, output_label):
        self.canvas = canvas
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
        self.inputs_connected = 0
        self.outputs = []

        # === Punkty wejściowe ===
        self.input_points = []
        self.input_circles = []
        self.input_labels = []
        gap = self.image.height / (self.inputs_expected + 1)
        for i in range(self.inputs_expected):
            px = self.x - 10
            py = self.y + (i + 1) * gap
            circle = canvas.create_oval(px-4, py-4, px+4, py+4, fill="blue", tags="input")
            canvas.tag_bind(circle, "<Button-1>", self.on_input_click)
            label = canvas.create_text(px - 10, py, text=chr(65 + i), anchor="e")
            self.input_points.append((px, py))
            self.input_circles.append(circle)
            self.input_labels.append(label)

        # === Punkt wyjściowy ===
        px_out = self.x + self.image.width + 10
        py_out = self.y + self.image.height / 2
        self.output_point = (px_out, py_out)
        self.output_circle = canvas.create_oval(px_out-4, py_out-4, px_out+4, py_out+4, fill="red", tags="output")
        canvas.tag_bind(self.output_circle, "<Button-1>", self.on_output_click)
        self.output_label_id = canvas.create_text(px_out + 15, py_out, text=output_label, anchor="w")

        # === Przesuwanie tylko klikając na obraz ===
        canvas.tag_bind(self.image_id, "<Button1-Motion>", self.move)

    def move(self, event):
        dx = event.x - self.x
        dy = event.y - self.y
        self.canvas.move(self.image_id, dx, dy)
        for c in self.input_circles:
            self.canvas.move(c, dx, dy)
        for l in self.input_labels:
            self.canvas.move(l, dx, dy)
        self.canvas.move(self.output_circle, dx, dy)
        self.canvas.move(self.output_label_id, dx, dy)

        # Aktualizacja punktów
        gap = self.image.height / (self.inputs_expected + 1)
        self.input_points = [(self.x - 10 + dx, self.y + (i + 1) * gap + dy)
                             for i in range(self.inputs_expected)]
        self.output_point = (self.output_point[0] + dx, self.output_point[1] + dy)

        self.x = event.x
        self.y = event.y

    def on_output_click(self, event):
        editor.selected_output_gate = self

    def on_input_click(self, event):
        if editor.selected_output_gate is None:
            return

        src = editor.selected_output_gate
        dst = self

        if src == dst or dst.inputs_connected >= dst.inputs_expected:
            editor.selected_output_gate = None
            return

        src_x, src_y = src.output_point
        dst_x, dst_y = dst.input_points[dst.inputs_connected]

        if src_x < dst_x:
            line_id = self.canvas.create_line(src_x, src_y, dst_x, dst_y, arrow=tk.LAST, width=2, tags="connection")
            editor.connections.append((src, dst, line_id))
            src.outputs.append(dst)
            dst.inputs_connected += 1

        editor.selected_output_gate = None

class CircuitEditor:
    def __init__(self, canvas):
        self.canvas = canvas
        self.gates = []
        self.connections = []
        self.selected_output_gate = None
        self.output_counter = 1
        self.history = []  # do cofania

        # Obsługa klawiatury do usuwania i cofania
        self.canvas.bind_all("<Delete>", self.delete_connection)
        self.canvas.bind_all("<Control-z>", self.undo)

    def add_gate(self, gate_type):
        output_label = f"F{self.output_counter}"
        self.output_counter += 1
        gate = GateImage(self.canvas, 100 + 80 * len(self.gates), 100, gate_type, output_label)
        self.gates.append(gate)
        self.history.append(('add_gate', gate))

    def delete_connection(self, event=None):
        # Usuń ostatnią połączenie z listy zaznaczonych linii (jeśli kliknięta)
        items = self.canvas.find_withtag("current")
        if not items:
            return
        item = items[0]
        # Sprawdź czy to linia połączenia
        for conn in self.connections:
            if conn[2] == item:
                src, dst, line_id = conn
                self.canvas.delete(line_id)
                dst.inputs_connected -= 1
                if dst.outputs and src in dst.outputs:
                    dst.outputs.remove(src)
                self.connections.remove(conn)
                self.history.append(('delete_connection', conn))
                break

    def undo(self, event=None):
        if not self.history:
            return
        action = self.history.pop()
        if action[0] == 'add_gate':
            gate = action[1]
            # usuń bramkę
            self.canvas.delete(gate.image_id)
            for c in gate.input_circles:
                self.canvas.delete(c)
            for l in gate.input_labels:
                self.canvas.delete(l)
            self.canvas.delete(gate.output_circle)
            self.canvas.delete(gate.output_label_id)
            self.gates.remove(gate)
            # usuń powiązane połączenia
            to_remove = [c for c in self.connections if c[0] == gate or c[1] == gate]
            for c in to_remove:
                self.canvas.delete(c[2])
                self.connections.remove(c)
        elif action[0] == 'delete_connection':
            src, dst, line_id = action[1]
            # odtwórz połączenie
            src_x, src_y = src.output_point
            dst_x, dst_y = dst.input_points[dst.inputs_connected]
            line = self.canvas.create_line(src_x, src_y, dst_x, dst_y, arrow=tk.LAST, width=2, tags="connection")
            self.connections.append((src, dst, line))
            dst.inputs_connected += 1

    def generate_expression(self):
        expressions = {}

        def dfs(gate):
            if gate.id in expressions:
                return expressions[gate.id]

            inputs = []
            # Znajdź wszystkie połączenia które mają gate jako cel
            for src, dst, _ in self.connections:
                if dst == gate:
                    inputs.append(dfs(src))

            # Uzupełnij brakujące wejścia jako "1"
            while len(inputs) < gate.inputs_expected:
                inputs.append("1")

            if gate.gate_type == "AND":
                expr = f"({inputs[0]} & {inputs[1]})"
            elif gate.gate_type == "OR":
                expr = f"({inputs[0]} | {inputs[1]})"
            elif gate.gate_type == "NOT":
                expr = f"(~{inputs[0]})"
            else:
                expr = gate.output_label

            expressions[gate.id] = expr
            return expr

        output_exprs = []
        for gate in self.gates:
            # Bramka, która nie jest źródłem połączenia (czyli nie jest na wyjściu innych)
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

# === GUI ===
root = tk.Tk()
root.title("Edytor bramek logicznych")

canvas = tk.Canvas(root, width=1000, height=700, bg="white")
canvas.pack()

editor = CircuitEditor(canvas)

frame = tk.Frame(root)
frame.pack()

for gate in ["AND", "OR", "NOT"]:
    tk.Button(frame, text=gate, command=lambda g=gate: editor.add_gate(g)).pack(side=tk.LEFT)

btn_generate = tk.Button(frame, text="Generuj funkcję", command=editor.generate_expression)
btn_generate.pack(side=tk.LEFT)

root.mainloop()
