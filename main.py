import sys, re

store = {}

def es(s): return f"+{s}\r\n"
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

def call(cmd, *args):
    cmd = cmd.upper()
    if cmd == "GET":
        return store.get(args[0])           # None or str
    if cmd == "SET":
        store[args[0]] = args[1]
        return "OK"                         # mapped to simple string
    if cmd == "INCR":
        v = int(store.get(args[0], "0")) + 1
        store[args[0]] = str(v)
        return v                             # mapped to integer
    return None

def eval_script(script, keys, argv):
    """Pattern-match supported script forms; return a RESP-encoded result string."""
    s = script.strip()

    # return redis.call('GET', KEYS[N])
    m = re.match(r"^return redis\.call\('GET',\s*KEYS\[(\d+)\]\)$", s)
    if m:
        v = call('GET', keys[int(m.group(1)) - 1])
        return eb(v)

    # return redis.call('SET', KEYS[N], ARGV[M])
    m = re.match(r"^return redis\.call\('SET',\s*KEYS\[(\d+)\],\s*ARGV\[(\d+)\]\)$", s)
    if m:
        r = call('SET', keys[int(m.group(1)) - 1], argv[int(m.group(2)) - 1])
        return es(r)

    # return redis.call('INCR', KEYS[N])
    m = re.match(r"^return redis\.call\('INCR',\s*KEYS\[(\d+)\]\)$", s)
    if m:
        v = call('INCR', keys[int(m.group(1)) - 1])
        return ei(v)

    # return tonumber(redis.call('GET', KEYS[N])) or 0
    m = re.match(r"^return tonumber\(redis\.call\('GET',\s*KEYS\[(\d+)\]\)\)\s+or\s+0$", s)
    if m:
        v = call('GET', keys[int(m.group(1)) - 1])
        return ei(int(v) if v else 0)

    # return #KEYS
    if re.match(r"^return #KEYS$", s):
        return ei(len(keys))

    # return ARGV[N]
    m = re.match(r"^return ARGV\[(\d+)\]$", s)
    if m:
        return eb(argv[int(m.group(1)) - 1])

    # return 'literal'
    m = re.match(r"^return '([^']*)'$", s)
    if m:
        return es(m.group(1))

    return ee("ERR unsupported script form")

def handle(args):
    cmd = args[0].upper()
    if cmd == "SET":  store[args[1]] = args[2]; return es("OK")
    if cmd == "GET":  return eb(store.get(args[1]))
    if cmd == "EVAL":
        # EVAL <script> <numkeys> <key1>...<keyN> <arg1>...<argM>
        script = args[1]
        numkeys = int(args[2])
        keys = args[3:3+numkeys]
        argv = args[3+numkeys:]
        return eval_script(script, keys, argv)
    return ee(f"ERR unknown command '{cmd}'")

def parse(line):
    # Quote-aware parser (script body comes in quotes)
    a, c, q = [], "", False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"' and not q:
            q = True
        elif ch == '"' and q:
            q = False
        elif ch == ' ' and not q:
            if c: a.append(c); c = ""
        else: c += ch
        i += 1
    if c: a.append(c)
    return a

for line in sys.stdin:
    line = line.rstrip("\r\n")
    if not line: continue
    sys.stdout.write(handle(parse(line)))
    sys.stdout.flush()
