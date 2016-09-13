from dnsproxy.resolver import OverrideResolver


def test_simple_overrides():
    resolver = OverrideResolver()
    resolver.add_override("google.com", "127.0.0.1")
    resolver.add_override("www.google.com", "127.0.0.1")

    assert resolver.resolve_a("google") is None
    assert resolver.resolve_a("google.com") == "127.0.0.1"
    assert resolver.resolve_a("www.google.com") == "127.0.0.1"
    assert resolver.resolve_a("mail.google.com") is None


def test_wildcard_overrides():
    resolver = OverrideResolver()
    resolver.add_override("google.com", "127.0.0.1")
    resolver.add_override("*.google.com", "127.0.0.2")

    assert resolver.resolve_a("google.com") == "127.0.0.1"
    assert resolver.resolve_a("www.google.com") == "127.0.0.2"
    assert resolver.resolve_a("mail.google.com") == "127.0.0.2"
    assert resolver.resolve_a("test.mail.google.com") is None
    assert resolver.resolve_a("github.com") is None


def test_double_wildcard_overrides():
    resolver = OverrideResolver()
    resolver.add_override("google.com", "127.0.0.1")
    resolver.add_override("**.google.com", "127.0.0.2")

    assert resolver.resolve_a("google.com") == "127.0.0.1"
    assert resolver.resolve_a("www.google.com") == "127.0.0.2"
    assert resolver.resolve_a("mail.google.com") == "127.0.0.2"
    assert resolver.resolve_a("test.mail.google.com") == "127.0.0.2"
    assert resolver.resolve_a("github.com") is None


def test_ipv6():
    resolver = OverrideResolver()
    resolver.add_override("google.com", "127.0.0.1")

    assert resolver.resolve_a("google.com", ipv6=False) == "127.0.0.1"
    assert resolver.resolve_a("google.com", ipv6=True) is None

    resolver = OverrideResolver(ipv6=True)
    resolver.add_override("google.com", "::1")

    assert resolver.resolve_a("google.com", ipv6=True) == "::1"
    assert resolver.resolve_a("google.com", ipv6=False) is None
