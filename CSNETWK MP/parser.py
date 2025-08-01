# parser.py

def build_message(fields: dict) -> str:
    """Build LSNP key-value formatted message."""
    return "\n".join(f"{k}: {v}" for k, v in fields.items()) + "\n\n"

def parse_message(raw: str) -> dict:
    """Parse LSNP key-value message into a dictionary."""
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
    msg = {}
    for line in lines:
        if ": " in line:
            k, v = line.split(": ", 1)
            msg[k.strip()] = v.strip()
    return msg