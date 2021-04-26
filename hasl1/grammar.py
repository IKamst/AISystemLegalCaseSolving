#!/usr/bin/env python

import sys
import traceback
import operator
import re
import inspect
from pprint import pprint
from functools import reduce
from itertools import chain
from typing import NamedTuple, Tuple

import spacy

import english
import parser
from parser import Rule, RuleRef, passthru, Continue


def coalesce(*args):
    for arg in args:
        if arg is not None:
            return arg
    return None


def unique(iter):
    seen = set()
    return tuple(item for item in iter if not (item in seen or seen.add(item)))


def merge(state, data):
    return reduce(operator.__add__, data)


def empty(state, data):
    return Span()


def indent(text, prefix='\t'):
    return '\n'.join(prefix + line for line in text.split('\n'))


def unique(seq):
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def singular_verb(verb):
    if len(verb.tokens) != 1:
        raise Exception('singular_verb can only process spans with one token')

    mapping = {
        'are': 'is',
        'can': 'can',
        'have': 'has',
    }
    singular = mapping[verb.text] if verb.text in mapping else verb.tokens[0].lemma_ + 's'
    return Span(verb.start, verb.end, [singular])


class Stamper(object):
    def __init__(self):
        self.seq = 0
        self.attr = '_id_stamp'

    def next(self):
        self.seq += 1
        return self.seq

    def read(self, obj):
        if not hasattr(obj, self.attr):
            raise Exception("Object {!r} has no id yet".format(obj))
        return getattr(obj, self.attr)

    def __call__(self, obj):
        if not hasattr(obj, self.attr):
            setattr(obj, self.attr, self.next())
        return getattr(obj, self.attr)


id = Stamper()


def print_pos_tags(doc):
    el_cnt = 3
    tokens = []
    for token in doc:
        tokens.append([
            str(token),
            str(token.pos_),
            str(token.tag_)
        ])
    
    lines = [[[] for _ in range(el_cnt)]]
    line_length = 0
    for token in tokens:
        token_length = max(len(el) for el in token)
        if line_length + token_length + 1 > 80:
            lines.append([[] for _ in range(el_cnt)])
            line_length = 0
        for n in range(el_cnt):
            lines[-1][n].append(token[n].ljust(token_length))
        line_length += token_length + 1

    for line in lines:
        for el_line in line:
            print(' '.join(el_line))
        print()


sentences = [
    'Socrates is mortal but Socrates is not mortal.',
    'Socrates is mortal but he is not mortal.',
    'Socrates is mortal because he is a man and men are mortal.',
    'Socrates is mortal because men are mortal and he is a man.',
    'Tweety can fly because Tweety is a bird and birds can fly. Tweety can fly but Tweety is a penguin.',
    'Tweety can fly because Tweety is a bird and birds can fly. Tweety is a bird but Tweety is a penguin.',
    'Tweety can fly because Tweety is a bird and birds can fly. birds can fly but Tweety is a penguin.',
    
    'Tweety can fly because Tweety is a bird and birds can fly but Tweety can not fly because Tweety is a penguin.',
    'Tweety can fly because Tweety is a bird and birds can fly but Tweety is a penguin and penguins can not fly.',
    
    'The object is red because the object appears red but it is illuminated by a red light.',
    'Harry is a British subject because Harry was born in Bermuda and a man born in Bermuda is a British subject because of the following statutes and legal provisions but Harry has become a naturalized American.',
];

# sentences = [
#     'Socrates is mortal because he is a man and he is not a god.',
#     'Socrates is mortal because he is a man and he is not a god because gods are not mortal.',
#     'Socrates is mortal because men are mortal.',
# ]

reed_sentences = [
    'Bob Sturges can not have a telephone because his name is not listed in the phone book.'
]

hasl0_sentences = [
    'Socrates is mortal because he is a man and men are mortal.',
    'The object is red because the object appears red but it is illuminated by a red light.',
    'Tweety can fly because he is a bird. He is a bird because he has wings.'
]

claims = [
    'Socrates is mortal',
    'he is a man',
    'men are mortal',
    'Tweety can fly',
    'Tweety is a bird',
    'birds can fly',
    'Tweety is a penguin',
    'penguins can not fly',
    'The object is red',
    'the object appears red',
    'it is illuminated by a red light',
    'Harry is a British subject',
    'Harry was born in Bermuda',
    'a man born in Bermuda is a British subject',
    'the following statutes and legal provisions',
    'Harry has become a naturalized American',
]


class Mapping(object):
    def __init__(self, entries = []):
        self.entries = dict(entries)
        for key in self.entries.keys():
            while id.read(self.entries[key]) != id.read(self.entries[id(self.entries[key])]):
                self.entries[key] = self.entries[id.read(self.entries[key])]

    def __add__(self, other):
        return Mapping(chain(self.entries.items(), other.entries.items()))

    def __getitem__(self, obj):
        if isinstance(obj, list):
            return list(self[el] for el in obj)
        else:
            return self.entries[id.read(obj)] if id(obj) in self.entries else obj

    def __setitem__(self, obj, replacement):
        self.entries[id(obj)] = replacement
        self.entries[id(replacement)] = replacement


