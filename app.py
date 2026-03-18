import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pygame
import math
import os
import threading
import hashlib

# ──────────────────────────────────────────────
# ENCODER / DECODER SETTINGS
# ──────────────────────────────────────────────
PIXEL_SIZE = 1
BITS_PER_CHAR = 8
DEFAULT_MAX_ROWS = 500  # fallback when no cover image
SEPARATOR_WIDTH = 0

# Version & metadata
ENCODER_VERSION = 2          # bump this when the format changes
ENCRYPTION_NONE = 0
ENCRYPTION_SCRAMBLE = 1

# The scramble seed — both encoder and decoder know this.
# It's NOT a user password; it's a built-in obfuscation key.
_SCRAMBLE_SEED = "sT3g0-Scr@mbl3!k3y_2024#NSD"

# ── Metadata layout (rows in column 0) ──
# Row 0 : format version   (0–255)
# Row 1 : encryption type  (0 = none, 1 = scramble)
# Row 2 : reserved / flags (0 for now)
# Row 3 : reserved         (0 for now)
# Row 4 : reserved         (0 for now)
# Rows 5+ in column 0 are unused (stay as cover / black)
METADATA_ROWS = 5


# ──────────────────────────────────────────────
# ENCRYPTION / DECRYPTION (built-in scramble)
# ──────────────────────────────────────────────
def _derive_key(seed: str, length: int) -> bytes:
    """Derive a repeatable key stream from a seed using SHA-256 in counter mode."""
    key = b""
    counter = 0
    while len(key) < length:
        block = hashlib.sha256((seed + str(counter)).encode("utf-8")).digest()
        key += block
        counter += 1
    return key[:length]


def scramble(message: str) -> str:
    """Scramble a message using the built-in key. Returns a hex-encoded string."""
    raw = message.encode("utf-8")
    key = _derive_key(_SCRAMBLE_SEED, len(raw))
    encrypted_bytes = bytes(r ^ k for r, k in zip(raw, key))
    return encrypted_bytes.hex()


def unscramble(hex_string: str) -> str:
    """Unscramble a hex-encoded message using the built-in key."""
    try:
        encrypted_bytes = bytes.fromhex(hex_string)
    except ValueError:
        raise ValueError("Decode failed -- image data is corrupted or not a v2 encoded image.")
    key = _derive_key(_SCRAMBLE_SEED, len(encrypted_bytes))
    decrypted_bytes = bytes(e ^ k for e, k in zip(encrypted_bytes, key))
    try:
        return decrypted_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Decode failed -- image data appears corrupted.")


# ──────────────────────────────────────────────
# METADATA helpers
# ──────────────────────────────────────────────
def _build_metadata(version: int, encryption: int, reserved1: int = 0,
                    reserved2: int = 0, reserved3: int = 0) -> list:
    """Build a list of binary strings for the metadata column rows."""
    return [
        format(version & 0xFF, '08b'),
        format(encryption & 0xFF, '08b'),
        format(reserved1 & 0xFF, '08b'),
        format(reserved2 & 0xFF, '08b'),
        format(reserved3 & 0xFF, '08b'),
    ]


def _parse_metadata(meta_bytes: list) -> dict:
    """Parse a list of byte-values from the metadata column into a dict."""
    return {
        'version': meta_bytes[0] if len(meta_bytes) > 0 else 0,
        'encryption': meta_bytes[1] if len(meta_bytes) > 1 else 0,
        'reserved1': meta_bytes[2] if len(meta_bytes) > 2 else 0,
        'reserved2': meta_bytes[3] if len(meta_bytes) > 3 else 0,
        'reserved3': meta_bytes[4] if len(meta_bytes) > 4 else 0,
    }


def _write_byte_to_surface(surface, x_offset, y, binary_str):
    """Write one 8-bit binary string into the surface at the given position."""
    for bit_col, bit in enumerate(binary_str):
        x = x_offset + bit_col * PIXEL_SIZE
        if x < surface.get_width() and y < surface.get_height():
            r, g, b, *_ = surface.get_at((x, y))
            if bit == '1':
                surface.set_at((x, y), ((r & ~3) | 2, (g & ~3) | 2, (b & ~3) | 2))
            else:
                surface.set_at((x, y), (r & ~3, g & ~3, b & ~3))


