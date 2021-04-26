#!/usr/bin/env python3

# Based on https://github.com/Hardmath123/nearley/blob/master/lib/nearley.js
import operator
from typing import List, Optional, Any, Callable, Union, cast
from collections import OrderedDict
import codecs
import functools
import re
import inspect
import os

import traceback

def log(line: str) -> None:
    pass


def flatten(lists):
    out = []
    for list in lists:
        out.extend(list)
    return out


def indent(text: str, indent: str = "\t"):
    return "\n".join((indent + line for line in text.split("\n"))) if text else ""


def passthru(state, data):
    return data[0]


class Continue(Exception):
    pass


class ParseError(Exception):
    def __init__(self, position: int, token: str, sentence: List[str] = None, expected: List[str] = None):
        self.position = position
        self.token = token
        self.sentence = sentence
        super().__init__("No possible parse for '{}' (at position {}){}".format(token, position + 1,
            ", expected:\n  " + "\n  | ".join(expected) if expected is not None else ""))

    def __repr__(self) -> str:
        return "{}\n{}\n{}{}{}{}".format(
            super().__repr__(),
            " ".join(self.sentence),
            " " * len(" ".join(self.sentence[0:self.position])),
            " " if self.position > 0 else "",
            "^" * len(self.sentence[self.position]),
            " " * len(" ".join(self.sentence[self.position + 1:])))


class RuleParseException(Exception):
    pass


class Span(str):
    """
    Behaves like a string, but has a start and end position of where it occurred
    in the text it originates from.
    """

    def __new__(cls, value, *args, **kwargs):
        return super(Span, cls).__new__(cls, value)

    def __init__(self, string: str, start: int = None, end: int = None):
        if isinstance(string, self.__class__):
            start = string.start
            end = string.end
        assert (start is None and end is None) or start < end
        self.start = start
        self.end = end

    def __repr__(self):
        return "Span({start}, {end}, {super})".format(start=self.start, end=self.end, super=super().__repr__())

    def __hash__(self):
        return hash(str(self))

    def __add__(self, other):
        if self.start is not None and other.end is not None and self.start > other.end:
            raise Exception('Cannot two spans that are not adjacent to each other')
        return Span(super().__add__(other),
            self.start if self.start is not None else other.start,
            other.end if other.end is not None else self.end)

    def before(self, other):
        if not isinstance(other, self.__class__):
            other = other.__str__()
        if self.start is None or other.start is None:
            return None
        return self.start < other.start

    def after(self, other):
        if not isinstance(other, self.__class__):
            other = other.__str__()
        if self.end is None or other.end is None:
            return None
        return self.start >= other.end

    def lower(self):
        return Span(super().lower(), self.start, self.end)

    def join(self, spans: List['Span']):
        it = iter(spans)
        acc = next(it)
        while True:
            try:
                acc = acc + self + next(it)
            except StopIteration:
                break
        return acc


def test_span():
    assert Span('Hele grote woorden', 0, 3) == 'Hele grote woorden'
    assert Span('Hele grote woorden', 0, 3).lower().end == 3
    assert Span('Hele grote woorden', 0, 3) == Span('Hele grote woorden', 3, 6)
    assert Span('Hele grote woorden', 0, 3) in ('x', 'Hele grote woorden')
    assert Span(':').join([Span('a', 0, 1), Span('b', 1, 2), Span('c', 2, 3)]) == Span('a:b:c', 0, 3)
    assert Span(':').join([Span('a', 0, 1), Span('b', 1, 2), Span('c', 2, 3)]).start == 0
    assert Span(':').join([Span('a', 0, 1), Span('b', 1, 2), Span('c', 2, 3)]).end == 3

test_span()

class Symbol:
    def test(self, literal: str, position: int, state: 'State') -> bool:
        raise NotImplementedError("Symbol.test is abstract")

    def finish(self, literal: str, position: int, state: 'State'):
        return Span(literal, position, position + 1)


