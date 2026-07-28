import sys
store = {}
expiry = {}  # key -> absolute ms timestamp
clock = 0    # simulated clock in ms

def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def es(s): return f"+{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

def check_expiry(key):
    if key in expiry and clock >= expiry[key]:
        del store[key]
        del expiry[key]

def handle(args):
    global clock
    cmd = args[0].upper()
    if cmd == "WAIT":
        clock += int(args[1]); return es("OK")
    if cmd == "SET":
        store[args[1]] = args[2]; return es("OK")
    elif cmd == "GET":
        check_expiry(args[1])
        return eb(store.get(args[1]))
    elif cmd == "EXPIRE":
        # Set expiry[args[1]] = clock + int(args[2]) * 1000
        expiry[args[1]] = clock + int(args[2]) * 1000
        # Return :1 if key exists, :0 if not
        return ei(1 if args[1] in store else 0)
    elif cmd == "TTL":
        # Return :-2 if key missing, :-1 if no expiry, else remaining seconds
        val: int = 0
        if args[1] not in store:
            val = -2
        else:
            if args[1] not in expiry:
                val = -1
            else:
                val = int(int(expiry[args[1]]) / 1000)
        return ei(val)
    elif cmd == "PERSIST":
        # Remove expiry, return :1 if had expiry, :0 if not
        if args[1] in expiry:
            expiry.pop(args[1])
            return ei(1)
        return ei(0)
    elif cmd == "PING": return es("PONG") if len(args)==1 else eb(args[1])
    elif cmd == "DBSIZE":
        # TODO: Count only non-expired keys
        pass
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
