from grammar.shared import instance, category, prototype, verb, action
from grammar.shared.claim import Claim
from grammar.shared.verb import VerbParser
from parser import RuleRef
from interpretation import Rule
from decorators import memoize


class SpecificClaim(Claim):
    """
    A specific claim is a claim that always has an instance as its subject. E.g.
    it is always about 'the' something instead of 'a' something, or a name, or
    a 'they'.
    """
    def __init__(self, subject, verb, object, **kwargs):
        assert isinstance(subject, instance.Instance) \
            or isinstance(subject, instance.GroupInstance), \
            "Subject of a specific claim is not an instance?"
        super().__init__(subject, verb, object, **kwargs)


@memoize
def grammar(**kwargs):
    return instance.grammar(**kwargs) | category.grammar(**kwargs) | prototype.grammar(**kwargs) | action.grammar(**kwargs) | verb.grammar(**kwargs) | {
        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCE'), VerbParser(r'is|has|was'), RuleRef('CATEGORY')],
            SpecificClaim.from_rule),
        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCE'), VerbParser(r'is|has|was'), RuleRef('PROTOTYPE')],
            SpecificClaim.from_rule),
        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCE'), VerbParser(r'is|has|was'), RuleRef('INSTANCE*')],
            SpecificClaim.from_rule),

        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCE'), VerbParser(r'has|was'), RuleRef('ACTION_PP')],
            SpecificClaim.from_rule),

        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCES'), VerbParser('are|have'), RuleRef('CATEGORY')],
            SpecificClaim.from_rule),
        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCES'), VerbParser('are|have'), RuleRef('PROTOTYPE')],
            SpecificClaim.from_rule),

        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCE'), VerbParser('can|may|must|should'), RuleRef('ACTION_INF')],
            SpecificClaim.from_rule),

        Rule('SPECIFIC_CLAIM', [RuleRef('INSTANCES'), VerbParser('can|may|must|should'), RuleRef('ACTION_INF')],
            SpecificClaim.from_rule),
    }