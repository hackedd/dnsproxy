class Resolver(object):
    def resolve_a(self, qname, ipv6=False):
        return None

    def resolve_mx(self, qname):
        return None

    def resolve(self, qname, rdtype, rdclass):
        return None


class OverrideResolver(Resolver):
    def __init__(self, overrides=None, ipv6=False):
        self.overrides = overrides or dict()
        self.star = {}
        self.starstar = {}
        self.ipv6 = ipv6

    def add_override(self, name, address):
        if name.startswith("**."):
            self.starstar[name[3:]] = address
        elif name.startswith("*."):
            self.star[name[2:]] = address
        else:
            self.overrides[name] = address

    def resolve_a(self, qname, ipv6=False):
        if ipv6 != self.ipv6:
            return None

        name = str(qname).lower().rstrip(".")
        if name in self.overrides:
            return self.overrides[name]

        if "." not in name:
            return None

        # Remove the leftmost label, to see if a wildcard was defined
        partial_name = name[name.find(".") + 1:]
        if partial_name in self.star:
            return self.star[partial_name]

        if partial_name in self.starstar:
            return self.starstar[partial_name]

        # continue removing the leftmost label
        while "." in partial_name:
            partial_name = partial_name[partial_name.find(".") + 1:]
            if partial_name in self.starstar:
                return self.starstar[partial_name]

        return None
