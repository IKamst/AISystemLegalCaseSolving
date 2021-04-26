from collections import OrderedDict
from typing import List
from parser import RuleRef, Literal, Span
from argumentation import Argument, Relation
from interpretation import Rule, Interpretation, Expression
from grammar.macros import and_rules
from grammar.shared.claim import Scope
from grammar.shared.instance import Instance
from grammar.shared.negation import Negation
from grammar.shared.prototype import Prototype
from grammar.shared.specific import SpecificClaim
from grammar.shared.conditional import GeneralClaim, find_conditions
from decorators import memoize

class PartialRelation(object):
    def __init__(self, relation_type, specifics: List['SpecificClaim'] = None, conditional = None, make_assumptions=True):
        # assert all(o.__class__.__name__ == 'SpecificClaim' for o in specifics)
        assert conditional is None or isinstance(conditional, GeneralClaim), "Expected the conditional to be a GeneralClaim, got a {} instead".format(conditional.__class__.__name__)
        assert specifics is None or all(isinstance(specific, SpecificClaim) for specific in specifics)
        self.type = relation_type
        self.specifics = specifics
        self.conditional = conditional
        self.make_assumptions = make_assumptions

    def instantiate(self, claim, context):
        relation = Relation(sources={}, target=claim, type=self.type)
        argument = Argument(relations={relation})
        
        if self.specifics is not None:
            instances = OrderedDict()
            claims = OrderedDict()
            for specific in self.specifics:
                # If we're connecting to a scoped statement, make sure we have the right scope
                if claim.scope and specific.scope != claim.scope:
                    scoped_specific = specific.update(scope=claim.scope)
                    relation.sources.add(scoped_specific)
                    instances[scoped_specific.subject] = {scoped_specific.subject, specific.subject}
                    claims[scoped_specific] = {scoped_specific, specific}
                else:
                    relation.sources.add(specific)
            argument = argument + Argument(instances=instances, claims=claims)

        if self.make_assumptions and self.conditional is not None:
            argument = argument + Argument(relations={Relation([self.conditional], relation, Relation.SUPPORT)})
            conditions = find_conditions(self.conditional, context)
            if len(conditions) > 0:
                assumptions = []
                for condition in conditions:
                    params = {
                        'subject': claim.subject,
                        'verb': condition.verb.for_subject(claim.subject),
                    }

                    if condition.verb.literal in ('is', 'are'):
                        params['object'] = getattr(condition.object, claim.subject.grammatical_number)
                    
                    assumptions.append(condition.assume(**params))

                argument = argument + Argument(claims=dict((assumption, {assumption}) for assumption in assumptions))
                relation.sources.update(assumptions)
        
        if self.make_assumptions and self.conditional is None and self.specifics is not None:
            """
            Make a general assumption in the trend of 'When Tweety can fly
            because she is a bird, anything that is a bird can fly.'
            """
            scope = Scope()
            subject = Instance(pronoun=Span('something'), scope=scope)
            
            if self.type == Relation.SUPPORT:
                object = claim.object
            elif self.type == Relation.ATTACK:
                object = Negation(claim.object) #is this ok? Or are we jumping to conclusions?
            else:
                assert False, "Can't deal with this kind of relation"

            conditional = GeneralClaim(subject, claim.verb, object, scope=scope, assumption=True)
            assumptions = []
            
            for specific in self.specifics:
                if claim.subject.could_be(specific.subject):
                    assumptions.append(specific.update(id=None, subject=conditional.subject, scope=scope))

            if len(assumptions) > 0:
                argument = argument + Argument(
                    instances={subject: {subject}},
                    claims={conditional: {conditional}, **{assumption: {assumption} for assumption in assumptions}},
                    relations={
                        Relation([conditional], relation, Relation.SUPPORT),
                        Relation(assumptions, conditional, Relation.CONDITION)
                    })

        if len(relation.sources) == 0:
            raise Exception("No specific claim or assumption to link the conditional claim to")
        
        return Interpretation(argument=argument, local=claim)
        

def expanded_claim(state, data):
    # specific claim; supports; attacks;
    interpretation = data[0]

    # Add the supporting relations (if there is a 'because' clause)
    if data[1].local:
        interpretation += data[1]
        for support in data[1].local:
            interpretation += support.instantiate(data[0].local, data[1].argument)

    # Add the attacking relations (if there is a 'but' clause)
    if data[2].local:
        interpretation += data[2]
        for attack in data[2].local:
            interpretation += attack.instantiate(data[0].local, data[2].argument)

    return interpretation

