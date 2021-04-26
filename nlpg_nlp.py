from typing import NamedTuple, List, Set, FrozenSet, Union, Any, Iterator

from pprint import pprint

import nlpg
from nlpg import Parser, \
	ruleset, rule, terminal, l, \
	empty, tlist, template, select, \
	relation, diagram, \
	NoMatchException

from nlpg_lc import LCParser

# nlpg.DEBUG=True


class sentence(NamedTuple):
	np: List
	vp: List


class prop(NamedTuple):
	subj: List
	verb: str
	obj: List


class tag(terminal):
	def __init__(self, tag):
		self.tag = tag

	def __repr__(self):
		return "<tag {}>".format(self.tag)

	def test(self, word):
		return word.tag_ == self.tag

	def consume(self, word):
		return word.text

	def reverse(self, word):
		if word is None:
			raise NoMatchException()
		return word


rules = ruleset([
	rule('sentence',
		['np(s)', 'vp(s)'],
		template(sentence, np=0, vp=1)),
	rule('sentence',
		['np(p)', 'vp(p)'],
		template(sentence, np=0, vp=1)),
	rule('np(s)',
		['det', 'jj', 'n(s)'],
		template(prop, subj=tlist(head=[0,2]), verb='is', obj=1)),
	rule('np(s)',
		['np(s)', tag('WDT'), 'vp(s)'],
		template(prop, subj=0, verb='is', obj=1)),
	rule('np(s)',
		['det', 'n(s)'],
		tlist(head=[0, 1])),
	rule('np(p)',
		['n(p)'],
		tlist(head=0)),
	rule('n(s)',
		[tag('NN')],
		select(0)),
	rule('n(p)',
		[tag('NNS')],
		select(0)),
	rule('det',
		[tag('DT')],
		select(0)),
	rule('det',
		[tag('DT')],
		select(0)),
	rule('vp(s)',
		['v(s)'],
		tlist(0)),
	rule('vp(s)',
		['md', 'v(inf)'],
		tlist(head=[0, 1])),
	rule('vp(s)',
		['vbz', 'jj'],
		tlist(head=[0, 1])),
	rule('vp(s)',
		['vbz', 'np(s)'],
		tlist(head=[0], tail=1)),
	rule('vp(p)',
		['v(p)'],
		tlist(0)),
	rule('v(s)',
		[tag('VBZ')],
		select(0)),
	rule('v(p)',
		[tag('VBP')],
		select(0)),
	rule('md',
		[tag('MD')],
		select(0)),
	rule('v(inf)',
		[tag('VB')],
		select(0)),
	rule('vbz',
		[tag('VBZ')],
		select(0)),
	rule('jj',
		[tag('JJ')],
		select(0)),
])

class Word(NamedTuple):
	text: str
	tag_: str

sentences = [
	('the red bird can fly', 'DT JJ NN MD VB'),
	('the bird that is red can fly', 'DT NN WDT VBZ JJ MD VB'),
	('the bird can fly', 'DT NN MD VB'),
]

if __name__ == '__main__':
	# import spacy
	# nlp = spacy.load('en')
	parser = LCParser(rules)
	for (sentence, tags) in sentences:
		# words = nlp(sentence)
		words = [Word(*pair) for pair in zip(sentence.split(' '), tags.split(' '))]

		print_sentence = []
		print_tokens = []

		for word in words:
			format = "{{:<{}}}".format(max(len(word.text), len(word.tag_)))
			print_sentence.append(format.format(word.text))
			print_tokens.append(format.format(word.tag_))

		print("Sentence: {}".format(" ".join(print_sentence)))
		print("Tokens:   {}".format(" ".join(print_tokens)))

		trees = set(parser.parse('sentence', words))
		for tree in trees:
			pprint(tree)
			for realisation in parser.reverse('sentence', tree):
				pprint(realisation)


