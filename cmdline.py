""""A module for writing command-line Python programs.

Use the App.command() and App.main() decorators to give modules
command-line interfaces with low effort.

Once things are more complete, real docs should be written.

For now, see hello.py for a simple example.

"""

# Standard library imports.
import inspect
import os
import re
import sys
import textwrap
import types

# Module constants.
# According to the Python docs, command line syntax errors usually yield an
# exit code of 2, so that's what I'm doing. I'm not sure this is the best
# value to use. http://docs.python.org/library/sys.html#sys.exit
_USAGE_ERR_CODE = 2

# Used to recognize PEP 257-style function arg descriptions in
# docstrings.
_PEP_257_RE = re.compile(r'^(\w+) --')

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
    self.min_argc -- number of args required.
    self.max_argc -- number of args allowed.
    self.num_given -- number of args given.

    """

    def __init__(self, cmd, min_argc, max_argc, num_given):

        self.input = cmd
        self.min_argc = min_argc
        self.max_argc = max_argc
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

    def __init__(self, name, value=None):
        self.name = name
        self.input = value

class DuplicateOption(InvalidInput):
    """Indicates that this option has already been passed."""

    def __init__(self, duplicate_name, name):
        self.input = duplicate_name
        self.name = name

class InvalidFlag(InvalidOption):
    """Indicates that an invalid flag was given.

    self.name is the flag name.
    self.input is the value that was rejected.

    """

    def __init__(self, name, value=None):
        self.name = name
        self.input = value

class InvalidShortName(InvalidInput):
    """Indicates that two short option names collide.

    self.input -- the command name with the colliding options.
    self.name -- the short name that's been used more than once.
    self.opt_one -- the first option to use the short name.
    self.opt_two -- the second option to use the short name.

    """

    def __init__(self, input, name, opt_one, opt_two):
        self.input = input
        self.name = name
        self.opt_one = opt_one
        self.opt_two = opt_two

def _get_usage_msg(docstr):
    """Parse `docstr` and return a usage message.

    Mostly, this tries to guess at what point a docstring stops
    being applicable to a command and returns everything before
    that.

    It assumes a docstring is no longer explaining the command in
    general once it has seen a parameter description or a doctest
    block.

    DEBUG This currently munges indented blocks horribly. That
    should be fixed, as many tools have reason to display codeish
    examples. The ugly bit is that it needs to deal with tabs,
    not just spaces.

    """

    if docstr is None:
        return

    paragraphs = []
    for para in docstr.split('\n' * 2):
        # GRIPE This is a lot like the code for getting param summaries -
        # should they be merged for DRYness, or would that hurt readability
        # too much?
        match = _PEP_257_RE.match(para)
        if para.startswith('>>>') or (para.startswith('@param') or
                                      para.startswith(':param') or
                                      match is not None):
            break
        else:
            paragraphs.append(para)

    sep = os.linesep * 2

    return sep.join(paragraphs)

def _get_param_summaries(docstr):
    """Parse `docstr` and return a dict mapping param => summary.

    It tries to understand three formats for describing params in
    docstrings:

    * PEP 257:
        param_name -- A summary of the function parameter, possibly
                      spanning multiple lines.

                      Or even paragraphs.

    * Sphinx:
        :param param_name: A summary of the function parameter,
                           possibly spanning multiple lines.

                           Or even paragraphs.

    * epydoc:
        @param param_name: A summary of the function parameter,
                           possibly spanning multiple lines.

                           Or even paragraphs.

    Other formats exist, but these seem to be the major ones, based
    on an utterly unscientific Google binge.

    """

    summaries = {}

    if docstr is None:
        return summaries

    param_name = None
    param_summary = None
    blank_line_seen = False
    for line in docstr.splitlines():
        match = _PEP_257_RE.match(line)
        if match is not None:
            param_name = match.groups()[0]
            remainder = line[match.end():].strip()
        elif line.startswith('@param') or line.startswith(':param'):
            next_colon_pos = line.find(':', 7)
            param_name = line[7:next_colon_pos]
            remainder = line[next_colon_pos + 1:].strip()
        elif line != '' and line.lstrip() == line:
            # This line is not blank, is not indented, and contains no
            # param name, so the param summary must be finished.
            param_name = None
            continue

        if param_name is not None:
            if remainder is not None:
                summaries[param_name] = remainder.strip()
                blank_line_seen = False
            elif line == '':
                # Remember this blank line, in case it's part of the
                # current summary.
                blank_line_seen = True
            else:
                if blank_line_seen:
                    # This will discard >2 blank lines in a summary,
                    # but that will probably look better anyway.
                    summaries[param_name] += os.linesep * 2 + line.strip()
                    blank_line_seen = False
                else:
                    summaries[param_name] += ' ' + line.strip()

        remainder = None

    return summaries

class Arg(object):
    """An argument for a command-line app."""

    def __init__(self, name, summary, default=None, type_converter=None):

        self.name = name
        self.summary = summary
        self.default = default
        self.type_converter = type_converter

    def format_name(self):
        """Return a string representing this argument's name."""

        return self.name

    def convert_type(self, val):
        """Return `val` after converting it to this Arg's type."""

        if val is not None and self.type_converter is not None:
            val = self.type_converter(val)

        return val

    def format_summary(self, width=70):
        """Return a formatted summary of `self`.

        Return `self.format_name()` if no summary is available.

        width -- Optional max width of a line in result. Defaults to 70.

        """

        summary = ''
        name = self.format_name()

        if self.summary is None:
            return '  ' + name

        for line in self.summary.splitlines():
            if line is not '':
                summary += textwrap.fill(line, width,
                                         initial_indent=' ' * 6,
                                         subsequent_indent=' ' * 6)
            else:
                summary += os.linesep * 2

        return '  %s%s%s' % (name, os.linesep, summary)

