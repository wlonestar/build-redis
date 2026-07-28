import sys
from collections import deque

store, expiry, clock = {}, {}, 0
lists = {}
key_types = {}

def encode_bulk_string(s):
    if s is None:
        return "$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n"

def encode_simple_string(s):
    return f"+{s}\r\n"

def encode_error(m):
    return f"-{m}\r\n"

def encode_integer(n):
    return f":{n}\r\n"

def check_expiry(key):
    """ Check if key is expired. If so, delete from store and expiry dicts."""
    if expiry[key] < clock:
        store.pop(key)
        expiry.pop(key)

def encode_array(items):
    result = f"*{len(items)}\r\n"
    for item in items:
        result += item
    return result

def check_type(key, expected):
    if key in key_types and key_types[key] != expected:
        return encode_error("WRONGTYPE Operation against a key holding the wrong kind of value")
    return None

def handle(args):
    global clock
    cmd = args[0].upper()
    if cmd == "WAIT": clock += int(args[1]); return encode_simple_string("OK")
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
        key_types[key] = "str"
        if ex_ms is not None: expiry[key] = clock + ex_ms
        return encode_simple_string("OK")
    elif cmd == "GET":
        # Call check_expiry before accessing
        check_expiry(args[1])
        return encode_bulk_string(store.get(args[1]))
    elif cmd == "EXISTS":
        # Check expiry for each key, count existing ones
        cnt = len(store)
        for key in store:
            if expiry[key] < clock:
                cnt -= 1
        return encode_integer(cnt)
    elif cmd == "TTL":
        check_expiry(args[1])
        if args[1] not in store: return encode_integer(-2)
        if args[1] not in expiry: return encode_integer(-1)
        return encode_integer(max(0, (expiry[args[1]] - clock) // 1000))
    elif cmd == "DBSIZE":
        # Count only non-expired keys
        cnt = 0
        for key in store:
            if expiry[key] < clock:
                cnt += 1
        return encode_integer(cnt)
    elif cmd == "EXPIRE":
        check_expiry(args[1])
        if args[1] not in store: return encode_integer(0)
        expiry[args[1]] = clock + int(args[2]) * 1000; return encode_integer(1)
    elif cmd == "PING":
        return encode_simple_string("PONG") if len(args)==1 else encode_bulk_string(args[1])
    elif cmd == "LPUSH":
        key = args[1]
        values = args[2:]
        err = check_type(key, "list")
        if err:
            return err
        # Create deque if key does not exist
        q = lists[key] if key in lists else deque()
        # Push values to LEFT (appendleft) in order
        for val in values:
            q.appendleft(val)
        # Set key_types[key] = "list"
        key_types[key] = "list"
        lists[key] = q
        # Return new length as integer
        return encode_integer(len(q))
    elif cmd == "RPUSH":
        key = args[1]
        values = args[2:]
        err = check_type(key, "list")
        if err:
            return err
        # Create deque if key does not exist
        q = lists[key] if key in lists else deque()
        # Push values to RIGHT (append) in order
        for val in values:
            q.append(val)
        # Set key_types[key] = "list"
        key_types[key] = "list"
        lists[key] = q
        # Return new length as integer
        return encode_integer(len(q))
    elif cmd == "LRANGE":
        # Implement LRANGE key start stop
        key = args[1]
        err = check_type(key, "list")
        if err:
            return err
        start = int(args[2])
        stop = len(lists[key]) if int(args[3]) == -1 else int(args[3])
        items = []
        for i in range(start, stop):
            items.append(encode_bulk_string(lists[key][i]))
        return encode_array(items)
    return encode_error(f"ERR unknown command '{cmd}'")

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
