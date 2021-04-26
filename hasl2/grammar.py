import re
from functools import partial, reduce
from itertools import takewhile
import operator
from typing import NamedTuple, List, Optional, Any
from hasl2.parser import ruleset, rule, tlist, template, l, slot, empty, terminal, NoMatchException, sparselist

class Text(object):
	def __init__(self, words):
		self.words = tuple(words)

	def __str__(self):
		return " ".join(self.words)

	def __repr__(self):
		return "Text('{}')".format(str(self))

	def __eq__(self, other):
		return type(self) == type(other) and self.words == other.words

	def __add__(self, other):
		return type(self)(self.words + other.words)

	def __sub__(self, other):
		if len(self.words) < len(other.words) or not all(self.words[n] == other.words[n] for n in range(len(other.words))):
			raise Exception("{!r} does not have prefix {!r}".format(self, other))
		return type(self)(self.words[len(other.words):])


class Claim(object):
	def __init__(self, text):
		self.text = text

	def __repr__(self):
		return "Claim('{}')".format(str(self.text))

	def __eq__(self, other):
		return type(self) == type(other) and self.text == other.text

	def map(self, func):
		return type(self)(func(self.text))


class Argument(NamedTuple):
	claim: Claim
	supports: List['Support']
	attack: Optional['Attack']


class Attack(NamedTuple):
	claims: List[Argument]


class Support(NamedTuple):
	datums: List[Claim]
	warrant: Optional['Warrant']
	undercutter: Optional[Argument]


class Warrant(NamedTuple):
	claim: Claim
	conditions: List['WarrantCondition'] # in Disjunctive Normal Form


class WarrantCondition(NamedTuple):
	claims: List[Claim] # Conjunctive
	exceptions: List['WarrantException'] # idem.

	def map(self, func):
		return type(self)(tuple(map(func, self.claims)))


class WarrantException(NamedTuple):
	claims: List[Claim] # Conjunctive

	def map(self, func):
		return type(self)(tuple(map(func, self.claims)))


class Word(terminal):
	def test(self, word):
		return isinstance(word, Text)

	def consume(self, word):
		return word

	def reverse(self, word):
		if not isinstance(word, Text):
			raise NoMatchException('Word not a unit')
		return word

	def __repr__(self):
		return '<text-unit>'

def and_rule(name, single, cc=l('and')):
	comma = '{}-list'.format(name)
	return [
		rule(name, [single], tlist(head=slot(0))),
		rule(name, [comma], slot(0)),
		rule(comma, [single, l(','), comma], tlist(head=slot(0), tail=slot(2))),
		rule(comma, [single, cc, single], tlist(head=[slot(0), slot(2)])),
	]


class word_merge(object):
	def __init__(self, *args):
		self.parts = args

	def consume(self, words):
		out = Text([])
		for part in self.parts:
			if isinstance(part, Text):
				out += part
			else:
				out += part.consume(words)
		return out

	def reverse(self, word):
		raise NoMatchException('Not implemented')


