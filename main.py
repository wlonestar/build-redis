import sys
from collections import deque

store, expiry, clock = {}, {}, 0
lists = {}
hashes = {}
sets = {}
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
        err = check_type(key, "list")
        if err: return err
        if key not in lists:
            lists[key] = deque()
            key_types[key] = "list"
        for val in args[2:]:
            lists[key].appendleft(val)
        return encode_integer(len(lists[key]))
    elif cmd == "RPUSH":
        key = args[1]
        err = check_type(key, "list")
        if err: return err
        if key not in lists:
            lists[key] = deque()
            key_types[key] = "list"
        for val in args[2:]:
            lists[key].append(val)
        return encode_integer(len(lists[key]))
    elif cmd == "LPOP":
        # Remove and return leftmost element, or $-1 if missing
        key = args[1]
        if key not in lists:
            return "$-1\r\n"
        elem = lists[key].popleft()
        # Auto-delete key if list becomes empty
        if len(lists[key]) == 0:
            lists.pop(key)
        return encode_bulk_string(elem)
    elif cmd == "RPOP":
        # Remove and return rightmost element
        key = args[1]
        if key not in lists:
            return "$-1\r\n"
        elem = lists[key].pop()
        if len(lists[key]) == 0:
            lists.pop(key)
        return encode_bulk_string(elem)
    elif cmd == "LLEN":
        # Return list length, or :0 if key missing
        key = args[1]
        return encode_integer(len(lists[key]) if key in lists else 0)
    elif cmd == "LRANGE":
        key = args[1]
        if key not in lists: return "*0\r\n"
        start, stop = int(args[2]), int(args[3])
        lst = list(lists[key])
        if start < 0: start = max(0, len(lists[key]) + start)
        if stop < 0: stop = len(lists[key]) + stop
        return encode_array([encode_bulk_string(x) for x in lst[start:stop+1]])
    elif cmd == "HSET":
        key = args[1]
        pairs = args[2:]
        if key not in hashes:
            hashes[key] = {}
            key_types[key] = "hash"
        for (field, value) in zip(pairs[0::2], pairs[1::2]):
            hashes[key][field] = value
        return encode_integer(len(hashes[key]))
    elif cmd == "HGET":
        key, field = args[1], args[2]
        if key not in hashes:
            return "$-1\r\n"
        return encode_bulk_string(hashes[key][field])
    elif cmd == "HDEL":
        key, field = args[1], args[2]
        fields = args[3:]
        cnt = 1
        hashes[key].pop(field)
        for f in fields:
            hashes[key].pop(f)
            cnt += 1
        if len(hashes[key]) == 0:
            hashes.pop(key)
        return encode_integer(cnt)
    elif cmd == "HGETALL":
        key = args[1]
        lst = []
        for field in hashes[key]:
            value = hashes[key][field]
            lst.append(field)
            lst.append(value)
        return encode_array([encode_bulk_string(x) for x in lst])
    elif cmd == "HEXISTS":
        key, field = args[1], args[2]
        return encode_integer(1 if field in hashes[key] else 0)
    elif cmd == "HLEN":
        key = args[1]
        return encode_integer(len(sets[key]))
    elif cmd == "SADD":
        key, members = args[1], args[2:]
        if key not in sets:
            sets[key] = set()
            key_types[key] = "set"
        cnt = len(sets[key])
        for m in members:
            sets[key].add(m)
        return encode_integer(len(sets[key]) - cnt)
    elif cmd == "SMEMBERS":
        key = args[1]
        lst = [encode_bulk_string(x) for x in sets[key]]
        return encode_array(lst)
    elif cmd == "SISMEMBER":
        key, member = args[1], args[2]
        return encode_integer(1 if member in sets[key] else 0)
    elif cmd == "SCARD":
        key = args[1]
        return encode_integer(len(sets[key]))
    elif cmd == "SREM":
        key, members = args[1], args[2:]
        cnt = len(sets[key])
        for member in members:
            sets[key].remove(member)
        return encode_integer(cnt - len(sets[key]))
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
