==========
cmdline.py
==========

A simple module for writing command-line programs in Python.

A minimal example
-----------------
::

  #! /usr/bin/env python

  import cmdline

  app = cmdline.App()

  @app.main
  def greet(greeting='Hello, world', punctuation='!'):
      print '%s%s' % (greeting, punctuation)

  if __name__ == '__main__':
      app.run()

If the above is put in ``demo.py``, made executable, and cmdline.py is
importable, then the following works::

  $ ./demo.py
  Hello, world!

  $ ./demo.py --greeting 'Goodbye, cruel world'
  Goodbye, cruel world!

  $ ./demo.py -p...
  Hello, world...

  $ ./demo.py help
  Usage:
  ./demo.py

  Options:

    -p/--punctuation

    -g/--greeting

  Available subcommands:

    help -- Display docs for this app.


How It Works
------------

cmdline.py introspects function definitions and creates commands from them.

The logic is thus:

* Function names become subcommand names (underscores become hyphens).
* Function args become positional args.
* Function kwargs become optional args. If a kwarg defaults to True or False,
  it becomes a flag, and passing it inverts the default value.
* Function docstrings become basic usage messages.

Inputs are specified much as to GNU getopt. Thus, if you have flags with short names 'a', 'b', and 'c', you can do::

  $ ./demo.py -abc

and if you want to pass option 'd' (which takes an int), you can do::

  $ ./demo.py -abcd123

Long option names can have an ``=`` between the name and value, or just leave
whitespace between them.

Programs are automatically given a 'help' subcommand, and can have others.

Note that '--' escapes options *and* subcommand names. This is handy for
programs with both a main command and subcommands. For instance, if you want
to use 'help' as the first input to the main command, you can do::

  $ ./demo.py -- help

Options like ``--help`` and ``--version``, which are mostly subcommands disguised as options, are not supported. They are a venerable tradition, but I
see no clean way to support them. A good patch would likely be accepted.


Better Help
-----------

If we add some docstrings, help gets more helpful::

  #! /usr/bin/env python

  """Greet things via standard output."""

  import cmdline

  app = cmdline.App(usage_msg=__doc__)

  @app.main
  def greet(greeting='Hello, world', punctuation='!'):
      """A more powerful version of the classic "Hello, world!" program.

      greeting -- A message to be displayed.
      @param punctuation: Text to be displayed after the greeting.

      """

      print '%s%s' % (greeting, punctuation)

  if __name__ == '__main__':
      app.run()

which results in the following improvements::

  $ ./demo.py help
  Greet things via standard output.

  Usage:
  ./test.py

  A more powerful version of the classic "Hello, world!" program.

  Options:

    -p, --punctuation
        Text to be displayed after the greeting.

    -g, --greeting
        A message to be displayed.

  Available subcommands:

    help -- Display docs for this app.

Note that per PEP 257, the file's docstring can be used as part of its usage
message (though that is opt-in). Also note that cmdline.py recognizes three
kinds of arg descriptions: Sphinx, pydoc, and PEP 257. As long as they're
indented, multi-paragraph arg descriptions will be picked up correctly.

Subcommands
-----------

Creating a program that has several subcommands, a la Mercurial or Git, is
easy::

  #! /usr/bin/env python

  """Meet and greet things via standard output."""

  import cmdline

  app = cmdline.App(usage_msg=__doc__)

  @app.command
  def greet(greeting='Hello, world', punctuation='!'):
      """A more powerful version of the classic "Hello, world!" program.

      greeting -- A message to be displayed.
      @param punctuation: Text to be displayed after the greeting.

      """

      print '%s%s' % (greeting, punctuation)

  @app.command
  def meet(person, title='Mr.'):
      """Introduce computer to person.

      person -- name of person computer is introducing itself to.
      title -- formal title for person computer is introducing itself to.

      """

      print 'Hello, %s %s. I am your computer.' % (person, title)

  if __name__ == '__main__':
      app.run()

The newly-minted program knows what commands exist::

  $ ./demo.py help
  Meet and greet things via standard output.

  Available commands:

    meet -- Introduce computer to person.
    help -- Display docs for this app.
    greet -- A more powerful version of the classic "Hello, world!" program.

and help is available for specific commands::

  $ ./demo.py help meet
  Usage:
  ./test.py meet <person>

  Introduce computer to person.

  Arguments:

    person
        name of person computer is introducing itself to.

  Options:

    -t, --title
        formal title for person computer is introducing itself to.


Command Return Values
---------------------

If cmdline.py understands a function's return value, it uses it to set the
program exit status. Otherwise, it ignores it.

If a command's function returns None (the default), cmdline.py
will set the exit status to 0.

If a command's function returns an integer from 0 to 127, cmdline.py will set
the exit status to that value.

Note that if user input is recognizably invalid, a cmdline.py App will set the
program's exit status to 2 (which the Python docs claim is the usual Unix move
for invalid syntax: http://docs.python.org/library/sys.html#sys.exit).


Other Features
--------------

There are a few other features worth mentioning. The code has pretty decent
docstrings, so reading through those should give you a good overview of what
you can do. A few highlights follow.

By default, input values are strings. Sometimes you don't want that. The App
constructor accepts a keyword arg named ``arg_types`` to handle that. The
docstrings cover how it works, so do::

  >>> import cmdline
  >>> help(cmdline.App)

to learn about it.

There is tentative support for global options - ones that can be set for all
commands. It's ugly, and such options are not documented by the help command,
but it could be useful for programs with subcommands that have common options
(think of ``--git-dir`` in git). It expects you to pass globals() to it, and
tries not to treat functions, classes, or modules as options. It looks like
this::

  app = cmdline.App(usage_msg=__doc__)

  foo = 21

  app.make_global_opts(globals(), arg_types={'foo': int})

  @app.command
  def greet(greeting='Hello, world', punctuation='!'):
      """A more powerful version of the classic "Hello, world!" program.

      greeting -- A message to be displayed.
      @param punctuation: Text to be displayed after the greeting.

      """

      print '%s%s' % (greeting, punctuation)

      if foo % 2 == 0:
          print 'Foo is even!'

  if __name__ == '__main__':
      app.run()

There is also tentative support for optional args. This was inspired by git,
but I wonder if it is a misfeature. It's easy to use - the App.command
decorator accepts a list of ``opt_args``.

There are some examples that served as a sort of ad-hoc test suite while I was
getting things to the current state - they are ``hello.py`` and
``subcommands.py``.

Alpha At Best
-------------

cmdline.py is **not** ready for production. It has no test suite, a todo.txt
with a number of missing features and known deficiencies, a few misfeatures,
and undoubtedly a lot of unknown missing features and deficiencies. The
interface is very likely to change - hopefully by removing warts and adding as
little as possible, but we'll see what transpires.

I'm putting it out in the wild because I would love to hear feedback from
people. What sucks about this? What's good about it? How can it be improved?

Suggestions (and patches) are welcome.

License
-------

This code is under the two-clause BSD license. See ``license.txt`` for details.
