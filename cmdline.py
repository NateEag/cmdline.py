"""A module for writing command-line Python programs.

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
import types

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

    def __init__(self, name, value=None):
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

class Arg(object):
    """An argument a command-line app accepts."""

    def __init__(self, name, summary, default=None):

        self.name = name
        self.summary = summary
        self.default = default

class Option(object):
    """An option a command-line app accepts."""

    def __init__(self, name, summary, default, short_name=None):
        self.name = name
        self.default = default
        self.summary = summary
        self.short_name = name[0] if short_name is None else short_name

class Command(object):
    """A sub-command in a command-line app.

    These are best created by decorating functions with App.command() or
    App.main().

    Using this class directly would work, but it wouldn't be as pretty.

    """

    # Used to recognize PEP 257-style function arg descriptions in
    # docstrings.
    _pep_257_re = re.compile(r'^(\w+) --')

    # GRIPE You could argue that __init__ should actually just be
    # from_func. I'm not sure if you'd be right or not.
    def __init__(self, func, args, opt_args, opts, flags, output_alg=None,
                 param_types=None, usage_msg=None, name=None):
        """Make a new Command.

        func -- callable that does the command's work.
        args -- list of required positional args for this command.
        opt_args -- list of optional positional args for this command.
        opts -- list of options for this command. Options map a name to a
            (required) passed value (with an optional short name).
        flags -- list of flags for this command. Flags are Booleans with a
            short name and a long name. When set, flags invert their default
            value.
        output_alg -- callable to display `func`'s return value.
            Defaults to None, as good *nix programs are silent by default.
        param_types -- optional dict mapping param names to callables
            that take a string as input and return an object of the
            desired type (or raise a ValueError).
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
        self.flags = flags
        self.output_alg = output_alg
        self.param_types = param_types
        self.usage_msg = usage_msg

        summary = None
        if usage_msg is not None:
            summary = self.usage_msg
            end_idx = summary.find('. ')
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
        for key, value in self.flags.items():
            if value.short_name in self.short_names:
                raise InvalidShortName(self.name, value.short_name,
                                       self.short_names[value.short_name],
                                       value.name)

            self.short_names[value.short_name] = key

    def _get_usage_str(self, width=80):
        """Return a usage string formatted to `width` chars.

        width -- max # of chars in a line.

        """

        # DEBUG Implement this.
        # Before we can, we'll have to add some decent docstring parsing.
        pass

    def show_usage(self, stream=None):
        """Display this Command's usage message.

        stream -- optional file-like output stream. Default is stdout.

        """

        if stream is None:
            stream = sys.stdout

        # STUB This is temporary - eventually we need to format this nicely
        # and think about how wide a device we're being displayed in.
        print >> stream, self.usage_msg

        if len(self.args) > 0:
            print >> stream
            print >> stream, 'Args:'
            for arg in self.args:
                print >> stream, '%s: %s'

        if len(self.opts) > 0:
            print >> stream
            print >> stream, 'Options:'
            for name, opt in self.opts.items():
                print >> stream, '%s: %s' % (name, opt.summary)

        if len(self.flags) > 0:
            print >> stream
            print >> stream, 'Flags:'
            for name, flag in self.flag.items():
                print >> stream, '%s: %s' % (name, flag.summary)

        # Figure out how many chars wide the device we're displaying to is.
        # Default to 80 if none are found?

        # Get a help string formatted to needed width and add it to stream.

    def run(self, inputs):
        """Run this command with `inputs` as our argv array."""

        args = []
        kwargs = {}

        num_args = len(self.args)
        num_opt_args = len(self.opt_args)
        max_args = num_args + num_opt_args
        num_inputs = len(inputs)
        i = 0
        arg_idx = 0
        opt_arg_names = [key for key in self.opt_args]
        opt_arg_idx = 0
        while i < num_inputs:
            item = inputs[i]
            if item.startswith('-'):
                # item is an option.
                item = item.lstrip('-')

                if '=' in item:
                    # An option and value are both in this item.
                    opt, junk, val = item.partition('=')
                    if opt in self.short_names:
                        opt = self.short_names[opt]

                    if opt in self.flags:
                        raise InvalidFlag(opt, val)
                else:
                    # This item is just an option.
                    opt = item
                    if opt in self.short_names:
                        opt = self.short_names[opt]

                    if opt in self.opts:
                        j = i + 1
                        if j >= num_inputs or inputs[j].startswith('-'):
                            # This is an option and requires a value.
                            raise InvalidOption(opt)

                        i += 1
                        val = inputs[i]

                if opt in self.flags:
                    val = not self.flags[opt].default
                elif opt not in self.opts:
                    raise UnknownOption(opt)

                if opt in self.param_types:
                    val = self.param_types[opt](val)

                kwargs[opt] = val
            else:
                # Item is an arg.
                if arg_idx < num_args:
                    cur_arg = self.args[arg_idx]
                    arg_idx += 1
                elif opt_arg_idx < num_opt_args:
                    opt_arg_name = opt_arg_names[opt_arg_idx]
                    opt_arg_idx += 1
                    cur_arg = self.opt_args[opt_arg_name]

                if (self.param_types is not None and
                    cur_arg.name in self.param_types):
                    item = self.param_types[cur_arg.name](item)

                args.append(item)

            i += 1

        num_args_passed = len(args)
        if num_args_passed < num_args or num_args > max_args:
            raise BadArgCount(self.name, num_args, max_args, num_args_passed)

        # Default any optional args that were not passed.
        num_opt_args_passed = num_args_passed - num_args
        for i, key in enumerate(self.opt_args):
            if i >= num_opt_args_passed:
                args.append(self.opt_args[key].default)

        result = self.func(*args, **kwargs)

        if self.output_alg is not None and result is not None:
            self.output_alg(result)

    @classmethod
    def _get_param_summaries(cls, docstr):
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
            match = cls._pep_257_re.match(line)
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

    @classmethod
    def _get_usage_msg(cls, docstr):
        """Parse `docstr` and return a usage message.

        Mostly, this tries to guess at what point a docstring stops
        being applicable to a command and returns everything before
        that, with paragraphs merged into a single line, so they can
        be formatted to an arbitrary width later.

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

        usage_msg = ''
        blank_line_seen = False
        for line in docstr.splitlines():
            # GRIPE This is a lot like the code for getting param summaries -
            # should they be merged for DRYness, or would that hurt readability
            # too much?
            match = cls._pep_257_re.match(line)
            if line.startswith('>>>') or (line.startswith('@param') or
                                          line.startswith(':param') or
                                          match is not None):
                break
            elif line == '':
                usage_msg += os.linesep * 2
            else:
                usage_msg += line if usage_msg.endswith(os.linesep) else ' ' + line

        return usage_msg.strip()

    @classmethod
    def from_func(cls, func, output_alg=None, short_names=None, opt_args=None,
                  param_types=None, usage_msg=None):
        """Get an instance of Command by introspecting func.

        func -- a callable object.
        output_alg -- an optional callable that displays output based
            on func's return value.
        short_names -- a dict mapping long option names to single letters.
        opt_args -- a list of func's optional params that should be
            treated as optional command-line args instead of options.
        param_types -- dict mapping optional param names to callables
            that take a string as input and return an object of the
            desired type (or raise a ValueError).
        usage_msg -- an optional string explaining the command. Defaults
            to a processed version of func's docstring.

        DEBUG This should ignore self/cls parameters. I'm not sure how
        to distinguish between functions and methods, so for now we're
        not worrying about it. We could just ignore those names if in
        0th position - only really nasty code would break on that.

        """

        if opt_args is None:
            # GRIPE It might be better to go through and make default
            # opt_args an empty list everywhere.
            opt_args = []

        # Grab any param summary from the docstring.
        docstr = inspect.getdoc(func)
        if docstr is not None:
            # GRIPE We should probably let you pass param summaries from
            # outside.
            summaries = cls._get_param_summaries(docstr)
            if usage_msg is None:
                usage_msg = cls._get_usage_msg(docstr)

        # Inspect func for hard data.
        func_args, varargs, varkw, defaults = inspect.getargspec(func)
        num_defaults = 0 if defaults is None else len(defaults)
        num_func_args = 0 if func_args is None else len(func_args) - num_defaults
        func_name = func.__name__

        # Build required arg dict.
        arg_list = func_args[:num_func_args]
        args = {}
        for i, arg in enumerate(arg_list):
            summary = summaries.get(arg)
            args[i] = Arg(arg, summary)

        # Build optional arg dict, option dict, and flag dict.
        # (Yes, this is rather ugly.)
        opt_args_dict = OrderedDict()
        opts = {}
        flags = {}
        for i, arg in enumerate(func_args[num_func_args:]):
            short_name = None
            if short_names is not None:
                tmp = short_names.get(arg)
                if tmp is not None and len(tmp) == 1:
                    short_name = tmp

            summary = summaries.get(arg)

            if arg in opt_args:
                opt_args_dict[arg] = Arg(arg, summary, defaults[i])

                continue

            if isinstance(defaults[i], bool):
                flags[arg] = Option(arg, summary, defaults[i], short_name)

                continue

            opts[arg] = Option(arg, summary, defaults[i], short_name)

        return cls(func, args, opt_args_dict, opts, flags, output_alg,
                   param_types, usage_msg)

class App(object):
    """A command-line application."""

    def __init__(self, usage_msg=None, output_alg=None):
        """Create an App.

        usage_msg -- optional string explaining this App to an end-user.
            PEP 257 says docstrings should be usable as a command-line
            module's usage statement, so this is usually __doc__.

        """

        self.cmd = None

        self.output_alg = output_alg
        self.main_cmd = None
        self.commands = {}
        self.script_name = None
        self.argv = []
        self.usage_msg = usage_msg if usage_msg is None else usage_msg.strip()

        # Stores the globals dict for whatever module this app was created in.
        self.module_globals = None
        # Options that modify the behavior of more than one command.
        # DEBUG This is only needed to store type mappings, really. Should I
        # bother with full Option objects?
        self.global_opts = {}
        self.global_opt_types = {}

        # Fields that support the main() and command() decorators.
        # They hold whatever args were passed to the decorators.

        # GRIPE They also have utterly lousy names. '_dec' stands for
        # 'decorator', but I keep forgetting that. Find a better one. Or put
        # these in a single dict, which would probably be simpler.
        self._dec_output_alg = None
        self._dec_short_names = None
        self._dec_opt_args = None
        self._dec_main_cmd = None
        self._dec_param_types = None
        self._dec_usage_msg = None

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

        DEBUG This strategy might be a bad idea. Certainly it's warty.
        If you have arguments in either direction, please tell me.

        """

        output_alg = self._dec_output_alg
        if self._dec_output_alg is None:
            # Use app's default output algorithm.
            output_alg = self.output_alg

        short_names = self._dec_short_names
        opt_args = self._dec_opt_args
        param_types = self._dec_param_types
        usage_msg = self._dec_usage_msg

        cmd = Command.from_func(func, output_alg, short_names, opt_args,
                                param_types, usage_msg)
        if self._dec_main_cmd is True:
            # This is the main command.
            self.main_cmd = cmd
        else:
            # This is a subcommand.
            self.commands[cmd.name] = cmd

        # Empty state-transfer fields for next call.
        self._dec_output_alg = None
        self._dec_short_names = None
        self._dec_opt_args = None
        self._dec_param_types = None
        self._dec_usage_msg = None

        return func

    def main(self, func=None, output_alg=None, short_names=None,
             opt_args=None, param_types=None):
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

        output_alg -- callable to format func's return value for output.
        short_names -- dict mapping func's optional arg names to single
            letters that can be used as short names.
        opt_args -- list of func's optional params that should be
            treated as optional command-line args instead of options.
        param_types -- dict mapping optional param names to callables
            that take a string as input and return an object of the
            desired type (or raise a ValueError).

        """

        default_args_passed = False
        if (output_alg is not None or short_names is not None or
            opt_args is not None or param_types is not None):
            default_args_passed = True

        self._dec_output_alg = output_alg
        self._dec_short_names = short_names
        self._dec_opt_args = opt_args
        self._dec_param_types = param_types

        self._dec_main_cmd = True

        if func is not None and default_args_passed is True:
            # DEBUG Unclear message.
            raise Exception('Either pass defaults with explicit keyword '
                            'names, or pass no args.')

        if default_args_passed is True:
            # Return a function that will decorate func.
            return self._cmd_decorator
        else:
            # Decorate func and return the result.
            return self._cmd_decorator(func)

    def command(self, func=None, output_alg=None, short_names=None,
                opt_args=None, param_types=None, usage_msg=None):
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

        output_alg -- callable to format func's return value for output.
        short_names -- dict mapping func's optional arg names to single
            letters that can be used as short names.
        opt_args -- list of func's optional params that should be
            treated as optional command-line args instead of options.
        param_types -- dict mapping optional param names to callables
            that take a string as input and return an object of the
            desired type (or raise a ValueError).
        usage_msg -- explanation of how to use the command. Defaults
                     to parsing func's docstring.

        """

        # GRIPE Most of this footwork is identical to what we do in
        # App.main(). This should be DRYed up.
        default_args_passed = False
        if (usage_msg is not None or output_alg is not None or
            short_names is not None or opt_args is not None or
            param_types is not None):
            default_args_passed = True

        self._dec_output_alg = output_alg
        self._dec_short_names = short_names
        self._dec_opt_args = opt_args
        self._dec_param_types = param_types
        self._dec_usage_msg = usage_msg

        self._dec_main_cmd = False

        if func is not None and default_args_passed is True:
            # DEBUG Unclear message.
            raise Exception('Either pass defaults with explicit keyword '
                            'names, or pass no args.')

        if default_args_passed is True:
            # Return a function that will decorate func.
            return self._cmd_decorator
        else:
            # Decorate func and return the result.
            return self._cmd_decorator(func)

    def make_global_opts(self, module_globals, var_types):
        """Set up our global options from module_globals."""

        self.module_globals = module_globals
        self.global_opt_types = var_types

        # Store only the module's public global variables as options.
        # GRIPE This is the step that's likely to go wrong, and is relatively
        # implicit. Is this actually a good idea? Should we make them explicitly
        # specify global options by name?
        for key, value in module_globals.items():
            if (not hasattr(value, '__call__') and
                type(value) != types.ClassType and
                type(value) != types.ModuleType and
                not isinstance(value, App) and
                not key.startswith('_')):
                # This is probably a module-level option.
                # GRIPE Also, this code is very ugly.
                name = key.replace('_', '-')
                opt = Option(name, None, value)
                self.global_opts[name] = opt

    def show_usage(self, stream=None):
        """Display this App's usage message.

        stream -- optional file-like output stream. Default is stdout.

        """

        if stream is None:
            stream = sys.stdout

        if self.usage_msg is not None:
            print >> stream, self.usage_msg
            print >> stream

        if len(self.commands):
            self.show_avail_cmds(stream=stream)

    def show_avail_cmds(self, stream=None):
        """Display this App's commands.

        stream -- optional file-like output stream. Default is stdout.

        """

        if stream is None:
            stream = sys.stdout

        print >> stream, "Available commands:\n"
        for name, cmd in self.commands.items():
            print >> stream, '%s -- %s' % (name, cmd.summary)

    def _do_cmd(self, argv):
        """Parse `argv` and run the specified command."""

        self.argv = argv[:]
        self.script_name = argv[0]

        inputs = argv[1:]
        global_opts = {}
        show_help = False
        for i, item in enumerate(inputs):
            if item.startswith('-'):
                item = item.strip('-')

                # GRIPE Try applying a similar approach to our other opt
                # parsing logic. It seems a bit cleaner.
                opt_name, junk, val = item.partition('=')
                # DEBUG Coders may want to use 'h' for opts other than 'help'.
                if opt_name == 'help' or opt_name == 'h':
                    show_help = True
                    # Throw out the 'help' option - it's always treated as
                    # global, and we don't want to actually pass it to a
                    # command.
                    inputs.pop(i)
                    continue
                if opt_name not in self.global_opts:
                    continue

                opt = self.global_opts[opt_name]
                inputs.pop(i)
                if type(opt.default) == types.BooleanType:
                    # This option is a flag.
                    if val is not '':
                        raise InvalidOption(opt_name, value)
                    val = not opt.default
                elif val is '':
                    # There was no '=' - if there's another item in the list,
                    # that's our value.
                    if len(inputs) > i:
                        val = inputs.pop(i)
                    else:
                        raise InvalidOption(opt_name)

                # DEBUG Here's where we ought to handle type mappings.
                var_name = opt_name.replace('-', '_')
                if var_name in self.global_opt_types:
                    val = self.global_opt_types[var_name](val)

                global_opts[opt_name] = val

        for opt_name in global_opts:
            val = global_opts[opt_name]
            var_name = opt_name.replace('-', '_')
            self.module_globals[var_name] = global_opts[opt_name]

        if len(inputs) > 0 and inputs[0] == 'help':
            # We should show help instead of running a command.
            show_help = True
            inputs.pop(0)

        self.cmd = self.main_cmd
        cmd_name = None
        if len(self.commands) > 0:
            # This program uses subcommands, so the first command must be one.

            # DEBUG Should an App with a self.main_cmd be allowed to have
            # subcommands? Bob pointed out that it probably shouldn't -
            # subcommands break badly, since you can't tell the difference
            # between input that matches a command name and an attempt to
            # invoke the command. This means @command and @main should throw an
            # exception if such a setup is detected. Unless there's a sane way
            # to escape inputs matching command names.
            if (self.main_cmd is None and len(self.commands) < 1 and
                len(inputs) < 1):
                raise UnknownCommand()

            if len(inputs) > 0:
                cmd_name = inputs[0]
                self.cmd = self.commands.get(cmd_name)

            args = inputs[1:]

            if self.cmd is None and cmd_name is not None:
                # GRIPE There should be more advanced error handling here.
                # Like printing a usage message if one is defined.
                raise UnknownCommand(cmd_name)
        else:
            args = inputs

        if show_help == True or self.cmd is None:
            if cmd_name is None:
                self.show_usage()
            elif self.cmd is not None:
                self.cmd.show_usage()
        else:
            self.cmd.run(args)

    def run(self, argv=None):
        """Run this app with argv as command-line input.

        argv -- defaults to sys.argv, but pass another list if you like.

        """

        if argv is None:
            argv = sys.argv

        try:
            self._do_cmd(argv)
        except UnknownCommand as exc:
            if exc.input is None:
                print >> sys.stderr, 'You must enter a command.'
            else:
                print >> sys.stderr, "'%s' is not a known command." % exc.input
                self.show_avail_cmds(sys.stderr)
        except InvalidInput as exc:
            print >> sys.stderr, 'Invalid input: %s' % exc.input
            raise

def print_str(obj):
    """Basic output algorithm for command-line programs.

    Cast `obj` to a string, then print the result.

    """

    text = str(obj)

    print text