# ──────────────────────────────────────────────
# ENCODER
# ──────────────────────────────────────────────
def encode_message(message, output_path="encoded_message.png", cover_path=None):
    """Encode a message into a steganographic image.

    Column 0 is always metadata (version, encryption type, reserved fields).
    The message is automatically scrambled before embedding.
    Data columns start at column 1.
    """
    # Always scramble -- no password needed
    scrambled = scramble(message)

    binary_list = [' ' if ch == ' ' else format(ord(ch), '08b') for ch in scrambled]

    total_chars = len(binary_list)
    if total_chars == 0:
        raise ValueError("Message is empty.")

    col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE

    pygame.init()

    if cover_path:
        cover = pygame.image.load(cover_path)
        cover_w, cover_h = cover.get_size()

        max_rows = cover_h // PIXEL_SIZE

        # Column 0 is metadata; data columns start at column 1
        max_data_cols = (cover_w + SEPARATOR_WIDTH) // (col_pixel_width + SEPARATOR_WIDTH) - 1
        if max_data_cols < 1:
            raise ValueError("Cover image is too narrow to hold metadata + data. Use a wider image.")
        max_capacity = max_rows * max_data_cols

        if total_chars > max_capacity:
            raise ValueError(
                f"Message too long! {total_chars} chars but cover image "
                f"can hold {max_capacity} chars ({cover_w}x{cover_h}). "
                f"Use a larger cover image."
            )

        num_data_columns = math.ceil(total_chars / max_rows)
        rows = min(total_chars, max_rows)

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
        num_data_columns = math.ceil(total_chars / max_rows)
        rows = min(total_chars, max_rows)

        # +1 column for metadata (column 0)
        total_columns = num_data_columns + 1
        data_width = total_columns * col_pixel_width + max(0, total_columns - 1) * SEPARATOR_WIDTH
        data_height = max(rows, METADATA_ROWS) * PIXEL_SIZE
        surface = pygame.Surface((data_width, data_height))
        surface.fill((0, 0, 0))

    # -- Write metadata into column 0 --
    metadata_bins = _build_metadata(ENCODER_VERSION, ENCRYPTION_SCRAMBLE)
    meta_x_offset = 0  # column 0
    for row_idx, mbin in enumerate(metadata_bins):
        y = row_idx * PIXEL_SIZE
        _write_byte_to_surface(surface, meta_x_offset, y, mbin)

    # -- Write message data starting at column 1 --
    for i, item in enumerate(binary_list):
        data_col = i // max_rows          # 0-based data column
        row_index = i % max_rows
        # Shift right by 1 column (column 0 = metadata)
        actual_col = data_col + 1
        x_offset = actual_col * (col_pixel_width + SEPARATOR_WIDTH)

        if data_col > 0 and row_index == 0:
            sep_x = actual_col * (col_pixel_width + SEPARATOR_WIDTH) - SEPARATOR_WIDTH
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
            _write_byte_to_surface(surface, x_offset, y, item)

    # End-of-message marker (in data-column space, so offset by 1)
    end_i = total_chars
    end_data_col = end_i // max_rows
    end_row = end_i % max_rows
    end_actual_col = end_data_col + 1
    end_x = end_actual_col * (col_pixel_width + SEPARATOR_WIDTH)
    end_y = end_row * PIXEL_SIZE
    if end_x < surface.get_width() and end_y < surface.get_height():
        r, g, b, *_ = surface.get_at((end_x, end_y))
        surface.set_at((end_x, end_y), (r & ~3, g & ~3, (b & ~3) | 3))

    pygame.image.save(surface, output_path)
    pygame.quit()

    return output_path, total_chars, num_data_columns, rows


# ──────────────────────────────────────────────
# DECODER
# ──────────────────────────────────────────────
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
    """Decode a steganographic binary image back into a message.

    Reads metadata from column 0, then reads message data from column 1+.
    Automatically unscrambles based on the encryption flag in the metadata.
    Returns (decoded_message, metadata_dict).
    """
    pygame.init()
    surface = pygame.image.load(image_path)
    width, height = surface.get_size()

    col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE
    total_columns = (width + SEPARATOR_WIDTH) // (col_pixel_width + SEPARATOR_WIDTH)
    num_rows = height // PIXEL_SIZE

    # -- Read metadata from column 0 --
    meta_values = []
    meta_x_offset = 0
    for row_idx in range(min(METADATA_ROWS, num_rows)):
        y = row_idx * PIXEL_SIZE
        bits = []
        for bit_col in range(BITS_PER_CHAR):
            sx = meta_x_offset + bit_col * PIXEL_SIZE
            if sx >= width or y >= height:
                break
            r, g, b, *_ = surface.get_at((sx, y))
            c = classify_pixel(r, g, b)
            bits.append('1' if c == '1' else '0')
        if len(bits) == 8:
            meta_values.append(int(''.join(bits), 2))
        else:
            meta_values.append(0)

    metadata = _parse_metadata(meta_values)

    # -- Read message from columns 1+ --
    num_data_columns = total_columns - 1
    decoded_message = ""
    done = False

    for data_col in range(num_data_columns):
        if done:
            break
        actual_col = data_col + 1   # skip column 0 (metadata)
        x_offset = actual_col * (col_pixel_width + SEPARATOR_WIDTH)

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

    # -- Apply decryption based on metadata --
    if metadata['encryption'] == ENCRYPTION_SCRAMBLE:
        decoded_message = unscramble(decoded_message)

    return decoded_message, metadata


