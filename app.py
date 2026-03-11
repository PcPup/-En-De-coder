import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pygame
import math
import os
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────
# ENCODER / DECODER SETTINGS
# ──────────────────────────────────────────────
PIXEL_SIZE = 1
BITS_PER_CHAR = 8
DEFAULT_MAX_ROWS = 500  # fallback when no cover image
SEPARATOR_WIDTH = 2


def encode_message(message, output_path="encoded_message.png", cover_path=None):
    """Encode a message into a steganographic image, optionally hidden inside a cover image."""
    binary_list = [' ' if char == ' ' else format(ord(char), '08b') for char in message]

    total_chars = len(binary_list)
    if total_chars == 0:
        raise ValueError("Message is empty.")

    col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE

    pygame.init()

    if cover_path:
        cover = pygame.image.load(cover_path)
        cover_w, cover_h = cover.get_size()

        # Use the FULL height of the cover image as max rows
        max_rows = cover_h // PIXEL_SIZE

        # Calculate how many columns of 8-pixel-wide data fit across the cover
        max_data_cols = (cover_w + SEPARATOR_WIDTH) // (col_pixel_width + SEPARATOR_WIDTH)
        max_capacity = max_rows * max_data_cols

        if total_chars > max_capacity:
            raise ValueError(
                f"Message too long! {total_chars} chars but cover image "
                f"can hold {max_capacity} chars ({cover_w}x{cover_h}). "
                f"Use a larger cover image."
            )

        num_columns = math.ceil(total_chars / max_rows)
        rows = min(total_chars, max_rows)

        # Output is exactly the cover image size — never resize it
        surface = pygame.Surface((cover_w, cover_h))
        surface.blit(cover, (0, 0))

        # Clear lowest 2 bits of ENTIRE image so data is invisible
        for py in range(cover_h):
            for px in range(cover_w):
                r, g, b, *_ = surface.get_at((px, py))
                r = (r >> 2) << 2
                g = (g >> 2) << 2
                b = (b >> 2) << 2
                surface.set_at((px, py), (r, g, b))
    else:
        max_rows = DEFAULT_MAX_ROWS
        num_columns = math.ceil(total_chars / max_rows)
        rows = min(total_chars, max_rows)

        data_width = num_columns * col_pixel_width + max(0, num_columns - 1) * SEPARATOR_WIDTH
        data_height = rows * PIXEL_SIZE
        surface = pygame.Surface((data_width, data_height))
        surface.fill((0, 0, 0))

    # Embed data into LSBs
    for i, item in enumerate(binary_list):
        col_index = i // max_rows
        row_index = i % max_rows
        x_offset = col_index * (col_pixel_width + SEPARATOR_WIDTH)

        if col_index > 0 and row_index == 0:
            sep_x = col_index * (col_pixel_width + SEPARATOR_WIDTH) - SEPARATOR_WIDTH
            for sy in range(min(rows, surface.get_height())):
                for sx_off in range(SEPARATOR_WIDTH):
                    sx = sep_x + sx_off
                    if sx < surface.get_width() and sy < surface.get_height():
                        r, g, b, *_ = surface.get_at((sx, sy))
                        surface.set_at((sx, sy), (r | 1, g | 1, b | 1))

        y = row_index * PIXEL_SIZE

        if item == ' ':
            for bit_col in range(BITS_PER_CHAR):
                x = x_offset + bit_col * PIXEL_SIZE
                if x < surface.get_width() and y < surface.get_height():
                    r, g, b, *_ = surface.get_at((x, y))
                    surface.set_at((x, y), (r | 1, g & ~1, b & ~1))
        else:
            for bit_col, bit in enumerate(item):
                x = x_offset + bit_col * PIXEL_SIZE
                if x < surface.get_width() and y < surface.get_height():
                    r, g, b, *_ = surface.get_at((x, y))
                    if bit == '1':
                        surface.set_at((x, y), ((r & ~3) | 2, (g & ~3) | 2, (b & ~3) | 2))
                    else:
                        surface.set_at((x, y), (r & ~3, g & ~3, b & ~3))

    # End-of-message marker
    end_i = total_chars
    end_col = end_i // max_rows
    end_row = end_i % max_rows
    end_x = end_col * (col_pixel_width + SEPARATOR_WIDTH)
    end_y = end_row * PIXEL_SIZE
    if end_x < surface.get_width() and end_y < surface.get_height():
        r, g, b, *_ = surface.get_at((end_x, end_y))
        surface.set_at((end_x, end_y), (r & ~3, g & ~3, (b & ~3) | 3))

    pygame.image.save(surface, output_path)
    pygame.quit()

    return output_path, total_chars, num_columns, rows


def classify_pixel(r, g, b):
    """Classify a pixel by its lowest 2 bits (steganographic decoding)."""
    r_low = r & 3
    g_low = g & 3
    b_low = b & 3

    if r_low == 0 and g_low == 0 and b_low == 3:
        return 'end'
    if (r_low & 1) == 1 and (g_low & 1) == 0 and (b_low & 1) == 0:
        return 'red'
    if r_low == 2 and g_low == 2 and b_low == 2:
        return '1'
    return '0'


