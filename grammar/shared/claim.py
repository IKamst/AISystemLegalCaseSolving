from grammar.shared import instance, prototype, category
from parser import Rule, RuleRef, passthru, Literal
from argumentation import Argument
from interpretation import Interpretation
from datastructures import Sequence
from debug import Boolean, print_comparator

class Scope(object):
    """
    Identifies the scope of a claim. Mainly used inside conditional claims, and
    all the claims that are conditions of that conditional claim. Prevents them
    from being merged.
    """
    
    counter = Sequence()

    def __init__(self):
        self.id = self.counter.next()

    def __repr__(self):
        return "Scope#{}".format(self.id)

    def __str__(self):
        return "{}".format(self.id)


class Claim(object):
    """
    Represents claims such as 'Cats are cool' or 'Tweety can fly'. The verb
    is often (always?) a modal verb.
    """

    counter = Sequence()

    def __init__(self, subject, verb, object, assumption=False, id=None, scope=None):
        self.id = id if id is not None else self.counter.next()
        self.subject = subject
        self.verb = verb
        self.object = object
        self.assumption = assumption
        self.scope = scope

    def __repr__(self):
        return "{type}(subject={subject!r}, verb={verb!r}, object={object!r}{assumption}{scope})".format(
            subject=self.subject,
            verb=self.verb,
            object=self.object,
            type=self.__class__.__name__,
            assumption=", assumption=True" if self.assumption else "",
            scope=", scope={}".format(self.scope.id) if self.scope else "")

    def __str__(self):
        return "{subject!s} {verb!s} {object!s}".format(**self.__dict__)

    @print_comparator
    def is_same(self, other: 'Claim', argument: Argument) -> bool:
        if not isinstance(other, Claim):
            return Boolean(False, 'other not a claim')

        if self.id == other.id:
            return Boolean(True, 'same id')

        if self.scope != other.scope:
            return Boolean(False, 'different scope')
        
        if self.verb != other.verb:
            return Boolean(False, 'different verb')
        
        if not self.subject.is_same(other.subject, argument):
            return Boolean(False, 'different subject instance')
   
        if not self.object.is_same(other.object, argument):
            return Boolean(False, 'different object instance')
       
        return Boolean(True, 'no false eh')

    def is_preferred_over(self, other: 'Claim', argument: Argument):
        return self.scope and not other.scope \
            or other.assumption and not self.assumption

    def text(self, argument: Argument) -> str:
        return "{subject!s} {verb!s} {object!s}".format(
            subject=self.subject.text(argument),
            verb=self.verb,
            object=self.object.text(argument))

    def update(self, cls=None, **kwargs):
        if cls is None:
            cls = self.__class__
        defaults = {
            'id': self.id,
            'subject': self.subject.update(scope=kwargs['scope']) if 'scope' in kwargs else self.subject,
            'verb': self.verb,
            'object': self.object,
            'assumption': self.assumption
        }
        return cls(**{**defaults, **kwargs})

    def assume(self, cls=None, **kwargs):
        return self.update(cls=cls, id=self.counter.next(), assumption=True, **kwargs)

    @classmethod
    def from_rule(cls, state, data):
        claim = cls(data[0].local, data[1].local, data[2].local)
        return data[0] + data[1] + data[2] + Interpretation(argument=Argument(claims={claim: {claim}}), local=claim)


# grammar = instance.grammar | prototype.grammar | category.grammar | {
#     Rule('SUBJECT', [RuleRef('INSTANCE')], passthru),
#     Rule('SUBJECT', [RuleRef('PROTOTYPE')], passthru),
#     Rule('SUBJECTS', [RuleRef('INSTANCES')], passthru),
#     Rule('SUBJECTS', [RuleRef('PROTOTYPES')], passthru),

#     Rule('CLAIM', [RuleRef('SUBJECT'), Literal('is'), RuleRef('CATEGORY')],
#         Claim.from_rule),

#     Rule('CLAIM', [RuleRef('SUBJECT'), Literal('is'), RuleRef('PROTOTYPE')],
#         Claim.from_rule),

#     Rule('CLAIM', [RuleRef('SUBJECTS'), Literal('are'), RuleRef('CATEGORY')],
#         Claim.from_rule),

#     Rule('CLAIM', [RuleRef('SUBJECTS'), Literal('are'), RuleRef('PROTOTYPES')],
#         Claim.from_rule),

#     # This allows the grammar to use GENERAL and SPECIFIC claims, but behave
#     # as if the distinction is not made, until the actual GENERAL and SPECIFIC
#     # rules are loaded. 
#     Rule('GENERAL_CLAIM', [RuleRef('CLAIM')], passthru),

#     Rule('SPECIFIC_CLAIM', [RuleRef('CLAIM')], passthru)
# }
