import sys

streams = {}        # name -> list of (id, [field, value, ...])
counters = {}       # name -> last auto-generated counter

def es(s): return f"+{s}\r\n"
def eb(s):
    if s is None: return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"
def ee(m): return f"-{m}\r\n"
def ei(n): return f":{n}\r\n"
def ea(items):
    return f"*{len(items)}\r\n" + "".join(items)

def cmp_id(a, b):
    """Compare two stream IDs like '5-3'."""
    am, asq = map(int, a.split("-"))
    bm, bsq = map(int, b.split("-"))
    return (am, asq) > (bm, bsq), (am, asq) == (bm, bsq)

def handle(args):
    cmd = args[0].upper()
    if cmd == "XADD":
        name, eid = args[1], args[2]
        fields = args[3:]
        if name not in streams:
            streams[name] = []; counters[name] = 0
        if eid == "*":
            counters[name] += 1
            eid = f"{counters[name]}-0"
        else:
            if streams[name]:
                last_id = streams[name][-1][0]
                gt, eq = cmp_id(eid, last_id)
                if not gt:
                    return ee("ERR The ID specified in XADD is equal or smaller than the target stream top item")
        streams[name].append((eid, fields))
        return eb(eid)
    if cmd == "XLEN":
        return ei(len(streams.get(args[1], [])))
    if cmd == "XRANGE":
        name, start, end = args[1], args[2], args[3]
        entries = streams.get(name, [])
        result = []
        for eid, fields in entries:
            if start != "-":
                gt, eq = cmp_id(eid, start)
                if not (gt or eq):
                    continue
            if end != "+":
                gt, eq = cmp_id(eid, end)
                if gt:
                    break
            result.append(ea([eb(eid), ea([eb(f) for f in fields])]))
        return ea(result)
    if cmd == "XREAD":
        # XREAD COUNT <n> STREAMS <stream> <last_id>
        count = None
        streams_start = None
        for i in range(1, len(args)):
            if args[i].upper() == "COUNT":
                count = int(args[i+1])
            elif args[i].upper() == "STREAMS":
                streams_start = i + 1
                break
        if streams_start is None:
            return ee("ERR syntax error")
        stream_args = args[streams_start:]
        n = len(stream_args) // 2
        stream_names = stream_args[:n]
        last_ids = stream_args[n:]
        result_parts = []
        for sn, lid in zip(stream_names, last_ids):
            entries = streams.get(sn, [])
            filtered = []
            for eid, fields in entries:
                gt, eq = cmp_id(eid, lid)
                if gt:
                    filtered.append((eid, fields))
            if count is not None:
                filtered = filtered[:count]
            if not filtered:
                continue
            entry_list = [ea([eb(eid), ea([eb(f) for f in fields])]) for eid, fields in filtered]
            result_parts.append(ea([eb(sn), ea(entry_list)]))
        if not result_parts:
            return eb(None)
        return ea(result_parts)
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
    sys.stdout.write(handle(parse(line)))
    sys.stdout.flush()
