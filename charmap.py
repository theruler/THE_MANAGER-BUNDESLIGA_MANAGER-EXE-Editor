class CharmapEncodeError(ValueError):
    """Raised when display text cannot be represented without data loss."""


def _validated_inverse(charmap: dict) -> dict[str, int]:
    inverse = {}
    for raw_key, display_char in charmap.items():
        try:
            raw = bytes.fromhex(raw_key)
        except (TypeError, ValueError) as exc:
            raise CharmapEncodeError(f"Invalid CharMap byte key: {raw_key!r}") from exc
        if len(raw) != 1:
            raise CharmapEncodeError(f"CharMap key must identify one byte: {raw_key!r}")
        if not isinstance(display_char, str) or len(display_char) != 1:
            raise CharmapEncodeError(f"CharMap value must be one character: {display_char!r}")
        if display_char in inverse and inverse[display_char] != raw[0]:
            raise CharmapEncodeError(f"Ambiguous CharMap character: {display_char!r}")
        inverse[display_char] = raw[0]
    return inverse


def charmap_decode(raw_bytes: bytes, charmap: dict) -> str:
    out = []
    for byte_value in raw_bytes:
        key = format(byte_value, "02x")
        out.append(charmap[key] if key in charmap else chr(byte_value))
    return "".join(out)


def charmap_encode(text: str, charmap: dict, *, allowed_bytes=None, preserve_bytes=()) -> bytes:
    """Encode display text without replacement or invented glyph mappings.

    ``allowed_bytes`` is the active font's glyph-code set. Bytes outside that
    set are accepted only when they already occur in the source entry via
    ``preserve_bytes``. This keeps unknown legacy/control bytes byte-exact while
    rejecting newly introduced, unconfirmed characters.
    """
    inverse = _validated_inverse(charmap)
    allowed = None if allowed_bytes is None else set(allowed_bytes)
    preserved = {}
    for byte_value in preserve_bytes:
        preserved[byte_value] = preserved.get(byte_value, 0) + 1
    out = bytearray()

    def accept_byte(byte_value: int, char: str, index: int):
        if allowed is not None and byte_value not in allowed:
            if preserved.get(byte_value, 0) <= 0:
                raise CharmapEncodeError(
                    f"Byte 0x{byte_value:02X} for {char!r} is outside the active font"
                )
            preserved[byte_value] -= 1
        out.append(byte_value)

    for index, char in enumerate(text):
        if char in inverse:
            accept_byte(inverse[char], char, index)
            continue

        codepoint = ord(char)
        if codepoint > 0xFF:
            raise CharmapEncodeError(
                f"Character U+{codepoint:04X} at position {index} has no CharMap entry"
            )

        key = format(codepoint, "02x")
        if key in charmap and charmap[key] != char:
            raise CharmapEncodeError(
                f"Character {char!r} at position {index} conflicts with glyph {charmap[key]!r}"
            )
        accept_byte(codepoint, char, index)

    return bytes(out)


__all__ = ['CharmapEncodeError', 'charmap_decode', 'charmap_encode']
