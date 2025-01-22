import pytest
#from subprocess import CalledProcessError
from subprocess import CompletedProcess

from bpe_docker_to_openwrt.main import getContainerIPs

@pytest.mark.parametrize("testRunReturn,expected", [
    # Basic valid input
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2 172.18.0.5
sample1 172.18.0.4
traefik 172.21.0.2
plik 172.21.0.3
subdomain_service 172.18.0.52
portainer 172.17.0.2
qbittorrent
vpn 172.18.0.2
prowlarr 172.18.0.96
""", stderr=""),
        {   'sample2': '172.18.0.5', 
            'sample1': '172.18.0.4',
            'traefik': '172.21.0.2',
            'plik': '172.21.0.3',
            'subdomain-service': '172.18.0.52',
            'portainer': '172.17.0.2',
            'vpn': '172.18.0.2',
            'prowlarr': '172.18.0.96' }),

    # stdout with multiple IPs on a single line (expect only the first to be parsed)
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2 172.18.0.5 192.168.1.1
sample1 172.18.0.4
traefik 172.21.0.2
plik 172.21.0.3 10.0.0.1
subdomain_service 172.18.0.52 38.0.101.76 2001:db8::1
portainer 172.17.0.2
""", stderr=""),
        {   'sample2': '172.18.0.5',
            'sample1': '172.18.0.4',
            'traefik': '172.21.0.2',
            'plik': '172.21.0.3',
            'subdomain-service': '172.18.0.52',
            'portainer': '172.17.0.2' }),

    # stdout with IPv6 addresses 
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2 172.18.0.5
sample1 fe80::1ff:fe23:4567:890a
traefik 172.21.0.2
plik fe80::1ff:fe23:4567:abcd 172.21.0.3
subdomain_service 172.18.0.52
portainer fe80::1ff:fe23:1234:abcd
""", stderr=""),
        {   'sample2': '172.18.0.5',
            'sample1': 'fe80::1ff:fe23:4567:890a',
            'traefik': '172.21.0.2',
            'plik': 'fe80::1ff:fe23:4567:abcd',
            'subdomain-service': '172.18.0.52',
            'portainer': 'fe80::1ff:fe23:1234:abcd' }),

    # stdout with blank lines (expect to ignore blank lines)
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2 172.18.0.5

sample1 172.18.0.4
traefik 172.21.0.2


plik 172.21.0.3
subdomain_service 172.18.0.52


""", stderr=""),
        {   'sample2': '172.18.0.5',
            'sample1': '172.18.0.4',
            'traefik': '172.21.0.2',
            'plik': '172.21.0.3',
            'subdomain-service': '172.18.0.52' }),

    # Names with periods (expect no issues)
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2.service 172.18.0.5
sample1.app 172.18.0.4
traefik.server 172.21.0.2
plik.resource 172.21.0.3
subdomain.service 172.18.0.52
""", stderr=""),
        {   'sample2.service': '172.18.0.5',
            'sample1.app': '172.18.0.4',
            'traefik.server': '172.21.0.2',
            'plik.resource': '172.21.0.3',
            'subdomain.service': '172.18.0.52' }),

    # Names with spaces (expect parsing to fail or skip those entries)
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2 172.18.0.5
invalid name 172.18.0.6
another-invalid.name 172.18.0.7
messed_up@name:2 172.18.0.8
traefik 172.21.0.2
""", stderr=""),
        {   'sample2': '172.18.0.5',
            'another-invalid.name': '172.18.0.7',
            'messed-upname-2': '172.18.0.8',
            'traefik': '172.21.0.2' }),

    # Unexpected characters or corrupted lines
    (CompletedProcess(
        args=[], returncode=0,
        stdout=r"""sample2 172.18.0.5
sample1 172.18.0.4
**randomgarbage**
traefik 172.21.0.2
plik@@172.21.0.3
subdomain_service 172.18.0.52
""", stderr=""),
        {   'sample2': '172.18.0.5',
            'sample1': '172.18.0.4',
            'traefik': '172.21.0.2',
            'subdomain-service': '172.18.0.52' }),
    # Command returns an error
    (CompletedProcess(
        args=[], returncode=255,
        stdout=r"""sample2 172.18.0.5
**randomgarbage**
traefik 172.21.0.2
""", stderr=""),
        {}),
])
def test_getContainerIPs(testRunReturn, expected):
    container_listing = getContainerIPs(doTest=True, testRunReturn=testRunReturn)

    assert container_listing == expected
    