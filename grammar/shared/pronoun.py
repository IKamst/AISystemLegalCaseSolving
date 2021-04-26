from parser import Rule, passthru
from interpretation import Expression
from decorators import memoize


@memoize
def grammar(**kwargs):
    return {
        # Singular
        Rule("PRONOUN", [Expression(r'^[Hh]e$')], passthru),
        Rule("PRONOUN", [Expression(r'^[Ss]he$')], passthru),
        Rule("PRONOUN", [Expression(r'^[Ii]t$')], passthru),

        # Plural
        Rule("PRONOUNS", [Expression(r'^[Tt]hey$')], passthru),

        # Undetermined
        Rule("PRONOUN", [Expression(r'^[Ss]omeone$')], passthru),
        Rule("PRONOUN", [Expression(r'^[Ss]omething$')], passthru),
    }