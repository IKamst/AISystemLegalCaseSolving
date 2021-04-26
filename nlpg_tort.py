from nlpg import Parser
from nlpg_grammar import rules, tokenize
from pprint import pprint

sentences = ' '.join([
	'A person must repair the damage \
		when they committed a tortious act,\
		against another person, \
		that can be attributed to him, \
		and that this other person has suffered as a result thereof.',
	'They committed a tortious act \
		if there was a violation of someone else\'s right, \
		if an act/omission in violation of a duty imposed by law, \
		or if of what according to unwritten law has to be regarded as proper social conduct \
		unless there was a justification for this behaviour.',
	'A tortious act can be attributed to the tortfeasor \
		if it results from his fault\
		or if it results from a cause for which he is accountable by virtue of law/generally accepted principles.',
])

sentences2 = ' '.join([
	'A person who commits an unlawful act toward another which can be imputed to him, \
		must repair the damage which the other person suffers as a consequence thereof.',
	'Except where there is a ground of justification, \
		the following acts are deemed to be unlawful: \
		the violation of a right, \
		an act or omission violating a statutory duty \
		or a rule of unwritten law pertaining to proper social conduct.',
	'An unlawful act can be imputed to its author \
		if it results from his fault \
			or from a cause for which he is answerable according to law or common opinion.',
])

assert rules.unreachable() == set()

parser = Parser(rules)

tokens = list(tokenize(rules.markers(), sentences))

pprint(tokens)

parses = list(parser.parse('sentences', tokens))

pprint(parses)

# for parse in parses:
# 	for n, realisation in enumerate(parser.reverse('sentences', parse)):
# 		print("{}: {}".format(n, ' '.join(map(str, realisation))))


