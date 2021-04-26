from parser import Rule, RuleRef, State, passthru
from grammar.shared.keywords import Expression
from interpretation import Symbol, Interpretation
import english
from decorators import memoize

class Category(object):
    def __init__(self, literal):
        self.literal = literal

    def __hash__(self):
        return hash(self.literal)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.literal == other.literal
    def text(self, argument):
        return "{}".format(self.literal)

    def __repr__(self):
        return "Category({!r})".format(self.literal)
    def is_same(self, other, argument):
        return isinstance(other, self.__class__) and self.literal == other.literal

    @property
    def singular(self):
        return self

    @property
    def plural(self):
        return self


"""
Adjectives typically and on -ly, -able, -ful, -ical, etc. but you also
have adjectives such as 'red', 'large', 'rich'. On top of that, you can
convert verbs to adjectives using -ed and -able. So we'll just accept
anything today :)
"""

@memoize
def grammar(**kwargs):
    return {
        # Rule("CATEGORY", [Expression(r'.+')],
        #     lambda state, data: data[0] + Interpretation(local=Category(data[0].local)))
        Rule('CATEGORY', [RuleRef('NOUN*')], passthru),
    }