class Span(object):
    def __init__(self, start = None, end = None, tokens = []):
        self.start = start
        self.end = end
        self.tokens = tokens

    def __add__(self, other):
        return Span(coalesce(self.start, other.start), coalesce(other.end, self.end), self.tokens + other.tokens)

    def __str__(self):
        return self.text

    def __repr__(self):
        return '"{}"[{},{}]'.format(self.text, self.start, self.end)

    def __eq__(self, other):
        return other is not None and self.text == other.text

    @property
    def pos(self):
        return slice(self.start, self.end)

    @property
    def text(self):
        return " ".join(str(token) for token in self.tokens)

    def map(self, callback):
        return self.__class__(self.start, self.end, callback(self.text).split(' '))


class Tag(parser.Symbol):
    def __init__(self, tag, exclude = frozenset()):
        self.tag = re.compile(tag)
        self.exclude = frozenset(exclude)

    def __repr__(self):
        return '<{}>'.format(self.tag.pattern)

    def test(self, literal, position, state):
        return self.tag.fullmatch(literal.tag_) and str(literal) not in self.exclude

    def finish(self, literal, position, state):
        return Span(position, position + 1, [literal])


class Literal(parser.Symbol):
    def __init__(self, literal, exclude = frozenset()):
        self.literal = re.compile(literal)
        self.exclude = frozenset(exclude)

    def __repr__(self):
        return '"{}"'.format(self.literal.pattern)

    def test(self, literal, position, state):
        return self.literal.fullmatch(str(literal)) and str(literal) not in self.exclude

    def finish(self, literal, position, state):
        return Span(position, position + 1, [literal])


if __name__ == '__main__':
    nlp = spacy.load('en', disable=['parser', 'ner', 'textcat'])

    def test(p, sentences):
        selection = frozenset(map(int, sys.argv[1:]))
        for n, sentence in enumerate(sentences, 1):
            if len(selection) > 0 and n not in selection:
                continue
            doc = nlp(sentence)
            print("{})".format(n))
            print_pos_tags(doc)
            try:
                parses = p.parse(doc)
                print("There are {} parses".format(len(parses)))
                datas = set(parse['data'] for parse in parses)
                pprint(datas)
                # for parse in parses:
                #     print("Parse:")
                #     pprint(parse['data'])
                #     print("Tree:")
                #     pprint(parse['tree'])

            except parser.ParseError as e:
                print("Failure: {}".format(e))
            print()
else:
    def test(p, sentences):
        """test as a no-op when pos_tags is loaded as library"""
        pass

class Entity(object):
    def __init__(self, name = None, noun = None, pronoun = None):
        self.name = name
        self.noun = noun
        self.pronoun = pronoun

    def __str__(self):
        return str(self.span) if self.span else 'something'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return self.name == other.name \
            and self.noun == other.noun \
            and self.pronoun == other.pronoun

    def __repr__(self):
        return "({} name={name} noun={noun} pronoun={pronoun})".format(id(self), **self.__dict__)

    @property
    def span(self):
        if self.name is not None:
            return self.name
        if self.noun is not None:
            return self.noun
        if self.pronoun is not None:
            return self.pronoun
        else:
            return None

    @property
    def pos(self):
        parts = [self.name, self.noun, self.pronoun]
        positions = [part.pos for part in parts if part is not None]
        return min(positions) if len(positions) > 0 else None

    def merge(self, other):
        """Merge this instance with one that refers to me"""
        return Entity(
            name = self.name,
            noun = self.noun if self.noun is not None else other.noun,
            pronoun = self.pronoun if self.pronoun is not None else other.pronoun)

    def refers_to(self, other):
        """Test whether this instance refers to a (better defined) other instance"""
        if self.name:
            return self.name == other.name
        elif self.noun:
            return self.noun == other.noun
        elif self.pronoun:
            if other.pronoun:
                return self.pronoun == other.pronoun
            else:
                return other.name is not None or other.noun is not None
        else:
            return False



class Claim(object):
    def __init__(self, subj, verb, negated=False, assumed=False, file=None, line=None):
        self.subj = subj
        self.verb = verb
        self.negated = negated
        self.assumed = assumed
        if file is not None:
            self.file = file
            self.line = line
        else:
            previous_frame = inspect.currentframe().f_back
            (self.file, self.line, *_) = inspect.getframeinfo(previous_frame)

    def __eq__(self, other):
        return str(self).lower() == str(other).lower()

    def __str__(self):
        return "{subj} {verb}".format(neg="not " if self.negated else "", **self.__dict__)

    def __repr__(self):
        return "{ass}{subj} {verb} ({file}:{line})".format(ass="assume " if self.assumed else "", neg = "not " if self.negated else "", **self.__dict__)

    def __hash__(self):
        return hash(str(self))

    @property
    def tooltip(self):
        return "Created in {}: {}".format(self.file, self.line)

    @property
    def entities(self):
        if isinstance(self.subj, Entity):
            yield self.subj

    def counters(self, other):
        return self.subj == other.subj \
            and self.verb == other.verb \
            and self.negated != other.negated

    def update(self, mapping):
        return Claim(mapping[self.subj], mapping[self.verb], negated=self.negated, assumed=self.assumed, file=self.file, line=self.line)


