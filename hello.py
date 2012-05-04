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
app = cmdline.App()

@app.main
def greet(greeting='Hello, world', yell=False, punctuation='!'):
    """Display a simple message to stdout.

    Optional Args:
    greeting -- the message to output.

    Flags:
    yell -- display the message in uppercase.

    Options:
    punctuation -- punctuation to display at the end of greeting. Defaults to
        '!'.

    """

    if yell:
        greeting = greeting.upper()

    result = greeting + punctuation

    print result

if __name__ == '__main__':
    app.run()
