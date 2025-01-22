#from typing import List
from typing import Optional
from typing import Dict
from typing import Any
from subprocess import CalledProcessError, CompletedProcess
from subprocess import run as runprocess
from sys import stderr
#from os import stdout
import pathlib

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

def getContainerIPs(doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)) -> Dict[str, str]:
    """Get a dictionary of docker container names and their IP addresses
    
    Uses the shell command: docker ps -q | xargs docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | sed 's/\\///'

    Returns:
        Dict[str, str]: A dictionary of container names and their IP addresses
    """

    querryCmd = r"docker ps -q | xargs docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | sed 's/\///'"
    #print(querryCmd)
    if not doTest:
        try:
            result = runprocess(['bash', '-c', querryCmd], capture_output=True, text=True)
        except CalledProcessError as e:
            stderr.write(f"Error running command '{str(querryCmd)}': {e}\n")
    else:
        stderr.write(f"Test: cmd[{querryCmd}]\n")
        result = testRunReturn

    if result.returncode != 0:
        stderr.write("ERROR: Error querying docker containers: {result.stderr}\n")
        return {}

    outDict = {}
    for line in result.stdout.split("\n"):
        if len(line) > 0:
            # Assign array instead, just in case multiple ips are returned
            returnArray = line.split(" ")
            name = returnArray[0]
            ip = returnArray[1]
            if len(name) > 0 and len(ip) > 0:
                outDict[name] = ip
            else:
                stderr.write(f"WARNING: Could not parse line '{line}'\n")

    return outDict

def main():

    identity_file = pathlib.Path(__file__).resolve().parent.parent / ".secrets" / "openwrt_id_rsa"
    base_domain = "docker.ardite.lan"

    router: RouterObject = RouterObject("openwrt.lan", identity_file=identity_file)

    container_listing: Dict[str, str] = {}
    #last_container_listing: Dict[str, str] = {}

    #last_container_listing = container_listing
    container_listing = getContainerIPs()

    definedDNS = router.getDefinedExtraDNS() #"openwrt.lan", str(identity_file))
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
