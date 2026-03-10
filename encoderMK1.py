# filepath: c:\Users\2001747\OneDrive - Northshore School District\Desktop\en-de-coder\encoderMK1.py
import pygame
import sys
import math

message = input("Enter a message to encode: ")

binary_list = [' ' if char == ' ' else format(ord(char), '08b') for char in message]

# Colors
BLACK = (0, 0, 0)       # 0
WHITE = (255, 255, 255)  # 1
RED = (255, 0, 0)        # space
GRAY = (50, 50, 50)      # column separator

PIXEL_SIZE = 20
BITS_PER_CHAR = 8
MAX_ROWS = 500  # max characters vertically before starting a new column
SEPARATOR_WIDTH = 2  # pixel gap between columns

# Calculate grid layout
total_chars = len(binary_list)
num_columns = math.ceil(total_chars / MAX_ROWS)
rows = min(total_chars, MAX_ROWS)

# Calculate window size
col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE
total_width = num_columns * col_pixel_width + (num_columns - 1) * SEPARATOR_WIDTH
total_height = rows * PIXEL_SIZE

# Set up pygame
pygame.init()
screen = pygame.display.set_mode((total_width, total_height))
pygame.display.set_caption("Binary Encoder")
screen.fill(GRAY)

# Draw the binary image
for i, item in enumerate(binary_list):
    col_index = i // MAX_ROWS  # which column
    row_index = i % MAX_ROWS   # which row within the column
    x_offset = col_index * (col_pixel_width + SEPARATOR_WIDTH)
    y = row_index * PIXEL_SIZE

    if item == ' ':
        for bit_col in range(BITS_PER_CHAR):
            x = x_offset + bit_col * PIXEL_SIZE
            pygame.draw.rect(screen, RED, (x, y, PIXEL_SIZE, PIXEL_SIZE))
    else:
        for bit_col, bit in enumerate(item):
            x = x_offset + bit_col * PIXEL_SIZE
            color = WHITE if bit == '1' else BLACK
            pygame.draw.rect(screen, color, (x, y, PIXEL_SIZE, PIXEL_SIZE))

pygame.display.flip()

# Save the image
pygame.image.save(screen, "encoded_message.png")
print(f"Image saved as encoded_message.png")
print(f"Layout: {num_columns} column(s), up to {MAX_ROWS} rows each")

# Keep window open until closed
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