class Relation(object):
    arrows = {
        'attack': '~*',
        'support': '~>'
    }

    def __init__(self, type, sources, target, file=None, line=None):
        assert type in self.arrows
        self.type = type
        
        assert all(isinstance(source, Claim) for source in sources)
        assert len(sources) > 0
        self.sources = tuple(sources)

        assert isinstance(target, Claim) or isinstance(target, Relation)
        self.target = target

        if file is not None:
            self.file = file
            self.line = line
        else:
            previous_frame = inspect.currentframe().f_back
            (self.file, self.line, *_) = inspect.getframeinfo(previous_frame)

    def __str__(self):
        return "({} {} {})".format(' ^ '.join(str(s) for s in self.sources), self.arrows[self.type], self.target)

    def __repr__(self):
        return "({} {} {}) ({}:{})".format(self.sources, self.arrows[self.type], self.target, self.file, self.line)

    def __hash__(self):
        return hash((self.type, self.sources, self.target))

    def __eq__(self, other):
        return isinstance(other, Relation) \
            and self.type == other.type \
            and frozenset(self.sources) == frozenset(other.sources) \
            and self.target == other.target

    def update(self, mapping):
        return Relation(self.type,
            sources = unique(mapping[source] for source in self.sources),
            target = mapping[self.target],
            file = self.file, line = self.line)


class Consolidation(NamedTuple):
    claims: Tuple[Claim, ...]
    relations: Tuple[Relation, ...]
    mapping: Mapping


class Argument(object):
    def __init__(self, claims = tuple(), relations = tuple()):
        assert all(isinstance(claim, Claim) for claim in claims)
        assert all(isinstance(relation, Relation) for relation in relations)
        consolidation = self.__class__.consolidate(claims, relations)
        self.claims = consolidation.claims
        self.relations = consolidation.relations

    @property
    def roots(self):
        roots = [claim for claim in self.claims if all(claim not in relation.sources or all(source == relation.target for source in relation.sources) for relation in self.relations)]
        if len(roots) == 0:
            print(repr(self))
            raise Exception('Cannot determine roots of argument')
        return roots

    @property
    def root(self):
        return self.roots[0]

    def __repr__(self):
        return "Claims:\n{}\nRelations:\n{}".format(
            indent("\n".join(repr(p) for p in self.claims), "  "),
            indent("\n".join(repr(r) for r in self.relations), "  "))

    def __add__(self, other):
        return self.__class__(claims = self.claims + other.claims, relations = self.relations + other.relations)

    def __hash__(self):
        return hash((self.claims, self.relations))

    def __eq__(self, other):
        return isinstance(other, Argument) \
            and frozenset(self.claims) == frozenset(other.claims) \
            and frozenset(self.relations) == frozenset(other.relations)

    @staticmethod
    def consolidate(claims, relations):
        def replace(old, new, list):
            old_ids = frozenset(id(el) for el in old)
            for el in list:
                if id(el[1]) in old_ids:
                    el[1] = new

        entities = [[id(entity), entity] for entity in sorted((entity for entity in chain.from_iterable(claim.entities for claim in claims) if entity.pos is not None), key=lambda entity: entity.pos)]

        c = len(entities)
        for m, entity in enumerate(entities[:c]):
            for n, other_entity in enumerate(entities[m+1:c], m+1):
                result = other_entity[1].refers_to(entity[1])
                # print("Does {!r} ({}) refer to {!r} ({}): {!r}".format(other_entity[1], id(other_entity[1]), entity[1], id(entity[1]), result))
                if result:
                    merged = entity[1].merge(other_entity[1])
                    entities.append([id(merged), merged])
                    replace((entity[1], other_entity[1]), merged, entities)

        mapping = Mapping(entities)

        entries = [[id(claim), claim] for claim in claims]

        # Update all claims with the new entities
        for entry in entries[0:len(entries)]: # to prevent iterating over new items
            updated = entry[1].update(mapping)
            entry[1] = updated
            entries.append([id(updated), updated])

        # Merge all claims that are (or have become) equal
        for m, entry in enumerate(entries):
            for n, other_entry in enumerate(entries[m:], m):
                if entry[1] == other_entry[1]:
                    entries[n][1] = entry[1]

        mapping += Mapping(entries)
        
        new_relations = []
        for i, relation in enumerate(relations):
            updated = relation.update(mapping)
            new_relations.append(updated)
            mapping[relation] = updated

        return Consolidation(
            claims=tuple(entry[1] for entry in entries if entry[0] == id(entry[1])),
            relations=tuple(new_relations),
            mapping=mapping)


class Grammar(object):
    def __init__(self, rules = None):
        self.rules = rules if rules is not None else []

    def __iter__(self):
        return iter(self.rules)

    def __add__(self, other):
        return self.__class__(list(self.rules) + list(other))

    def without(self, names):
        return self.__class__(rule for rule in self.rules if rule.name not in names)

    def rule(self, name, symbols):
        previous_frame = inspect.currentframe().f_back
        (filename, line_number, function_name, lines, index) = inspect.getframeinfo(previous_frame)
        rule = Rule(name, symbols, file=filename, line=line_number)
        self.rules.append(rule)
        def wrapper(callback):
            rule.callback = lambda state, data: callback(*data)
            return callback
        return wrapper


