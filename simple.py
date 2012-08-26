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

@app.command
def stub():
    """Do absolutely nothing."""

    pass

if __name__ == '__main__':
    app.run()