class Literal(Symbol):
    def __init__(self, literal: str) -> None:
        self.literal = literal

    def test(self, literal: str, position: int, state: 'State') -> bool:
        return self.literal == literal

    def __repr__(self) -> str:
        return "\"{}\"".format(self.literal)


class RuleRef(Symbol):
    def __init__(self, name: str) -> None:
        self.name = name

    def test(self, literal: str, position: int, state: 'State') -> bool:
        return False

    def __repr__(self, with_cursor_at: int = None) -> str:
        return "{}".format(self.name)


class Rule:
    def __init__(self, name: str, symbols: List[Symbol], callback: Optional[Callable[[Any, int], Any]] = None, file=None, line=None) -> None:
        self.name = name
        self.symbols = symbols
        if callback is not None:
            self.callback = callback
        else:
            self.callback = lambda state, data: RuleInstance(self, data)  # flatten(data)
        if file is not None or line is not None:
            self.file = file
            self.line = line
        else:
            previous_frame = inspect.currentframe().f_back
            (filename, line_number, function_name, lines, index) = inspect.getframeinfo(previous_frame)
            self.file = filename
            self.line = line_number
        
    def __repr__(self, with_cursor_at: int = None) -> str:
        if with_cursor_at is not None:
            return "{} ⇒ {} ● {}".format(
                self.name,
                " ".join(map(repr, self.symbols[:with_cursor_at])),
                " ".join(map(repr, self.symbols[with_cursor_at:])))
        else:
            return "{} ⇒ {}".format(self.name, " ".join(map(repr, self.symbols)))

    @property
    def tooltip(self):
        return "{file}: {line}\n{repr}".format(
            file=os.path.relpath(self.file, os.path.dirname(__file__)),
            line=self.line,
            repr=repr(self))

    def consume(self, state: 'State'):
        return self

    def finish(self, state: 'State', data: List[Any]) -> Any:
        log("!!! Finishing {} with data {} and reference {}!".format(self.name, state.data, state.reference))
        try:
            return self.callback(state, data)
        except Exception as e:
            if isinstance(e, Continue):
                print("1111111")
                raise e
            else:
                print("222222")
                raise Exception('Error while trying to finish the rule {!r}'.format(self)) from e


class RuleInstance:
    def __init__(self, rule: Rule, data: List[Any]):
        self.rule = rule
        self.data = data

    def __repr__(self):
        if len(self.data) > 0:
            return "[{}:\n{}\n]".format(self.rule.name, indent("\n".join(map(repr, self.data))))
        else:
            return "[{}: (empty)]".format(self.rule.name)