en_grammar = Grammar([
    Rule('name', [Tag('NNP')], merge),
    Rule('name', [RuleRef('name'), Tag('NNP')], merge), # longer names
    Rule('name', [RuleRef('name'), Tag('NNPS')], merge), # Catholic Swedes
    Rule('name', [Literal('Tweety')], merge),
    
    Rule('instance', [RuleRef('name')],
        lambda state, data: Entity(name=data[0])),
    Rule('instance', [Tag('PRP')], # "I"
        lambda state, data: Entity(pronoun=data[0])),
    Rule('instance', [RuleRef('def-dt'), RuleRef('adjectives?'), RuleRef('noun')],
        lambda state, data: Entity(noun=data[0] + data[1] + data[2])),
    Rule('instance', [RuleRef('def-dt'), RuleRef('adjectives?'), RuleRef('noun'), RuleRef('prep-phrase')],
        lambda state, data: Entity(noun=data[0] + data[1] + data[2] + data[3])),
    Rule('instance', [Tag('PRP\\$'), RuleRef('noun')], # his name
        lambda state, data: Entity(noun=data[0] + data[1])),

    Rule('adjectives?', [RuleRef('adjectives')], merge),
    Rule('adjectives?', [], empty),

    Rule('adjectives', [Tag('JJ')], merge),
    Rule('adjectives', [Tag('JJ'), RuleRef('adjectives')], merge),

    Rule('noun-sg', [Tag('NN')], merge),
    Rule('noun-sg', [RuleRef('noun'), Tag('NN')], merge),

    Rule('noun-pl', [Tag('NNS')], merge),
    Rule('noun-pl', [RuleRef('noun'), Tag('NNS')], merge),

    Rule('noun', [RuleRef('noun-sg')], merge),
    Rule('noun', [RuleRef('noun-pl')], merge),

    Rule('dt?', [RuleRef('dt')], passthru), # Matches the optional qualifier (i.e. all, some, most)
    Rule('dt?', [], empty), # And matches if there is no qualifier

    Rule('dt', [Tag('DT', exclude={'no'})], merge),

    Rule('noun-phrase?', [RuleRef('noun-phrase')], passthru),
    Rule('noun-phrase?', [], empty),
    
    Rule('noun-phrase', [RuleRef('name')], merge),
    Rule('noun-phrase', [RuleRef('noun')], merge),
    Rule('noun-phrase', [RuleRef('instance')], lambda state, data: data[0].span),
    Rule('noun-phrase', [RuleRef('dt'), RuleRef('adjectives?'), RuleRef('noun')], merge),
    Rule('noun-phrase', [RuleRef('dt'), RuleRef('adjectives?'), RuleRef('name')], merge),
    # Rule('noun-phrase', [RuleRef('vbn')], merge), # (is) born, (can) fly
    Rule('noun-phrase', [RuleRef('noun-phrase'), RuleRef('vbn')], merge), # a man born in Bermuda
    Rule('noun-phrase', [RuleRef('noun-phrase'), RuleRef('prep-phrase')], merge), # an act of John

    Rule('noun-phrase', [Tag('VBG'), RuleRef('noun-phrase')], merge), # encouraging waste

    Rule('noun-phrase', [Tag('JJR?'), Tag('IN'), Tag('CD'), Tag('NN')], merge), # less than 2%

    Rule('prototype-sg', [RuleRef('indef-dt'), RuleRef('adjectives?'), RuleRef('noun-sg'), RuleRef('vbn')], merge),
    Rule('prototype-sg', [RuleRef('indef-dt'), RuleRef('adjectives?'), RuleRef('noun-sg'), RuleRef('prep-phrase?'), RuleRef('that-phrase-sg?')], merge),
    
    Rule('prototype-pl', [RuleRef('dt?'), RuleRef('adjectives?'), RuleRef('noun-pl'), RuleRef('vbn')],
        lambda state, data: Span(None, None, ['a']) + data[1] + data[2].map(english.singularize) + data[3]),
    
    Rule('prototype-pl', [RuleRef('dt?'), RuleRef('adjectives?'), RuleRef('noun-pl'), RuleRef('prep-phrase?')],
        lambda state, data: Span(None, None, ['a']) + data[1] + data[2].map(english.singularize) + data[3]),

    Rule('vbn', [Tag('VBN')], passthru),
    Rule('vbn', [Tag('VBN'), RuleRef('prep-phrase')], merge),

    Rule('prep-phrase?', [RuleRef('prep-phrase')], passthru),
    Rule('prep-phrase?', [], empty),

    Rule('prep-phrase', [Tag('IN'), RuleRef('noun-phrase')], merge), # for "by a red light"

    Rule('that-phrase-sg?', [RuleRef('that-phrase-sg')], passthru),
    Rule('that-phrase-sg?', [], empty),

    Rule('that-phrase-sg', [Tag('WDT'), RuleRef('verb-phrase-sg')], merge), # "that appears red"
    Rule('that-phrase-pl', [Tag('WDT'), RuleRef('verb-phrase-pl')], merge), # "that appear red"

    Rule('def-dt', [Literal('[Tt]he')], passthru),
    Rule('def-dt', [Literal('[Tt]his')], passthru),

    Rule('indef-dt', [Literal('[Aa]n?')], passthru),

    Rule('sentences',   [RuleRef('sentences'), RuleRef('sentence')], merge),
    Rule('sentences',   [RuleRef('sentence')], passthru),
    Rule('sentence',    [RuleRef('argument'), Literal('.')], passthru),

    Rule('verb-sg', [Tag('VBZ')], merge), # is, has, appears
    Rule('verb-pl', [Tag('VBP')], lambda state, data: singular_verb(data[0])), # are, have

    Rule('verb-sg', [Tag('VBD')], merge), # became
    Rule('verb-pl', [Tag('VBD')], merge), # became

    Rule('verb-sg', [Tag('MD'), Tag('VB')], merge), # can fly
    Rule('verb-pl', [Tag('MD'), Tag('VB')], merge), # can fly

    Rule('verb-sg', [Tag('MD'), Tag('VB'), Tag('VBN')], merge), # should be abolished
    Rule('verb-pl', [Tag('MD'), Tag('VB'), Tag('VBN')], merge), # should be abolished
    
    Rule('verb-sg', [Tag('VBZ'), Tag('VBN')], merge), # has eaten
    Rule('verb-pl', [Tag('VBP'), Tag('VBN')], lambda state, data: singular_verb(data[0]) + data[1]), # are, have eaten

    Rule('verb-sg', [Tag('VBZ'), Tag('VBN'), Tag('VBN')], merge), # has become naturalized
    Rule('verb-pl', [Tag('VBP'), Tag('VBN'), Tag('VBN')], lambda state, data: singular_verb(data[0]) + data[1] + data[2]), # have become naturalized
    
    Rule('neg-verb-sg', [Tag('MD'), Literal('not'), Tag('VB')], merge), # can not fly, should not swim
    Rule('neg-verb-pl', [Tag('MD'), Literal('not'), Tag('VB')], merge), # can not fly

    Rule('neg-verb-sg', [Tag('VBZ'), Literal('not?')], merge), # has no, is not
    Rule('neg-verb-pl', [Tag('VBP'), Literal('not?')], lambda state, data: singular_verb(data[0]) + data[1]), # have no, are not

    Rule('verb-phrase-sg', [RuleRef('verb-sg'), RuleRef('noun-phrase?'), RuleRef('prep-phrase?')], merge), # can fly (a plane) (in the sky)
    Rule('verb-phrase-pl', [RuleRef('verb-pl'), RuleRef('noun-phrase?'), RuleRef('prep-phrase?')], merge),

    Rule('verb-phrase-sg', [RuleRef('verb-sg'), RuleRef('adjectives'), RuleRef('prep-phrase?')], merge), # appears red
    Rule('verb-phrase-pl', [RuleRef('verb-pl'), RuleRef('adjectives'), RuleRef('prep-phrase?')], merge), # appear red

    Rule('neg-verb-phrase-sg', [RuleRef('neg-verb-sg'), RuleRef('noun-phrase?')], merge), # cannot fly a plane
    Rule('neg-verb-phrase-pl', [RuleRef('neg-verb-pl'), RuleRef('noun-phrase?')], merge), # cannot fly a plane

    Rule('neg-verb-phrase-sg', [RuleRef('neg-verb-sg'), RuleRef('adjectives'), RuleRef('prep-phrase?')], merge), # appears not red, is not mortal
    Rule('neg-verb-phrase-pl', [RuleRef('neg-verb-pl'), RuleRef('adjectives'), RuleRef('prep-phrase?')], merge), # appear not red, are not mortal
])

