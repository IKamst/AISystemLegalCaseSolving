import re
from parser import Rule, passthru
from grammar.shared.keywords import Expression
from decorators import memoize


@memoize
def grammar(**kwargs):
    return {
        Rule("ADJECTIVE", [Expression(r"^\w+$")], passthru)
    }