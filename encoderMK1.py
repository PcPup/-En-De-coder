# filepath: c:\Users\2001747\OneDrive - Northshore School District\Desktop\en-de-coder\encoderMK1.py
import pygame
import sys
import math

message = input("Enter a message to encode: ")
cover_path = input("Enter path to cover image (or press Enter to skip): ").strip()

binary_list = [' ' if char == ' ' else format(ord(char), '08b') for char in message]

# ── Settings ──
PIXEL_SIZE = 1
BITS_PER_CHAR = 8
DEFAULT_MAX_ROWS = 500
SEPARATOR_WIDTH = 2

total_chars = len(binary_list)
col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE

pygame.init()

# ── Load cover image or create blank ──
if cover_path:
    cover = pygame.image.load(cover_path)
    cover_w, cover_h = cover.get_size()

    # Use the FULL height of the cover image
    max_rows = cover_h // PIXEL_SIZE
    max_data_cols = (cover_w + SEPARATOR_WIDTH) // (col_pixel_width + SEPARATOR_WIDTH)
    max_capacity = max_rows * max_data_cols

    if total_chars > max_capacity:
        print(f"ERROR: Message too long! {total_chars} chars but cover can hold {max_capacity}.")
        pygame.quit()
        sys.exit(1)

    num_columns = math.ceil(total_chars / max_rows)
    rows = min(total_chars, max_rows)

    # Keep exact cover image size
    surface = pygame.Surface((cover_w, cover_h))
    surface.blit(cover, (0, 0))

    # Clear lowest 2 bits of ENTIRE image
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

# ── Embed the binary data ──
for i, item in enumerate(binary_list):
    col_index = i // max_rows
    row_index = i % max_rows
    x_offset = col_index * (col_pixel_width + SEPARATOR_WIDTH)

    # Draw separator column pixels
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

# ── End-of-message marker ──
end_i = total_chars
end_col = end_i // max_rows
end_row = end_i % max_rows
end_x = end_col * (col_pixel_width + SEPARATOR_WIDTH)
end_y = end_row * PIXEL_SIZE
if end_x < surface.get_width() and end_y < surface.get_height():
    r, g, b, *_ = surface.get_at((end_x, end_y))
    surface.set_at((end_x, end_y), (r & ~3, g & ~3, (b & ~3) | 3))

pygame.display.set_mode((surface.get_width(), surface.get_height()))
screen = pygame.display.get_surface()
screen.blit(surface, (0, 0))
pygame.display.set_caption("Binary Encoder - Steganographic")
pygame.display.flip()

pygame.image.save(surface, "encoded_message.png")
print(f"Image saved as encoded_message.png")
print(f"Layout: {num_columns} column(s), {max_rows} max rows, {total_chars} chars encoded")
if cover_path:
    print("Message hidden inside cover image!")

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()