def decode_image(image_path):
    """Decode a steganographic binary image back into a message."""
    pygame.init()
    surface = pygame.image.load(image_path)
    width, height = surface.get_size()

    col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE
    num_columns = (width + SEPARATOR_WIDTH) // (col_pixel_width + SEPARATOR_WIDTH)
    num_rows = height // PIXEL_SIZE

    decoded_message = ""
    done = False

    for col_index in range(num_columns):
        if done:
            break
        x_offset = col_index * (col_pixel_width + SEPARATOR_WIDTH)

        for row_index in range(num_rows):
            if done:
                break
            y = row_index * PIXEL_SIZE

            if y >= height:
                break

            first_x = x_offset
            if first_x < width and y < height:
                r, g, b, *_ = surface.get_at((first_x, y))
                if classify_pixel(r, g, b) == 'end':
                    done = True
                    break

            bits = []
            is_space = False
            for bit_col in range(BITS_PER_CHAR):
                sample_x = x_offset + bit_col * PIXEL_SIZE
                if sample_x >= width:
                    break
                r, g, b, *_ = surface.get_at((sample_x, y))
                classification = classify_pixel(r, g, b)
                if classification == 'end':
                    done = True
                    break
                if classification == 'red':
                    is_space = True
                    break
                bits.append(classification)

            if done:
                break

            if is_space:
                decoded_message += ' '
            elif len(bits) == 8:
                binary_str = ''.join(bits)
                char_value = int(binary_str, 2)
                if char_value == 0:
                    break
                decoded_message += chr(char_value)

    pygame.quit()
    return decoded_message


