import sys
store = {}
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def es(s): return f"+{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

def handle(args):
    cmd = args[0].upper()
    if cmd == "PING": return es("PONG") if len(args)==1 else eb(args[1])
    elif cmd == "ECHO": return eb(args[1])
    elif cmd == "SET":
        key, val = args[1], args[2]
        flags = [a.upper() for a in args[3:]]
        # Check for NX flag - only set if key NOT in store
        if "NX" in flags and key in store:
            return eb(None)
        # Check for XX flag - only set if key IS in store
        if "XX" in flags and key not in store:
            return eb(None)
        # Return $-1\r\n if condition not met
        store[key] = val
        return es("OK")
    elif cmd == "GET": return eb(store.get(args[1]))
    elif cmd == "DBSIZE": return ei(len(store))
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
