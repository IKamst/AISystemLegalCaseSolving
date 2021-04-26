from grammar.shared import prototype, verb
from interpretation import Interpretation, Symbol
from parser import Rule, RuleRef, passthru
from decorators import memoize


class PrepositionPhrase(object):
    def __init__(self, preposition, prep_object):
        self.preposition = preposition
        self.object = prep_object

    def __hash__(self):
        return hash(self.preposition) + hash(self.object)

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and self.preposition == other.preposition \
            and self.object == other.object
    
    def __str__(self):
        return "{!s} {!s}".format(self.preposition, self.object)

    def __repr__(self):
        return "PP({!r} {!r})".format(self.preposition, self.object)

    def text(self, argument):
        return "{!s} {!s}".format(self.preposition, self.object.text(argument))

    def is_same(self, other, argument):
        return isinstance(other, PrepositionPhrase) \
            and self.preposition == other.preposition \
            and (self.object.is_same(other.object, argument) if hasattr(self.object, 'is_same') else self.object == other.object)

    @property
    def singular(self):
        return self

    @property
    def plural(self):
        return self


prepositions = frozenset([
    'with',
    'at',
    'from',
    'into',
    'during',
    'including',
    'until',
    'against',
    'among',
    'throughout',
    'towards',
    'upon',
    'concerning',
    'of',
    'to',
    'in',
    'for',
    'on',
    'by',
    'about',
    'like',
    'through',
    'over',
    'before',
    'between',
    'after',
    'without',
    'under',
    'within',
    'along',
    'following',
    'across',
    'behind',
    'beyond',
    'up',
    'out',
    'around',
    'down',
    'off',
    'above',
    'near',
])


class PrepositionSymbol(Symbol):
    def test(self, literal: str, position: int, state: 'State') -> bool:
        return literal in prepositions


@memoize
def grammar(**kwargs): 
    return {
        Rule('PREPOSITION', [PrepositionSymbol()], passthru),

        Rule('PP', [RuleRef('PREPOSITION'), RuleRef('INSTANCE*')],
            lambda state, data: data[1] + Interpretation(local=PrepositionPhrase(data[0].local, data[1].local))),

        Rule('PP', [RuleRef('PREPOSITION'), RuleRef('PROTOTYPE*')],
            lambda state, data: data[1] + Interpretation(local=PrepositionPhrase(data[0].local, data[1].local))),

        Rule('PP', [RuleRef('PREPOSITION'), RuleRef('CATEGORY')],
            lambda state, data: data[1] + Interpretation(local=PrepositionPhrase(data[0].local, data[1].local))),
    }