from typing import Set
from itertools import chain
from parser import RuleRef, Literal, Span, passthru
from grammar.shared.claim import Claim, Scope
from grammar.shared.instance import Instance, GroupInstance
from grammar.shared.specific import SpecificClaim
from grammar.shared.prototype import Prototype
from grammar.shared.verb import VerbParser, Verb
from grammar.shared import pronoun, category, prototype, verb, specific
from grammar.macros import and_rules
from argumentation import Argument, Relation
from interpretation import Rule, Expression, Interpretation
import english
from decorators import memoize


def find_conditions(claim, argument):
    return set(chain(*[relation.sources for relation in argument.relations \
            if relation.target == claim and relation.type == Relation.CONDITION]))


class GeneralClaim(Claim):
    """
    An Undetermined Claim is in many ways similar to a specific Claim
    except that the subject is undetermined. It functions as an unbound
    variable, often with the word "something" or "someone".
    """
    def __init__(self, subject, verb, object, conj = None, **kwargs):
        super().__init__(subject, verb, object, **kwargs)
        self.conj = conj

    def is_preferred_over(self, other: Claim, argument: Argument) -> bool:
        # assert isinstance(other, GeneralClaim)
        # return len(find_conditions(self,argument)) > len(find_conditions(other, argument))
        return False

    def text(self, argument: Argument) -> str:
        conditions = find_conditions(self, argument)
        
        # Special condition: something can fly if it is a bird -> birds can fly
        if len(conditions) == 1:
            (condition,) = conditions
            if self.subject == condition.subject \
                and condition.verb is not None \
                and condition.verb.literal in ('is', 'are') \
                and isinstance(condition.object, Prototype):
                return "{a!s} {verb!s} {b!s}".format(a=condition.object.text(argument), verb=self.verb, b=self.object.text(argument))

        return "{} {} {}".format(
            super().text(argument),
            self.conj if self.conj is not None else "if",
            english.join([claim.text(argument) for claim in sorted(conditions, key=lambda condition: condition.id)]))

    @classmethod
    def from_claim(cls, claim: 'SpecificClaim', scope: 'Scope', conj: str = None) -> 'GeneralClaim':
        return claim.update(cls=cls, scope=scope, conj=conj)


def undetermined_claim(state, data):
    scope = Scope()
    conditions = set(claim.update(scope=scope) for claim in data[2].local)
    claim = GeneralClaim.from_claim(data[0].local, scope=scope, conj=data[1].local)
    relation = Relation(conditions, claim, Relation.CONDITION)
    return data[0] + data[2] + Interpretation(
        argument=Argument(
            claims={
                claim: {claim}, 
                **{condition: {condition} for condition in conditions}
            },
            relations={relation},
            instances={
                claim.subject: {claim.subject},
                **{condition.subject: {condition.subject} for condition in conditions}
            }
        ),
        local=claim)


def expanded_general_claim(state, data):
    assert len(data[0].argument.claims) == 2
    assert len(data[0].argument.relations) == 1
    
    claim = data[0].local
    conditions = set(claim.update(scope=data[0].local.scope) for claim in data[2].local)
    remaining_claims = set(data[0].argument.claims.keys()) ^ {claim}
    relation = Relation(remaining_claims | conditions , claim, Relation.CONDITION)
    return data[0] + data[2] + Interpretation(
        argument=Argument(
            claims={condition: {condition} for condition in conditions},
            relations={relation},
            instances={condition.subject: {condition.subject} for condition in conditions}
        ),
        local=claim)


def general_claim_singular(state, data):
    scope = Scope()
    subj = Instance(pronoun=Span('something'), scope=scope)
    condition = SpecificClaim(subj, Verb('is'), data[0].local.singular, scope=scope)
    claim = GeneralClaim(subj, data[1].local, data[2].local, scope=scope)
    relation = Relation({condition}, claim, Relation.CONDITION)
    return data[0] + data[2] + Interpretation(
        argument=Argument(
            claims={claim: {claim}, condition: {condition}},
            relations={relation},
            instances={subj: {subj}}
        ),
        local=claim)


def general_claim_plural(state, data):
    scope = Scope()
    subj = GroupInstance(pronoun=Span('all'), scope=scope)
    condition = SpecificClaim(subj, Verb('are'), data[0].local.plural, scope=scope)
    claim = GeneralClaim(subj, data[1].local, data[2].local, scope=scope)
    relation = Relation({condition}, claim, Relation.CONDITION)
    return data[0] + data[2] + Interpretation(
        argument=Argument(
            claims={claim: {claim}, condition: {condition}},
            relations={relation},
            instances={subj: {subj}}
        ),
        local=claim)


@memoize
def grammar(**kwargs):
    return pronoun.grammar(**kwargs) \
    | category.grammar(**kwargs) \
    | prototype.grammar(**kwargs) \
    | verb.grammar(**kwargs) \
    | specific.grammar(**kwargs) \
    | and_rules('SPECIFIC_CLAIMS', 'SPECIFIC_CLAIM', accept_singular=True) \
    | {
        # x is an A when x is a B
        Rule('CONDITIONAL_CLAIM', [RuleRef('SPECIFIC_CLAIM'), Expression(r'^if|when$'), RuleRef('SPECIFIC_CLAIMS')],
            undetermined_claim),

        Rule('CONDITIONAL_CLAIM', [RuleRef('GENERAL_CLAIM'), Expression(r'^if|when$'), RuleRef('SPECIFIC_CLAIMS')],
            expanded_general_claim),

        Rule('CONDITIONAL_CLAIM', [RuleRef('GENERAL_CLAIM')],
            passthru),

        # an A is a B
        Rule('GENERAL_CLAIM', [RuleRef('PROTOTYPE'), VerbParser(r'^is|has|was$'), RuleRef('CATEGORY')],
            general_claim_singular),
        Rule('GENERAL_CLAIM', [RuleRef('PROTOTYPE'), VerbParser(r'^is|has|was$'), RuleRef('PROTOTYPE')],
            general_claim_singular),

        Rule('GENERAL_CLAIM', [RuleRef('PROTOTYPE'), VerbParser(r'^can|may|should$'), RuleRef('VERB_INF')],
            general_claim_singular),

        # A's are B's
        Rule('GENERAL_CLAIM', [RuleRef('PROTOTYPES'), VerbParser(r'^are|have$'), RuleRef('CATEGORY')],
            general_claim_plural),
        Rule('GENERAL_CLAIM', [RuleRef('PROTOTYPES'), VerbParser(r'^are|have$'), RuleRef('PROTOTYPES')],
            general_claim_plural),

        Rule('GENERAL_CLAIM', [RuleRef('PROTOTYPES'), VerbParser(r'^can|may|should$'), RuleRef('VERB_INF')],
            general_claim_plural),
    }