import pytest
#from subprocess import CalledProcessError
from subprocess import CompletedProcess
from typing import Dict, Any
import pathlib

from bpe_docker_to_openwrt.RouterObject import RouterObject

testData_RouterObject_init = [ 
    (
        {
            'hostname' : 'host1',
            'port': 22,
            'identity_file': 'test_id1',
            'username': 'user1',
            'cmdname': 'ssh'
        },
        {
            'hostname': 'host1',
            'port': 22,
            'identity_file': None,
            'username': 'user1',
            'cmdname': 'ssh'
        }
    ),
    (
        {
            'hostname' : 'host1',
            'port': 1922,
        },
        {
            'hostname': 'host1',
            'port': 1922,
        }
    ),
    (
        {
            'hostname' : 'host1'
        },
        {
            'hostname': 'host1',
            'port': 22,
        }
    ),
    (
        {
            'hostname' : 'host1',
            'identity_file': 'tests/test_id1',
        },
        {
            'hostname': 'host1',
            'identity_file': 'tests/test_id1'
        }
    ),
    (
        {
            'hostname' : 'host1'
        },
        {
            'hostname': 'host1',
            'port': 22,
            'identity_file': None,
            'username': 'root',
            'cmdname': 'ssh'
        }
    ),
    (
        {
            'hostname' : 'host1',
            'identity_file': pathlib.Path('tests/test_id1').expanduser().resolve()
        },
        {
            'hostname' : 'host1',
            'identity_file': 'tests/test_id1',
        }
    ),
    (
        {
            'hostname' : 'host1',
            'cmdname' : 'nothere'
        },
        {
            'hostname' : 'host1',
            'cmdname' : 'ssh',
            'ShellCmd' : '/usr/bin/ssh'
        }
    ),
    (
        {
            'hostname' : 'host1',
            'cmdname' : '/usr/bin/ssh-keygen'
        },
        {
            'hostname' : 'host1',
            'cmdname' : '/usr/bin/ssh-keygen'
        }
    ),
    (
        {
            'hostname' : 'host1',
            'cmdname' : 'find'
        },
        {
            'hostname' : 'host1',
            'cmdname' : '/usr/bin/find',
            'ShellCmd': '/usr/bin/find'
        }
    ),
    (
        {
            'hostname': 'host',
            'port' : 2222,
            'username': 'bob'
        },
        {
            'check_bad' : 'Check if test test works'
        }
    )
]

testData_RouterObject_setSSHcmd = [
    ('/usr/bin/find','/usr/bin/find'),
    ('nothere', '/usr/bin/ssh')
]

# 'errorcode, output, expected_ret, expected_var'
testData_RouterObject_getDefinedExtraDNS = [
    (255,"",None,[]),
    (0,None,None,[]),
    (0,"",None,[]),
    (0,"uci: Entry not found",[],[]),
    (
        0,
        "dhcp.cfg01522b.address='/bob.lan/172.17.0.99' '/bob2.lan/172.17.0.98'",
        ["'/bob.lan/172.17.0.99'", "'/bob2.lan/172.17.0.98'"],
        ["'/bob.lan/172.17.0.99'", "'/bob2.lan/172.17.0.98'"]
    ),
]

# 'desc, dns, definitions, last, expected'
testData_RouterObject_findDefinitionWithDNS = [
    ( "only last",
        "bob1",
        [],
        ["'/bob1/1.2.3.4'","'/bob2/4.5.6.7'"],
        '/bob1/1.2.3.4'
    ),
    ( "only def",
        "bob2",
        ["'/bob1/1.2.3.4'","'/bob2/4.5.6.7'"],
        [],
        '/bob2/4.5.6.7'
    ),
    ( "not found",
        "bob2",
        ["'/bob1/1.2.3.4'","'/bob3/4.5.6.7'"],
        [],
        ""
    ),
    ( "1 of 2",
        "bob2",
        ["'/bob1/1.2.3.4'","'/bob2/bob2.lan/4.5.6.7'"],
        [],
        '/bob2/bob2.lan/4.5.6.7'
    ),
    ( "2 of 2",
        "bob2.lan",
        ["'/bob1/1.2.3.4'","'/bob2/bob2.lan/4.5.6.7'"],
        [],
        '/bob2/bob2.lan/4.5.6.7'
    ),
    ( "almost",
        "bob2",
        ["'/bob1/1.2.3.4'","'/bob2.lan/4.5.6.7'"],
        [],
        ''
    ),
    ( "Empty",
        "bob2",
        [],
        [],
        ''
    ),
    ( "casein",
        "Bob2",
        ["'/bob1/1.2.3.4'","'/bob2/bob2.lan/4.5.6.7'"],
        [],
        '/bob2/bob2.lan/4.5.6.7'
    ),
    ( "caseout",
        "bob2",
        ["'/bob1/1.2.3.4'","'/Bob2/bob2.lan/4.5.6.7'"],
        [],
        '/Bob2/bob2.lan/4.5.6.7'
    ),
]

# 'desc, definitions, expected'
testData_RouterObject_mappingsFromDefinitions = [
    ( "empty",
        [],
        {
        }
    ),
    ( "single",
        ["'/bob1/1.2.3.4'"],
        {
            'bob1' : '1.2.3.4'
        }
    ),
]