class State:
    def __init__(self, rule: Rule, expect: int, reference: int) -> None:
        assert len(rule.symbols) > 0
        self.rule = rule
        self.expect = expect
        self.reference = reference
        self.inp = []
        self.data = []  # type: List[Any]
        self.trace = []
        self.error = None

    def __repr__(self) -> str:
        return "{rule}, from: {ref} (data:{data!r})".format(rule=self.rule.__repr__(self.expect), ref=self.reference, data=self.data)

    def __eq__(self, other) -> bool:
        return self.rule is other.rule \
            and self.expect == other.expect \
            and self.reference == other.reference \
            and self.trace == other.trace

    @property
    def tree(self):
        return {
            'label': self.rule.name,
            'tooltip': self.rule.tooltip,
            # 'data': self.data,
            'nodes': [child.tree if isinstance(child, State) else {'label': child} for child in self.inp]
        }


    def nextState(self, inp, data, trace) -> 'State':
        state = State(self.rule, self.expect + 1, self.reference)
        state.inp = self.inp + inp
        state.data = self.data + [data]
        state.trace = trace + self.trace
        return state

    def consumeTerminal(self, inp: str, token_pos: int) -> Optional['State']:
        log("consumeTerminal {} using {} expecting {}".format(inp, self.rule, self.rule.symbols[self.expect] if len(
            self.rule.symbols) > self.expect else '>END<'))
        if len(self.rule.symbols) > self.expect and self.rule.symbols[self.expect].test(inp, token_pos, self):
            log("Terminal consumed")
            try:
                return self.nextState([inp], self.rule.symbols[self.expect].finish(inp, token_pos, self), ['Consume terminal {!r}({}) with {!r}'.format(inp, token_pos, self.rule.symbols[self.expect])])
            except Exception as e:
                raise Exception('Exception while trying to consume {!r} with {!r}'.format(inp, self.rule.symbols[self.expect])) from e
        else:
            return None

    def consumeNonTerminal(self, inp: Rule) -> Optional['State']:
        assert isinstance(inp, Rule)
        if len(self.rule.symbols) > self.expect \
                and isinstance(self.rule.symbols[self.expect], RuleRef) \
                and self.rule.symbols[self.expect].name == inp.name:
            return self.nextState([], inp.consume(self), ['{!r}: Consume non-terminal {!r}'.format(self.rule.__repr__(self.expect), inp)])
        else:
            return None

    def process(self, location, table: List[List['State']], rules: List[Rule], added_rules: List[Rule]) -> None:
        if self.expect == len(self.rule.symbols):
            # We have a completed rule
            self.data = self.rule.finish(self, self.data)
            self.trace.insert(0, 'Finish rule {!r}'.format(self.rule))

            w = 0
            # We need a while here because the empty rule will modify table[reference] when location == reference
            while w < len(table[self.reference]):
                state = table[self.reference][w]
                next_state = state.consumeNonTerminal(self.rule)
                if next_state is not None:
                    next_state.data[-1] = self.data
                    next_state.inp.append(self)
                    next_state.trace = self.trace + next_state.trace
                    table[location].append(next_state)
                w += 1

                # --- The comment below is OUTDATED. It's left so that future
                # editors know not to try and do that.

                # Remove this rule from "addedRules" so that another one can be
                # added if some future added rule requires it.
                # Note: I can be optimized by someone clever and not-lazy. Somehow
                # queue rules so that everything that this completion "spawns" can
                # affect the rest of the rules yet-to-be-added-to-the-table.
                # Maybe.

                # I repeat, this is a *bad* idea.

                # var i = addedRules.indexOf(this.rule);
                # if (i !== -1) {
                #     addedRules.splice(i, 1);
                # }
        else:
            # in case I missed an older nullable's sweep, update yourself. See
            # above context for why this makes sense
            ind = table[location].index(self)
            for i in range(ind):
                state = table[location][i]
                if len(state.rule.symbols) == state.expect and state.reference == location:
                    raise NotImplementedError("Code should not reach this place because we don't do nullables")
                    x = self.consumeNonTerminal(state.rule)
                    if x is not None:
                        x.data[-1] = state.data
                        x.trace = state.trace + x.trace
                        table[location].append(x)

            # I'm not done, but I can predict something
            expected_symbol = self.rule.symbols[self.expect]

            if isinstance(expected_symbol, RuleRef):
                for rule in rules:
                    if rule.name == expected_symbol.name and rule not in added_rules:
                        # Make a note that you've added it already, and don't need to
                        # add it again; otherwise left recursive rules are going to go
                        # into an infinite loop by adding themselves over and over
                        # again.

                        # If it's the null rule, however, you don't do this because it
                        # affects the current table row, so you might need it to be
                        # called again later. Instead, I just insert a copy whose
                        # state has been advanced one position (since that's all the
                        # null rule means anyway)
                        if len(rule.symbols) > 0:
                            added_rules.append(rule)
                            table[location].append(State(rule, 0, location))
                        else:
                            # Empty rule, this is special
                            copy = self.consumeNonTerminal(rule)
                            copy.data[-1] = rule.finish(self, [])
                            table[location].append(copy)


