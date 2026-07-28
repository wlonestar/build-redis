import sys

def encode_bulk_string(s: str | None) -> str:
    if s is None:
        return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"

def encode_simle_string(s: str) -> str:
    return f"+{s}\r\n"

def encode_error(msg: str) -> str:
    return f"-{msg}\r\n"

def encode_integer(n: int) -> str:
    return f":{n}\r\n"

def handle_command(args):
    """Process a Redis command and return the RESP response."""
    cmd = args[0].upper()

    if cmd == "PING":
        if len(args) == 1:
            return encode_simle_string("PONG")
        return encode_bulk_string(args[1])
    elif cmd == "ECHO":
        return encode_bulk_string(args[1])
    elif cmd == "COMMAND":
        return encode_simle_string("OK")
    return encode_error(f"ERR unknown command '{cmd}'")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        args = parse_args(line)
        response = handle_command(args)
        sys.stdout.write(response)
        sys.stdout.flush()

def parse_args(line):
    """Split a command line into arguments, handling quoted strings."""
    args, current, in_quotes= [], "", False
    for ch in line:
        if ch == '"' and not in_quotes:
            in_quotes = True
        elif ch == '"' and in_quotes:
            in_quotes = False
        elif ch == ' ' and not in_quotes:
            if current:
                args.append(current)
                current = ""
        else:
            current += ch
    if current:
        args.append(current)
    return args

if __name__ == "__main__":
    main()
