"""A module for writing command-line Python programs.

Use the App.command() and App.main() decorators to give modules
command-line interfaces with low effort.

Once things are more complete, real docs should be written.

For now, see hello.py for a simple example.

"""

# Standard library imports.
import inspect
import sys

# Python 2.7 has OrderedDict; for 2.4 - 2.6, we fall back to an external
# implementation.
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

class InvalidInput(Exception):
    """Indicates that invalid input was given.

    `self.input` is the invalid input, or None if input was expected but
    not given.

    """

    def __init__(self, value=None):
        self.input = value

class BadArgCount(InvalidInput):
    """Indicates that an invalid number of args were given.

    self.cmd -- name of command.
    self.min_required -- number of args required.
    self.max_allowed -- number of args allowed.
    self.num_given -- number of args given.

    """

    def __init__(self, cmd, min_required, max_allowed, num_given):

        self.cmd = cmd
        self.min_required = min_required
        self.max_allowed = max_allowed
        self.num_given = num_given

class UnknownCommand(InvalidInput):
    """Indicates that an unknown command was given.

    self.input is the command, or None if a command was expected but not
    given.

    """

    def __init__(self, cmd=None):
        self.input = cmd

class UnknownOption(InvalidInput):
    """Indicates that an unknown option was given.

    self.input is the option's name.

    """

    def __init__(self, name):
        self.input = name

class InvalidOption(InvalidInput):
    """Indicates that an invalid option was given.

    self.name is the option name.
    self.input is the invalid value (or None, if none was given).

    """

    def __init__(self, name, value):
        self.name = name
        self.input = value

class InvalidFlag(InvalidOption):
    """Indicates that an invalid flag was given.

    self.name is the flag name.
    self.input is the value that was rejected.

    """

    def __init__(self, name, value=None):
        self.name = name
        self.input = value


class Arg(object):
    """An argument a command-line app accepts."""

    def __init__(self, name, summary, default=None):

        self.name = name
        self.summary = summary
        self.default = default

class Option(object):
    """An option a command-line app accepts."""

    def __init__(self, name, summary, default, shortname=None):
        self.name = name
        self.default = default
        self.summary = summary

        # DEBUG This fails if two names collide. How do we deal with that?
        # Just crash and tell them to resolve it manually?
        self.shortname = name[0] if shortname is None else shortname

class Command(object):
    """A sub-command in a command-line app.

    These are best created by decorating functions with App.command() or
    App.main().

    Using this class directly would work, but it wouldn't be as pretty.

    """

    # GRIPE You could argue that __init__ should actually just be from_func.
    # I'm not sure if you'd be right or not.
    def __init__(self, func, args, opt_args, opts, flags, output_alg=None,
                 name=None):
        """Make a new Command.

        func -- callable that does the command's work.
        args -- list of required positional args for this command.
        opt_args -- list of optional positional args for this command.
        opts -- list of options for this command. Options map a short name
            or a long name to a (required) passed value.
        flags -- list of flags for this command. Flags are Booleans with a
            short name and a long name. When set, flags invert their default
            value.
        output_alg -- callable to generate output from `func`'s return value.
            Defaults to None, as good *nix programs are silent by default.
        name -- Optional command name. If None, self.name is set by
            replacing '_' with '-' in func.__name__.

        """

        self.func = func
        self.name = func.__name__.replace('_', '-') if name is None else name
        self.args = args
        self.opt_args = opt_args
        self.opts = opts
        self.flags = flags
        self.output_alg = output_alg

    def run(self, inputs):
        """Run this command with `inputs` as our argv array."""

        args = []
        kwargs = {}

        num_inputs = len(inputs)
        i = 0
        # DEBUG Eventually this loop should get type handling.
        while i < num_inputs:
            item = inputs[i]
            if item.startswith('-'):
                # item is an option.
                item = item.lstrip('-')

                if '=' in item:
                    # An option and value are both in this item.
                    opt, junk, val = item.partition('=')
                    if opt in self.flags:
                        raise InvalidFlag(opt, val)
                else:
                    # This item is just an option.
                    # DEBUG How do we deal with it when there is no next item?
                    opt = item
                    if opt in self.opts:
                        j = i + 1
                        if j >= num_inputs or inputs[j].startswith('-'):
                            # It requires a value to be passed.
                            raise InvalidOption(opt)

                        i += 1
                        val = inputs[i]

                if opt in self.flags:
                    val = not self.flags[opt].default
                elif opt not in self.opts:
                    raise UnknownOption(opt)

                kwargs[opt] = val
            else:
                args.append(item)

            i += 1

        num_args = len(args)
        min_args = len(self.args)
        max_args = len(self.args) + len(self.opt_args)
        if num_args < min_args or num_args > max_args:
            raise BadArgCount(self.name, min_args, max_args, num_args)

        # Default any optional args that were not passed.
        num_opt_args = num_args - min_args
        for i, key in enumerate(self.opt_args):
            if i >= num_opt_args:
                args.append(self.opt_args[key].default)

        result = self.func(*args, **kwargs)

        if self.output_alg is not None:
            self.output_alg(result)

    @classmethod
    def from_func(cls, func, output_alg=None):
        """Get an instance of Command by introspecting func.

        func -- a callable object.
        output_alg -- a callable object that processes func's return
            value and prints any output.

        DEBUG This should ignore self/cls parameters. I'm not sure how
        to distinguish between functions and methods, so for now we're
        not worrying about it. We could just ignore those names if in
        0th position - only really nasty code would break on that.

        """

        # Grab any param annotations from the docstring.
        # GRIPE There has got to be a less ugly way to do this.
        docstr = inspect.getdoc(func)
        section = None
        cur_name = None
        annotations = {}
        for line in docstr.splitlines():
            section_chk = line.lower()
            if section_chk == 'args:':
                section = 'args'
                continue
            elif section_chk == 'optional args:':
                section = 'opt_args'
                continue
            elif section_chk == 'flags:':
                section = 'flags'
                continue
            elif section_chk == 'options:':
                section = 'opts'
                continue
            elif section_chk is not None and section_chk.strip() == '':
                section = None
                continue

            if section is None:
                continue

            if '--' in line:
                name, junk, summary = line.partition('--')
                cur_name = name.strip()
                annotation = {}
                annotation['summary'] = summary.strip()
                annotation['section'] = section

                annotations[cur_name] = annotation
            elif cur_name is not None:
                annotations[cur_name]['summary'] += ' ' + line.strip()

        # Inspect func for hard data.
        func_args, varargs, varkw, defaults = inspect.getargspec(func)
        num_defaults = 0 if defaults is None else len(defaults)
        num_func_args = 0 if func_args is None else len(func_args) - num_defaults
        func_name = func.__name__

        # Build required arg dict.
        arg_list = func_args[:num_func_args]
        args = {}
        for i, arg in enumerate(arg_list):
            summary = None
            annotation = annotations.get(arg)
            if annotation is not None:
                if annotation['section'] != 'args':
                    # GRIPE Is this a custom exception type?
                    raise Exception('%s is a required arg, but is described '
                                    "as a %s in %s's docstring."
                                    % (arg, annotation['section'], func_name))

                summary = annotation['summary']

            args[i] = Arg(name, summary)

        # Build optional arg dict, option dict, and flag dict.
        # (Yes, this is rather ugly.)
        opt_args = OrderedDict()
        opts = {}
        flags = {}
        for i, arg in enumerate(func_args[num_func_args:]):
            summary = None
            annotation = annotations.get(arg)
            if annotation is not None:
                summary = annotation['summary']
                if annotation['section'] == 'opt_args':
                    if isinstance(defaults[i], bool):
                        # GRIPE Is this a custom exception type?
                        raise Exception('%s is a flag, but is described as a '
                                        "%s in %s's docstring."
                                        % (arg, annotation['section'],
                                           func_name))

                    opt_args[arg] = Arg(arg, summary, defaults[i])

                    continue

            if isinstance(defaults[i], bool):
                # DEBUG Should check whether metadata says this is a flag.
                flags[arg] = Option(arg, summary, defaults[i])

                continue

            opts[arg] = Option(arg, summary, defaults[i])

        return cls(func, args, opt_args, opts, flags, output_alg)

