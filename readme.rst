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

  $ ./demo.py -p=...
  Hello, world...

  $ ./demo.py --help
  Usage:
  ./demo.py

  Options:

    -p/--punctuation

    -g/--greeting

As is probably obvious, cmdline.py treats args with no default value as
command-line args, and args with a default value as options. If an arg
defaults to True or False, it is treated as a flag, and passing it inverts the
default value.

Better Help
-----------

If we add some docstrings, things get more helpful::

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

  $ ./demo.py --help
  Greet things via standard output.

  Usage:
  ./test.py

  A more powerful version of the classic "Hello, world!" program.

  Options:

    -p/--punctuation
        Text to be displayed after the greeting.

    -g/--greeting
        A message to be displayed.

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

  $ ./demo.py
  Meet and greet things via standard output.

  Available commands:

  meet -- Introduce computer to person.
  greet -- A more powerful version of the classic "Hello, world!" program.

and help is available for specific commands::

  $ ./demo.py meet --help
  Usage: ./test.py meet <person>

  Introduce computer to `person`.

  Arguments:

    person
        name of person computer is introducing itself to.

  Options:

    -t/--title
        formal title for person computer is introducing itself to.

N.B.: Having both subcommands and a main command causes difficulties that I
have not taken the time to think through yet. cmdline.py does not currently
keep you from doing that, but perhaps it should.

Other Features
--------------

There are a few other features worth mentioning that I'm currently too lazy to
document in-depth. A few quick notes follow.

By default, input values are strings. Sometimes you don't want that. The App
constructor accepts a keyword arg named ``arg_types`` that solves that
problem.  The docstrings cover how it works, so do::

  >>> import cmdline
  >>> help(cmdline.App)

to learn about it.

There is tentative support for global options - ones that can be set for every
command. It's ugly, and may get axed or highly modified, but it could be
useful for programs with subcommands that have common options (think of
``--git-dir`` in git). It expects you to pass globals() to it, and tries not
to treat functions, classes, or modules as options. It looks like so::

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

There is tentative support for optional args. This was inspired by git, but I wonder if it is a misfeature. It's easy to use - the App.command decorator accepts a list of ``opt_args``.

There are some examples that served as a sort of ad-hoc test suite while I was
getting things to the current state - they are ``hello.py`` and
``subcommands.py``.

Alpha At Best
-------------

cmdline.py is **not** ready for production. It has no test suite, very little cleanup done, a todo.txt with a number of missing features and known deficiencies, a few misfeatures, and undoubtedly a lot of unknown missing features and deficiencies. The interface is very likely to change - hopefully by removing warts and adding as little as possible, but we'll see what transpires.

I'm putting it out in the wild because I would love to hear feedback from
people. What sucks about this? What's good about it? How can it be improved?

Suggestions (and patches) are welcome.

License
-------

This code is under the two-clause BSD license. See ``license.txt`` for details.