hasl0_grammar = en_grammar + [
    Rule('specific-claim', [RuleRef('instance'), RuleRef('verb-phrase-sg')], # Tweety has a wing, Tweety is a bird
        lambda state, data: Claim(data[0], data[1])),
    Rule('specific-claim', [RuleRef('instance'), RuleRef('neg-verb-phrase-sg')], # Tweety has a wing, Tweety is a bird
        lambda state, data: Claim(data[0], data[1], negated=True)),
    Rule('specific-claim', [RuleRef('instance'), RuleRef('verb-phrase-pl')],
        lambda state, data: Claim(data[0], data[1])),
    
    Rule('general-claim', [RuleRef('prototype-sg'), RuleRef('verb-phrase-sg')],
        lambda state, data: Claim(data[0], data[1])),
    Rule('general-claim', [RuleRef('prototype-pl'), RuleRef('verb-phrase-pl')],
        lambda state, data: Claim(data[0], data[1])),
    
    Rule('claim', [RuleRef('general-claim')], passthru),
    Rule('claim', [RuleRef('specific-claim')], passthru),


    Rule('specific-claims', [RuleRef('specific-claim')],
        lambda state, data: (data[0],)),
    Rule('specific-claims', [RuleRef('specific-claim-list'), Literal('and'), RuleRef('specific-claim')],
        lambda state, data: (*data[0], data[2])),
    Rule('specific-claim-list', [RuleRef('specific-claim')],
        lambda state, data: (data[0],)),
    Rule('specific-claim-list', [RuleRef('specific-claim-list'), Literal(','), RuleRef('specific-claim')],
        lambda state, data: (*data[0], data[2])),

    Rule('argument',    [RuleRef('support')], passthru),
    Rule('argument',    [RuleRef('attack')], passthru),
    Rule('argument',    [RuleRef('warranted-support')], passthru),
    Rule('argument',    [RuleRef('undercutter')], passthru),
]

@hasl0_grammar.rule('support', [RuleRef('claim'), Literal('because'), RuleRef('specific-claims')])
def support(conclusion, marker, specifics):
    """a <~ b+"""
    return Argument(claims=(conclusion,) + specifics, relations=(Relation('support', specifics, conclusion),))

@hasl0_grammar.rule('attack', [RuleRef('claim'), Literal('but'), RuleRef('specific-claims')])
def support(conclusion, marker, specifics):
    """a *- b+"""
    return Argument(claims=(conclusion, *specifics), relations=[Relation('attack', specifics, conclusion)])

@hasl0_grammar.rule('warranted-support', [RuleRef('claim'), Literal('because'), RuleRef('specific-claim-list'), Literal('and'), RuleRef('general-claim')])
def warranted_support_specific_general(conclusion, marker, specifics, conj, general):
    """(a <~ b+) <~ c"""
    support = Relation('support', specifics, conclusion)
    warrant = Relation('support', (general,), support)
    return Argument(claims=(conclusion, *specifics, general), relations=(support, warrant))

