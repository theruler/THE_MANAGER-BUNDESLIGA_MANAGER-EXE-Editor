from i18n import tr


class CharmapEncodeError(ValueError):
    pass


def _validated_inverse(charmap: dict) -> dict[str, int]:
    inverse = {}
    for raw_key, display_char in charmap.items():
        try:
            raw = bytes.fromhex(raw_key)
        except (TypeError, ValueError) as exc:
            raise CharmapEncodeError(tr("charmap.err.invalid_key", key=raw_key)) from exc
        if len(raw) != 1:
            raise CharmapEncodeError(tr("charmap.err.key_not_one_byte", key=raw_key))
        if not isinstance(display_char, str) or len(display_char) != 1:
            raise CharmapEncodeError(tr("charmap.err.value_not_char", value=display_char))
        if display_char in inverse and inverse[display_char] != raw[0]:
            raise CharmapEncodeError(tr("charmap.err.ambiguous", char=display_char))
        inverse[display_char] = raw[0]
    return inverse


def charmap_decode(raw_bytes: bytes, charmap: dict) -> str:
    out = []
    for byte_value in raw_bytes:
        key = format(byte_value, "02x")
        out.append(charmap[key] if key in charmap else chr(byte_value))
    return "".join(out)


def charmap_encode(text: str, charmap: dict, *, allowed_bytes=None, preserve_bytes=()) -> bytes:
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
                    tr("charmap.err.outside_font", byte=byte_value, char=char)
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
                tr("charmap.err.no_codepoint", cp=codepoint, pos=index)
            )

        key = format(codepoint, "02x")
        if key in charmap and charmap[key] != char:
            raise CharmapEncodeError(
                tr("charmap.err.conflict", char=char, pos=index, glyph=charmap[key])
            )
        accept_byte(codepoint, char, index)

    return bytes(out)


__all__ = ['CharmapEncodeError', 'charmap_decode', 'charmap_encode']
