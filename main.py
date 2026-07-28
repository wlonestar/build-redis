import sys
from collections import deque

store, expiry, clock = {}, {}, 0
lists, hashes, sets, zsets = {}, {}, {}, {}
key_types = {}

in_tx = False
queue = []

subscriptions = set()

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
    if key in expiry and expiry[key] < clock:
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

def exec_cmd(args):
    global clock
    cmd = args[0].upper()
    if cmd == "WAIT":
        clock += int(args[1]);
        return encode_simple_string("OK")
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
        key_types[key] = "string"
        if ex_ms is not None: expiry[key] = clock + ex_ms
        return encode_simple_string("OK")
    elif cmd == "GET":
        # Call check_expiry before accessing
        check_expiry(args[1])
        return encode_bulk_string(store.get(args[1]))
    elif cmd == "EXISTS":
        keys = args[1:]
        cnt = 0
        for key in keys:
            if key in key_types:
                cnt += 1
        return encode_integer(cnt)
    elif cmd == "DEL":
        keys = args[1:]
        cnt = 0
        for key in keys:
            if key in store:
                cnt += 1
                store.pop(key)
                key_types.pop(key)
        return encode_integer(cnt)
    elif cmd == "KEYS":
        lst = [encode_bulk_string(x) for x in store]
        return encode_array(lst) 
    elif cmd == "TYPE":
        key = args[1]
        return encode_simple_string(key_types[key] if key in key_types else "none")
    elif cmd == "RENAME":
        key, newkey = args[1], args[2]
        if key not in store:
            return encode_error("ERR source does not exist")
        return encode_simple_string("OK")
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
    elif cmd == "ZADD":
        key = args[1]
        err = check_type(key, "zset")
        if err: return err
        pairs = args[2:]
        if key not in zsets:
            zsets[key] = {}
            key_types[key] = "zset"
        cnt = 0
        for (score_str, member) in zip(pairs[0::2], pairs[1::2]):
            score = float(score_str)
            if member not in zsets[key]:
                cnt += 1
            zsets[key][member] = score
        return encode_integer(cnt)
    elif cmd == "ZSCORE":
        key, member = args[1], args[2]
        if key not in zsets or member not in zsets[key]:
            return "$-1\r\n"
        return encode_bulk_string(f"{zsets[key][member]:g}")
    elif cmd == "ZRANGE":
        key = args[1]
        if key not in zsets:
            return "*0\r\n"
        start, stop = int(args[2]), int(args[3])
        withscores = len(args) > 4 and args[4].upper() == "WITHSCORES"
        members_sorted = sorted(zsets[key].items(), key=lambda x: (x[1], x[0]))
        lst = [m for m, s in members_sorted]
        if start < 0:
            start = max(0, len(lst) + start)
        if stop < 0:
            stop = len(lst) + stop
        result = lst[start:stop + 1]
        if withscores:
            items = []
            for m in result:
                items.append(encode_bulk_string(m))
                items.append(encode_bulk_string(f"{zsets[key][m]:g}"))
            return encode_array(items)
        return encode_array([encode_bulk_string(m) for m in result])
    elif cmd == "ZRANK":
        key, member = args[1], args[2]
        if key not in zsets or member not in zsets[key]:
            return "$-1\r\n"
        members_sorted = sorted(zsets[key].items(), key=lambda x: (x[1], x[0]))
        for i, (m, s) in enumerate(members_sorted):
            if m == member:
                return encode_integer(i)
        return "$-1\r\n"
    elif cmd == "ZCARD":
        key = args[1]
        if key not in zsets:
            return encode_integer(0)
        return encode_integer(len(zsets[key]))
    return encode_error(f"ERR unknown command '{cmd}'")

def handle(args):
    global in_tx, queue
    cmd = args[0].upper()
    if cmd == "MULTI":
        if in_tx:
            return encode_error("ERR already in tx")
        in_tx = True
        queue = []
        return encode_simple_string("OK")
    elif cmd == "EXEC":
        if not in_tx:
            return encode_error("ERR EXEC without MULTI")
        lst = []
        for cmd in queue:
            lst.append(exec_cmd(cmd))
        in_tx = False
        queue = []
        return encode_array(lst)
    elif cmd == "DISCARD":
        in_tx = False
        queue.clear()
        return encode_simple_string("OK")
    elif in_tx:
        queue.append(args)
        return encode_simple_string("QUEUED")
    elif cmd == "SUBSCRIBE":
        channels = args[1:]
        total_count = len(subscriptions)
        result = ""
        for channel in channels:
            subscriptions.add(channel)
            total_count += 1
            result += encode_simple_string(f"subscribe {channel} {total_count}")
        return result
    elif cmd == "PUBLISH":
        channel, message = args[1], args[2]
        result = ""
        if channel in subscriptions:
            result += encode_simple_string(f"message {channel} {message}")
        return result + encode_integer(1 if channel in subscriptions else 0)
    elif cmd == "UNSUBSCRIBE":
        lst = []
        if len(args) == 1:
            lst = reversed(list(subscriptions))
        else:
            lst = args[1:]
        remaining = len(subscriptions)
        result = ""
        for channel in lst:
            subscriptions.remove(channel)
            remaining -= 1
            result += encode_simple_string(f"unsubscribe {channel} {remaining}")
        return result
    elif cmd == "SAVE":
        result = ""
        for key in sorted(store.keys()):
            result += f"KEY string {key} {store[key]}\r\n"
        for key in lists:
            items = [f"{x}" for x in lists[key]]
            result += f"KEY list {key} {','.join(items)}\r\n"
        for key in hashes:
            items = [f"{k}={v}" for k, v in hashes[key]]
            result += f"KEY hash {key} {','.join(items)}\r\n"
        for key in sets:
            items = [f"{x}" for x in sets[key]]
            result += f"KEY set {key} {','.join(items)}\r\n"
        return result + encode_simple_string("OK")
    elif cmd == "RESTORE":
        data: str = args[1]
        _, type, key, data = data.split(" ")
        if type == "string":
            store[key] = data
        return encode_simple_string("OK")
    else:
        return exec_cmd(args)

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
