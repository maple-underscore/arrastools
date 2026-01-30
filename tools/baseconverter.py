#convert bases

def convert_base(number: str, from_base: int, to_base: int) -> str:
    """Convert a number from one base to another.

    Args:
        number (str): The number to convert, as a string.
        from_base (int): The base of the input number (2-36).
        to_base (int): The base to convert the number to (2-36).
    Returns:
        str: The converted number as a string.
    """
    if not (2 <= from_base <= 36) or not (2 <= to_base <= 36):
        raise ValueError("Bases must be in the range 2-36.")

    # Convert number to base 10
    base10_number = int(number, from_base)

    # Convert base 10 number to target base
    if to_base == 10:
        return str(base10_number)

    digits = []
    while base10_number > 0:
        remainder = base10_number % to_base
        if remainder < 10:
            digits.append(str(remainder))
        else:
            digits.append(chr(remainder - 10 + ord('A')))
        base10_number //= to_base

    digits.reverse()
    return ''.join(digits) if digits else '0'

print(convert_base("SHITYOURSELF", 36, 10))