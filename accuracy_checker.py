
def check_accuracy(original, decoded):
    """Compare original and decoded messages and report accuracy."""
    total_chars = max(len(original), len(decoded))

    if total_chars == 0:
        print("Both messages are empty.")
        return

    # Character-by-character comparison
    correct = 0
    errors = []
    for i in range(total_chars):
        orig_char = original[i] if i < len(original) else None
        dec_char = decoded[i] if i < len(decoded) else None

        if orig_char == dec_char:
            correct += 1
        else:
            errors.append({
                'position': i,
                'expected': repr(orig_char) if orig_char is not None else '<missing>',
                'got': repr(dec_char) if dec_char is not None else '<missing>'
            })

    accuracy = (correct / total_chars) * 100

    # Print results
    print("=" * 50)
    print("        ACCURACY REPORT")
    print("=" * 50)
    print(f"Original length : {len(original)} characters")
    print(f"Decoded length  : {len(decoded)} characters")
    print(f"Matching chars  : {correct}/{total_chars}")
    print(f"Accuracy        : {accuracy:.2f}%")
    print("=" * 50)

    if errors:
        print(f"\n{len(errors)} error(s) found:")
        print("-" * 50)
        for err in errors[:20]:  # Show first 20 errors
            print(f"  Position {err['position']}: expected {err['expected']}, got {err['got']}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
    else:
        print("\n✓ PERFECT MATCH! No errors found.")

    return accuracy

if __name__ == "__main__":
    print("=== Accuracy Checker ===\n")
    original = input("Enter the original message: ")
    decoded = input("Enter the decoded message:  ")
    check_accuracy(original, decoded)
