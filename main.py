import sys
store = {}
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def es(s): return f"+{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

def parse_value(key):
    value = 0
    if key in store:
        value_str = store[key]
        try:
            value = int(value_str)
        except (ValueError, TypeError):
            return None
    return value

def handle(args):
    cmd = args[0].upper()
    if cmd == "PING": return es("PONG") if len(args)==1 else eb(args[1])
    elif cmd == "ECHO": return eb(args[1])
    elif cmd == "SET":
        key, val = args[1], args[2]
        flags = [a.upper() for a in args[3:]]
        if "NX" in flags and key in store: return "$-1\r\n"
        if "XX" in flags and key not in store: return "$-1\r\n"
        store[key] = val; return es("OK")
    elif cmd == "GET": return eb(store.get(args[1]))
    elif cmd == "DBSIZE": return ei(len(store))
    elif cmd == "INCR":
        # Get current value (default "0"), parse as int, add 1, store, return new value
        value = parse_value(args[1])
        if value is None:
            return ee("ERR value is not an integer or out of range")
        value += 1
        store[args[1]] = value
        return ei(value)
    elif cmd == "DECR":
        # Same as INCR but subtract 1
        value = parse_value(args[1])
        if value is None:
            return ee("ERR value is not an integer or out of range")
        value -= 1
        store[args[1]] = value
        return ei(value)
    elif cmd == "INCRBY":
        # Increment by args[2]
        value = parse_value(args[1])
        if value is None:
            return ee("ERR value is not an integer or out of range")
        value += int(args[2])
        store[args[1]] = value
        return ei(value)
    elif cmd == "DECRBY":
        # Decrement by args[2]
        value = parse_value(args[1])
        if value is None:
            return ee("ERR value is not an integer or out of range")
        value -= int(args[2])
        store[args[1]] = value
        return ei(value)
    return ee(f"ERR unknown command '{cmd}'")

def pa(line):
    a, c, q = [], "", False
    for ch in line:
        if ch=='"': q=not q
        elif ch==' ' and not q:
            if c: a.append(c); c=""
        else: c+=ch
    if c: a.append(c)
    return a
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    sys.stdout.write(handle(pa(line))); sys.stdout.flush()