class Option(Arg):
    """An option for a command-line app."""

    def __init__(self, name, summary, default, short_name=None,
                 type_converter=None):
        self.name = name
        self.default = default
        self.summary = summary
        self.short_name = name[0] if short_name is None else short_name
        self.type_converter = type_converter

    def format_name(self):
        """Return this Option's name(s) as a string."""

        result = ''
        if self.short_name is not None:
            result += '-%s, ' % self.short_name

        result += '--%s' % self.name

        return result

    @property
    def is_flag(self):
        """Return True if this Option is a flag. Return False otherwise."""

        return type(self.default) is types.BooleanType

class Command(object):
    """A sub-command in a command-line app.

    These are best created by decorating functions with App.command() or
    App.main().

    Using this class directly would work, but it wouldn't be as pretty.

    """

    # GRIPE You could argue that __init__ should actually just be
    # from_func. I'm not sure if you'd be right or not.
    def __init__(self, func, args, opt_args, opts, arg_types=None,
                 usage_msg=None, name=None):
        """Make a new Command.

        func -- callable that does the command's work.
        args -- list of required positional args for this command.
        opt_args -- list of optional positional args for this command.
        opts -- dict of options for this command. Options map a name to a
            (required) passed value (with an optional short name).
        usage_msg -- Optional string explaining the command. Defaults to
            None.
        name -- Optional command name. If None, self.name is set by
            replacing '_' with '-' in func.__name__.

        """

        self.func = func
        self.name = func.__name__.replace('_', '-') if name is None else name
        self.args = args
        self.opt_args = opt_args
        self.opts = opts
        self.usage_msg = usage_msg

        summary = None
        if usage_msg is not None:
            summary = self.usage_msg
            end_idx = summary.find('.')
            if end_idx > 0:
                summary = summary[0:end_idx + 1]
        self.summary = summary

        self.short_names = {}
        for key, value in self.opts.items():
            if value.short_name in self.short_names:
                raise InvalidShortName(self.name, value.short_name,
                                       self.short_names[value.short_name],
                                       value.name)

            self.short_names[value.short_name] = key

    @property
    def min_argc(self):
        """Minimum number of args to this Command."""

        return len(self.args)

    @property
    def max_argc(self):
        """Maximum number of args to this Command."""

        return len(self.args) + len(self.opt_args)

    def run(self, args, kwargs):
        """Run this command using args and kwargs."""

        return self.func(*args, **kwargs)

    @classmethod
    def from_func(cls, func, short_names=None, opt_args=None, arg_types=None,
                  usage_msg=None, name=None):
        """Get an instance of Command by introspecting func.

        func -- a callable object.
        short_names -- a dict mapping long option names to single letters.
        opt_args -- a list of func's optional params that should be
                    treated as optional command-line args instead of
                    options.
        arg_types -- optional dict mapping arg names to callables that
                     take a string as input and either return an object
                     of the desired type or raise a ValueError.
        usage_msg -- an optional string explaining the command. Defaults
                     to a processed version of func's docstring.
        name -- an optional name for the command. Defaults to a
                transformed version of `func`'s name.

        """

        if opt_args is None:
            # GRIPE It might be better to go through and make default
            # opt_args an empty list everywhere.
            opt_args = []

        if arg_types is None:
            arg_types = {}

        # Grab any param summary from the docstring.
        docstr = inspect.getdoc(func)
        summaries = {}
        if docstr is not None:
            # GRIPE We should probably let you pass param summaries from
            # outside.
            summaries = _get_param_summaries(docstr)
            if usage_msg is None:
                usage_msg = _get_usage_msg(docstr)

        # Inspect func for hard data.
        func_args, varargs, varkw, defaults = inspect.getargspec(func)
        if inspect.ismethod(func):
            # Do not include the self/cls parameter.
            func_args = func_args[1:]
        num_defaults = 0 if defaults is None else len(defaults)
        num_func_args = 0 if func_args is None else len(func_args) - num_defaults
        func_name = func.__name__

        # Build required arg dict.
        arg_list = func_args[:num_func_args]
        args = []
        for arg in arg_list:
            summary = summaries.get(arg)
            type_converter = arg_types.get(arg)
            arg_name = arg.replace('_', '-')

            args.append(Arg(arg_name, summary, type_converter=type_converter))

        # Build optional arg list and options dict.
        opts = {}
        for i, arg in enumerate(func_args[num_func_args:]):
            short_name = None
            if short_names is not None:
                tmp = short_names.get(arg)
                if tmp is not None and len(tmp) == 1:
                    short_name = tmp

            summary = summaries.get(arg)

            if arg in opt_args:
                pos = opt_args.index(arg)
                type_converter = arg_types.get(arg)
                arg_name = arg.replace('_', '-')
                opt_args[pos] = Arg(arg_name, summary, defaults[i],
                                    type_converter)

                continue

            type_converter = arg_types.get(arg)
            opt_name = arg.replace('_', '-')
            opts[arg] = Option(opt_name, summary, defaults[i], short_name,
                               type_converter)

        return cls(func, args, opt_args, opts, arg_types, usage_msg, name)