def check_accuracy(original, decoded):
    """Compare original and decoded messages, return report string and accuracy %."""
    total_chars = max(len(original), len(decoded))
    if total_chars == 0:
        return "Both messages are empty.", 100.0

    correct = 0
    errors = []
    for i in range(total_chars):
        orig_char = original[i] if i < len(original) else None
        dec_char = decoded[i] if i < len(decoded) else None
        if orig_char == dec_char:
            correct += 1
        else:
            errors.append((i, repr(orig_char) if orig_char else '<missing>',
                              repr(dec_char) if dec_char else '<missing>'))

    accuracy = (correct / total_chars) * 100

    lines = []
    lines.append("=" * 50)
    lines.append("           ACCURACY REPORT")
    lines.append("=" * 50)
    lines.append(f"  Original length : {len(original)} characters")
    lines.append(f"  Decoded length  : {len(decoded)} characters")
    lines.append(f"  Matching chars  : {correct}/{total_chars}")
    lines.append(f"  Accuracy        : {accuracy:.2f}%")
    lines.append("=" * 50)

    if errors:
        lines.append(f"\n  {len(errors)} error(s) found:")
        lines.append("  " + "-" * 46)
        for pos, exp, got in errors[:30]:
            lines.append(f"    Position {pos}: expected {exp}, got {got}")
        if len(errors) > 30:
            lines.append(f"    ... and {len(errors) - 30} more errors")
    else:
        lines.append("\n  ✓ PERFECT MATCH! No errors found.")

    return "\n".join(lines), accuracy


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Binary Encoder / Decoder — Steganographic")
        self.geometry("900x750")
        self.configure(bg="#1e1e1e")
        self.minsize(700, 550)

        self.cover_image_path = None

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#cccccc",
                         padding=[14, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                   background=[("selected", "#0078d4")],
                   foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#cccccc",
                         font=("Segoe UI", 10))
        style.configure("Accent.TButton", background="#0078d4", foreground="#ffffff",
                         font=("Segoe UI", 10, "bold"), padding=[12, 6])
        style.map("Accent.TButton",
                   background=[("active", "#005fa3")])
        style.configure("Secondary.TButton", background="#3c3c3c", foreground="#cccccc",
                         font=("Segoe UI", 10), padding=[10, 5])
        style.map("Secondary.TButton",
                   background=[("active", "#505050")])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.encode_tab = ttk.Frame(notebook)
        self.decode_tab = ttk.Frame(notebook)
        self.accuracy_tab = ttk.Frame(notebook)

        notebook.add(self.encode_tab, text="  Encode  ")
        notebook.add(self.decode_tab, text="  Decode  ")
        notebook.add(self.accuracy_tab, text="  Accuracy Check  ")

        self._build_encode_tab()
        self._build_decode_tab()
        self._build_accuracy_tab()

    # ── helpers ──
    def _make_text(self, parent, height=10):
        txt = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 11),
                                        bg="#252526", fg="#d4d4d4", insertbackground="#d4d4d4",
                                        selectbackground="#264f78", relief="flat",
                                        borderwidth=1, height=height)
        return txt

    def _make_label(self, parent, text):
        lbl = ttk.Label(parent, text=text)
        lbl.pack(anchor="w", padx=8, pady=(10, 2))
        return lbl

    def _make_button(self, parent, text, command, style_name="Accent.TButton"):
        btn = ttk.Button(parent, text=text, style=style_name, command=command)
        btn.pack(side="left", padx=4, pady=8)
        return btn

    # ── Encode tab ──
    def _build_encode_tab(self):
        self._make_label(self.encode_tab, "Paste or type your message below:")
        self.encode_input = self._make_text(self.encode_tab, height=14)
        self.encode_input.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Cover image section
        cover_frame = ttk.Frame(self.encode_tab)
        cover_frame.pack(fill="x", padx=8)
        self._make_button(cover_frame, "🖼️  Select Cover Image", self._on_select_cover, "Secondary.TButton")
        self._make_button(cover_frame, "❌  Clear Cover", self._on_clear_cover, "Secondary.TButton")

        self.cover_label = ttk.Label(self.encode_tab, text="  No cover image (output will be near-black)",
                                     foreground="#888888")
        self.cover_label.pack(anchor="w", padx=8, pady=(0, 4))

        # Encode button
        btn_frame = ttk.Frame(self.encode_tab)
        btn_frame.pack(fill="x", padx=8)
        self._make_button(btn_frame, "⚡  Encode & Save Image", self._on_encode)

        self.encode_status = ttk.Label(self.encode_tab, text="", foreground="#6a9955")
        self.encode_status.pack(anchor="w", padx=8, pady=(0, 8))

    def _on_select_cover(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All files", "*.*")],
            initialdir=BASE_DIR,
            title="Select cover image"
        )
        if path:
            self.cover_image_path = path
            self.cover_label.config(text=f"  ✓ Cover: {os.path.basename(path)}",
                                    foreground="#6a9955")

    def _on_clear_cover(self):
        self.cover_image_path = None
        self.cover_label.config(text="  No cover image (output will be near-black)",
                                foreground="#888888")

    def _on_encode(self):
        message = self.encode_input.get("1.0", tk.END).rstrip("\n")
        if not message:
            messagebox.showwarning("Empty", "Please enter a message to encode.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialdir=BASE_DIR,
            initialfile="encoded_message.png",
            title="Save encoded image"
        )
        if not save_path:
            return

        cover = self.cover_image_path
        self.encode_status.config(text="Encoding...", foreground="#dcdcaa")
        self.update_idletasks()

        def work():
            try:
                _, total, cols, rows = encode_message(message, save_path, cover_path=cover)
                hidden_str = "hidden in cover image!" if cover else "near-black steganographic"
                self.after(0, lambda: self.encode_status.config(
                    text=f"✓ Saved  |  {total} chars  •  {cols} col(s)  •  "
                         f"{rows} rows  •  {hidden_str}",
                    foreground="#6a9955"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.encode_status.config(text=""))

        threading.Thread(target=work, daemon=True).start()

    # ── Decode tab ──
    def _build_decode_tab(self):
        self._make_label(self.decode_tab, "Select an encoded image to decode:")

        btn_frame = ttk.Frame(self.decode_tab)
        btn_frame.pack(fill="x", padx=8)
        self._make_button(btn_frame, "📂  Open Image & Decode", self._on_decode)

        self._make_label(self.decode_tab, "Decoded message:")
        self.decode_output = self._make_text(self.decode_tab, height=18)
        self.decode_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _on_decode(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PNG Image", "*.png"), ("All files", "*.*")],
            initialdir=BASE_DIR,
            title="Open encoded image"
        )
        if not file_path:
            return

        self.decode_output.delete("1.0", tk.END)
        self.decode_output.insert(tk.END, "Decoding...")
        self.update_idletasks()

        def work():
            try:
                result = decode_image(file_path)
                self.after(0, lambda: self._set_decode_result(result))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.decode_output.delete("1.0", tk.END))

        threading.Thread(target=work, daemon=True).start()

    def _set_decode_result(self, text):
        self.decode_output.delete("1.0", tk.END)
        self.decode_output.insert(tk.END, text)

    # ── Accuracy tab ──
    def _build_accuracy_tab(self):
        self._make_label(self.accuracy_tab, "Original message:")
        self.acc_original = self._make_text(self.accuracy_tab, height=8)
        self.acc_original.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._make_label(self.accuracy_tab, "Decoded message:")
        self.acc_decoded = self._make_text(self.accuracy_tab, height=8)
        self.acc_decoded.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        btn_frame = ttk.Frame(self.accuracy_tab)
        btn_frame.pack(fill="x", padx=8)
        self._make_button(btn_frame, "🔍  Check Accuracy", self._on_accuracy)

        self._make_label(self.accuracy_tab, "Report:")
        self.acc_report = self._make_text(self.accuracy_tab, height=8)
        self.acc_report.config(state=tk.DISABLED)
        self.acc_report.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _on_accuracy(self):
        original = self.acc_original.get("1.0", tk.END).rstrip("\n")
        decoded = self.acc_decoded.get("1.0", tk.END).rstrip("\n")

        if not original and not decoded:
            messagebox.showwarning("Empty", "Please enter both messages.")
            return

        report, _ = check_accuracy(original, decoded)

        self.acc_report.config(state=tk.NORMAL)
        self.acc_report.delete("1.0", tk.END)
        self.acc_report.insert(tk.END, report)
        self.acc_report.config(state=tk.DISABLED)


if __name__ == "__main__":
    app = App()
    app.mainloop()
