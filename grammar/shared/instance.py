from parser import Rule, RuleRef, State, passthru
from grammar.shared import name, pronoun, noun
from argumentation import Argument
from interpretation import Interpretation, Literal, Expression
from datastructures import Sequence
import english
from decorators import memoize
from debug import Boolean, print_comparator

counter = Sequence()


class Instance(object):
    def __init__(self, name: str = None, noun: str = None, pronoun: str = None, origin: 'Instance' = None, scope: 'Scope' = None):
        self.id = counter.next()
        self.name = name
        self.noun = noun
        self.pronoun = pronoun
        self.origin = origin
        self.scope = scope

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id
        
    def __str__(self):
        if self.name is not None:
            return "{} (#{})".format(self.name, self.id)
        elif self.noun is not None:
            return "the {} (#{})".format(self.noun, self.id)
        elif self.pronoun is not None:
            return "{} (#{})".format(self.pronoun, self.id)
        else:
            return "(#{})".format(self.id)

    def __repr__(self):
        return "Instance(id={id!r} name={name!r} noun={noun!r} pronoun={pronoun!r} scope={scope!r})".format(**self.__dict__)

    @property
    def grammatical_number(self):
        return 'singular'

    def text(self, argument: Argument):
        return argument.get_instance(self).__str__()[:-1] + '/{})'.format(self.id)

    def is_same(self, other: 'Instance', argument: Argument) -> bool:
        return argument.get_instance(self) == argument.get_instance(other)

    @print_comparator
    def could_be(self, other: 'Instance') -> bool:
        if isinstance(other, GroupInstance):
            return Boolean(False, '{}/{}: different class'.format(self.id, other.id))
        elif self.scope != other.scope:
            return Boolean(False, '{}/{}: different scope'.format(self.id, other.id))
        elif self.pronoun and self.pronoun.lower() == 'something':
            return Boolean(other.pronoun and other.pronoun.after(self.pronoun) is not False and other.pronoun.lower() == 'it', '{}/{}: my pronoun is something, other pronoun is it'.format(self.id, other.id))
        elif self.pronoun and self.pronoun.lower() == 'someone':
            return Boolean(other.pronoun and other.pronoun.after(self.pronoun) is not False and other.pronoun.lower() in ('he', 'she'), '{}/{}: my pronoun is someone, other pronoun is he/she'.format(self.id, other.id))
        elif self.name is not None:
            if other.name is not None and other.name.after(self.name) is not False:
                return Boolean(self.name == other.name, '{}/{}: same name'.format(self.id, other.id))
            elif self.pronoun is None:
                return Boolean(other.pronoun and other.pronoun.after(self.name) is not False and other.pronoun.lower() in ('he', 'she'), '{}/{}: I have a name but my pronoun is None and other pronoun is he/she'.format(self.id, other.id))
            else:
                return Boolean(other.pronoun and other.pronoun.after(self.pronoun) is not False and self.pronoun.lower() == other.pronoun.lower(), '{}/{}: I have a name, but same pronoun'.format(self.id, other.id))
        elif self.noun is not None:
            if other.noun is not None:
                return Boolean(self.noun.before(other.noun) and self.noun == other.noun, '{}/{}: same noun'.format(self.id, other.id))
            else:
                return Boolean(other.pronoun and other.pronoun.after(self.noun) is not False and other.pronoun.lower() in ('he', 'she', 'it'), '{}/{}: other noun is none but pronoun is he/she/it'.format(self.id, other.id))
        elif self.pronoun and self.pronoun.lower() in ('he', 'she', 'it') and not other.name and not other.noun:
            return Boolean(other.pronoun and other.pronoun.after(self.pronoun) is not False and self.pronoun.lower() == other.pronoun.lower(), '{}/{}: same pronoun'.format(self.id, other.id))
        else:
            return Boolean(False, '{}/{}: undefined case'.format(self.id, other.id))

    def replaces(self, instance: 'Instance') -> bool:
        """
        Test whether this instance is an updated version of the supplied instance.
        :param instance: the supposed origin of this instance
        :return: whether this instance is a more accurate version of the supplied instance
        """
        previous = self.origin
        while previous is not None:
            if previous == instance:
                return True
            previous = previous.origin
        return False

    def replace(self, other: 'Instance') -> 'Instance':
        return self.update(other.name, other.noun, other.pronoun)

    def update(self, name: str = None, noun: str = None, pronoun: str = None, scope = None) -> 'Instance':
        return Instance(
            name=self.name if self.name and (name is None or name.after(self.name) is not False) else name,
            noun=self.noun if self.noun and (noun is None or noun.after(self.noun) is not False) else noun,
            pronoun=self.pronoun if self.pronoun and (pronoun is None or pronoun.after(self.pronoun)) else pronoun,
            origin=self,
            scope=scope if scope is not None else self.scope)

    @classmethod
    def from_pronoun_rule(cls, state, data):
        instance = cls(pronoun=data[0].local)
        return data[0] + Interpretation(argument=Argument(instances={instance: {instance}}), local=instance)

    @classmethod
    def from_name_rule(cls, state, data):
        instance = cls(name=data[0].local)
        return data[0] + Interpretation(argument=Argument(instances={instance: {instance}}), local=instance)

    @classmethod
    def from_noun_rule(cls, state, data):
        instance = cls(noun=data[1].local) # because 'the'
        return data[1] + Interpretation(argument=Argument(instances={instance: {instance}}), local=instance)