class Parser:
    FAIL = {}  # type: Any

    def __init__(self, rules: List[Rule], start: str) -> None:
        self.rules = rules
        self.start = start
        self.table = []  # type: List[List[State]] (first index is token, second index is possible state)
        self.results = []  # type: List[Any]
        self.current = 0
        self.reset()

    def __repr__(self) -> str:
        rules = map(repr, self.rules)
        table = ["{}: {}".format(n, "\n   ".join(map(repr, level))) for n, level in enumerate(self.table)]
        return "Rules:\n{}\nTable:\n{}\n".format("\n".join(rules), "\n".join(table))

    def reset(self) -> None:
        # Clear previous work
        self.results = []
        self.current = 0

        # Setup a table
        added_rules = []
        self.table = [[]]

        # Prepare the table with all rules that match the start name
        for rule in self.rules:
            if rule.name == self.start:
                added_rules.append(rule)
                self.table[0].append(State(rule, 0, 0))
        self.advanceTo(0, added_rules)

    def advanceTo(self, position: int, added_rules: List[Rule]) -> None:
        w = 0
        while w < len(self.table[position]):
            try:
                self.table[position][w].process(position, self.table, self.rules, added_rules)
            except Continue:
                pass
            w += 1

    def feed(self, chunk) -> None:
        for token_pos, token in enumerate(chunk):
            # We add anew states to table[current + 1]
            self.table.append([])

            # Advance all tokens that expect the symbol
            # So for each state in the previous row,

            w = 0
            while w < len(self.table[self.current + token_pos]):
                current_state = self.table[self.current + token_pos][w]
                next_state = current_state.consumeTerminal(token, token_pos)
                if next_state is not None:
                    self.table[self.current + token_pos + 1].append(next_state)
                w += 1

            # Are there duplicates?
            t = self.table[self.current + token_pos + 1] 
            for i, left in enumerate(t):
                for right in t[i+1:]:
                    if left == right:
                        t[i] = None
                        break
            self.table[self.current + token_pos + 1] = list(filter(lambda s: s is not None, t))

            # Next, for each of the rules, we either
            # (a) complete it, and try to see if the reference row expected that rule
            # (b) predict the next nonterminal it expects by adding that nonterminal's stat state
            # To prevent duplication, we also keep track of rules we have already added.

            added_rules = []  # type: List[Rule]
            self.advanceTo(self.current + token_pos + 1, added_rules)

            # If needed, throw an error
            if len(self.table[-1]) == 0:
                # No states at all! This is not good
                # print(self.table)
                raise ParseError(self.current + token_pos, token, sentence=chunk,
                    expected=[str(state.rule.symbols[state.expect] \
                        if len(state.rule.symbols) < state.expect \
                        else "{}".format(state.rule)) for state in self.table[-2]])

        self.current += len(chunk)

        # Incrementally keep track of results
        self.results = self.finish()

    def finish(self) -> List[List[Any]]:
        # Return the possible parsings
        return [dict(data=state.data, trace=list(reversed(state.trace)), tree=state.tree) for state in self.table[-1] if
                state.rule.name == self.start
                and state.expect == len(state.rule.symbols)
                and state.reference == 0
                and state.data is not self.FAIL]

    def parse(self, chunk: List[str]) -> List[State]:
        self.reset()
        self.feed(chunk)
        return self.results


def tokenize(sentence: str) -> List[str]:
    return re.compile(r'\w+|\$[\d\.\;]+|\S+').findall(sentence)


def parse_rule(line: str, callback: Optional[Callable[[Any, int], Any]] = None) -> Rule:
    match = re.match(r'^(?P<name>\w+) ::= (?P<antecedent>.*)$', line)
    if match is None:
        raise RuleParseException("Cannot parse {}".format(line))

    antecedent = []  # type: List[Symbol]
    tokens = match.group("antecedent").split(" ")
    for token in tokens:
        if token.isupper():
            antecedent.append(RuleRef(token))
        elif token != "":
            antecedent.append(Literal(token))

    return Rule(match.group("name"), antecedent, callback)


