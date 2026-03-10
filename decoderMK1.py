# filepath: c:\Users\2001747\OneDrive - Northshore School District\Desktop\en-de-coder\decoderMK1.py
import pygame
import sys

# Settings (must match encoder)
PIXEL_SIZE = 20
BITS_PER_CHAR = 8
MAX_ROWS = 500
SEPARATOR_WIDTH = 2

# Color thresholds
def classify_pixel(r, g, b):
    """Classify a pixel as '1' (white), '0' (black), or 'space' (red)."""
    if r > 200 and g < 80 and b < 80:
        return 'red'
    elif r > 180 and g > 180 and b > 180:
        return '1'
    else:
        return '0'

def decode_image(image_path):
    pygame.init()
    surface = pygame.image.load(image_path)
    width, height = surface.get_size()

    col_pixel_width = BITS_PER_CHAR * PIXEL_SIZE
    num_columns = round((width + SEPARATOR_WIDTH) / (col_pixel_width + SEPARATOR_WIDTH))
    num_rows = height // PIXEL_SIZE

    decoded_message = ""

    for col_index in range(num_columns):
        x_offset = col_index * (col_pixel_width + SEPARATOR_WIDTH)

        for row_index in range(num_rows):
            y = row_index * PIXEL_SIZE
            sample_y = y + PIXEL_SIZE // 2

            if sample_y >= height:
                break

            # Read the 8 bits of this character
            bits = []
            is_space = False
            for bit_col in range(BITS_PER_CHAR):
                sample_x = x_offset + bit_col * PIXEL_SIZE + PIXEL_SIZE // 2
                if sample_x >= width:
                    break
                r, g, b, *_ = surface.get_at((sample_x, sample_y))
                classification = classify_pixel(r, g, b)
                if classification == 'red':
                    is_space = True
                    break
                bits.append(classification)

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

if __name__ == "__main__":
    image_path = input("Enter image path to decode (default: encoded_message.png): ").strip()
    if not image_path:
        image_path = "encoded_message.png"

    decoded = decode_image(image_path)
    print(f"\nDecoded message:\n{decoded}")
