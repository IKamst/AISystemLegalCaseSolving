import re
from grammar.shared import adjective, preposition
from grammar.shared.keywords import keywords
from parser import Rule, RuleRef, Symbol, passthru, Span
from interpretation import Interpretation
import english
from decorators import memoize


class NounParser(Symbol):
    def __init__(self, is_plural):
        self.is_plural = is_plural

    def __repr__(self):
        return 'NounParser({})'.format('plural' if self.is_plural else 'singular')

    def test(self, literal: str, position: int, state: 'State') -> bool:
        # Is it a name?
        if not literal.islower() and position != 0: 
            return False

        if literal in keywords:
            return False

        # Otherwise, delegate the testing to the English library of hacks.
        if self.is_plural:
            return english.is_plural(literal)
        else:
            return english.is_singular(literal)

    def finish(self, literal: str, position: int, state: 'State'):
        span = super().finish(literal, position, state)
        return Interpretation(local=Noun(span, self.is_plural))


class Noun(object):
    def __init__(self, literal: str, is_plural: bool, adjectives = tuple(), prep_phrase = tuple()):
        self.literal = literal if not is_plural else english.singularize(literal)
        self.is_plural = is_plural
        self.adjectives = adjectives
        self.prep_phrase = prep_phrase

    def __hash__(self):
        return hash(self.literal) + hash(self.is_plural) + hash(self.adjectives) + hash(self.prep_phrase)

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and self.is_same(other, None)

    def __str__(self):
        noun = english.pluralize(self.literal) if self.is_plural else self.literal
        return Span(" ").join(map(Span, self.adjectives + (noun,) + self.prep_phrase))

    def __repr__(self):
        return "Noun({}, {})".format(" ".join(map(str, self.adjectives + (self.literal,) + self.prep_phrase)), self.grammatical_number)

    def text(self, argument):
        if len(self.prep_phrase) > 0 and hasattr(self.prep_phrase[0], 'text'):
            noun = english.pluralize(self.literal) if self.is_plural else self.literal
            return " ".join(map(str, self.adjectives + (noun,) + (self.prep_phrase[0].text(argument),)))
        else:
            return str(self)

    def with_adjective(self, adjective):
        return self.__class__(self.literal, is_plural=self.is_plural, adjectives=(adjective,) + self.adjectives, prep_phrase=self.prep_phrase)

    def with_preposition_phrase(self, preposition_phrase):
        return self.__class__(self.literal, is_plural=self.is_plural, adjectives=self.adjectives, prep_phrase=(preposition_phrase,))

    @property
    def singular(self) -> 'Noun':
        return self if not self.is_plural else self.__class__(self.literal, is_plural=False, adjectives=self.adjectives, prep_phrase=self.prep_phrase)

    @property
    def plural(self) -> 'Noun':
        return self if self.is_plural else self.__class__(self.literal, is_plural=True, adjectives=self.adjectives, prep_phrase=self.prep_phrase)

    @property
    def grammatical_number(self) -> str:
        return 'plural' if self.is_plural else 'singular'

    def is_same(self, other, argument):
        return isinstance(other, self.__class__) \
            and self.literal.lower() == other.literal.lower() \
            and self.is_plural == other.is_plural \
            and self.adjectives == other.adjectives \
            and (\
                self.prep_phrase is None \
                or other.prep_phrase is None \
                or self.prep_phrase == other.prep_phrase \
            )

@memoize
def grammar(**kwargs):
    return adjective.grammar(**kwargs) | preposition.grammar(**kwargs) | {
        # Raw nouns
        Rule("NOUN^", [NounParser(is_plural=False)], passthru),

        Rule("NOUNS^", [NounParser(is_plural=True)], passthru),

        # Nouns without prepositions
        Rule("NOUN", [RuleRef('NOUN^')], passthru),

        Rule("NOUNS", [RuleRef('NOUNS^')], passthru),

        # Nouns with prepositions (the car of (the owner of the building))
        Rule("NOUN", [RuleRef('NOUN^'), RuleRef('PP')],
            lambda state, data: data[1] + Interpretation(local=data[0].local.with_preposition_phrase(data[1].local))),

        Rule("NOUNS", [RuleRef('NOUNS^'), RuleRef('PP')],
            lambda state, data: data[1] + Interpretation(local=data[0].local.with_preposition_phrase(data[1].local))),
        
        Rule("NOUN", [RuleRef('ADJECTIVE'), RuleRef('NOUN')],
            lambda state, data: data[1] + Interpretation(local=data[1].local.with_adjective(data[0].local))),

        Rule("NOUNS", [RuleRef('ADJECTIVE'), RuleRef('NOUNS')],
            lambda state, data: data[1] + Interpretation(local=data[1].local.with_adjective(data[0].local))),

        Rule("NOUN*", [RuleRef('NOUN')], passthru),
        Rule("NOUN*", [RuleRef('NOUNS')], passthru),
    }