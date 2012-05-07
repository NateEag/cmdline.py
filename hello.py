#! /usr/bin/env python

"""A simple test of the cmdline module.

When run without args, prints 'Hello, world!' to stdout.

When run with a single arg, prints the arg to stdout.

If the --yell flag is set, output is in all caps.

If the --punctuation option is passed, the phrase will end with it.

Hopefully, a similar usage message will soon be introspected, rather
than hardcoded.

"""

# Local imports.
import cmdline

# Set up app for this script.
app = cmdline.App(output_alg=cmdline.print_str)

# The default short name of 'y' for 'yell' is better. We use 'u' only to test
# the short name override feature.
@app.main(opt_args=['greeting'], short_names={'yell': 'u'})
def greet(greeting='Hello, world', punctuation='!', yell=False):
    """Return a simple greeting.

    greeting -- A greeting. Defaults to 'Hello, world'.
    punctuation -- Post-greeting punctuation. Defaults to '!'.
    yell -- If True, display the message in all uppercase.

    """

    if yell:
        greeting = greeting.upper()

    result = greeting + punctuation

    return result

if __name__ == '__main__':
    app.run()