class GroupInstance(object):
    def __init__(self, instances = None, noun = None, pronoun = None, origin: 'GroupInstance' = None, scope: 'Scope' = None):
        assert instances is None or len(instances) > 1, "A group of one"
        self.id = counter.next()
        self.instances = instances
        self.noun = noun
        self.pronoun = pronoun
        self.origin = origin
        self.scope = scope

    def __repr__(self):
        return "GroupInstance(id={id!r} instances={instances!r} noun={noun!r} pronoun={pronoun!r} scope={scope!r})".format(**self.__dict__)

    def __str__(self):
        if self.instances:
            return "{} (#{})".format(english.join(self.instances), self.id)
        elif self.noun:
            return "the {} (#{})".format(self.noun.plural, self.id)
        elif self.pronoun:
            return "{} (#{})".format(self.pronoun, self.id)
        else:
            return "(anonymous group of instances #{})".format(self.id)

    def text(self, argument: Argument):
        return argument.get_instance(self).__str__()

    @property
    def grammatical_number(self):
        return 'plural'

    def is_same(self, other: 'GroupInstance', argument: Argument) -> bool:
        return argument.get_instance(self) == argument.get_instance(other)

    def could_be(self, other: 'GroupInstance') -> bool:
        if not isinstance(other, self.__class__):
            return Boolean(False, 'different class')
        elif self.scope != other.scope:
            return Boolean(False, 'different scope')
        elif self.pronoun == 'all':
            return Boolean(other.pronoun in ('all', 'they',), 'my pronoun is all theirs is all/they')
        elif self.instances:
            if other.instances:
                return Boolean(all(any(instance.could_be(other_instance) for other_instance in other.instances) for instance in self.instances), 'all instances could be the same')
            else:
                return Boolean(other.pronoun in ('they',), 'other has no instances, but their pronoun is they')
        elif self.noun:
            if other.noun is not None:
                return Boolean(self.noun == other.noun, 'same noun')
            else:
                return Boolean(other.pronoun in ('they',), 'other has no noun, but has pronoun they')
        elif self.pronoun:
            return Boolean(self.pronoun == other.pronoun, 'same pronoun')
        else:
            return Boolean(False, 'undefined case')

    def replaces(self, instance: 'GroupInstance') -> bool:
        """
        Test whether this instance is an updated version of the supplied instance.
        :param instance: the supposed origin of this instance
        :return: whether this instance is a more accurate version of the supplied instance
        """
        previous = self.origin
        while previous is not None:
            if previous == instance:
                return True
            previous = previous.origin
        return False

    def replace(self, other: 'GroupInstance') -> 'GroupInstance':
        return self.update(other.instances, other.noun, other.pronoun)

    def update(self, instances = None, noun: str = None, pronoun: str = None, scope = None) -> 'GroupInstance':
        return GroupInstance(
            instances=instances if instances is not None else self.instances,
            noun=noun if noun is not None else self.noun,
            pronoun=pronoun if pronoun is not None else self.pronoun,
            origin=self,
            scope=scope if scope is not None else self.scope)

    @classmethod
    def from_pronoun_rule(cls, state, data):
        instance = cls(pronoun=data[0].local)
        return data[0] + Interpretation(local=instance, argument=Argument(instances={instance: {instance}}))

    @classmethod
    def from_names_rule(cls, state, data):
        instances = {Instance(name=name) for name in data[0].local}
        instance=cls(instances=instances)
        return data[0] + Interpretation(local=instance, argument=Argument(instances={instance: {instance}}))

    @classmethod
    def from_noun_rule(cls, state, data):
        instance = cls(noun=data[1].local)  # 1 because of the 'the' at pos 0.
        return data[1] + Interpretation(local=instance, argument=Argument(instances={instance: {instance}}))


