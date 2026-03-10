
import pygame
import sys

# Settings (must match encoder)
PIXEL_SIZE = 1
BITS_PER_CHAR = 8
SEPARATOR_WIDTH = 2


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
    # Use FULL image height as max_rows (matches encoder behavior with cover images)
    num_rows = height // PIXEL_SIZE
    num_columns = (width + SEPARATOR_WIDTH) // (col_pixel_width + SEPARATOR_WIDTH)

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

            # Check for end-of-message marker at first pixel
            first_x = x_offset
            if first_x < width and y < height:
                r, g, b, *_ = surface.get_at((first_x, y))
                if classify_pixel(r, g, b) == 'end':
                    done = True
                    break

            # Read the 8 bits of this character
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


if __name__ == "__main__":
    image_path = input("Enter image path to decode (default: encoded_message.png): ").strip()
    if not image_path:
        image_path = "encoded_message.png"

    decoded = decode_image(image_path)
    print(f"\nDecoded message:\n{decoded}")