rules = ruleset([
	rule('sentences',
		['sentence', 'sentences'],
		tlist(head=slot(0), tail=slot(1))),

	rule('sentences',
		['sentence'],
		tlist(head=slot(0))),

	rule('sentence',
		['argument', l('.')],
		slot(0)),

	rule('sentence',
		['warrant', l('.')],
		slot(0)),
	
	] + and_rule('arguments', 'argument') + [
	
	rule('argument',
		['claim', 'supports?', 'attack?'],
		template(Argument, claim=slot(0), supports=slot(1), attack=slot(2))),

	rule('claim',
		['word'],
		template(Claim, text=slot(0))),

	] + and_rule('claims', 'claim') + [
	
	rule('word',
		[Word()],
		slot(0)),
 
	### Begin experiment to support discourse markers inside text

	rule('word',
		[Word(), l('or'), 'word'],
		word_merge(slot(0), Text(['or']), slot(2))),

	### End experiment

	rule('attack?',
		[],
		empty()),

	rule('attack?',
		['attack'],
		slot(0)),
	
	rule('attack-marker',
		[l('but')],
		empty()),

	rule('attack-marker',
		[l('except')],
		empty()),

	rule('attack-marker',
		[l('except'), l('that')],
		empty()),

	rule('attack',
		['attack-marker', 'arguments'],
		template(Attack, claims=slot(1))),

	rule('supports?',
		[],
		tlist()),
	rule('supports?',
		['supports'],
		slot(0)),

	] + and_rule('supports', 'support') + [
	
	rule('support',
		[l('because'), 'arguments', 'warrant?', 'undercutter?'],
		template(Support, datums=slot(1), warrant=slot(2), undercutter=slot(3))),

	rule('undercutter?',
		[],
		empty()),
	rule('undercutter?',
		['attack-marker', 'argument'],
		slot(1)),

	rule('warrant?',
		[],
		empty()),
	rule('warrant?',
		[l('and'), 'warrant'],
		slot(1)),

	rule('warrant',
		['claim', 'conditions?'],
		template(Warrant, claim=slot(0), conditions=slot(1))),

	rule('warrant',
		['claim', 'exceptions'],
		template(Warrant,
			claim=slot(0),
			conditions=tlist(head=[
				template(WarrantCondition,
					claims=None,
					exceptions=slot(1)
				)
			])
		)
	),

	rule('conditions?',
		[],
		tlist()),
	rule('conditions?',
		['conditions'],
		slot(0)),
	
	] + and_rule('conditions', 'condition', l('or')) + [
	
	rule('condition',
		['condition_marker', 'claims', 'exceptions?'],
		template(WarrantCondition, claims=slot(1), exceptions=slot(2))),

	rule('condition_marker',
		[l('if')],
		empty()),

	rule('condition_marker',
		[l('when')],
		empty()),

	rule('exceptions?',
		[],
		tlist()),

	rule('exceptions?',
		['exceptions'],
		slot(0)),

	rule('exceptions',
		[l('unless'), 'unmarked_exceptions'],
		slot(1)),
	
	] + and_rule('unmarked_exceptions', 'unmarked_exception', l('or')) + [
	
	rule('unmarked_exception',
		['claims'],
		template(WarrantException, claims=slot(0))),

	rule('exceptions',
		[l('except'), 'marked_exceptions'],
		slot(1)),

	] + and_rule('marked_exceptions', 'marked_exception', l('or')) + [

	rule('marked_exception',
		['condition_marker', 'claims'],
		template(WarrantException, claims=slot(1))),
])


class Action(Claim):
	subject: Text
	verb: Text
	object: Claim

	def __init__(self, subject, verb, object):
		self.subject = subject
		self.verb = verb
		self.object = object
		super().__init__(text=subject + verb + object.text)
		

class prepend(object):
	def __init__(self, subject, object):
		self.subject = subject
		self.object = object

	def consume(self, args):
		return self._prepend(self.subject.consume(args), self.object.consume(args))

	def reverse(self, structure):
		all_texts = []
		self._apply(partial(self._find_text, all_texts), structure)

		word_tuples = zip(*(text.words for text in all_texts))
		prefix_tuples = takewhile(lambda x: all(x[0] == y for y in x), word_tuples)
		
		subject = Text(x[0] for x in prefix_tuples)
		object = self._apply(partial(self._remove, subject), structure)

		flat = sparselist()
		flat |= self.subject.reverse(subject)
		flat |= self.object.reverse(object)

		return flat

	def _find_text(self, list, object):
		if isinstance(object, Text):
			list.append(object)
		else:
			self._apply(partial(self._find_text, list), object)
	
	def _prepend(self, subject, object):
		if isinstance(object, Text):
			return subject + object
		else:
			return self._apply(partial(self._prepend, subject), object)

	def _remove(self, subject, object):
		if isinstance(object, Text):
			return object - subject
		else:
			return self._apply(partial(self._remove, subject), object)		

	def _apply(self, func, object):
		if hasattr(object, 'map'):
			return object.map(func)
		elif isinstance(object, tuple):
			return tuple(map(func, object))
		elif isinstance(object, list):
			return map(func, object)
		else:
			raise Exception("I can't prepend to {!r}".format(object))