@pytest.mark.parametrize("dict_in,dict_expected", testData_RouterObject_init)
def test_RouterObject_init(dict_in: Dict[str,Any], dict_expected: Dict[str, Any]):
    if 'port' in dict_in and 'identity_file' in dict_in and 'username' in dict_in and 'cmdname' in dict_in:
        testObj = RouterObject(hostname=dict_in['hostname'], port=dict_in['port'],
                                identity_file=dict_in['identity_file'],
                                username=dict_in['username'],
                                cmdname=dict_in['cmdname'])
    elif 'port' in dict_in and 'identity_file' not in dict_in and 'username' not in dict_in and 'cmdname' not in dict_in:
        testObj = RouterObject(hostname=dict_in['hostname'], port=dict_in['port'])
    elif 'port' not in dict_in and 'identity_file' in dict_in and 'username' not in dict_in and 'cmdname' not in dict_in:
        testObj = RouterObject(hostname=dict_in['hostname'],
                                identity_file=dict_in['identity_file'])
    elif 'port' not in dict_in and 'identity_file' not in dict_in and 'username' in dict_in and 'cmdname' not in dict_in:
        testObj = RouterObject(hostname=dict_in['hostname'], 
                                username=dict_in['username'])
    elif 'port' not in dict_in and 'identity_file' not in dict_in and 'username' not in dict_in and 'cmdname' in dict_in:
        testObj = RouterObject(hostname=dict_in['hostname'], cmdname=dict_in['cmdname'])
    elif 'hostname' not in dict_in and 'port' not in dict_in and 'identity_file' not in dict_in and 'username' not in dict_in and 'cmdname' not in dict_in:
        testObj = RouterObject()
    elif 'port' not in dict_in and 'identity_file' not in dict_in and 'username' not in dict_in and 'cmdname' not in dict_in and 'hostname' in dict_in:
        testObj = RouterObject(dict_in['hostname'])
    else:
        # Badly formatted test
        print("Badly formatted test. We should never get here")
        if 'check_bad' in dict_expected:
            assert True
        else:
            assert False
    

    for k in dict_expected:
        if k == 'hostname':
            assert testObj._hostname == dict_expected[k]
        elif k == 'port':
            assert testObj._port == dict_expected[k]
        elif k == 'identity_file':
            #assert testObj._identity_file == dict_expected[k]
            #pkg = pathlib.Path(__package__)
            if dict_expected[k] is None:
                assert testObj._identity_file is None
            else:
                assert pathlib.Path(testObj._identity_file).expanduser().resolve().parts[-1] == pathlib.Path(dict_expected[k]).parts[-1]
        elif k == 'username':
            assert testObj._username == dict_expected[k]
        elif k == 'cmdname':
            if len(dict_expected[k]) > 0 and dict_expected[k] == 'exists':
                assert pathlib.Path(testObj._sshexe).exists()
            else:
                assert pathlib.Path(testObj._sshexe).parts[-1] == pathlib.Path(dict_expected[k]).parts[-1]
            
        elif k == 'ShellCmd':
            assert pathlib.Path(testObj.ShellCmd).parts[-1] == pathlib.Path(dict_expected[k]).parts[-1]

@pytest.mark.parametrize("cmdnamein,expected", testData_RouterObject_setSSHcmd)
def test_RouterObject_setSSHcmd(cmdnamein,expected):
    testObj = RouterObject('hostname')
    testObj.setSSHcmd(cmdnamein)

    assert testObj.ShellCmd == expected

def test_RouterObject_doSSHcmd():
    testObj = RouterObject('hostname', port=1234)
    
    res = testObj.doSSHcmd('command1', doTest=True, testRunReturn=CompletedProcess(args=[], returncode=0))
    assert res.stderr.strip() == "Test: cmd[/usr/bin/ssh root@hostname -p 1234 command1]"

    testObj.setUsername('bob')
    testObj._hostname = 'ahost'
    res = testObj.doSSHcmd('command1 arg1 arg2', doTest=True, testRunReturn=CompletedProcess(args=[], returncode=0))
    assert res.stderr.strip() == "Test: cmd[/usr/bin/ssh bob@ahost -p 1234 command1 arg1 arg2]"

    testObj.setIdentityFile('tests/test_id1')
    testObj._username = ""
    res = testObj.doSSHcmd(['one','two','three'], doTest=True, testRunReturn=CompletedProcess(args=[], returncode=0))
    assert res.stderr.strip() == f"Test: cmd[/usr/bin/ssh ahost -p 1234 -i {pathlib.Path('tests/test_id1').expanduser().resolve()} one two three]"

    testObj._sshexe = None
    try:
        res = testObj.doSSHcmd(['one','two','three'], doTest=True, testRunReturn=CompletedProcess(args=[], returncode=0))
        assert False
    except Exception as e:
        assert isinstance(e, FileNotFoundError)

@pytest.mark.parametrize('errorcode,output,expected_ret,expected_var', testData_RouterObject_getDefinedExtraDNS)
def test_RouterObject_getDefinedExtraDNS(errorcode,output,expected_ret,expected_var):
    testObj = RouterObject('hostname')

    res = testObj.getDefinedExtraDNS(doTest=True, testRunReturn=CompletedProcess(args=[], returncode=errorcode, stdout=output))
    assert res == expected_ret
    assert testObj._lastDefinedExtraDNS == expected_var

@pytest.mark.parametrize('desc, dns, definitions, last, expected', testData_RouterObject_findDefinitionWithDNS)
def test_RouterObject_findDefinitionWithDNS(desc, dns, definitions, last, expected):
    testObj = RouterObject('hostname')

    testObj._lastDefinedExtraDNS = last
    res = testObj.findDefinitionWithDNS(dns,definitions=definitions)

    assert res == expected

@pytest.mark.parametrize('desc, definitions, expected', testData_RouterObject_mappingsFromDefinitions)
def test_RouterObject_mappingsFromDefinitions(desc, definitions, expected):
    testObj = RouterObject('hostname')

    testObj._lastDefinedExtraDNS = []
    res = testObj.mappingsFromDefinitions(definitions=definitions)

    assert res == expected