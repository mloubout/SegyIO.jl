import struct

# Conversion between 32-bit IBM float and IEEE float

def ibm_to_ieee(value):
    """Convert a 4-byte IBM floating point number to Python float."""
    if isinstance(value, (bytes, bytearray)):
        if len(value) != 4:
            raise ValueError("IBM float must be 4 bytes")
        val = int.from_bytes(value, byteorder='big', signed=False)
    else:
        val = value & 0xffffffff
    if val == 0:
        return 0.0
    sign = 1 if (val >> 31) == 0 else -1
    exponent = (val >> 24) & 0x7f
    fraction = val & 0x00ffffff
    # IBM exponent is base 16 biased by 64
    mant = fraction / float(0x01000000)
    return sign * mant * 16 ** (exponent - 64)

def ieee_to_ibm(f):
    """Convert Python float to IBM 32 bit float encoded as bytes."""
    if f == 0.0:
        return b"\x00\x00\x00\x00"
    sign = 0
    if f < 0:
        sign = 0x80
        f = -f
    exponent = 64
    while f < 1.0:
        f *= 16.0
        exponent -= 1
    while f >= 16.0:
        f /= 16.0
        exponent += 1
    fraction = int(f * 0x01000000) & 0x00ffffff
    val = (sign << 24) | (exponent << 24) | fraction
    return val.to_bytes(4, byteorder='big')
