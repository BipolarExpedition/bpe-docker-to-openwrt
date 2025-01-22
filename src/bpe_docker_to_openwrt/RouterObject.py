from subprocess import run as runprocess
from sys import stderr
#from os import stdout
import pathlib

from dataclasses import dataclass
from typing import List, Optional, Dict
from subprocess import CalledProcessError, CompletedProcess
from os import access, X_OK
from shutil import which as shellwhich

@dataclass
class RouterObject:

    def __init__(self, hostname: str, port: Optional[int] = None, identity_file: Optional[str] = None, username: Optional[str] = None, cmdname: Optional[str] = None):
        self._hostname = hostname
        self.setSSHcmd(cmdname)
        self._port: Optional[int]
        self.setPort(port)
        self._identity_file: Optional[str]
        self.setIdentityFile(identity_file)
        self._username: str
        self.setUsername(username)

        self._lastDefinedExtraDNS: List[str] = []
        self._lastDefinedMappings: Dict[str, str] = {}
        self._sshexe: str = ""
        self.setSSHcmd(cmdname)

        self._cmd_showDns: str = "uci show dhcp.@dnsmasq[0].address"
        self._cmd_addDns: str = "uci add_list dhcp.@dnsmasq[0].address='{definition}'"
        self._cmd_delDns: str = "uci del_list dhcp.@dnsmasq[0].address='{definition}'"
        self._cmd_commit: str = "uci commit dhcp"
        self._cmd_reload: str = "service dnsmasq reload"      

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
        if not beQuiet:
            stderr.write("WARNING: Could not find ssh command, using 'ssh'\n")

        found = shellwhich("ssh", mode=X_OK)
        if found is not None:
            self._sshexe = found
            return
        
        # We couldnt find the command, lets use SSH and hope for the best
        self._sshexe = "ssh"
        if not beQuiet:
            stderr.write("ERROR: We could not find 'ssh' either! This may not work!\n")

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

    def setUsername(self, username: Optional[str]):
        if username is not None and len(username) > 0:
            self._username = username
        else:
            self._username = "root"

    def doSSHcmd(self, cmd: str | List[str], doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)) -> CompletedProcess[str]:
        if self._sshexe is None:
            raise FileNotFoundError("ssh not found")
        
        shellcmd = [self._sshexe]
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
            if not doTest:
                result = runprocess(shellcmd, capture_output=True, text=True)
            else:
                stderr.write(f"Test: cmd[{shellcmd}]\n")
                result = testRunReturn
        except CalledProcessError as e:
            stderr.write(f"Error running command '{str(cmd)}': {e}\n")
        
        if result.returncode != 0:
            stderr.write(f"Error running command '{str(cmd)}': {result.stderr}\n")

        return result

    def getDefinedExtraDNS(self, doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)) -> List[str] | None:

        result = self.doSSHcmd(self._cmd_showDns, doTest=doTest, testRunReturn=testRunReturn)

        if result.returncode != 0:
            stderr.write("Error querying router for DNS mappings: {result.stderr}\n")
            self._lastDefinedExtraDNS = []
            return None
        
        output = result.stdout

        if output is not None and len(output) > 0:        
            if output.strip().startswith("uci: Entry not found"):
                self._lastDefinedExtraDNS = []
                return []
            configfile, definitions = output.strip().split("=",1)
            if definitions is not None and len(definitions) > 0:
                mappings = definitions.split(" ")
                self._lastDefinedExtraDNS = mappings
                return mappings
        self._lastDefinedExtraDNS = []
        return None
    
    def findDefinitionWithDNS(self,dns: str, definitions: List[str] = []) -> str:
        if definitions is None or len(definitions) == 0:
            if self._lastDefinedExtraDNS is None:
                self._lastDefinedExtraDNS = self.getDefinedExtraDNS()
            definitions = self._lastDefinedExtraDNS
        
        if definitions is None or len(definitions) == 0:
            return ""
        
        for mapping in definitions:
            if mapping[0] == "'":
                mapping = mapping[1:]
            if mapping[-1] == "'":
                mapping = mapping[:-1]
            sections = mapping.split("/")
            if len(sections) > 2:
                #ip = 
                sections.pop()
                for addr in sections:
                    if addr == dns:
                        return mapping
        return ""

    def mappingsFromDefinitions(self, definitions: Optional[List[str]] = None) -> Dict[str, str]:
        outDict: Dict[str, str] = {}

        if definitions is None or len(definitions) == 0:
            if self._lastDefinedExtraDNS is None:
                self._lastDefinedExtraDNS = self.getDefinedExtraDNS()
            definitions = self._lastDefinedExtraDNS

        if definitions is None or len(definitions) == 0:
            self._lastDefinedMappings = outDict
            return outDict
        
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

        self._lastDefinedMappings = outDict

        return outDict

    def addDNSMapping(self, dns: str, ip: str, doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)):
        existingDefinition = self.findDefinitionWithDNS(dns)

        if existingDefinition is not None and len(existingDefinition) > 0:
            print(f"TODO:  Updating mapping {dns} -> {ip}")
            # TODO: Update the existing mapping

        else:
            print(f"Adding mapping {dns} -> {ip}")
            definition = f"/{dns}/{ip}"
            print("DEBUG:  ", self._cmd_addDns.format(definition=definition))
            #self.doSSHcmd(self._cmd_addDns.format(definition=definition), doTest=doTest, testRunReturn=testRunReturn)
            self._lastDefinedExtraDNS.append(definition)
    
    def removeDNSMapping(self, dns: str, doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)):
        print(f"Removing mapping {dns} -> {self._lastDefinedMappings[dns]}")

        #definition = findDefinitionWithDNS(mapp, definedDNS)
        definition = self.findDefinitionWithDNS(dns)
        print("DEBUG:  ", self._cmd_delDns.format(definition=definition))
        #self.doSSHcmd(self._cmd_addDns.format(definition=definition)self._cmd_delDns.format(definition=definition), doTest=doTest, testRunReturn=testRunReturn)
        self._lastDefinedExtraDNS.remove(definition)

    def commit(self, doTest: bool = False, testRunReturn: CompletedProcess[str] = CompletedProcess(args=[], returncode=255)):
        print("Committing changes")
        self.doSSHcmd(self._cmd_commit, doTest=doTest, testRunReturn=testRunReturn)
        self.doSSHcmd(self._cmd_reload, doTest=doTest, testRunReturn=testRunReturn)

    # ------------------
    # --- Properties ---
    # ------------------
    @property
    def ShellCmd(self) -> str:
        return self._sshexe
