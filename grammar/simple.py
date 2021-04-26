from parser import Rule, RuleRef, Literal
from argumentation import Argument, Relation
from interpretation import Interpretation, Expression
from grammar.macros import and_rules
from grammar.shared.specific import SpecificClaim
from decorators import memoize


def relation(type, claim, specifics, general=None):
    relation = Relation(specifics, claim, type)
    argument = Argument(relations={relation})
    if general is not None:
        argument = argument + Argument(relations={Relation([general], relation, Relation.SUPPORT)})
    return argument


def assume(claim, general):
    assumption = SpecificClaim(claim.subject, 'is', general.subject.singular, assumption=True)
    argument = Argument(claims={assumption: {assumption}})
    argument += relation(Relation.SUPPORT, claim, general=general, specifics={assumption})
    return Interpretation(argument=argument, local=claim)


def support_relation(interpretation):
    target = interpretation.local # A relation
    for relation in interpretation.argument.relations:
        if relation.target == target and relation.type == Relation.SUPPORT:
            return relation
    raise Exception('Could not find support relation')


def warrant_relation(interpretation):
    target = support_relation(interpretation)
    for relation in interpretation.argument.relations:
        if relation.target == target and relation.type == Relation.SUPPORT:
            return relation
    raise Exception('Could not find relation between support relation and warrant')


@memoize
def grammar(**kwargs):
    return and_rules('SPECIFIC_CLAIMS', 'SPECIFIC_CLAIM', accept_singular=True) \
    | and_rules('SPECIFIC_CLAIMS_CONDITIONAL_FIRST', 'SPECIFIC_CLAIM', first_singleton='CONDITIONAL_CLAIM') \
    | and_rules('SPECIFIC_CLAIMS_CONDITIONAL_LAST', 'SPECIFIC_CLAIM', last_singleton='CONDITIONAL_CLAIM') \
    | {
        Rule('ARGUMENT', [RuleRef('SENTENCE')],
            lambda state, data: data[0]),

        Rule('ARGUMENT', [RuleRef('ARGUMENT'), RuleRef('SENTENCE')],
            lambda state, data: data[0] + data[1]),


        Rule('SENTENCE', [RuleRef('SUPPORTED_CLAIM'), Literal('.')],
            lambda state, data: data[0]),

        Rule('SENTENCE', [RuleRef('ATTACKED_CLAIM'), Literal('.')],
            lambda state, data: data[0]),


        Rule('SUPPORTED_CLAIM', [RuleRef('SPECIFIC_CLAIM'), Literal('because'), RuleRef('SPECIFIC_CLAIMS')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.SUPPORT, data[0].local, specifics=data[2].local), local=data[0].local)),

        Rule('SUPPORTED_CLAIM', [RuleRef('SUPPORTED_CLAIM_WITH_WARRANT')],
            lambda state, data: data[0]),

        Rule('SUPPORTED_CLAIM_WITH_WARRANT', [RuleRef('SPECIFIC_CLAIM'), Literal('because'), RuleRef('SPECIFIC_CLAIMS_CONDITIONAL_FIRST')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.SUPPORT, data[0].local, general=data[2].local[0], specifics=data[2].local[1:]), local=data[0].local)),
        
        Rule('SUPPORTED_CLAIM_WITH_WARRANT', [RuleRef('SPECIFIC_CLAIM'), Literal('because'), RuleRef('SPECIFIC_CLAIMS_CONDITIONAL_LAST')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.SUPPORT, data[0].local, general=data[2].local[-1], specifics=data[2].local[:-1]), local=data[0].local)),
        
        
        Rule('ATTACKED_CLAIM', [RuleRef('SPECIFIC_CLAIM'), Expression(r'^but|except$'), RuleRef('SPECIFIC_CLAIMS')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.ATTACK, data[0].local, specifics=data[2].local), local=data[0].local)),

        Rule('ATTACKED_CLAIM', [RuleRef('ATTACKED_CLAIM_WITH_WARRANT')],
            lambda state, data: data[0]),

        Rule('ATTACKED_CLAIM_WITH_WARRANT', [RuleRef('SPECIFIC_CLAIM'), Expression(r'^but|except$'), RuleRef('SPECIFIC_CLAIMS_CONDITIONAL_FIRST')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.ATTACK, data[0].local, general=data[2].local[0], specifics=data[2].local[1:]), local=data[0].local)),
        
        Rule('ATTACKED_CLAIM_WITH_WARRANT', [RuleRef('SPECIFIC_CLAIM'), Expression(r'^but|except$'), RuleRef('SPECIFIC_CLAIMS_CONDITIONAL_LAST')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.ATTACK, data[0].local, general=data[2].local[-1], specifics=data[2].local[:-1]), local=data[0].local)),
        
        # Experimental, don't know if I want this
        # Rule('SUPPORTED_CLAIM', [RuleRef('SPECIFIC_CLAIM'), Literal('because'), RuleRef('CONDITIONAL_CLAIM')],
        #     lambda state, data: data[0] + data[2] + assume(data[0].local, data[2].local)),

        # Attacking a warrant?
        Rule('SUPPORTED_CLAIM', [RuleRef('SUPPORTED_CLAIM'), Expression(r'^but|except$'), RuleRef('SPECIFIC_CLAIMS')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.ATTACK, data[0].local, specifics=data[2].local))),

        Rule('SUPPORTED_CLAIM', [RuleRef('SUPPORTED_CLAIM_WITH_WARRANT'), Expression(r'^but|except$'), RuleRef('SPECIFIC_CLAIMS')],
            lambda state, data: data[0] + data[2] + Interpretation(argument=relation(Relation.ATTACK, warrant_relation(data[0]), specifics=data[2].local)))
    }