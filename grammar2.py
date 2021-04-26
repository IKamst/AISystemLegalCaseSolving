import itertools

from parser import parse_syntax, parse_rule, read_sentences, Parser, Rule, State, Symbol, ParseError, indent, flatten, tokenize
from typing import List, Optional, Any, Callable, Union, cast, Set, Dict
from collections import OrderedDict
import re
import copy
import debug
import os.path
from langutil import indefinite_article

logger = debug.Console()


def newline(text):
    return "\n" + text if text else ""


class ArgumentativeDiscourseUnit:
    def __init__(self):
        self.arrows = []

    def __repr__(self):
        lines = []
        if self.arrows:
            lines.append("Supporting/Attacking:")
            lines.extend(map(repr, self.arrows))
        return "\n".join(lines)

    def elements(self) -> Set[Any]:
        # Maybe it is unwise to use a set instead of a list here, as the
        # order does matter!
        return set(itertools.chain(*[arrow.elements() for arrow in self.arrows]))

    def as_tuple(self):
        return {
            "type": "adu",
            "text": str(self),
            "repr": repr(self),
            "args": list(map(lambda el: el.as_tuple(), self.arrows))
        }


class Statement(ArgumentativeDiscourseUnit):
    def __init__(self, a, verb, b):
        super().__init__()
        self.a = a
        self.verb = verb
        self.b = b

    @property
    def subject(self):
        return self.a

    @property
    def object(self):
        return self.b

    def elements(self):
        return {self.a, self.b} | super().elements()

    def __str__(self):
        return "{a} {verb} {b}".format(**self.__dict__)

    def __repr__(self):
        return "Statement({}){}".format(str(self), newline(indent(super().__repr__(), "|\t")))


class RuleStatement(Statement):
    @property
    def premise(self):
        return self.a
    
    @property
    def consequent(self):
        return self.b


class Conjunction(ArgumentativeDiscourseUnit):
    def __init__(self, general: List[Statement] = [], specific: List[Statement] = []):
        super().__init__()
        self.general = general
        self.specific = specific

    def __str__(self):
        adus = self.general + self.specific
        return "{} and {}".format(", ".join(map(str, adus[:-1])) if len(adus) > 2 else adus[0], adus[-1])

    def __repr__(self):
        return "Conjunction({!r})".format(self.general + self.specific)

    def elements(self):
        return set(itertools.chain(*[adu.elements() for adu in self.general + self.specific])) | super().elements()

    def as_tuple(self):
        return {**super().as_tuple(), 'type': 'compound',
                'sources': list(source.as_tuple() for source in self.general + self.specific)}

class Arrow(ArgumentativeDiscourseUnit):
    def __init__(self, sources: List[Statement]):
        super().__init__()
        self.sources = sources

    def elements(self) -> List[Any]:
        return set(itertools.chain(*[src.elements() for src in self.sources])) | super().elements()

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, ", ".join(map(str, self.sources)))

    def __repr__(self):
        return "{}{}".format(str(self), newline(indent(super().__repr__(), "+\t")))

    def as_tuple(self):
        return {**super().as_tuple(), 'type': 'undefarrow', 'sources': [src.as_tuple() for src in self.sources]}


class Attack(Arrow):
    def as_tuple(self):
        return {**super().as_tuple(), 'type': 'attack'}


class Support(Arrow):
    def as_tuple(self):
        return {**super().as_tuple(), 'type': 'support'}


class Negation(ArgumentativeDiscourseUnit):
    def __init__(self, statement):
        #super().__init__() // Don't call super.init since we've overridden the arrows attribute!
        self.statement = statement

    def elements(self):
        return self.statement.elements() | super().elements()

    def __str__(self):
        return "¬{}".format(str(self.statement))

    def __repr__(self):
        return "¬{}".format(repr(self.statement))

    @property
    def arrows(self):
        return self.statement.arrows


def find_sentences(parse):
    return [parse] + flatten(map(find_sentences, parse.arrows))


def attack(statement, args):
    state_copy = copy.deepcopy(statement)
    state_copy.arrows.append(Attack(args))
    return state_copy


def support(statement, args):
    state_copy = copy.deepcopy(statement)
    state_copy.arrows.append(Support(args))
    return state_copy


