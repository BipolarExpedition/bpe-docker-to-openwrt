#from typing import List
#from typing import Optional
from typing import Dict
from typing import Any
from subprocess import CalledProcessError, CompletedProcess
from subprocess import run as runprocess
from sys import stderr
#from os import stdout
import pathlib
import re

from bpe_docker_to_openwrt.RouterObject import RouterObject

from bpe_docker_to_openwrt.__about__ import __version__
from bpe_docker_to_openwrt.__about__ import __title__, __description__, __url__, __author__  # noqa: F401

# ---------------------------
# --- Conditional imports ---
# ---------------------------
# If rich is installed, use pretty print, otherwise use standard print
try:
    from rich.pretty import pprint as original_pprint
    def pprint(*args: Any, **kwargs: Any) -> Any:
        return original_pprint(*args, **kwargs)
except ImportError:
    def pprint(*args: Any, **kwargs: Any) -> Any:
        return print(*args, **kwargs)

# If rich is installed, use the color enhanced print from rich
try:
    from rich import print
except ImportError:
    pass

# If rich is installed, install rich traceback for nicer looking exceptions
try:
    from rich.traceback import install
    install()
except ImportError:
    pass
# ---------------------------

def getContainerIPs(replaceUnderscores: str = "-", replaceDots: str = ".", replaceColons: str = "-", replaceSymbols: str = "", doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)) -> Dict[str, str]:
    """Get a dictionary of docker container names and their IP addresses
    
    Uses the shell command: docker ps -q | xargs docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | sed 's/\\///'

    Returns:
        Dict[str, str]: A dictionary of container names and their IP addresses
    """

    # Note: regex is proving difficult to match, and capture multipe ips

    querryCmd = r"docker ps -q | xargs docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | sed 's/\///'"
    #re_valid_name_followed_by_ips = re.compile(r"^([a-zA-Z0-9_\-\.\@\#\$\%]+)(?:\s+([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|[0-9a-fA-F:]+))+$", re.M | re.S)
    #re_valid_name_followed_by_ips = re.compile(r"^([a-zA-Z0-9_\-\.\@\#\$\%]+)(\s*[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|\s*[0-9a-fA-F:]+)+$", re.M | re.S)

    # I was strugling with capturing multiple ips. It would match those lines, but only capture one ip. I finally asked copilot for help and it gave me this regex
    re_valid_name_followed_by_ips = re.compile(r"^([a-zA-Z0-9_\-\.\@\#\$\:\%]+)((?:\s+[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|\s+[0-9a-fA-F:]+)+)$", re.M | re.S)
    re_match_symbol = re.compile(r"[\@\#\$\%\\]")
        
    #print(querryCmd)
    if not doTest:
        try:
            result = runprocess(['bash', '-c', querryCmd], capture_output=True, text=True)
        except CalledProcessError as e:
            stderr.write(f"Error running command '{str(querryCmd)}': {e}\n")
            return {}
    else:
        stderr.write(f"Test: cmd[{querryCmd}]\n")
        result = testRunReturn

    if result.returncode != 0:
        stderr.write("ERROR: Error querying docker containers: {result.stderr}\n")
        return {}

    outDict = {}
    # TODO: Consider replacing the for loop with just the findall
    for line in result.stdout.split("\n"):
        if len(line) > 0:
            # Redo this area to a regex match
            match = re_valid_name_followed_by_ips.findall(line)
            
            if match is not None and len(match) > 0:
                for m in match:
                    name: str = m[0]
                    ips = m[1].strip().split(" ")
                    # TODO: Consider only adding ipv4 addresses
                    if len(name) > 0:
                        name = name.replace(r"_", replaceUnderscores).replace(r".", replaceDots).replace(r":", replaceColons)
                        name = re_match_symbol.sub(replaceSymbols, name)
                        # take only the first ip
                        outDict[name] = ips[0]
            else:
                stderr.write(f"WARNING: Could not parse line '{line}'\n")

    return outDict

def main():

    identity_file = pathlib.Path(__file__).resolve().parent.parent / ".secrets" / "openwrt_id_rsa"
    base_domain = "docker.ardite.lan"

    router: RouterObject = RouterObject("openwrt.lan", identity_file=identity_file)

    container_listing: Dict[str, str] = getContainerIPs()

    definedDNS = router.getDefinedExtraDNS()
    if definedDNS is not None:
        pprint(definedDNS)
        mappings = router.mappingsFromDefinitions(definedDNS)
        pprint(mappings)
    
    # Determine if any of the mappings may be old containers
    dns2remove: Dict[str, str] = {}
    for mapp in mappings:
        if mapp.endswith(base_domain):
            # This might be an old container
            container = mapp[:-len(base_domain)]
            if container not in container_listing:
                dns2remove[mapp] = mappings[mapp]

    # Determine if any of the containers are not in the mappings
    dns2add: Dict[str, str] = {}
    for container in container_listing:
        wanted_name = f"{container}.{base_domain}"
        if wanted_name not in mappings:
            print(f"Could not find mapping for {container}")
            dns2add[wanted_name] = container_listing[container]
        else:
            print(f"Found mapping for {container}: {mappings[wanted_name]}")

    # remove old mappings
    if len(dns2remove) > 0:
        for mapp in dns2remove:
            router.removeDNSMapping(mapp)


    # add new mappings
    if len(dns2add) > 0:
        for wanted_name in dns2add:
            router.addDNSMapping(wanted_name, dns2add[wanted_name])

if __name__ == "__main__":
    print(f"bpe-docker-to-openwrt {__version__}")
    main()
