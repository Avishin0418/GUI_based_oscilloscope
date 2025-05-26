import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
from collections import deque
import numpy as np
import time
import sys

class AetheraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AETHERA Kit – ESP32 Waveform Generator")
        self.root.configure(bg="#1e1e2f")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.state('zoomed')

        self.serial_port = self.find_serial_port(default="COM9")
        self.baud_rate = 115200

        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            time.sleep(2)
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", f"Could not open {self.serial_port}.\n{e}")
            sys.exit(1)

        self.MAX_POINTS = 1024
        self.gen_data = deque([0]*self.MAX_POINTS, maxlen=self.MAX_POINTS)
        self.in_data = deque([0]*self.MAX_POINTS, maxlen=self.MAX_POINTS)
        self.paused = False

        self.waveform_var = tk.StringVar(value="sine")
        self.freq_var = tk.IntVar(value=1000)
        self.amp_var = tk.IntVar(value=200)
        self.phase_var = tk.IntVar(value=0)

        self.setup_gui()
        self.start_serial_thread()
        self.update_plot()

    def find_serial_port(self, default="COM9"):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "USB" in port.description or "ESP32" in port.description:
                return port.device
        return default

    def setup_gui(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TLabel", background="#1e1e2f", foreground="white", font=('Segoe UI', 10))
        style.configure("TButton", padding=6, font=('Segoe UI', 10))
        style.configure("TCombobox", padding=4)

        control_frame = tk.Frame(self.root, bg="#1e1e2f")
        control_frame.pack(side=tk.LEFT, padx=20, pady=20, fill=tk.Y)

        form_frame = ttk.LabelFrame(control_frame, text="Waveform Settings", padding=10)
        form_frame.pack(fill=tk.X, pady=10)

        ttk.Label(form_frame, text="Waveform Type").pack(anchor='w', pady=(5, 0))
        self.waveform_combo = ttk.Combobox(form_frame, textvariable=self.waveform_var,
                                           values=["sine", "square", "triangle", "sawtooth"], width=18)
        self.waveform_combo.pack(pady=(0, 5))

        self.add_labeled_entry(form_frame, "Frequency (Hz)", self.freq_var)
        self.add_labeled_entry(form_frame, "Amplitude (0–255)", self.amp_var)
        self.add_labeled_entry(form_frame, "Phase (0–360°)", self.phase_var)

        ttk.Button(control_frame, text="Send to ESP32", command=self.send_command).pack(pady=10, fill=tk.X)
        ttk.Button(control_frame, text="Pause / Resume", command=self.toggle_pause).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="Export CSV", command=self.export_csv).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="Toggle Theme", command=self.toggle_theme).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="About", command=self.show_about).pack(pady=5, fill=tk.X)

        self.freq_label = tk.Label(control_frame, text="Estimated Freq: -- Hz",
                                   font=("Arial", 10), fg="white", bg="#1e1e2f")
        self.freq_label.pack(pady=10)

        plot_frame = tk.Frame(self.root, bg="#1e1e2f")
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = plt.figure(figsize=(10, 8))
        self.fig.patch.set_facecolor("#1e1e2f")
        gs = GridSpec(2, 1, figure=self.fig, height_ratios=[1, 1], hspace=0.4)

        self.ax1 = self.fig.add_subplot(gs[0])
        self.ax2 = self.fig.add_subplot(gs[1])

        self.gen_line, = self.ax1.plot(range(self.MAX_POINTS), list(self.gen_data), color='cyan', label='Generated')
        self.in_line, = self.ax2.plot(range(self.MAX_POINTS), list(self.in_data), color='magenta', label='Input')

        self.setup_axis(self.ax1, "Generated Signal", "DAC Value")
        self.setup_axis(self.ax2, "Input Signal", "ADC Value")

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def add_labeled_entry(self, parent, label, variable):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(5, 0))
        entry = tk.Entry(parent, textvariable=variable, width=20)
        entry.pack(pady=(0, 5))
        return entry

    def setup_axis(self, axis, title, ylabel):
        axis.set_ylim(0, 4096)
        axis.set_title(title, color='white')
        axis.set_xlabel("Samples", color='white')
        axis.set_ylabel(ylabel, color='white')
        axis.tick_params(colors='white')
        axis.set_facecolor("#2e2e3f")
        axis.legend(loc='upper right', facecolor='#2e2e3f', edgecolor='white', labelcolor='white')

    def send_command(self):
        try:
            freq = int(self.freq_var.get())
            amp = int(self.amp_var.get())
            phase = int(self.phase_var.get())
            waveform = self.waveform_var.get()

            if not (0 <= amp <= 255) or not (0 <= phase <= 360):
                raise ValueError("Amplitude or Phase out of range")

            cmd = f"wave={waveform},freq={freq},amp={amp},phase={phase}\n"
            print("Sending:", cmd.strip())
            self.ser.write(cmd.encode())

        except Exception as e:
            messagebox.showerror("Input Error", f"Invalid input or serial failure:\n{e}")

    def toggle_pause(self):
        self.paused = not self.paused

    def export_csv(self):
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
            if file_path:
                with open(file_path, 'w') as f:
                    f.write("Sample,Generated,Input\n")
                    for i in range(len(self.gen_data)):
                        f.write(f"{i},{self.gen_data[i]},{self.in_data[i]}\n")
                messagebox.showinfo("Export Complete", "Data exported successfully.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def toggle_theme(self):
        messagebox.showinfo("Theme", "Currently only dark mode is supported.")

    def show_about(self):
        messagebox.showinfo("About", "AETHERA Kit GUI\nDeveloped using Tkinter and Matplotlib")

    def update_plot(self):
        gen_vals = list(self.gen_data)
        in_vals = list(self.in_data)

        self.gen_line.set_ydata(gen_vals)
        self.in_line.set_ydata(in_vals)

        mean_val = np.mean(gen_vals)
        crossings = np.where(np.diff(np.signbit(np.array(in_vals) - mean_val)))[0]
        if len(crossings) > 1:
            periods = np.diff(crossings)
            if len(periods) > 0:
                avg_period = np.mean(periods)
                est_freq = 1000 / avg_period
                self.freq_label.config(text=f"Estimated Freq: {est_freq:.1f} Hz")
            else:
                self.freq_label.config(text="Estimated Freq: -- Hz")
        else:
            self.freq_label.config(text="Estimated Freq: -- Hz")

        self.canvas.draw()
        self.root.after(50, self.update_plot)

    def start_serial_thread(self):
        threading.Thread(target=self.read_serial, daemon=True).start()

    def read_serial(self):
        while True:
            if not self.paused:
                try:
                    line = self.ser.readline().decode().strip()
                    if line.startswith("GEN:") and "IN:" in line:
                        parts = line.split(',')
                        gen_val = int(parts[0].split(':')[1])
                        in_val = int(parts[1].split(':')[1])
                        self.gen_data.append(gen_val)
                        self.in_data.append(in_val)
                except Exception:
                    continue

    def on_close(self):
        try:
            if self.ser.is_open:
                self.ser.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AetheraGUI(root)
    root.mainloop()
