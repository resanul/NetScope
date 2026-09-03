from core.network import calculate_network

def test_ipv4_network():
    result = calculate_network("192.168.1.10/24")
    assert result["Network"] == "192.168.1.0"
    assert result["Broadcast"] == "192.168.1.255"
    assert result["Usable hosts"] == "254"

def test_ipv6_network():
    result = calculate_network("2001:db8::1234/64")
    assert result["Version"] == "IPv6"
    assert result["Prefix"] == "/64"
    assert result["Network"] == "2001:db8::"
