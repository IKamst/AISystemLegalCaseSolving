from grammar.shared import prototype, verb
from interpretation import Interpretation
from parser import Rule, RuleRef
from decorators import memoize


class Action(object):
    def __init__(self, verb, object=None):
        self.verb = verb
        self.object = object

    def __hash__(self):
        return hash(self.verb) + hash(self.object)

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and self.verb == other.verb \
            and self.object == other.object
    
    def __str__(self):
        if self.object:
            return "{!s} {!s}".format(self.verb, self.object)
        else:
            return str(self.verb)

    def __repr__(self):
        return "Action({!r} {!r})".format(self.verb, self.object)


    def text(self, argument):
        if self.object:
            return "{!s} {!s}".format(self.verb, self.object.text(argument))
        else:
            return str(self.verb)

    def is_same(self, other, argument):
        return isinstance(other, Action) \
            and self.verb == other.verb \
            and self.object.is_same(other.object, argument)

    @property
    def singular(self):
        return self

    @property
    def plural(self):
        return self


@memoize
def grammar(**kwargs):
    return prototype.grammar(**kwargs) | verb.grammar(**kwargs) | {
        Rule('ACTION_INF', [RuleRef('VERB_INF')],
            lambda state, data: Interpretation(local=Action(data[0].local))),

        Rule('ACTION_INF', [RuleRef('VERB_INF'), RuleRef('PROTOTYPE*')],
            lambda state, data: data[1] + Interpretation(local=Action(data[0].local, data[1].local))),

        Rule('ACTION_INF', [RuleRef('VERB_INF'), RuleRef('INSTANCE*')],
            lambda state, data: data[1] + Interpretation(local=Action(data[0].local, data[1].local))),

        Rule('ACTION_INF', [RuleRef('VERB_INF'), RuleRef('CATEGORY')],
            lambda state, data: data[1] + Interpretation(local=Action(data[0].local, data[1].local))),

        Rule('ACTION_INF', [RuleRef('VERB_BE'), RuleRef('ACTION_PP')],
            lambda state, data: data[1] + Interpretation(local=Action(data[1].local.verb.passive, data[1].local.object))),
        
        Rule('ACTION_PP', [RuleRef('VERB_PP'), RuleRef('INSTANCE*')],
            lambda state, data: data[1] + Interpretation(local=Action(data[0].local, data[1].local))),

        Rule('ACTION_PP', [RuleRef('VERB_PP'), RuleRef('PROTOTYPE*')],
            lambda state, data: data[1] + Interpretation(local=Action(data[0].local, data[1].local))),
    }