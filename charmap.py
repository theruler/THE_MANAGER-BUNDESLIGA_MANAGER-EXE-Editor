def charmap_decode(raw_bytes: bytes, charmap: dict) -> str:
    out = []
    for b in raw_bytes:
        key = format(b, "02x")
        out.append(charmap[key] if key in charmap else chr(b))
    return "".join(out)


def charmap_encode(text: str, charmap: dict) -> bytes:
    inv = {v: bytes.fromhex(k) for k, v in charmap.items()}
    out, i = bytearray(), 0
    while i < len(text):
        ch = text[i]
        if ch in inv:
            out += inv[ch]
        else:
            try:
                out.append(ord(ch))
            except Exception:
                out.append(0x3F)
        i += 1
    return bytes(out)


__all__ = ['charmap_decode', 'charmap_encode']