@memoize
def grammar(assumptions=True, **kwargs):
    return and_rules('EXPANDED_SPECIFIC_CLAIMS', 'EXPANDED_SPECIFIC_CLAIM', accept_singular=True) \
    | and_rules('EXPANDED_SPECIFIC_CLAIMS_GENERAL_FIRST', 'EXPANDED_SPECIFIC_CLAIM', first_singleton='EXPANDED_GENERAL_CLAIM') \
    | and_rules('EXPANDED_SPECIFIC_CLAIMS_GENERAL_LAST', 'EXPANDED_SPECIFIC_CLAIM', last_singleton='EXPANDED_GENERAL_CLAIM') \
    | and_rules('SUPPORTS', 'SUPPORT', accept_singular=True) \
    | and_rules('ATTACKS', 'ATTACK', accept_singular=True) \
    | {
        Rule('ARGUMENT', [RuleRef('SENTENCE')],
            lambda state, data: data[0]),

        Rule('ARGUMENT', [RuleRef('ARGUMENT'), RuleRef('SENTENCE')],
            lambda state, data: data[0] + data[1]),

        
        Rule('SENTENCE', [RuleRef('EXPANDED_SPECIFIC_CLAIM'), Literal('.')],
            lambda state, data: data[0]),

        Rule('EXPANDED_SPECIFIC_CLAIM', [RuleRef('SPECIFIC_CLAIM'), RuleRef('SUPPORTS'), RuleRef('ATTACKS')],
            expanded_claim),

        # We use CONDITIONAL_CLAIM instead of GENERAL_CLAIM here because a conditional claim is a more specific
        # structure that can contain a general claim, and that is why it has to be above general claim in the
        # hierarchy. And hey, in a sense a general claim is also a conditional claim because for a general claim
        # to be applicable the subject has to match the group of the subject of the general claim, making it
        # more or less a conditional claim, right? 
        Rule('EXPANDED_GENERAL_CLAIM', [RuleRef('CONDITIONAL_CLAIM'), RuleRef('SUPPORTS'), RuleRef('ATTACKS')],
            expanded_claim),

        Rule('SUPPORT', [Literal('because'), RuleRef('EXPANDED_SPECIFIC_CLAIMS')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.SUPPORT, specifics=data[1].local, make_assumptions=assumptions))),

        Rule('SUPPORT', [Literal('because'), RuleRef('EXPANDED_SPECIFIC_CLAIMS_GENERAL_FIRST')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.SUPPORT, conditional=data[1].local[0], specifics=data[1].local[1:], make_assumptions=assumptions))),

        Rule('SUPPORT', [Literal('because'), RuleRef('EXPANDED_SPECIFIC_CLAIMS_GENERAL_LAST')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.SUPPORT, conditional=data[1].local[-1], specifics=data[1].local[0:-1], make_assumptions=assumptions))),

        Rule('SUPPORT', [Literal('because'), RuleRef('EXPANDED_GENERAL_CLAIM')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.SUPPORT, conditional=data[1].local, make_assumptions=assumptions))),

        Rule('SUPPORTS', [],
            lambda state, data: Interpretation()),

        Rule('ATTACK', [Expression(r'^except|but$'), RuleRef('EXPANDED_SPECIFIC_CLAIMS')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.ATTACK, specifics=data[1].local, make_assumptions=assumptions))),

        Rule('ATTACK', [Expression(r'^except|but$'), RuleRef('EXPANDED_SPECIFIC_CLAIMS_GENERAL_FIRST')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.ATTACK, conditional=data[1].local[0], specifics=data[1].local[1:], make_assumptions=assumptions))),

        Rule('ATTACK', [Expression(r'^except|but$'), RuleRef('EXPANDED_SPECIFIC_CLAIMS_GENERAL_LAST')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.ATTACK, conditional=data[1].local[-1], specifics=data[1].local[0:-1], make_assumptions=assumptions))),

        Rule('ATTACK', [Expression(r'^except|but$'), RuleRef('EXPANDED_GENERAL_CLAIM')],
            lambda state, data: data[1] + Interpretation(local=PartialRelation(Relation.ATTACK, conditional=data[1].local, make_assumptions=assumptions))),

        Rule('ATTACKS', [],
            lambda state, data: Interpretation()),
    }