def _unused_support_with_rule(statement, rule: RuleStatement, args: List[Statement]):
    # Say we have the following case:
    #
    #   statement = Henry can fly
    #   rule = birds can fly
    #   args = [Henry is a bird, Henry is cool]
    #
    # Then, the support which supports the rule need
    # to have the same subject as the statement, and
    # the rhs of the statement has to be the consequent
    # of the rule. The rhs of the support has to be the
    # premise of the rule.

    if not statement.object.is_same(rule.consequent):
        print("Statement's object ({!r}) is not equal to the rule's consequent ({!r}).".format(statement.object, rule.consequent))
        return Parser.FAIL

    rule_supported = False

    for support in args:
        if support.subject.is_same(statement.subject):
            if support.object.is_same(rule.premise):
                rule_supported = True
            else:
                print("Same subjects, but premise ({!r}) does not match object ({!r}).".format(rule.premise, support.object))

    if not rule_supported:
        print("Rule premise ({!r}) not supported.".format(rule.premise))
        return Parser.FAIL

    support_arrow = Support(args)
    support_arrow.arrows.append(Support([rule]))
    state_copy = copy.deepcopy(statement)
    state_copy.arrows.append(support_arrow)
    return state_copy


def support_with_rule(statement, rule: RuleStatement, args: List[Statement]):
    # Say we have the following case:
    #
    #   statement = Henry can fly
    #   rule = birds can fly
    #   args = [Henry is a bird, Henry is cool]
    #
    # Then, the support which supports the rule need
    # to have the same subject as the statement, and
    # the rhs of the statement has to be the consequent
    # of the rule. The rhs of the support has to be the
    # premise of the rule.

    if not statement.object.is_same(rule.consequent):
        print("Statement's object ({!r}) is not equal to the rule's consequent ({!r}).".format(statement.object, rule.consequent))
        return Parser.FAIL

    
    state_copy = copy.deepcopy(statement)
    
    rule_supported = False

    for support in args:
        support_arrow = Support([support])
        state_copy.arrows.append(support_arrow)

        if support.subject.is_same(statement.subject):
            if support.object.is_same(rule.premise):
                support_arrow.arrows.append(Support([rule]))
                rule_supported = True
            else:
                print("Same subjects, but premise ({!r}) does not match object ({!r}).".format(rule.premise, support.object))

    if not rule_supported:
        print("Rule premise ({!r}) not supported.".format(rule.premise))
        return Parser.FAIL

    return state_copy


def passthru(state, data):
    return data[0]


def noop(state, data):
    return 'empty'


class Instance(object):
    def __init__(self, name: str = None, noun: str = None, pronoun: str = None, origin: 'Instance' = None):
        self.name = name
        self.noun = noun
        self.pronoun = pronoun
        self.origin = origin

    def __str__(self):
        if self.name is not None:
            return self.name
        if self.noun is not None:
            return "the {}".format(self.noun)
        else:
            return "(instance)"

    def __repr__(self):
        return "Instance({})".format(" ".join("{}={}".format(k, v) for k,v in self.__dict__.items() if v is not None))

    def is_same(self, other):
        are_same_individuals = self.replaces(other) or other.replaces(self)
        print("Comparing {!r} and {!r}: {!r}".format(self, other, are_same_individuals))
        return are_same_individuals

    def replaces(self, instance: 'Instance') -> bool:
        """
        Test whether this instance is an updated version of the supplied instance.
        :param instance: the supposed origin of this instance
        :return: whether this instance is a more accurate version of the supplied instance
        """
        previous = self.origin
        while previous is not None:
            if previous == instance:
                return True
            previous = previous.origin
        return False

    def update(self, name: str = None, noun: str = None, pronoun: str = None) -> 'Instance':
        return Instance(
            name=name if name is not None else self.name,
            noun=noun if noun is not None else self.noun,
            pronoun=pronoun if pronoun is not None else self.pronoun,
            origin=self)


class InstanceList(object):
    @classmethod
    def from_state(cls, state: State) -> 'InstanceList':
        instances = cls()
        for adu in state.data:
            if isinstance(adu, ArgumentativeDiscourseUnit):
                for item in adu.elements():
                    if isinstance(item, Instance) and item not in instances:
                        instances.append(item)
        if state.parent:
            instances.extend(InstanceList.from_state(state.parent))
        return instances

    def __init__(self):
        self.instances = list() # type: List[Instance]

    def __iter__(self):
        return self.instances.__iter__()

    def __len__(self):
        return len(self.instances)

    def append(self, new_instance: Instance):
        for known_instance in self.instances:
            if new_instance.replaces(known_instance):
                self.instances.remove(known_instance)
                break
            if known_instance.replaces(new_instance):
                logger.warn("Trying to add an instance ({!r}) of which already a more specific one ({!r}) is known. "
                            "Ignoring new instance.".format(new_instance, known_instance))
                return
        self.instances.append(new_instance)

    def extend(self, instances: 'InstanceList'):
        for instance in instances:
            self.append(instance)


