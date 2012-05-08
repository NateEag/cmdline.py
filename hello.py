#! /usr/bin/env python

"""A simple test of the cmdline module.

When run without args, prints 'Hello, world!' to stdout.

When run with a single arg, prints the arg to stdout.

If the --yell flag is set, output is in all caps.

If the --punctuation option is passed, the phrase will end with it.

Hopefully, a similar usage message will soon be introspected, rather
than hardcoded.

"""

# Standard library imports.
import os

# Local imports.
import cmdline

# Set up app for this script.
app = cmdline.App(output_alg=cmdline.print_str)

# The default short name of 'y' for 'yell' is better. We use 'u' only to test
# the short name override feature.
@app.main(opt_args=['greeting'],
          short_names={'yell': 'u'},
          param_types={'reps': int})
def greet(greeting='Hello, world', punctuation='!', reps=1, sep=os.linesep,
          yell=False):
    """Return a simple greeting.

    greeting -- A greeting. Defaults to 'Hello, world'.
    punctuation -- Post-greeting punctuation. Defaults to '!'.
    reps -- number of times the greeting should be repeated.
    sep -- string to separate repetitions of greeting. Defaults to
        os.linesep.
    yell -- If True, display the message in all uppercase.

    """

    if yell:
        greeting = greeting.upper()

    result = greeting + punctuation

    result = sep.join([result] * reps)

    return result

if __name__ == '__main__':
    app.run()
