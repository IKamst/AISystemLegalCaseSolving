import parser
from grammar.shared import specific, negation, claim, conditional, instance
from grammar import simple, recursive, blob
from pprint import pprint

def debug_signal_handler(signal, frame):
    import pdb
    pdb.set_trace()

import signal
signal.signal(signal.SIGINT, debug_signal_handler)

options = dict(anaphora=True)

grammar = conditional.grammar(**options) \
    | negation.grammar(**options) \
    | recursive.grammar(**options)

p = parser.Parser(grammar, 'ARGUMENT')

tokens = parser.tokenize('Tweety can fly because he has wings, he has feathers and he is capable.')

parses = p.parse(tokens)

print("All OK")