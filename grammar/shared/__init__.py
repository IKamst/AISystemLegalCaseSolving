from grammar.shared import prototype, instance, category, verb, negation
from decorators import memoize

@memoize
def grammar(**kwargs):
	return prototype.grammar(**kwargs) \
	    | instance.grammar(**kwargs) \
	    | category.grammar(**kwargs) \
	    | verb.grammar(**kwargs) \
	    | negation.grammar(**kwargs)