@hasl0_grammar.rule('warranted-support', [RuleRef('claim'), Literal('because'), RuleRef('general-claim'), Literal('and'), RuleRef('specific-claims')])
def warranted_support_general_specific(conclusion, marker, general, conj, specifics):
    """(a <~ c+) <~ b"""
    support = Relation('support', specifics, conclusion)
    warrant = Relation('support', (general,), support)
    return Argument(claims=(conclusion, general, *specifics), relations=(support, warrant))

@hasl0_grammar.rule('warranted-attack', [RuleRef('claim'), Literal('because'), RuleRef('specific-claim-list'), Literal('and'), RuleRef('general-claim')])
def warranted_attack_specific_general(conclusion, marker, specifics, conj, general):
    """(a <~ b+) <~ c"""
    attack = Relation('attack', specifics, conclusion)
    warrant = Relation('support', (general,), attack)
    return Argument(claims=(conclusion, *specifics, general), relations=(attack, warrant))

@hasl0_grammar.rule('warranted-attack', [RuleRef('claim'), Literal('because'), RuleRef('general-claim'), Literal('and'), RuleRef('specific-claims')])
def warranted_attack_general_specific(conclusion, marker, general, conj, specifics):
    """(a <~ c+) <~ b"""
    attack = Relation('attack', specifics, conclusion)
    warrant = Relation('support', (general,), attack)
    return Argument(claims=(conclusion, general, *specifics), relations=(attack, warrant))


"""
> (a because b) but c: (a<~b)<~c
Tweety is a bird because Tweety can fly but planes can also fly
Tweety is a bird because Tweety can fly but Tweety was thrown
Conclusie: zinloos om iets achter te zetten -> geval apart. Also de enige manier om deze te construeren.
"""
@hasl0_grammar.rule('undercutter', [RuleRef('claim'), Literal('because'), RuleRef('specific-claims'), Literal('but'), RuleRef('claim')])
def undercutter(conclusion, because, specifics, but, attack):
    """(a <~ b+) *- c (c can be both specific and general)"""
    support = Relation('support', specifics, conclusion)
    undercutter = Relation('attack', (attack,), support)
    return Argument(claims=(conclusion, *specifics, attack), relations=(support, undercutter))

# test(parser.Parser(hasl0_grammar, 'sentences'), hasl0_sentences)

###
### Recursion
###

hasl1_grammar = hasl0_grammar.without({'argument', 'general-claim'}) + [
    Rule('argument',    [RuleRef('specific-argument')], passthru),
    Rule('argument',    [RuleRef('general-argument')], passthru),
]

@hasl1_grammar.rule('specific-arguments', [RuleRef('specific-argument')])
def hasl1_argued_specific_claims_single(specific):
    return specific

@hasl1_grammar.rule('specific-arguments', [RuleRef('specific-claim-list'), Literal('and'), RuleRef('specific-argument')])
def hasl1_argued_specific_claims_multiple(list, conj, specific):
    return Argument(claims=[*list, *specific.claims], relations=specific.relations)

@hasl1_grammar.rule('specific-claim-list', [RuleRef('specific-claim')])
def hasl1_specific_claims_list_single(specific):
    return (specific,)

@hasl1_grammar.rule('specific-claim-list', [RuleRef('specific-claim-list'), Literal(','), RuleRef('specific-claim')])
def hasl1_specific_claims_list_multiple(list, conj, specific):
    return (*list, specific)


# @hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('specific-arguments')])
# def hasl1_support_specific(conclusion, because, specifics):
#     """a <~ b+"""
#     support = Relation('support', specifics.roots, conclusion)
#     return Argument(claims=[conclusion, *specifics.claims], relations=[support, *specifics.relations])

@hasl1_grammar.rule('general-argument', [RuleRef('general-claim'), Literal('because'), RuleRef('specific-arguments')])
def hasl1_support_general(conclusion, because, specifics):
    """A <~ b+"""
    support = Relation('support', specifics.roots, conclusion)
    return Argument(claims=[conclusion, *specifics.claims], relations=[support, *specifics.relations])

@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('general-claim'), Literal('and'), RuleRef('specific-arguments')])
def hasl1_warranted_support_general_specific(conclusion, because, general, conj, specifics):
    """(a <~ c) <~ B"""
    support = Relation('support', specifics.roots, conclusion)
    warrant = Relation('support', [general], support)
    return Argument(claims=[conclusion, general, *specifics.claims], relations=[support, warrant, *specifics.relations])

@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('specific-claim-list'), Literal('and'), RuleRef('general-argument')])
def hasl1_warranted_support_specific_general(conclusion, because, specifics, conj, general):
    """(a <~ b) <~ C"""
    support = Relation('support', specifics, conclusion)
    warrant = Relation('support', [general.root], support)
    return Argument(claims=[conclusion, *specifics, *general.claims], relations=[*general.relations, support, warrant])

@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('general-claim'), Literal('and'), RuleRef('specific-arguments'), Literal('but'), RuleRef('specific-argument')])
def hasl1_warranted_support_general_specific_undercutter(conclusion, because, general, conj, specifics, but, undercutter):
    """((a <~ c) <~ B) *- D"""
    support = Relation('support', specifics.roots, conclusion)
    warrant = Relation('support', [general], support)
    attack = Relation('attack', undercutter.roots, support)
    return Argument(claims=[conclusion, general, *specifics.claims, *undercutter.claims], relations=[support, warrant, attack, *specifics.relations, *undercutter.relations])

