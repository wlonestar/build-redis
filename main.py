import sys

store = {}

def encode_bulk_string(s):
    if s is None:
        return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"

def encode_simple_string(s):
    return f"+{s}\r\n"

def encode_error(msg):
    return f"-{msg}\r\n"

def encode_integer(n):
    return f":{n}\r\n"

def handle_command(args):
    cmd = args[0].upper()

    if cmd == "PING":
        if len(args) == 1:
            return encode_simple_string("PONG")
        return encode_bulk_string(args[1])

    elif cmd == "ECHO":
        return encode_bulk_string(args[1])

    elif cmd == "SET":
        # Store args[1] = args[2] in the store dict
        store[args[1]] = args[2]
        # Return +OK
        return encode_simple_string("OK")

    elif cmd == "GET":
        # Look up args[1] in store
        val = store[args[1]] if args[1] in store else None
        # Return bulk string or $-1 for missing
        return encode_bulk_string(val)

    return encode_error(f"ERR unknown command '{cmd}'")

def parse_args(line):
    args = []
    current = ""
    in_quotes = False
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

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        args = parse_args(line)
        response = handle_command(args)
        sys.stdout.write(response)
        sys.stdout.flush()

if __name__ == "__main__":
    main()