# ──────────────────────────────────────────────
# ACCURACY CHECKER
# ──────────────────────────────────────────────
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
        lines.append("\n  PERFECT MATCH! No errors found.")

    return "\n".join(lines), accuracy


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Binary Encoder / Decoder v2 -- Steganographic")
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

    # -- helpers --
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

    # -- Encode tab --
    def _build_encode_tab(self):
        self._make_label(self.encode_tab, "Paste or type your message below:")
        self.encode_input = self._make_text(self.encode_tab, height=14)
        self.encode_input.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Cover image section
        cover_frame = ttk.Frame(self.encode_tab)
        cover_frame.pack(fill="x", padx=8)
        self._make_button(cover_frame, "Select Cover Image", self._on_select_cover, "Secondary.TButton")
        self._make_button(cover_frame, "Clear Cover", self._on_clear_cover, "Secondary.TButton")

        self.cover_label = ttk.Label(self.encode_tab, text="  No cover image (output will be near-black)",
                                     foreground="#888888")
        self.cover_label.pack(anchor="w", padx=8, pady=(0, 4))

        ttk.Label(self.encode_tab, text="  Message is automatically scrambled (built-in encryption)",
                  foreground="#6a9955").pack(anchor="w", padx=8, pady=(0, 4))

        # Encode button
        btn_frame = ttk.Frame(self.encode_tab)
        btn_frame.pack(fill="x", padx=8)
        self._make_button(btn_frame, "Encode & Save Image", self._on_encode)

        self.encode_status = ttk.Label(self.encode_tab, text="", foreground="#6a9955")
        self.encode_status.pack(anchor="w", padx=8, pady=(0, 8))

    def _on_select_cover(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All files", "*.*")],
            title="Select cover image"
        )
        if path:
            self.cover_image_path = path
            self.cover_label.config(text=f"  Cover: {os.path.basename(path)}",
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
                    text=f"Saved  |  {total} chars  |  {cols} data col(s)  |  "
                         f"{rows} rows  |  {hidden_str}  |  scrambled",
                    foreground="#6a9955"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.encode_status.config(text=""))

        threading.Thread(target=work, daemon=True).start()

    # -- Decode tab --
    def _build_decode_tab(self):
        self._make_label(self.decode_tab, "Select an encoded image to decode:")

        btn_frame = ttk.Frame(self.decode_tab)
        btn_frame.pack(fill="x", padx=8)
        self._make_button(btn_frame, "Open Image & Decode", self._on_decode)

        self._make_label(self.decode_tab, "Decoded message:")
        self.decode_output = self._make_text(self.decode_tab, height=16)
        self.decode_output.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._make_label(self.decode_tab, "Image metadata:")
        self.decode_meta = self._make_text(self.decode_tab, height=4)
        self.decode_meta.config(state=tk.DISABLED)
        self.decode_meta.pack(fill="x", padx=8, pady=(0, 8))

    def _on_decode(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PNG Image", "*.png"), ("All files", "*.*")],
            title="Open encoded image"
        )
        if not file_path:
            return

        self.decode_output.delete("1.0", tk.END)
        self.decode_output.insert(tk.END, "Decoding...")
        self.update_idletasks()

        def work():
            try:
                result, metadata = decode_image(file_path)
                self.after(0, lambda: self._set_decode_result(result, metadata))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.decode_output.delete("1.0", tk.END))

        threading.Thread(target=work, daemon=True).start()

    def _set_decode_result(self, text, metadata):
        self.decode_output.delete("1.0", tk.END)
        self.decode_output.insert(tk.END, text)

        enc_name = {ENCRYPTION_NONE: "None", ENCRYPTION_SCRAMBLE: "Scramble (built-in)"}.get(
            metadata['encryption'], f"Unknown ({metadata['encryption']})")

        meta_str = (
            f"Format version : {metadata['version']}  |  "
            f"Encryption : {enc_name}  |  "
            f"Reserved : [{metadata['reserved1']}, {metadata['reserved2']}, {metadata['reserved3']}]"
        )
        self.decode_meta.config(state=tk.NORMAL)
        self.decode_meta.delete("1.0", tk.END)
        self.decode_meta.insert(tk.END, meta_str)
        self.decode_meta.config(state=tk.DISABLED)

    # -- Accuracy tab --
    def _build_accuracy_tab(self):
        self._make_label(self.accuracy_tab, "Original message:")
        self.acc_original = self._make_text(self.accuracy_tab, height=8)
        self.acc_original.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._make_label(self.accuracy_tab, "Decoded message:")
        self.acc_decoded = self._make_text(self.accuracy_tab, height=8)
        self.acc_decoded.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        btn_frame = ttk.Frame(self.accuracy_tab)
        btn_frame.pack(fill="x", padx=8)
        self._make_button(btn_frame, "Check Accuracy", self._on_accuracy)

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