class App(object):
    """A command-line application."""

    def __init__(self, output_alg=None):

        self.args = []
        self.opts = {}
        self.cmd = None

        self.output_alg = output_alg
        self.main_cmd = None
        self.commands = {}
        self.script_name = None
        self.argv = []

    def main(self, func, output_alg=None):
        """Decorator to make func the main command for this app."""

        if output_alg is None:
            output_alg = self.output_alg

        cmd = Command.from_func(func, output_alg)
        self.main_cmd = cmd

        return func

    def command(self, func, output_alg=None):
        """Decorator to make func an app command."""

        if output_alg is None:
            output_alg = self.output_alg

        # DEBUG It would be faster to only create the Command object when the
        # user actually tries to run that command. Right now I'm incredibly
        # tired and just trying to get this working.
        cmd = Command.from_func(func, output_alg)
        self.commands[cmd.name] = cmd

        return func

    def _do_cmd(self, argv):
        """Parse `argv` and run the specified command."""

        self.argv = argv[:]
        self.script_name = argv[0]

        inputs = argv[1:]

        # DEBUG If a program with subcommands wants to accept general options,
        # we'd need to handle those here somehow... Maybe we register certain
        # param names with the app as being global, and therefore not
        # command-specific, even though they show up in a bunch of functions?
        # Or maybe they're global vars the functions use?

        self.cmd = self.main_cmd
        if len(self.commands) > 0:
            # This program uses subcommands, so the first command must be one.
            # GRIPE Is that necessarily true? Git behaves that way, but a main
            # command with optional subcommands might be conceivable, mightn't
            # it? Bob points out that it probably isn't - subcommands break
            # badly. This means @command and @main should throw an exception if
            # such a setup is detected.
            if len(args) < 1:
                raise UnknownCommand()

            self.cmd = self.commands.get(arg[0])
            args = args[1:]

            if self.cmd is None:
                # GRIPE There should be more advanced error handling here.
                # Like printing a usage message if one is defined.
                raise UnknownCommand(self.cmd)

        self.cmd.run(inputs)

    def run(self, argv=None):
        """Run this app with argv as command-line input.

        argv -- defaults to sys.argv, but pass another list if you like.

        """

        if argv is None:
            argv = sys.argv

        try:
            self._do_cmd(argv)
        except UnknownCommand as exc:
            if exc.cmd is None:
                print >> sys.stderr, 'You must enter a command.'
            else:
                print >> sys.stderr, '%s is not a known command.' % exc.value
        except InvalidInput as exc:
            print >> sys.stderr, 'Invalid input: %s' % exc.input

def print_str(obj):
    """Basic output algorithm for command-line programs.

    Cast `obj` to a string, then print the result.

    """

    text = str(obj)

    print text