def parse_syntax(syntax: str) -> List[Rule]:
    rules = []
    for i, line in enumerate(syntax.splitlines()):
        if line == "":
            continue

        try:
            rules.append(parse_rule(line))
        except RuleParseException as e:
            raise RuleParseException("{} (line {})".format(str(e), i))

    return rules


def read_sentences(path):
    if path.endswith('.tex'):
        reader = read_sentences_tex
    else:
        reader = read_sentences_txt

    with codecs.open(path, encoding='utf-8') as fh:
        return reader(fh)


def read_sentences_txt(fh):
    sections = OrderedDict()
    section = None
    
    for line in fh:
        if line.startswith('#'):
            section = line[1:].strip()
            if section not in sections:
                sections[section] = list()
        elif len(line.strip()) > 0:
            sections[section].append(line.strip())

    return sections


def read_sentences_tex(fh):
    sections = OrderedDict()
    section = None

    for line in fh:
        match = re.match(r'^\\subsubsection\{(.+?)\}\s*$', line)
        if match:
            section = match.group(1)
            sections[section] = OrderedDict()
            continue

        match = re.match(r'\s*\\ex\s*\\label\{(.+?)\}\s*(.+?)\s*$', line)
        if match:
            sections[section][match.group(1)] = match.group(2).replace('\\\\', '')
            continue

    return sections


if __name__ == '__main__':
    import traceback
    import sys

    # Test simple literals
    # p = Parser([Rule('START', [Literal('a'), Literal('b'), Literal('c')])], 'START')
    # assert len(p.parse(['a', 'b', 'c'])) == 1

    class Digit(Symbol):
        def test(self, literal: str, position: int, state: 'State') -> bool:
            return literal.isdigit()


    class Alpha(Symbol):
        def test(self, literal: str, position: int, state: 'State') -> bool:
            return literal.isalpha()


    def test_left_recursion():
        """Test left recursion"""
        p = Parser([
            Rule('A', [RuleRef('A'), Literal('A')]),
            Rule('A', [Literal('A')]),
        ], 'A')
        print(p.parse(list('AAAA')))

    def test_right_recursion():
        """Test right recursion"""
        p = Parser([
            Rule('A', [Literal('A'), RuleRef('A')]),
            Rule('A', [Literal('A')]),
        ], 'A')
        print(p.parse(list('AAAA')))


    def test_nested_left_recursion():
        """Test nested left recursion"""
        p = Parser([
            Rule('X', [Literal('0'), RuleRef('A'), Literal('1')]),
            Rule('A', [Literal('A'), RuleRef('A')]),
            Rule('A', [Literal('A')]),
        ], 'X')
        print(p.parse(list('0AAAA1')))


    def test_custom_literal():
        """Test custom literal"""
        p = Parser([
            Rule('A', [RuleRef('A'), Digit()]),
            Rule('A', [Literal('A')]),
        ], 'A')
        print(p.parse(list('A1234')))

    def test_empty_rule():
        """Test recursion and the empty rule"""
        p = Parser([
            Rule('START', [RuleRef('AB')]),
            Rule('AB', [Literal('A'), RuleRef('AB'), Literal('B')]),
            Rule('AB', [])
        ], 'START')
        print(p.parse(list('AAABBB')))

    if len(sys.argv) > 1:
        tests = [globals()[arg] for arg in sys.argv[1:]]
    else:
        tests = [value for name, value in dict(globals()).items() if name.startswith('test_') and callable(value)]

    for test in tests:
        print("{}: {}".format(test.__name__, test.__doc__))
        try:
            test()
        except:
            traceback.print_exc(file=sys.stderr)
        print("\n")

    print("Done.")
