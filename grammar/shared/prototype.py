from parser import Rule, RuleRef, Literal, passthru
from grammar.shared import noun
from english import indefinite_article
from interpretation import Interpretation, Expression
from decorators import memoize
from debug import Boolean

class Prototype(object):
    def __init__(self, noun, article=None):
        self.noun = noun
        self.article = article

    def __hash__(self):
        return hash(self.article) + hash(self.noun)

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and self.noun == other.noun \
            and (self.article is None or other.article is None or self.article == other.article)

    def is_same(self, other, argument):
        return isinstance(other, self.__class__) \
            and self.noun.is_same(other.noun, argument) \
            and (self.article is None or other.article is None or self.article == other.article)
    
    def text(self, argument):
        if self.noun.grammatical_number is 'singular':
            if self.article:
                article = self.article
            else:
                article = indefinite_article(str(self.noun.text(argument)))
            return "{} {!s}".format(article, self.noun.text(argument))
        else:
            if self.article:
                return "{} {!s}".format(self.article, self.noun.plural.text(argument))
            else:
                return str(self.noun.plural.text(argument))

    def __repr__(self):
        return "Prototype(noun={!r}{})".format(self.noun, ' article=' + self.article if self.article else '')

    def _transform(self, grammatical_number):
        if self.noun.grammatical_number == grammatical_number:
            return self
        else:
            return self.__class__(getattr(self.noun, grammatical_number))

    @property
    def singular(self):
        return self._transform('singular')

    @property
    def plural(self):
        return self._transform('plural')


@memoize
def grammar(**kwargs):
    return noun.grammar(**kwargs) | {
        Rule("PROTOTYPE", [Expression(r'^every|an?$'), RuleRef("NOUN")],
            lambda state, data: data[1] + Interpretation(local=Prototype(data[1].local, article=data[0].local))),

        Rule("PROTOTYPES", [RuleRef("NOUNS")],
            lambda state, data: data[0] + Interpretation(local=Prototype(data[0].local))),

        Rule("PROTOTYPES", [Expression(r'^all|most|many|some$'), RuleRef("NOUNS")],
            lambda state, data: data[0] + Interpretation(local=Prototype(data[1].local, article=data[0].local))),

        Rule("PROTOTYPE*", [RuleRef("PROTOTYPE")], passthru),
        Rule("PROTOTYPE*", [RuleRef("PROTOTYPES")], passthru),
    }