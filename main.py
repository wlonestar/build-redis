import sys

store = {}
backlog = []          # list of raw command strings, in order
role = "master"       # "master" or "replica"
REPLID = "abc0000000000000000000000000000000000000"

def es(s): return f"+{s}\r\n"
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"

WRITE_CMDS = {"SET", "DEL", "LPUSH", "RPUSH", "HSET", "SADD", "ZADD", "EXPIRE", "INCR", "DECR"}

def log_write(line):
    backlog.append(line)

def handle(line, args):
    global role
    cmd = args[0].upper()
    if cmd == "ROLE":
        return eb(role)
    if cmd == "REPLICAOF":
        # REPLICAOF NO ONE -> master; REPLICAOF host port -> replica
        if args[1].upper() == "NO" and args[2].upper() == "ONE":
            role = "master"
        else:
            role = "replica"
        return es("OK")
    if cmd == "REPLICATION_LOG":
        result = ""
        for entry in backlog:
            result += eb(entry)
        result += es("OK")
        return result
    if cmd == "PSYNC":
        # PSYNC ? -1  -> full resync
        # PSYNC <replid> <offset>  -> partial if known, else full
        if args[1] == "?" or args[1] != REPLID:
            # full resync: snapshot + log
            snapshot = ""
            for k, v in store.items():
                snapshot += f"SET {k} {v}\n"
            log_content = ""
            for entry in backlog:
                log_content += entry + "\n"
            bulk_data = snapshot + log_content
            return f"+FULLRESYNC {REPLID} 0\r\n" + eb(bulk_data)
        else:
            # partial sync: backlog from offset
            offset = int(args[2])
            log_content = ""
            for entry in backlog[offset:]:
                log_content += entry + "\n"
            return "+CONTINUE\r\n" + eb(log_content)
    if cmd == "SET":
        store[args[1]] = args[2]; log_write(line); return es("OK")
    if cmd == "DEL":
        c = 0
        for k in args[1:]:
            if k in store: del store[k]; c += 1
        log_write(line); return ei(c)
    if cmd == "GET":
        return eb(store.get(args[1]))
    if cmd in WRITE_CMDS:
        log_write(line)
        return es("OK")
    return ee(f"ERR unknown command '{cmd}'")

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
    line = line.rstrip("\r\n")
    if not line: continue
    args = parse(line)
    sys.stdout.write(handle(line, args))
    sys.stdout.flush()
