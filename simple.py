#! /usr/bin/env python

"""A simple test of the cmdline module.

It really doesn't do anything of use. Pay it no mind.

"""

# Local imports.
import cmdline

app = cmdline.App(usage_msg=__doc__, output_alg=cmdline.print_str)

@app.command(usage_msg='Do absolutely nothing.')
def stub():
    pass

@app.command(param_types={'times': int})
def foobar(times=1):
    """Return 'foobar'.

    times -- number of repetitions of foobar to return.

    """

    return 'foobar' * times

if __name__ == '__main__':
    app.run()
