from dataclasses import dataclass
#import subprocess
from subprocess import CalledProcessError, CompletedProcess
from subprocess import run as runprocess
from os import access, X_OK
from typing import List, Optional, Dict
from shutil import which as shellwhich
import pathlib

from bpe_docker_to_openwrt.__about__ import __version__

try:
    from rich import pprint
except ImportError:
    def pprint(*args, **kwargs):
        print(*args, **kwargs)

try:
    from rich import print
except ImportError:
    pass

try:
    from rich.traceback import install
    install()
except ImportError:
    pass

sshexe = shellwhich("ssh")

# def doSSHcmd(cmd: str | List[str], hostname: str, port: Optional[int] = None, username: str = "root", identity_file: Optional[str] = None, shell: bool = False) -> CompletedProcess[str]:
#     if sshexe is None:
#         raise FileNotFoundError("ssh not found")
    
#     shellcmd = [sshexe]
#     if len(username) > 0:
#         shellcmd.append(f"{username}@{hostname}")
#     else:
#         shellcmd.append(hostname)
        
#     if port is not None and port > 0:
#         shellcmd.append("-p")
#         shellcmd.append(f"{port}")

#     if identity_file is not None and len(str(identity_file)) > 0:
#         identity_file = pathlib.Path(identity_file).expanduser().resolve()
#         if identity_file.exists():
#             shellcmd.append("-i")
#             shellcmd.append(str(identity_file))

#     if isinstance(cmd, str):
#         # Try appending the string as a single list entry
#         shellcmd.append(cmd)
#     else:
#         shellcmd.extend(cmd)

#     try:
#         result = runprocess(shellcmd, capture_output=True, text=True)
#     except CalledProcessError as e:
#         print(f"Error running command '{str(cmd)}':", e)
    
#     if result.returncode != 0:
#         print(f"Error running command '{str(cmd)}': {result.stderr}")

#     return result

def getContainerIPs() -> Dict[str, str]:
    """Get a dictionary of docker container names and their IP addresses
    
    Uses the shell command: docker ps -q | xargs docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | sed 's/\\///'

    Returns:
        Dict[str, str]: A dictionary of container names and their IP addresses
    """

    querryCmd = r"docker ps -q | xargs docker inspect --format '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | sed 's/\///'"
    #print(querryCmd)
    result = runprocess(['bash', '-c', querryCmd], capture_output=True, text=True)

    if result.returncode != 0:
        print("Error querying docker containers:", result.stderr)
        return {}

    outDict = {}
    for line in result.stdout.split("\n"):
        if len(line) > 0:
            name, ip = line.split(" ")
            if len(name) > 0 and len(ip) > 0:
                outDict[name] = ip
            else:
                print(f"Warning: Could not parse line '{line}'")

    return outDict

def findDefinitionWithDNS(dns: str, definitions: List[str]) -> str | None:
    for mapping in definitions:
        if mapping[0] == "'":
            mapping = mapping[1:]
        if mapping[-1] == "'":
            mapping = mapping[:-1]
        sections = mapping.split("/")
        if len(sections) > 2:
            ip = sections.pop()
            for addr in sections:
                if addr == dns:
                    return mapping
    return None


def mappingsFromDefinitions(definitions: List[str]) -> Dict[str, str]:
    outDict = {}

    for mapping in definitions:
        if mapping[0] == "'":
            mapping = mapping[1:]
        if mapping[-1] == "'":
            mapping = mapping[:-1]
        sections = mapping.split("/")
        if len(sections) > 2:
            ip = sections.pop()
            for addr in sections:
                if len(addr) > 0:
                    outDict[addr] = ip

    return outDict

def undefineDNS(dns: str, definitions: List[str]) -> List[str]:
    pass

