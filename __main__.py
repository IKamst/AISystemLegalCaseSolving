#!/usr/bin/env python3
import sys

commands = dict()

def do_hasl1(*args):
    from hasl1.server import run
    run()


def do_hasl2(*args):
    from hasl2.server import run
    run()


def do_help():
    print("Usage: {} command".format(sys.argv[0]))
    print("Available commands: {}".format(' '.join(sorted(commands.keys()))))


commands.update((name[3:], fun) for name, fun in globals().items() if name.startswith('do_'))


if len(sys.argv) < 2 or sys.argv[1] not in commands:
    do_help()
    sys.exit(1)
else:
    commands[sys.argv[1]](*sys.argv[2:])
    sys.exit(0)