class DumbInstance(Instance):
    def is_same(self, other: 'Instance', argument: Argument) -> bool:
        return self == other

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def could_be(self, other: 'Instance') -> bool:
        return Boolean(False, 'anaphora resolution disabled')

    def text(self, argument: Argument):
        return str(self)

    def __str__(self):
        if self.name is not None:
            return "{}".format(self.name)
        elif self.noun is not None:
            return "the {}".format(self.noun)
        elif self.pronoun is not None:
            return "{}".format(self.pronoun)
        else:
            return "#{}".format(self.id)


class DumbGroupInstance(GroupInstance):
    def is_same(self, other: 'GroupInstance', argument: Argument) -> bool:
        return self == other

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def could_be(self, other: 'GroupInstance') -> bool:
        return Boolean(False, 'anaphora resolution disabled')

    def text(self, argument: Argument):
        return str(self)

    def __str__(self):
        if self.instances:
            return "{}".format(english.join(self.instances))
        elif self.noun:
            return "the {}".format(self.noun.plural)
        elif self.pronoun:
            return "{}".format(self.pronoun)
        else:
            return "(anonymous group of instances #{})".format(self.id)

@memoize
def grammar(anaphora=True, **kwargs):
    if anaphora:
        singular = Instance
        plural = GroupInstance
    else:
        singular = DumbInstance
        plural = DumbGroupInstance

    return name.grammar(**kwargs) | noun.grammar(**kwargs) | pronoun.grammar(**kwargs) | {
        # Singular
        Rule("INSTANCE", [RuleRef("PRONOUN")],
            singular.from_pronoun_rule),

        Rule("INSTANCE", [RuleRef("NAME")],
            singular.from_name_rule),

        Rule("INSTANCE", [Expression(r"^[Tt]he$"), RuleRef("NOUN")],
            singular.from_noun_rule),

        Rule("INSTANCE", [Expression(r"^[Hh]is|[Hh]er|[Tt]heir$"), RuleRef("NOUN")],
            singular.from_noun_rule),

        # Plural
        Rule("INSTANCES", [RuleRef("PRONOUNS")],
            plural.from_pronoun_rule),

        Rule("INSTANCES", [RuleRef("NAMES")],
            plural.from_names_rule),

        Rule("INSTANCES", [Expression(r"^[Tt]he$"), RuleRef("NOUNS")],
            plural.from_noun_rule),

        Rule("INSTANCES", [Expression(r"^[Hh]is|[Hh]er|[Tt]heir$"), RuleRef("NOUNS")],
            plural.from_noun_rule),

        # Shortcuts
        Rule("INSTANCE*", [RuleRef("INSTANCE")], passthru),

        Rule("INSTANCE*", [RuleRef("INSTANCES")], passthru),
    }

