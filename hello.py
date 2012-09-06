#! /usr/bin/env python

"""A command for greeting things.

When run with a single arg, prints the arg to stdout.

Hopefully, details about options and a useful command format diagram
will be forthcoming.

"""

# Standard library imports.
import os

# Local imports.
import cmdline

# Set up app for this script.
app = cmdline.App(usage_msg=__doc__, output_alg=cmdline.print_str)

# Module variables.
panic = False
rand_val = 123

# Create global command options from module settings.
app.make_global_opts(globals(), var_types={'rand_val': int})

# The default short name of 'y' for 'yell' is better. We use 'u' only to test
# the short name override feature.
@app.main(opt_args=['greeting'],
          short_names={'yell': 'u'},
          param_types={'reps': int})
def greet(greeting='Hello, world', punctuation='!', reps=1, sep=os.linesep,
          yell=False):
    """Return a simple greeting.

    It is fairly conventional to have some extra commentary, unless you
    really don't need it, so I'm going to include it here.

    >>> print 'Bogus doctest here'
    Bogus doctest here

    Note the use of three param description formats below. In order to
    test the param summary extractor, I have tried to make this
    docstring do whatever weird things we'll permit.

    @param greeting: A greeting. Defaults to 'Hello, world'.

                     Because sometimes param descriptions can get long,
                     this one demonstrates multiple paragraphs.
    punctuation -- Post-greeting punctuation.

                   Defaults to '!', as is conventional.
    :param reps: number of times the greeting should be repeated.

    In here I'm putting some pointless commentary that actually has
    nothing to do with function or command arguments. Assume I'm making
    some mildly abstruse point about the rationale for including a set
    of kwargs for the function.

    Following, a summary of such kwargs

    sep -- string to separate repetitions of greeting. Defaults to
        os.linesep.
    yell -- If True, return the message in all uppercase.

    """

    if yell:
        greeting = greeting.upper()

    if panic:
        greeting += ' -- LOOK OUT'

    if rand_val % 2 == 0:
        print rand_val

    result = greeting + punctuation

    result = sep.join([result] * reps)

    return result

if __name__ == '__main__':
    app.run()