def find_instance_by_name(state: State, name: str) -> Instance:
    """
    We've received a name, and now we want to link this to an existing instance
    with the same name, or create a new instance.
    :param state:
    :param name:
    :return:
    """
    for instance in InstanceList.from_state(state):
        if instance.name == name:
            return instance
    return Instance(name=name)


def find_instance_by_pronoun(state: State, pronoun: str) -> Instance:
    instances = InstanceList.from_state(state)
    # First of all, we assume the pronoun refers to at least something
    if len(instances) == 0:
        raise Exception("Cannot figure out where '{}' refers to".format(pronoun))
    # Then, we assume that the pronoun refers to the last mentioned instance
    for instance in instances:
        if instance.pronoun == pronoun:
            return instance
        if instance.pronoun is None:
            return instance.update(pronoun=pronoun)


def find_instance_by_noun(state: State, noun: str) -> Instance:
    for instance in InstanceList.from_state(state):
        if instance.noun == noun:
            return instance
    return Instance(noun=noun)


grammar = [
    ("START ::= S .", passthru),
    ("S ::= STMT", passthru),
    ("STMT ::= GENERAL", passthru),
    ("STMT ::= SPECIFIC", passthru),
    
    # ("S ::= S but S", lambda state, data: attack(data[0], data[2])),
    ("S ::= S because SPECIFIC", lambda state, data: support(data[0], args=[data[2]])),
    ("S ::= S because SCON", lambda state, data: support(data[0], args=data[2].specific)),
    
    ("S ::= S because GCON", lambda state, data: support_with_rule(data[0], rule=data[2].general[0], args=data[2].specific)),
    # ("S ::= S because GCON", lambda state, data: _unused_support_with_rule(data[0], rule=data[2].general[0], args=data[2].specific)),
    # ("S ::= S because S and because S", lambda state, data: support(data[0], data[2], data[5])),
    
    ("GCON ::= GENERAL and SPECIFIC", lambda state, data: Conjunction(general=[data[0]], specific=[data[2]])),
    ("GCON ::= SPECIFIC and GENERAL", lambda state, data: Conjunction(specific=[data[0]], general=[data[2]])),
    ("GCON ::= GENERAL , SCON", lambda state, data: Conjunction(general=[data[0]], specific=data[2].specific)),
    ("GCON ::= SPECIFIC , GCON", lambda state, data: Conjunction(general=data[2].general, specific=[data[0]] + data[2].specific)),

    ("SCON ::= SPECIFIC and SPECIFIC", lambda state, data: Conjunction(specific=[data[0], data[2]])),
    ("SCON ::= SPECIFIC , SCON", lambda state, data: Conjunction(specific=[data[0]] + data[2].specific)),

    ("SPECIFIC ::= INSTANCE is TYPE", lambda state, data: Statement(data[0], "is", data[2])),
    ("SPECIFIC ::= INSTANCE is VERB_NOUN", lambda state, data: Statement(data[0], "is", data[2])),
    ("SPECIFIC ::= INSTANCE is not TYPE", lambda state, data: Negation(Statement(data[0], "is", data[3]))),
    ("SPECIFIC ::= INSTANCE has TYPES", lambda state, data: Statement(data[0], "has", data[2])),
    ("TYPE ::= a NOUN", lambda state, data: data[1]),
    ("TYPE ::= an NOUN", lambda state, data: data[1]),
    ("TYPES ::= NOUNS", lambda state, data: data[0]),
    ("SPECIFIC ::= INSTANCE can VERB_INF", lambda state, data: Statement(data[0], "can", data[2])),
    ("GENERAL ::= VERB_NOUN is VERB_NOUN", lambda state, data: RuleStatement(data[0], "is", data[2])),
    ("GENERAL ::= TYPES are TYPES", lambda state, data: RuleStatement(data[0], "are", data[2])),
    ("GENERAL ::= TYPES are VERB_NOUN", lambda state, data: RuleStatement(data[0], "are", data[2])),
    ("GENERAL ::= TYPES can VERB_INF", lambda state, data: RuleStatement(data[0], "can", data[2])),
    ("GENERAL ::= TYPES have TYPES", lambda state, data: RuleStatement(data[0], "have", data[2])),
    ("GENERAL ::= TYPE can VERB_INF", lambda state, data: RuleStatement(data[0], "can", data[2])),
    ("GENERAL ::= TYPE is VERB_NOUN", lambda state, data: RuleStatement(data[0], "is", data[2])),
    ("GENERAL ::= TYPE is TYPE", lambda state, data: RuleStatement(data[0], "is", data[2])),
    ("SPECIFIC ::= INSTANCE can not VERB_INF", lambda state, data: Negation(Statement(data[0], "can", data[3]))),
    ("GENERAL ::= TYPES can not VERB_INF", lambda state, data: Negation(RuleStatement(data[0], "can", data[3]))),
    ("INSTANCE ::= NAME", lambda state, data: find_instance_by_name(state, data[0])),
    ("INSTANCE ::= PRONOUN", lambda state, data: find_instance_by_pronoun(state, data[0])),
    ("INSTANCE ::= the NOUN", lambda state, data: find_instance_by_noun(state, data[1])),
]

