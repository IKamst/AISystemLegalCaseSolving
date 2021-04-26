from parser import Rule, RuleRef, Literal
from argumentation import Argument
from interpretation import Interpretation, Expression
from grammar.shared.conditional import GeneralClaim
from grammar.shared.specific import SpecificClaim
from grammar.shared.instance import Instance
from grammar import recursive
from decorators import memoize


class SpecificBlob(SpecificClaim):
    def __init__(self, subject, verb, object, literals, **kwargs):
        self.literals = literals
        super().__init__(subject, verb, object, **kwargs)

    def update(self, cls=None, **kwargs):
        kwargs['literals'] = self.literals
        return super().update(cls, **kwargs)

    def text(self, argument):
        return " ".join(self.literals)


class GeneralBlob(GeneralClaim):
    def __init__(self, subject, verb, object, literals, **kwargs):
        self.literals = literals
        super().__init__(subject, verb, object, **kwargs)

    def update(self, cls=None, **kwargs):
        kwargs['literals'] = self.literals
        return super().update(cls, **kwargs)

    def text(self, argument):
        return " ".join(self.literals)


def blob_specific_claim(state, data):
    subject = Instance()
    verb = None
    object = None
    claim = SpecificBlob(subject, verb, object, data[0])
    argument = Argument(instances={subject: {subject}}, claims={claim: {claim}})
    return Interpretation(argument=argument, local=claim)


def blob_conditional_claim(state, data):
    subject = Instance()
    verb = None
    object = None
    claim = GeneralBlob(subject, verb, object, data[0])
    argument = Argument(instances={subject: {subject}}, claims={claim: {claim}})
    return Interpretation(argument=argument, local=claim)


@memoize
def grammar(**kwargs):
    return recursive.grammar(**kwargs) | {
    Rule('SPECIFIC_CLAIM', [RuleRef('BLOB')], blob_specific_claim),
    
    Rule('CONDITIONAL_CLAIM', [RuleRef('BLOB')], blob_conditional_claim),

    Rule('BLOB_WORD', [Expression(r'^(?!because|but|except)$')],
        lambda state, data: data[0].local),
    
    Rule('BLOB', [RuleRef('BLOB_WORD')],
        lambda state, data: [data[0]]),
    
    Rule('BLOB', [RuleRef('BLOB'), RuleRef('BLOB_WORD')],
        lambda state, data: data[0] + [data[1]]),
}