# rules += ruleset([
# 	rule('warrant',
# 		['subject', l('who'), 'conditions', l('must'), 'claim', 'exceptions?'],
# 		template(Warrant,
# 			claim=template(Action, subject=slot(0), verb=Text(['must']), object=slot(4)),
# 			conditions=prepend(slot(0), slot(2)),
# 			exceptions=slot(5))),

# 	rule('claim',
# 		['subject', l('must'), 'claim'],
# 		template(Action, subject=slot(0), verb=Text(['must']), object=slot(2))),

# 	rule('subject',
# 		['word'],
# 		slot(0)),
# ])


def tokenize(markers, sentence):
	unit = []
	for token in re.findall(r"[\w'/]+|[.,!?;]", sentence):
		if token in markers:
			if len(unit) > 0:
				yield Text(unit)
				unit = []
			yield token
		else:
			unit.append(token)
	if len(unit) > 0:
		yield Text(unit)


def concatenate(tokens):
	string = ""
	for token in tokens:
		if len(string) > 0 and (not len(token) == 1 or token.isalpha()):
			string += " "
		if len(string) > 1 and string[-2] == '.':
			token = token[0].upper() + token[1:]
		string += token
	if len(string) > 1:
		string = string[0].upper() + string[1:]
	return string



def parse(sentence, start = 'sentences'):
	from hasl2.parser import Parser
	parser = Parser(rules)
	tokens = tokenize(rules.markers(), sentence)
	return parser.parse(start, tokens)


def reverse(tree, start = 'sentences'):
	from hasl2.parser import Parser
	parser = Parser(rules)
	for realisation in parser.reverse(start, tree):
		yield concatenate(map(str, realisation))


if __name__ == '__main__':
	from hasl2.parser import Parser
	from nlpg_lc import LCParser
	from pprint import pprint
	from sys import exit

	assert len(rules.missing()) == 0, "Missing rules for {!r}".format(rules.missing())

	print("Unreachable", end=": ")
	pprint(rules.unreachable())

	print("Markers", end=": ")
	pprint(rules.markers())

	parser = Parser(rules)

	class Test(object):
		def __init__(self, start, sentence, expected = None):
			self.start = start
			self.sentence = sentence
			self.expected = expected

		def test(self, runner):
			out = runner(self.sentence, start=self.start)
			if self.expected and out != self.expected:
				print("Expected ", end='')
				pprint(self.expected)

	def parse(sentence, start='sentence'):
		tokens = list(tokenize(rules.markers(), sentence))
		parse = parser.parse(start, tokens)
		parses = []
		print(tokens)
		for n, tree in enumerate(parse):
			print(n, end=': ')
			pprint(tree)
			parses.append(tree)

			for realisation in parser.reverse(start, tree):
				print(" ".join(map(str, realisation)))

		if hasattr(parse, 'counter'):
			print("Evaluated {} paths".format(parse.counter))
		return parses

	# parse('Tweety can fly because Tweety is a bird and animals can fly when they have wings unless they are a penguin .')
	# parse('The act is unlawful when someone\'s right is violated except when there is a justification .')
	# parse('The act is unlawful because someone\'s right was violated except there is a justification .')
	# parse('A suspect is innocent unless they are found guilty .')
	# parse('Claim A because claim B, claim C, and claim D.')
	# parse('the man who bested the king and took the throne or married the princess must reign the country.')
	# parse('A because B because C because D except E.')

	# parse('The ball is red when the material of the ball is red or when the light shining on it is red.')
	# parse('The ball is red if the ball looks red unless the light shining on it is red or if an expert says the ball is red except when the expert is not trustworthy or when the expert was misunderstood.')

	# Exception:
	parse('This ball is red because it looks red and balls are red when they look red except when the light is red.')

	# Undercutter :)
	parse('This ball is red because it looks red and balls are red when they look red except the light is red.')

	parse('A because B and C if D and E or if E and F.')