@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('specific-claim-list'), Literal('and'), RuleRef('general-argument'), Literal('but'), RuleRef('specific-argument')])
def hasl1_warranted_support_specific_general_undercutter(conclusion, because, specifics, conj, general, but, undercutter):
    """((a <~ b) <~ C) *- D"""
    support = Relation('support', specifics, conclusion)
    warrant = Relation('support', [general.root], support)
    attack = Relation('attack', undercutter.roots, support)
    return Argument(claims=[conclusion, *specifics, *general.claims, *undercutter.claims], relations=[*general.relations, support, warrant, attack, *undercutter.relations])



# a because b and because c?
# <specific-argument> ::= <specific-claim> <reasons>

# <reasons> ::= <reason-list> `and' <reason>

# <reason-list> ::= <reason-list> `,' <reason>
# \alt <reason>

# <reason> ::= `because' <specific-argument>

@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), RuleRef('reasons')])
def hasl1_minr_argument_support_reasons(conclusion, reasons):
    reasons_claims = reduce(lambda claims, reason: claims + reason, reasons, tuple())
    supports = list(Relation('support', reason, conclusion) for reason in reasons)
    return Argument(claims=[conclusion, *reasons_claims], relations=[*supports])

@hasl1_grammar.rule('reasons', [RuleRef('reason-list'), Literal('and'), RuleRef('reason')])
def hasl1_reasons(reasons, conj, reason):
    return (*reasons, reason)

@hasl1_grammar.rule('reason-list', [RuleRef('reason-list'), Literal(','), RuleRef('reason')])
def hasl1_reasonlist_recursive(reasons, conj, reason):
    return (*reasons, reason)

@hasl1_grammar.rule('reason-list', [RuleRef('reason')])
def hasl1_reasonlist_base_case(reason):
    return (reason,)

@hasl1_grammar.rule('reason', [Literal('because'), RuleRef('specific-claims')])
def hasl1_reason(because, claims):
    return claims


@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim')])
def hasl1_specific_claim(specific):
    """a"""
    return Argument(claims=[specific])

@hasl1_grammar.rule('general-argument', [RuleRef('general-claim')])
def hasl1_general_claim(general):
    """A"""
    return Argument(claims=[general])


@hasl1_grammar.rule('specific-argument', [RuleRef('specific-argument'), Literal('but'), RuleRef('specific-argument')])
def hasl1_attack_specific(conclusion, but, specific):
    """a *- b but a can also be argued"""
    attacks = [Relation('attack', specific.roots, conclusion.root)]
    return Argument(claims=[*conclusion.claims, *specific.claims], relations=[*conclusion.relations, *specific.relations, *attacks])

# def hasl1_attack_specific(conclusion, but, specific):
#     """a *- b but a can also be argued"""
#     merged = (conclusion + specific).consolidate()
#     if merged.mapping[conclusion.root].counters(merged.mapping[specific.root]):
#         attacks = [
#             Relation('attack', [specific.root], conclusion.root),
#             Relation('attack', [conclusion.root], specific.root)
#         ]
#     else:
#         attacks = [
#             Relation('attack', [specific.root], conclusion.root),
#         ]
#     return Argument(claims=[*conclusion.claims, *specific.claims], relations=[*conclusion.relations, *specific.relations, *attacks])


@hasl1_grammar.rule('general-argument', [RuleRef('general-argument'), Literal('but'), RuleRef('argument')])
def hasl1_attack_general(conclusion, but, specific):
    """A *- b but A can also be argued"""
    assert len(conclusion.roots) == 1, 'Attacked claim has multiple root claims'
    attack = Relation('attack', specific.roots, conclusion.root)
    return Argument(claims=[*conclusion.claims, *specific.claims], relations=[*conclusion.relations, *specific.relations, attack])

###
### Enthymeme
###

class GeneralClaim(Claim):
    def __init__(self, *args, conditions=tuple(), file=None, line=None, **kwargs):
        if file is None:
            previous_frame = inspect.currentframe().f_back
            (file, line, *_) = inspect.getframeinfo(previous_frame)
        super().__init__(*args, file=file, line=line, **kwargs)
        self.conditions = tuple(conditions)

    def __str__(self):
        return super().__str__() + ' if ' + english.join(self.conditions)

    def update(self, mapping):
        return GeneralClaim(mapping[self.subj], mapping[self.verb],
            negated=self.negated,
            assumed=self.assumed,
            file=self.file,
            line=self.line,
            conditions=tuple(condition.update(mapping) for condition in self.conditions))

@hasl1_grammar.rule('general-claim', [RuleRef('prototype-sg'), RuleRef('verb-phrase-sg')])
def hasl1_general_claim_vbp(cond, vp):
    """Parse general claim as rule: a man is mortal"""
    subj = Entity()
    return GeneralClaim(subj, vp, conditions=(Claim(subj, Span(None, None, ['is']) + cond),))

@hasl1_grammar.rule('general-claim', [RuleRef('prototype-sg'), RuleRef('neg-verb-phrase-sg')])
def hasl1_negated_general_claim_vbp(cond, vp):
    """Parse general claim as rule: a man is mortal"""
    subj = Entity()
    return GeneralClaim(subj, vp, conditions=(Claim(subj, Span(None, None, ['is']) + cond),), negated=True)

@hasl1_grammar.rule('general-claim', [RuleRef('prototype-pl'), RuleRef('verb-phrase-pl')])
def hasl1_general_claim_vbp(cond, vp):
    """Parse general claim as rule: men are mortal"""
    subj = Entity()
    return GeneralClaim(subj, vp, conditions=(Claim(subj, Span(None, None, ['is']) + cond),))

