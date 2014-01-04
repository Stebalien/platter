import netifaces

__all__ = ('find_ip', 'get_default_iface')

def __parse_table(iterable):
    return (row.rstrip('\n').split('\t') for row in iterable)

def get_default_iface():
    with open('/proc/net/route') as f:
        f.readline() # Chop off header
        for items in __parse_table(f):
            if int(items[3]) & 1 and int(items[1]) == 0:
                return items[0]
    return None

def find_ip():
    iface = get_default_iface()
    if iface is None:
        return '127.0.0.1'
    else:
        for a in netifaces.ifaddresses(iface)[netifaces.AF_INET]:
            try:
                return a['addr']
            except KeyError:
                pass

