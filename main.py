import sys
store = {}
access_times = {}  # key -> last access clock time
clock = 0
maxkeys = 0  # 0 = unlimited

def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def es(s): return f"+{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

def touch(key):
    """Update access time for a key."""
    access_times[key] = clock

def evict_if_needed():
    """If maxkeys is set and we're at capacity, evict LRU key."""
    if maxkeys <= 0 or len(store) < maxkeys:
        return
    lru_key = min(access_times, key=access_times.get)
    del store[lru_key]
    del access_times[lru_key]

def handle(args):
    global clock, maxkeys
    cmd = args[0].upper()
    if cmd == "WAIT": clock += int(args[1]); return es("OK")
    elif cmd == "MAXKEYS": maxkeys = int(args[1]); return es("OK")
    elif cmd == "SET":
        key = args[1]
        if key not in store:
            evict_if_needed()
        store[key] = args[2]; touch(key); return es("OK")
    elif cmd == "GET":
        if args[1] in store:
            touch(args[1])
        return eb(store.get(args[1]))
    elif cmd == "DBSIZE": return ei(len(store))
    elif cmd == "INFO":
        if len(args) > 1 and args[1].lower() == "memory":
            info = f"keys:{len(store)},maxkeys:{maxkeys}"
            return eb(info)
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
