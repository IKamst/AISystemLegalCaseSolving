from typing import Any, Dict, Set, List
from argumentation import Argument
import parser
import re


class Rule(parser.Rule):
    def __init__(self, name, symbols, callback = None):
        super().__init__(name, symbols, callback)
        self.callback = lambda state, data: callback(state, data).validated()


class Interpretation(object):
    def __init__(self, argument: Argument = Argument(), local: Any = None):
        self.argument = argument
        self.local = local

    def __add__(self, other: 'Interpretation') -> 'Interpretation':
        return Interpretation(
            argument = self.argument + other.argument,
            local = other.local)

    def __str__(self) -> str:
        return str(self.argument)

    def __repr__(self) -> str:
        return "Interpretation(argument={argument!r} local={local!r})".format(**self.__dict__)

    def validated(self):
        self.argument = self.argument.validated()
        return self
    


class Symbol(parser.Symbol):
    def finish(self, literal: str, position: int, state: parser.State):
        return Interpretation(local=super().finish(literal, position, state))


class Literal(parser.Literal):
    def finish(self, literal: str, position: int, state: parser.State):
        return Interpretation(local=super().finish(literal, position, state))


class Expression(Literal):
    def __init__(self, expression: str) -> None:
        self.expression = re.compile(expression)

    def test(self, literal: str, position: int, state: 'State') -> bool:
        return self.expression.match(literal) is not None

    def __repr__(self) -> str:
        return "/{}/".format(self.expression.pattern)
