import sys

store = {}
versions = {}        # key -> int (incremented on every write)
watched = {}         # key -> snapshot version captured at WATCH time
in_multi = False
queue = []

def es(s): return f"+{s}\r\n"
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

def bump(key):
    versions[key] = versions.get(key, 0) + 1

def run_write(args):
    """Apply a write command (used both during normal ops and during EXEC)."""
    cmd = args[0].upper()
    if cmd == "SET":
        store[args[1]] = args[2]; bump(args[1])
        return es("OK")
    if cmd == "INCR":
        v = int(store.get(args[1], "0")) + 1
        store[args[1]] = str(v); bump(args[1])
        return ei(v)
    if cmd == "DEL":
        deleted = 0
        for k in args[1:]:
            if k in store:
                del store[k]; bump(k); deleted += 1
        return ei(deleted)
    return ee(f"ERR unknown command '{cmd}'")

def handle(args):
    global in_multi, queue, watched
    cmd = args[0].upper()
    if cmd == "WATCH":
        if in_multi:
            return ee("ERR WATCH inside MULTI is not allowed")
        for k in args[1:]:
            watched[k] = versions.get(k, 0)
        return es("OK")
    elif cmd == "UNWATCH":
        watched = {}
        return es("OK")
    elif cmd == "MULTI":
        in_multi = True; queue = []
        return es("OK")
    elif cmd == "EXEC":
        if not in_multi:
            return ee("ERR EXEC without MULTI")
        for k, snap in watched.items():
            if versions.get(k, 0) != snap:
                in_multi = False; queue = []; watched = {}
                return "$-1\r\n"
        results = "".join(run_write(cmd) for cmd in queue)
        n = len(queue)
        in_multi = False; queue = []; watched = {}
        return f"*{n}\r\n{results}"

    elif cmd == "DISCARD":
        in_multi = False; queue = []; watched = {}
        return es("OK")
    elif cmd == "GET":
        return eb(store.get(args[1]))
    else:
        if in_multi:
            queue.append(args)
            return es("QUEUED")
        return run_write(args)

def parse(line):
    a, c, q = [], "", False
    for ch in line:
        if ch == '"': q = not q
        elif ch == ' ' and not q:
            if c: a.append(c); c = ""
        else: c += ch
    if c: a.append(c)
    return a

for line in sys.stdin:
    line = line.strip()
    if not line: continue
    sys.stdout.write(handle(parse(line)))
    sys.stdout.flush()