@dataclass
class RouterObject:
    _hostname: str
    _port: Optional[int]
    _identity_file: Optional[str]
    _username: str
    _sshexe: str

    def __init__(self, hostname: str, port: Optional[int] = None, identity_file: Optional[str] = None, username: Optional[str] = None, cmdname: Optional[str] = None):
        self._hostname = hostname
        self.setSSHcmd(cmdname)
        self.setPort(port)
        self.setIdentityFile(identity_file)
        self.setUsername(username)

    def setSSHcmd(self, cmdname: str | None, beQuiet: bool = False):
        if cmdname is not None and len(cmdname) > 0:
            cmdname = str(pathlib.Path(cmdname).expanduser().resolve())
            if pathlib.Path(cmdname).exists() and pathlib.Path(cmdname).is_file() and access(cmdname, X_OK):
                self._sshexe = cmdname
                return
            found = shellwhich(cmdname, mode=X_OK)
            if found is not None:
                self._sshexe = found
                return
            
        # We couldnt find the requested command. Lets try ssh
        found = shellwhich("ssh", mode=X_OK)
        if found is not None:
            self._sshexe = found
            return
        
        # We couldnt find the command, lets use SSH and hope for the best
        self._sshexe = "ssh"
        if not beQuiet:
            print("Could not find ssh command, using 'ssh'")
        self._sshexe = "ssh"

    def setPort(self, port: Optional[int]):
        if port is not None and port > 0:
            self._port = port
        else:
            self._port = None
    
    def setIdentityFile(self, identity_file: str | pathlib.Path | None):
        if identity_file is not None and isinstance(identity_file, pathlib.Path):
            truepath = str(identity_file.expanduser().resolve())
        elif identity_file is not None and isinstance(identity_file, str) and len(identity_file) > 0:
            truepath = str(pathlib.Path(identity_file).expanduser().resolve())
        else:
            truepath = None

        if truepath is not None and not pathlib.Path(truepath).exists():
            truepath = None

        self._identity_file = truepath

    def setUsername(self, username: str):
        if username is not None and len(username) > 0:
            self._username = username
        else:
            self._username = "root"

    def doSSHcmd(self, cmd: str | List[str]) -> CompletedProcess[str]:
        if sshexe is None:
            raise FileNotFoundError("ssh not found")
        
        shellcmd = [sshexe]
        if len(self._username) > 0:
            shellcmd.append(f"{self._username}@{self._hostname}")
        else:
            shellcmd.append(self._hostname)
            
        if self._port is not None and self._port > 0:
            shellcmd.append("-p")
            shellcmd.append(f"{self._port}")

        if self._identity_file is not None and len(self._identity_file) > 0:
            shellcmd.append("-i")
            shellcmd.append(self._identity_file)

        if isinstance(cmd, str):
            # Try appending the string as a single list entry
            shellcmd.append(cmd)
        else:
            shellcmd.extend(cmd)

        try:
            result = runprocess(shellcmd, capture_output=True, text=True)
        except CalledProcessError as e:
            print(f"Error running command '{str(cmd)}':", e)
        
        if result.returncode != 0:
            print(f"Error running command '{str(cmd)}': {result.stderr}")

        return result

    def getDefinedExtraDNS(self) -> List[str] | None:
        result = self.doSSHcmd("uci show dhcp.@dnsmasq[0].address")
        if result.returncode != 0:
            print("Error querying DNS server:", result.stderr)
            self._lastDefinedExtraDNS = None
            return None
        
        output = result.stdout

        if output is not None and len(output) > 0:        
            if output.strip().startswith("uci: Entry not found"):
                self._lastDefinedExtraDNS = {}
                return {}
            configfile, definitions = output.strip().split("=",1)
            if definitions is not None and len(definitions) > 0:
                mappings = definitions.split(" ")
                self._lastDefinedExtraDNS = mappings
                return mappings

def main():

    identity_file = pathlib.Path(__file__).resolve().parent.parent / ".secrets" / "openwrt_id_rsa"
    base_domain = "docker.ardite.lan"

    router: RouterObject = RouterObject("openwrt.lan", identity_file=identity_file)

    container_listing: Dict[str, str] = {}
    last_container_listing: Dict[str, str] = {}

    last_container_listing = container_listing
    container_listing = getContainerIPs()

    definedDNS = router.getDefinedExtraDNS() #"openwrt.lan", str(identity_file))
    if definedDNS is not None:
        pprint(definedDNS)
        mappings = mappingsFromDefinitions(definedDNS)
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
            print(f"Removing mapping {mapp} -> {dns2remove[mapp]}")
            definition = findDefinitionWithDNS(mapp, definedDNS)
            print(f"DEBUG:  uci del_list dhcp.@dnsmasq[0].address='{definition}'")
            #doSSHcmd(f"uci del_list dhcp.@dnsmasq[0].address='{definition}'", "openwrt.lan", identity_file=str(identity_file))
            definedDNS.remove(definition)

    # add new mappings
    if len(dns2add) > 0:
        for wanted_name in dns2add:
            existingDefinition = findDefinitionWithDNS(wanted_name, definedDNS)
            if existingDefinition is not None:
                print(f"TODO:  Updating mapping {wanted_name} -> {dns2add[wanted_name]}")
            else:
                print(f"Adding mapping {wanted_name} -> {dns2add[wanted_name]}")
                definition = f"'/{wanted_name}/{dns2add[wanted_name]}'"
                print(f"DEBUG:  uci add_list dhcp.@dnsmasq[0].address={definition}")
                definedDNS.append(definition)


    #res = doSSHcmd("ls /tmp", "openwrt.lan", identity_file=str(identity_file))
    


if __name__ == "__main__":
    print(f"bpe-docker-to-openwrt {__version__}")
    main()


### Notes
# uci del_list dhcp.@dnsmasq[0].address='/bob.lan/172.17.0.99'
# uci add_list dhcp.@dnsmasq[0].address='/imaginary.docker.ardite.lan/172.17.0.66'
# uci commit dhcp
# service dnsmasq reload