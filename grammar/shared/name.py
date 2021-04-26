from parser import Rule, RuleRef, State, passthru
from interpretation import Literal, Symbol, Interpretation
from grammar.macros import and_rules
from decorators import memoize
import re


class NameParser(Symbol):
    def test(self, literal: str, position: int, state: State) -> bool:
        return literal[0].isupper() and literal not in ('He', 'She', 'It', 'They', 'Someone', 'Something')


@memoize
def grammar(**kwargs):
    return and_rules('NAMES', 'NAME', accept_singular=False) | {
        Rule("NAME", [NameParser()], passthru)
    }