sentence_files = [os.path.join(os.path.dirname(__file__), 'sentences.txt')]
sentences = OrderedDict()

for sentence_file in sentence_files:
    with open(sentence_file, 'r') as fh:
        sentences.update(read_sentences(fh))


class NounSymbol(Symbol):
    def __init__(self, plural):
        self.plural = plural

    def test(self, literal: str, position: int, state: 'State') -> bool:
        if not literal.islower() and position != 0:
            return False
        if self.plural and literal[-1] != 's':
            return False
        return True

    def finish(self, literal: str, state: 'State'):
        return Noun(literal, self.plural)

    


class Noun(object):
    def __init__(self, literal: str, plural: bool):
        self.literal = literal
        self.plural = plural

    def singular(self) -> str:
        word = self.literal
        if self.plural:
            word = re.sub('(e?s)$', '', word)  # Strip 'es' from thieves
            word = re.sub('v$', 'f', word)  # Replace 'v' in 'thiev' with 'f'
        return word

    def is_same(self, other):
        return self.singular() == other.singular()

    def __str__(self):
        if self.plural:
            return self.literal
        else:
            return "{} {}".format(indefinite_article(self.literal), self.literal)

    def __repr__(self):
        return "Noun({})".format(self.literal)


class Verb(object):
    def __init__(self, literal: str):
        self.literal = literal

    def is_same(self, other):
        print("Verb: comparing {!r} to {!r}".format(self.literal, other.literal))
        return self.literal == other.literal

    def __str__(self):
        return self.literal

    def __repr__(self):
        return "Verb({})".format(self.literal)


class NameSymbol(Symbol):
    def test(self, literal: str, position: int, state: State) -> bool:
        return literal[0].isupper()


class PronounSymbol(Symbol):
    def test(self, literal: str, position: int, state: State) -> bool:
        return literal in ('he', 'she', 'it')


class ReSymbol(Symbol):
    def __init__(self, pattern: str, negate=False) -> None:
        self.pattern = re.compile(pattern)
        self.negate = negate

    def test(self, literal: str, position: int, state: State) -> bool:
        accept = re.match(self.pattern, literal) is not None
        return not accept if self.negate else accept

    def __repr__(self):
        return "ReSymbol({}{!r})".format("¬" if self.negate else "", self.pattern)


rules = list(parse_rule(expression, callback) for expression, callback in grammar)

rules += [
    Rule("NOUN", [NounSymbol(plural=False)], passthru),
    Rule("NOUNS", [NounSymbol(plural=True)], passthru),
    Rule("NAME", [NameSymbol()], lambda state, data: data[0]),
    Rule("PRONOUN", [PronounSymbol()], lambda state, data: data[0]),
    Rule("VERB_INF", [ReSymbol(r'^\w+([^e]ed|ing|able)$', negate=True)], lambda state, data: Verb(data[0])),
    Rule("VERB_NOUN", [ReSymbol(r'^\w+([^e]ed|ing|able)$')], lambda state, data: Verb(data[0]))
]

start = "START"

Operation = ArgumentativeDiscourseUnit  # for compatibility for now

if __name__ == '__main__':
    try:
        for sentence in sentences[:4]:
            parser = Parser(rules, start)
            tokens = tokenize(sentence)
            output = parser.parse(tokens)
            print(sentence)
            for i, parsing in enumerate(output):
                print("{}: {}".format(i + 1, repr(parsing)))
                print("Summary:")
                print("\n".join(map(str, find_sentences(parsing))))
    except ParseError as e:
        print(repr(e))