@hasl1_grammar.rule('general-claim', [RuleRef('prototype-pl'), RuleRef('neg-verb-phrase-pl')])
def hasl1_negated_general_claim_vbp(cond, vp):
    """Parse general claim as rule: men are not mortal"""
    subj = Entity()
    return GeneralClaim(subj, vp, conditions=(Claim(subj, Span(None, None, ['is']) + cond),), negated=True)

##
## Real enthymeme resolution rules
##

@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('general-argument')])
def hasl1_support_general_missing_specific(conclusion, because, general):
    specifics = [Claim(conclusion.subj, condition.verb, negated=condition.negated, assumed=True) for condition in general.root.conditions]
    support = Relation('support', specifics, conclusion)
    warrant = Relation('support', [general.root], support)
    return Argument(claims=[conclusion, *general.claims, *specifics], relations=[*general.relations, support, warrant])


@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('specific-arguments')])
def hasl1_support_general_missing_general(conclusion, because, specifics):
    try:
        # Special case: if the specific is the conclusion, but only assumed, just pass it on including the conclusion
        # which will override the assumed conclusion.
        if len(specifics.roots) == 1 and specifics.root == conclusion:
            raise Continue('A because A')
        subj = Entity()
        conditions = [Claim(subj, specific.verb, negated=specific.negated, assumed=True) for specific in specifics.roots]
        general = GeneralClaim(subj, conclusion.verb, negated=conclusion.negated, conditions=tuple(conditions), assumed=True)
        support = Relation('support', specifics.roots, conclusion)
        warrant = Relation('support', [general], support)
        return Argument(claims=[general, conclusion, *specifics.claims], relations=[*specifics.relations, support, warrant])
    except:
        raise Continue("could not combine {!r} with {!r}".format(conclusion, specifics))


@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim'), Literal('because'), RuleRef('specific-arguments'), Literal('but'), RuleRef('specific-argument')])
def hasl1_support_general_missing_general_with_undercutter(conclusion, because, specifics, but, attack):
    """(a <~ b) <~ C"""
    if len(specifics.roots) == 1 and specifics.root == conclusion:
        raise Continue('A because A')

    subj = Entity()
    conditions = [Claim(subj, specific.verb, negated=specific.negated, assumed=True) for specific in specifics.roots]
    general = GeneralClaim(subj, conclusion.verb, negated=conclusion.negated, conditions=tuple(conditions), assumed=True)
    support = Relation('support', specifics.roots, conclusion)
    warrant = Relation('support', [general], support)
    undercutter = Relation('attack', attack.roots, support)
    return Argument(claims=[general, conclusion, *specifics.claims, *attack.claims], relations=[*specifics.relations, *attack.relations, support, warrant, undercutter])


@hasl1_grammar.rule('specific-argument', [RuleRef('specific-claim-list'), Literal('and'), RuleRef('general-argument')])
def hasl1_support_general_missing_conclusion(specifics, conj, general):
    try:
        subj = specifics[0].subj
        conclusion = Claim(subj, general.root.verb, negated=general.root.negated, assumed=True)
        expected_specifics = [Claim(subj, condition.verb, negated=condition.negated, assumed=True) for condition in general.root.conditions]
        support = Relation('support', [*specifics, *expected_specifics], conclusion)
        warrant = Relation('support', [general.root], support)
        return Argument(claims=[*specifics, *expected_specifics, *general.claims, conclusion], relations=[*general.relations, support, warrant])
    except:
        raise Continue("could not combine {!r} with {!r}".format(specifics, general))

"""
> a because (b but c): a<~b; b*-c
Tweety can fly because Tweety is a bird but Tweety is a dog.
Tweety can fly because Tweety is a bird but Tweety is a dog because birds do not have teeth because they have a beak.
-> a because (b but (c because (d because e)))
Conclusie: b but c returnt b.

> (a because b).conclusion but c: a<~b; a*-c
Tweety can fly because Tweety is a bird but Tweety is a penguin because Tweety has these features.
(a because b).conclusion but (c because d).conclusion
Conclusie: a because b returnt a.

en eigenlijk ook nog
a because b but c: (a<~x)<~b & alle bovenstaande varianten?

(a because (b because (c because d)))
"""

# test(parser.Parser(hasl1_grammar, 'sentences'), sentences)

##
## Evaluation
##

# test(parser.Parser(hasl1_grammar, 'sentences'), [
#     'Socrates is mortal because he is a man and men are mortal.',
#     'Socrates is mortal because he is a man.',
#     'Socrates is mortal because men are mortal.',
#     'Socrates is a man and men are mortal.',
# ])

test(parser.Parser(hasl1_grammar, 'sentences'), [
    # 'Tweety can fly because birds can fly but Tweety is a penguin.',
    # 'Tweety can fly because Tweety is a bird but Tweety is a penguin.',
    'Birds can fly but Tweety can not fly because Tweety is a penguin.',
    # 'The object is red because the object appears red to me but it is illuminated by a red light.'
])

# test(parser.Parser(hasl1_grammar, 'sentences'), [
#     'Petersen will not be a Roman Catholic because he is a Swede and a Swede can be taken almost certainly not to be a Roman Catholic because the proportion of Roman Catholic Swedes is less than 2%.'
# ])

# test(parser.Parser(hasl1_grammar, 'sentences'), [
#     'Harry is a British subject because Harry is a man born in Bermuda but Harry has become naturalized.'
# ])