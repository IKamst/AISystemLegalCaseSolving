from grammar.shared import category, prototype, verb
from parser import Rule, RuleRef
from interpretation import Interpretation, Expression
from decorators import memoize


class Negation(object):
    def __init__(self, object):
        self.object = object

    def __repr__(self):
        return "Negation({!r})".format(self.object)

    @property
    def adverb(self):
        # Todo: this is not how English works: it should be related to whether
        # object is a noun. However, we don't really classify "nouns" as in a
        # grammatical manner, so we have no idea...
        return 'no' if isinstance(self.object, category.Category) else 'not'

    def __str__(self):
        return "{} {!s}".format(self.adverb, self.object)

    def is_same(self, other, argument):
        return isinstance(other, self.__class__) \
            and self.object.is_same(other.object, argument) if hasattr(self.object, 'is_same') else self.object == other.object

    def text(self, argument):
        return "{} {}".format(self.adverb, self.object.text(argument) if hasattr(self.object, 'text') else str(self.object))

    @property
    def singular(self):
        return Negation(self.object.singular)

    @property
    def plural(self):
        return Negation(self.object.plural)

    @classmethod
    def from_rule(cls, state, data):
        if isinstance(data[1].local, cls):
            neg = data[1].local.object  # Unwrap double negations
        else:
            neg = cls(data[1].local)
        return data[1] + Interpretation(local=neg)


@memoize
def grammar(**kwargs):
    return category.grammar(**kwargs) | prototype.grammar(**kwargs) | verb.grammar(**kwargs) | {
        Rule('CATEGORY', [Expression(r'^not?$'), RuleRef('CATEGORY')],
            Negation.from_rule),

        Rule('PROTOTYPE', [Expression(r'^not$'), RuleRef('PROTOTYPE')],
            Negation.from_rule),

        Rule('PROTOTYPES', [Expression(r'^not$'), RuleRef('PROTOTYPES')],
            Negation.from_rule),

        Rule('VERB_INF', [Expression(r'^not$'), RuleRef('VERB_INF')],
            Negation.from_rule)
    }