"""What the static checker stops, what it lets through, and what it cannot see.

The paper's security discussion rests on a case table, and this file is that
table: each case stands for a class of code, not for a count, and the expected
verdict is what the paper reports. If a rule changes, a case here fails and the
paper's table is what needs another look.

The third group is the honest one. A static rule matches names, so it cannot see
a name built at run time, a module nobody listed, or I/O done by a library the
agent must be allowed to use: pandas reads any path and any URL. That is why the
checker is a first filter and not a security boundary.
Nothing here is executed; a case is only checked.
"""

import pytest

from core.security import SECURITY_CHECKER


def blocked(code: str) -> bool:
    return bool(SECURITY_CHECKER.check_code(code))


ORDINARY_ANALYSIS = {
    "a grouped aggregate": "import pandas as pd\ntotal = df.groupby('state')['deposits'].sum()",
    "numerical work": "import numpy as np\nratio = float(np.mean(values) / np.std(values))",
    "standard-library helpers": (
        "import json, re, math, datetime\n"
        "when = datetime.date(2024, 12, 31)\nfound = re.findall(r'\\d+', text)"),
    # Names and comments that only look like the forbidden ones.
    "a harmless name and comment": "evaluate = 3  # not os.system, not eval\nscore = evaluate + 1",
}

DIRECT_OVERREACH = {
    "a shell command": "import os\nos.system('id')",
    "a subprocess": "import subprocess\nsubprocess.run(['ls'])",
    "a network socket": "import socket\ns = socket.socket()",
    "a file opened directly": "data = open('/etc/hostname').read()",
    "evaluated text": "value = eval('1 + 1')",
    "executed text": "exec('x = 1')",
    "a walk through function internals": "scope = (lambda: 0).__globals__",
    "a walk up the class hierarchy": "kinds = ().__class__.__bases__[0].__subclasses__()",
    "a dynamic import": "import importlib\nmodule = importlib.import_module('os')",
    "the benchmark's answer key": "from evals.some_case import ground_truth",
}

BEYOND_A_STATIC_RULE = {
    # An allowed library that does its own I/O: the rule sees only `import pandas`.
    "a file read through pandas": "import pandas as pd\nrows = pd.read_csv('/etc/hostname')",
    "a URL fetched through pandas": "import pandas as pd\nrows = pd.read_csv('http://example.invalid/x.csv')",
    # A name assembled at run time never appears in the syntax tree.
    "a forbidden name built from pieces": (
        "import builtins\nrun = getattr(builtins, 'ev' + 'al')\nvalue = run('1 + 1')"),
    # A blocklist names what someone thought of.
    "a module nobody listed": "import tempfile\nhandle = tempfile.mkstemp()",
}


@pytest.mark.parametrize("code", ORDINARY_ANALYSIS.values(), ids=ORDINARY_ANALYSIS.keys())
def test_ordinary_analysis_is_let_through(code):
    assert not blocked(code)


@pytest.mark.parametrize("code", DIRECT_OVERREACH.values(), ids=DIRECT_OVERREACH.keys())
def test_direct_overreach_is_stopped(code):
    assert blocked(code)


@pytest.mark.parametrize("code", BEYOND_A_STATIC_RULE.values(), ids=BEYOND_A_STATIC_RULE.keys())
def test_what_a_static_rule_cannot_see_gets_through(code):
    """Recorded as the checker's limit. If one of these starts failing, a rule has
    grown to cover it, and the paper's table should say so."""
    assert not blocked(code)
