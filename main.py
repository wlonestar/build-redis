import sys
store, expiry, clock = {}, {}, 0
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def es(s): return f"+{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"
def check_expiry(key):
    if key in expiry and clock >= expiry[key]:
        store.pop(key, None); expiry.pop(key, None)

def handle(args):
    global clock
    cmd = args[0].upper()
    if cmd == "WAIT": clock += int(args[1]); return es("OK")
    elif cmd == "SET":
        key, val = args[1], args[2]
        # Parse optional flags: EX <secs>, PX <ms>, NX, XX
        ex_secs, px_ms, nx, xx = None, None, False, False
        i = 3
        while i < len(args):
            flag = args[i].upper()
            if flag == "EX" and i + 1 < len(args):
                ex_secs = int(args[i+1]); i += 2
            elif flag == "PX" and i + 1 < len(args):
                px_ms = int(args[i+1]); i += 2
            elif flag == "NX":
                nx = True; i += 1
            elif flag == "XX":
                xx = True; i += 1
            else:
                i += 1
        # Handle NX/XX flags
        if nx and key in store:
            return eb(None)
        if xx and key not in store:
            return eb(None)
        store[key] = val
        # Set expiry if EX or PX provided
        if ex_secs is not None:
            expiry[key] = clock + ex_secs * 1000
        elif px_ms is not None:
            expiry[key] = clock + px_ms
        return es("OK")
    elif cmd == "GET":
        check_expiry(args[1]); return eb(store.get(args[1]))
    elif cmd == "TTL":
        check_expiry(args[1])
        if args[1] not in store: return ei(-2)
        if args[1] not in expiry: return ei(-1)
        return ei((expiry[args[1]] - clock) // 1000)
    elif cmd == "PTTL":
        check_expiry(args[1])
        if args[1] not in store: return ei(-2)
        if args[1] not in expiry: return ei(-1)
        return ei(expiry[args[1]] - clock)
    elif cmd == "EXPIRE":
        if args[1] not in store: return ei(0)
        expiry[args[1]] = clock + int(args[2]) * 1000; return ei(1)
    elif cmd == "PERSIST":
        if args[1] in expiry: del expiry[args[1]]; return ei(1)
        return ei(0)
    elif cmd == "PING": return es("PONG") if len(args)==1 else eb(args[1])
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