class App(object):
    """A command-line application."""

    def __init__(self, usage_msg=None, arg_types={}, opt_args=[]):
        """Create an App.

        usage_msg -- optional string explaining this App to an end-user.
                     PEP 257 says docstrings should be usable as a
                     command-line module's usage statement, so this is
                     usually __doc__.

                     Anything that looks like a parameter description
                     will be removed.

        arg_types -- optional dict mapping arg names to callables that
                     take a string as input and either return an object
                     of the desired type or raise a ValueError.

        opt_args -- optional list of arg names that should be treated as
                    optional args instead of options.

        """

        self.cmd = None

        self.arg_types = arg_types
        self.opt_args = opt_args
        self.main_cmd = None
        self.commands = {}
        self.name = None
        self.argv = []

        if usage_msg is not None:
            usage_msg = _get_usage_msg(usage_msg).strip()

        self.usage_msg = usage_msg

        # Stores the globals dict for whatever module this app was created in.
        self.module_globals = None
        self.global_opts = {}

        # Fields that support the main() and command() decorators.
        # They hold whatever args were passed to the decorators.

        # GRIPE They also have utterly lousy names. '_dec' stands for
        # 'decorator', but I keep forgetting that. Find a better one. Or put
        # these in a single dict, which would probably be simpler.
        self._dec_short_names = None
        self._dec_opt_args = None
        self._dec_main_cmd = None
        self._dec_arg_types = None
        self._dec_usage_msg = None

    @property
    def has_subcmds(self):
        """Boolean indicating whether this app has subcommands."""

        return len(self.commands) > 0

    def _cmd_decorator(self, func):
        """Do the work of decorating func as a command.

        Interprets private fields that store any params passed to the
        actual decorators.

        This exists so we can mostly hide the different behavior
        of decorators with args vs. decorators without args from the end
        user.

        Really, we just want to avoid having two decorators with
        virtually identical names for a single purpose. Who really wants
        to worry about App.command() vs. App.command_args()?

        We achieve this by requiring all args to our decorators to be
        passed as keyword arguments. That's a little noxious, but I
        think it's better than having two differently-named decorators
        for what looks to a user like the same task.

        """

        short_names = self._dec_short_names
        opt_args = self._dec_opt_args
        usage_msg = self._dec_usage_msg

        # Merge self.arg_types with the command's arg_types, deferring to the
        # command's data.
        arg_types = dict(self.arg_types)
        if self._dec_arg_types is not None:
            arg_types.update(self._dec_arg_types)

        if len(self.opt_args) > 0:
            if opt_args is not None:
                opt_args.extend(self.opt_args)
            else:
                opt_args = self.opt_args[:]
        cmd = Command.from_func(func, short_names, opt_args, arg_types,
                                usage_msg)

        if self._dec_main_cmd is True:
            # This is the main command.
            self.main_cmd = cmd
        else:
            # This is a subcommand.
            self.commands[cmd.name] = cmd

        if 'help' not in self.commands:
            # Add a 'help' command.
            help_cmd = Command.from_func(self.show_help, name='help',
                                         opt_args=['cmd'])
            self.commands[help_cmd.name] = help_cmd

        # Empty state-transfer fields for next call.
        self._dec_short_names = None
        self._dec_opt_args = None
        self._dec_arg_types = None
        self._dec_usage_msg = None

        return func

    def main(self, func=None, short_names=None, opt_args=None, arg_types=None):
        """Decorator to make func the main command for this app.

        All arguments to it *must* be passed as keyword args, like so:

        >>> @app.main(short_names={'foobar': 'o'})
        >>> def func(foobar='thing'):
        ...     pass

        This wart is due to a perhaps-ill-conceived attempt to hide the
        gorier details of how decorators work from the programmer. It
        seems preferable to having multiple decorators with different
        names that perform the same task.

        If you attempt to call it on a function without using keyword
        args, it will throw an exception.

        N.B.: if you pass a single callable as the only non-keyword arg,
        it will try to make it a command. That is very undesireable
        behavior, for which I apologize, but I do not currently see a
        way to avoid it.

        short_names -- dict mapping func's optional arg names to single
            letters that can be used as short names.
        opt_args -- list of func's optional params that should be
            treated as optional command-line args instead of options.
        arg_types -- dict mapping optional param names to callables
            that take a string as input and return an object of the
            desired type (or raise a ValueError).

        """

        kwargs_passed = False
        if (short_names is not None or opt_args is not None or
            arg_types is not None):
            kwargs_passed = True

        self._dec_short_names = short_names
        self._dec_opt_args = opt_args
        self._dec_arg_types = arg_types

        self._dec_main_cmd = True

        if func is not None and kwargs_passed is True:
            raise Exception('You may only pass args to this decorator as '
                            'keyword args.')

        if kwargs_passed is True:
            # Return a function that will decorate func.
            return self._cmd_decorator
        else:
            # Decorate func and return the result.
            return self._cmd_decorator(func)

    def command(self, func=None, short_names=None, opt_args=None,
                arg_types=None, usage_msg=None):
        """Decorator to mark func as a command.

        All arguments to it *must* be passed as keyword args, like so:

        >>> @app.command(short_names={'foobar': 'o'})
        >>> def func(foobar='thing'):
        ...     pass

        If you attempt to call it on a function without using keyword
        args, it will throw an exception.

        This wart is due to a perhaps-ill-conceived attempt to hide the
        gorier details of how decorators work from the programmer. It
        seems preferable to having multiple decorators with different
        names that perform the same task, however.

        short_names -- dict mapping func's optional arg names to single
            letters that can be used as short names.
        opt_args -- list of func's optional params that should be
            treated as optional command-line args instead of options.
        arg_types -- dict mapping optional param names to callables
            that take a string as input and return an object of the
            desired type (or raise a ValueError).
        usage_msg -- explanation of how to use the command. Defaults
                     a version of func's docstring.

        """

        # GRIPE Most of this footwork is identical to what we do in
        # App.main(). This should be DRYed up.
        kwargs_passed = False
        if (usage_msg is not None or short_names is not None or
            opt_args is not None or arg_types is not None):
            kwargs_passed = True

        self._dec_short_names = short_names
        self._dec_opt_args = opt_args
        self._dec_arg_types = arg_types
        self._dec_usage_msg = usage_msg

        self._dec_main_cmd = False

        if func is not None and kwargs_passed is True:
            raise Exception('You may only pass args to this decorator as '
                            'keyword args.')

        if kwargs_passed is True:
            # Return a function that will decorate func.
            return self._cmd_decorator
        else:
            # Decorate func and return the result.
            return self._cmd_decorator(func)

    def make_global_opts(self, module_globals, arg_types):
        """Set up our global options from module_globals.

        module_globals -- The calling module's __dict__, which is used
                          to get references to the actual variables.
                          Best retrieved by calling globals().

        arg_types -- A dict mapping module variable names to type
                     conversion callables. Module vars will only be
                     treated as global options if they're in this
                     dict.

        """

        self.module_globals = module_globals

        summaries = _get_param_summaries(self.usage_msg)

        for var_name, type_converter in arg_types.items():
            name = var_name.replace('_', '-')
            value = module_globals[var_name]
            summary = None if var_name not in summaries else summaries[var_name]
            opt = Option(name, summary, value, type_converter=type_converter)
            self.global_opts[name] = opt

    @classmethod
    def _format_opt_summaries(self, opts):
        """Return a formatted list of option summaries.

        Meant as a helper method for self.show_help, really.

        opts -- a dict of Options, with option name as the key.

        """

        opt_summaries = []
        for opt in opts.values():
            summary = opt.format_summary()
            if summary is not None:
                opt_summaries.append(summary)

        return opt_summaries

    def show_help(self, cmd=None, show_global_opts=False):
        """Display help for this app.

        cmd -- optional string specifying a subcommand.
        show_global_opts -- optional flag controlling whether we display
                            global options in output. Defaults to False.

        """

        # DEBUG This should be calculated based on the App's current
        # environment, not hardcoded.
        width = 70
        sep = os.linesep * 2

        if cmd is None:
            cmd = self.main_cmd

            # In this case, we want to show global options. This is technically
            # a violation of the flag's default state, but is probably better
            # UI.
            show_global_opts = True

            if self.usage_msg is not None:
                print self.usage_msg
                print

            if self.has_subcmds and cmd is None:
                print self.get_avail_cmds()

                # GRIPE Ugly - explicitly dumping global opts in this case,
                # even though we're not showing any other info of this sort.
                if show_global_opts:
                    opt_summaries = self._format_opt_summaries(self.global_opts)
                    if len(opt_summaries) > 0:
                        opt_summaries.insert(0, 'Global Options:')
                        print
                        print sep.join(opt_summaries)
                return
        else:
            cmd = self.commands.get(cmd)
            if cmd is None:
                raise UnknownCommand(cmd)

        app_name = self.name
        if cmd is not None and cmd is not self.main_cmd:
            app_name += ' %s' % cmd.name

        example = 'Usage:%s%s' % (os.linesep, app_name)

        help_msg = ''
        usage_paras = []
        usage_msg = self.usage_msg
        if cmd.usage_msg is not None:
            usage_msg = cmd.usage_msg

        if usage_msg is not None:
            for paragraph in usage_msg.split('\n' * 2):
                indent_level = 0
                for char in paragraph:
                    if char == ' ':
                        indent_level += 1
                        break

                if indent_level == 0:
                    usage_paras.append(textwrap.fill(paragraph, width))
                else:
                    # As there was indentation, we leave the lines exactly as
                    # they were - could be a sample code block or similar.
                    usage_paras.append(paragraph)

                indent_level = 0

            help_msg += sep.join(usage_paras)

        input_summaries = []
        if cmd.max_argc > 0:
            arg_summaries = []
            for arg in cmd.args:
                example += ' <%s>' % arg.name
                summary = arg.format_summary()
                if summary is not None:
                    # Only explain inputs that have explanations.
                    arg_summaries.append(summary)

            for arg in cmd.opt_args:
                example += ' [<%s>]' % arg.name
                summary = arg.format_summary()
                if summary is not None:
                    arg_summaries.append(summary)

            if len(arg_summaries) > 0:
                arg_summaries.insert(0, 'Arguments:')
                input_summaries.extend(arg_summaries)

        opt_summaries = self._format_opt_summaries(cmd.opts)
        if len(opt_summaries) > 0:
            # GRIPE It might be a nice touch to distinguish between
            # options and flags.
            opt_summaries.insert(0, 'Options:')
            input_summaries.extend(opt_summaries)

        if show_global_opts:
            opt_summaries = self._format_opt_summaries(self.global_opts)
            if len(opt_summaries) > 0:
                opt_summaries.insert(0, 'Global Options:')
                input_summaries.extend(opt_summaries)

        if help_msg:
            input_summaries.insert(0, help_msg)

        if self.has_subcmds and cmd is self.main_cmd:
            input_summaries.append(self.get_avail_cmds())

        sep = os.linesep * 2
        help_msg = sep.join(input_summaries)

        print os.linesep.join([example + os.linesep, help_msg])

    def get_avail_cmds(self):
        """Return a string listing this App's commands."""

        header = 'Available commands:\n'
        if self.main_cmd is not None:
            header = 'Available subcommands:\n'

        lines = [header]
        for name, cmd in self.commands.items():
            lines.append('  %s -- %s' % (name, cmd.summary))

        return os.linesep.join(lines)

    def _parse_argv(self, argv=None):
        """Return (cmd, args, opts) from `argv`.

        It is a helper, only meant for use by `self._do_cmd`.

        `cmd` is the Command to run.
        `args` is a list of argument values.
        `opts` is a dict mapping option name to passed value.

        argv -- List of inputs to program, including executable name.
                Defaults to `sys.argv`.

        """

        if argv is None:
            argv = sys.argv

        self.name = argv[0]
        cmd = self.main_cmd
        inputs = argv[1:]

        args = []
        opts = {}

        known_opts = {}
        def _add_known_opts(opts):
            """Given an iterable of Options, add them to `known_opts`.

            I don't like inline functions much, but this DRYs a few
            lines fairly cleanly.

            """

            for opt in opts:
                known_opts[opt.name] = opt
                if opt.short_name is not None:
                    known_opts[opt.short_name] = opt

        _add_known_opts(self.global_opts.values())

        if cmd is not None:
            _add_known_opts(cmd.opts.values())

        # When literal_inputs is True, items are treated as input to a Command,
        # and cannot be command names or options.
        literal_inputs = False
        while len(inputs) > 0:
            item = inputs.pop(0)

            if item == '--':
                literal_inputs = True
                continue

            if item.startswith('--') and not literal_inputs:
                # item is a long option name, possibly including a value.
                item = item.strip('-')
                opt_name, sep, val = item.partition('=')

                for opt in known_opts.values():
                    if opt_name == opt.short_name and (opt.name in opts or
                                                       opt.short_name in opts):
                        raise DuplicateOption(opt_name, opt.short_name)
                    elif opt_name == opt.name and (opt.name in opts or
                                                   opt.short_name in opts):
                        raise DuplicateOption(opt_name, opt.name)

                if opt_name not in known_opts:
                    raise UnknownOption(opt_name)

                opt = known_opts[opt_name]
                if opt.is_flag:
                    val = not opt.default
                elif val == '':
                    val = inputs.pop(0)

                opt_name = opt.name
                opts[opt_name] = opt.convert_type(val)
            elif item.startswith('-') and not literal_inputs:
                # item is one or more short option names, possibly followed by
                # a value. All but the last short name must be flags.
                item = item.strip('-')

                val = None
                last_opt = None
                for i, char in enumerate(item):
                    if char not in known_opts and val is None:
                        raise UnknownOption(char)

                    if val is not None:
                        val += char
                        continue

                    # GRIPE This exact block (with a single name change)
                    # appears in the long-option-name if, which is very sad.
                    for opt in known_opts.values():
                        if char == opt.short_name and (opt.name in opts or
                                                       opt.short_name in opts):
                            raise DuplicateOption(char, opt.short_name)
                        elif char == opt.name and (opt.name in opts or
                                                       opt.short_name in opts):
                            raise DuplicateOption(char, opt.name)

                    opt = known_opts[char]
                    if opt.is_flag:
                        opt_name = opt.name
                        opts[opt_name] = not opt.default
                    else:
                        last_opt = char
                        val = ''

                if last_opt is not None:
                    if val is None or '':
                        val = inputs.pop(0)

                    last_opt = known_opts[last_opt]
                    opt_name = last_opt.name
                    opts[opt_name] = last_opt.convert_type(val)
            else:
                args_len = len(args)
                if (cmd is self.main_cmd and self.has_subcmds and
                    len(args) == 0 and not literal_inputs):
                    # This may be a command name.
                    cand = self.commands.get(item)
                    if cand is None:
                        if self.main_cmd is None:
                            # A command must be specified.
                            raise UnknownCommand(item)
                        else:
                            # This is a positional argument.
                            args.append(item)
                    else:
                        cmd = cand
                        _add_known_opts(cmd.opts.values())
                else:
                    args.append(item)

                if args_len < len(args):
                    # A new arg was added - set its type.
                    # GRIPE Doing this retroactively is ugly.
                    arg_pos = len(args) - 1
                    num_req_args = len(cmd.args)
                    if arg_pos <= num_req_args - 1:
                        # Required arg.
                        arg = cmd.args[arg_pos]
                    else:
                        # Optional arg.
                        if arg_pos >= cmd.max_argc:
                            raise BadArgCount(cmd.name, cmd.min_argc,
                                              cmd.max_argc, len(args))

                        arg = cmd.opt_args[arg_pos - num_req_args - 1]

                    args[-1] = arg.convert_type(args[-1])

        if cmd is None:
            raise UnknownCommand()

        if len(args) < cmd.min_argc:
            raise BadArgCount(cmd.name, cmd.min_argc, cmd.max_argc, len(args))

        return cmd, args, opts

    def _do_cmd(self, argv):
        """Return result of running command specified by `argv`."""

        cmd, args, opts = self._parse_argv(argv)
        self.cmd = cmd

        # Set any global options.
        for name, opt in self.global_opts.items():
            val = opts.get(name)
            if val is not None:
                # Don't pass the command options it doesn't know.
                del opts[name]
            else:
                val = opt.default

            var_name = name.replace('-', '_')

            self.module_globals[var_name] = opt.convert_type(val)

        # Convert option names into variable names for use as **kwargs.
        for opt_name, value in opts.items():
            var_name = opt_name.replace('-', '_')
            del opts[opt_name]
            opts[var_name] = value

        return cmd.run(args, opts)

    def _show_err_msg(self, msg):
        """Display an error message to `sys.stderr`."""

        print >> sys.stderr, 'ERROR: %s' % msg

        if self.cmd is not self.main_cmd and self.cmd is not None:
            help_msg = "Run '%s help %s' for usage message." % (self.name,
                                                                self.cmd.name)
        else:
            help_msg = "Run '%s help' for usage message." % self.name

        print >> sys.stderr, help_msg

    def run(self, argv=None):
        """Run this app with argv as command-line input.

        argv -- defaults to sys.argv, but pass another list if you like.

        """

        if argv is None:
            argv = sys.argv

        err_msg = None
        try:
            exit_code = self._do_cmd(argv)
            if exit_code is None:
                # If we haven't been told otherwise, assume things worked.
                exit_code = 0

            if type(exit_code) is int and (exit_code >= 0 or exit_code <= 127):
                sys.exit(exit_code)
        except UnknownCommand as exc:
            # We want to display the available commands in this case, so we
            # don't populate err_msg.
            msg = None
            if exc.input is not None:
                msg = "ERROR: '%s' is not a known command." % exc.input

            if msg is not None:
                print >> sys.stderr, 'ERROR: %s' % msg

            print >> sys.stderr, self.get_avail_cmds()
        except BadArgCount as exc:
            arg_str = 'arg' if exc.max_argc is 1 else 'args'
            if exc.num_given > exc.max_argc:
                err_msg = "'%s' takes at most %s %s." % (exc.input,
                                                         exc.max_argc,
                                                         arg_str)
            else:
                err_msg = 'You must enter at least %s %s.' % (exc.min_argc,
                                                              arg_str)
        except ValueError as exc:
            err_msg = "'%s' is not a valid value for '%s'." % (exc.value,
                                                               exc.input)
        except UnknownOption as exc:
            err_msg = "'%s' is not a known option." % exc.input
        except DuplicateOption as exc:
            err_msg = ("You have passed options '%s' and '%s', which are "
                       "duplicates.")
            err_msg = err_msg % (exc.name, exc.input)
        except InvalidInput as exc:
            err_msg = "'%s' is invalid input." % exc.input

        if err_msg is not None:
            self._show_err_msg(err_msg)
            sys.exit(_USAGE_ERR_CODE)
