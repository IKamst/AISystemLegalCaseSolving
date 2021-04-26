from typing import Set, Optional
from parser import Rule, Literal, RuleRef
from interpretation import Interpretation
from datastructures import OrderedSet
from decorators import memoize


@memoize
def and_rules(name: str, singleton: str, accept_singular: bool = False, first_singleton: Optional[str] = None, last_singleton: Optional[str] = None) -> Set[Rule]:
    """
    Creates a mini-grammar of rules that are needed to parse 'A and B',
    'A, B and C', 'A, B, C and D', etc. where A, B, C and D all are parseable
    using the rule name passed using the singleton argument.

    Grammar:

        <As> ::= A_helper `and' A_last
        <A_helper> ::= A_helper `,' A
        <A_helper> ::= A_first
        <As> ::= A
    
    """
    if last_singleton is None:
        last_singleton = singleton

    if first_singleton is None:
        first_singleton = singleton

    helper = name + "_"
    
    rules = {
        # _ and C
        Rule(name, [RuleRef(helper), Literal('and'), RuleRef(last_singleton)],
            lambda state, data: data[0] + data[2] + Interpretation(local=data[0].local | OrderedSet([data[2].local]))),

        # A, B # (allows for 'A, B and C')
        Rule(helper, [RuleRef(helper), Literal(','), RuleRef(singleton)],
            lambda state, data: data[0] + data[2] + Interpretation(local=data[0].local | OrderedSet([data[2].local]))),

        # A (allows for 'A and B')
        Rule(helper, [RuleRef(first_singleton)],
            lambda state, data: data[0] + Interpretation(local=OrderedSet([data[0].local])))
    }

    if accept_singular:
        rules |= {
            Rule(name, [RuleRef(singleton)],
                lambda state, data: data[0] + Interpretation(local=OrderedSet([data[0].local])))
        }

    return rules