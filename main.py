import sys

store = {}

def encode_bulk(s: str | None) -> bytes:
    if s is None:
        return b"$-1\r\n"
    b = s.encode() if isinstance(s, str) else s
    return b"$" + str(len(s)).encode() +  b"\r\n" + b + b"\r\n"

def encode_simle(s: str) -> bytes:
    return b"+" + s.encode() +  b"\r\n"

def encode_error(msg: str) -> bytes:
    return b"-" + msg.encode() + b"\r\n"

def encode_integer(n: int) -> str:
    return f":{n}\r\n"

def handle_command(args):
    """Process a Redis command and return the RESP response."""
    cmd = args[0].upper()

    if cmd == "PING":
        if len(args) == 1:
            return encode_simle("PONG")
        elif len(args) == 2:
            return encode_bulk(args[1])
        return encode_error(f"ERR wrong number of arguments for '{cmd}' command")
    elif cmd == "ECHO":
        if len(args) == 2:
            return encode_bulk(args[1])
        return encode_error(f"ERR wrong number of arguments for '{cmd}' command")
    elif cmd == "SET":
        store[args[1]] = args[2]
        return encode_simle("OK")
    elif cmd == "GET":
        return encode_bulk(store.get(args[1]))
    return encode_error(f"ERR unknown command '{cmd}'")

def read_line(buf):
    """Read up to and including \r\n. Return (line_bytes_without_crlf, rest)."""
    idx = buf.find(b"\r\n")
    if idx < 0:
        return None, buf
    return buf[:idx], buf[idx+2:]

def parse_request(buf):
    """Parse one RESP array request from buf. Return (args_list, rest_buf) or (None, buf)."""
    # 1. Read the first line — must start with `*`
    line, buf = read_line(buf)
    if line is None:
        return None, buf
    if line[0] != ord('*'):
        return None, buf
    # 2. Parse N (the array length) from the rest of the line
    N = int(line[1:])
    # 3. Loop N times, each time reading a bulk string:
    #  - read a line starting with `$<len>`
    #  - read exactly <len> bytes, then a trailing \r\n
    args_list = []
    for _ in range(N):
        line, buf = read_line(buf)
        if line is None:
            return None, buf
        len_ = int(line[1:])
        s = buf[:len_]
        buf = buf[len_ + 2:]
        args_list.append(s.decode())
    # 4. Return (args, rest_of_buf)
    # Hint: be careful — bulk-string bodies can contain CRLF, so do NOT split on \r\n inside the body.
    return args_list, buf

def main():
    buf = sys.stdin.buffer.read()
    while buf:
        args, buf = parse_request(buf)
        if args is None:
            break
        sys.stdout.buffer.write(handle_command(args))
    sys.stdout.buffer.flush()

if __name__ == "__main__":
    main()
