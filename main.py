import sys
store, expiry, clock = {}, {}, 0
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def es(s): return f"+{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"
def check_expiry(key):
    """ Check if key is expired. If so, delete from store and expiry dicts."""
    if expiry[key] < clock:
        store.pop(key)
        expiry.pop(key)

def handle(args):
    global clock
    cmd = args[0].upper()
    if cmd == "WAIT": clock += int(args[1]); return es("OK")
    elif cmd == "SET":
        key, val = args[1], args[2]
        ex_ms = None
        i = 3
        while i < len(args):
            f = args[i].upper()
            if f == "EX": ex_ms = int(args[i+1]) * 1000; i += 2
            elif f == "PX": ex_ms = int(args[i+1]); i += 2
            else: i += 1
        store[key] = val
        if ex_ms is not None: expiry[key] = clock + ex_ms
        return es("OK")
    elif cmd == "GET":
        # Call check_expiry before accessing
        check_expiry(args[1])
        return eb(store.get(args[1]))
    elif cmd == "EXISTS":
        # Check expiry for each key, count existing ones
        cnt = len(store)
        for key in store:
            if expiry[key] < clock:
                cnt -= 1
        return ei(cnt)
    elif cmd == "TTL":
        check_expiry(args[1])
        if args[1] not in store: return ei(-2)
        if args[1] not in expiry: return ei(-1)
        return ei(max(0, (expiry[args[1]] - clock) // 1000))
    elif cmd == "DBSIZE":
        # Count only non-expired keys
        cnt = 0
        for key in store:
            if expiry[key] < clock:
                cnt += 1
        return ei(cnt)
    elif cmd == "EXPIRE":
        check_expiry(args[1])
        if args[1] not in store: return ei(0)
        expiry[args[1]] = clock + int(args[2]) * 1000; return ei(1)
    elif cmd == "PING": return es("PONG") if len(args)==1 else eb(args[1])
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
