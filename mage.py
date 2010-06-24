# -*- coding: utf-8 -*-

import sys


__all__ = ['manage', 'CommandDigest']


class CommandNotFound(AttributeError): pass


def manage(commands, argv):
    '''
    Parses argv and runs neccessary command. Is to be used in manage.py file.

    Accept a dict with digest name as keys and instances of
    :class:`CommandDigest<insanities.management.commands.CommandDigest>`
    objects as values.

    The format of command is the following::

        ./manage.py digest_name:command_name[ arg1[ arg2[...]]][ --key1=kwarg1[...]]

    where command_name is a part of digest instance method name, args and kwargs
    are passed to the method. For details, see
    :class:`CommandDigest<insanities.management.commands.CommandDigest>` docs.
    '''
    if len(argv) > 1:
        cmd_name = argv[1]
        raw_args = argv[2:]
        args, kwargs = [], {}
        # parsing params
        for item in raw_args:
            if item.startswith('--'):
                splited = item[2:].split('=', 1)
                if len(splited) == 2:
                    k,v = splited
                elif len(splited) == 1:
                    k,v = splited[0], True
                else:
                    sys.exit('Error while parsing argument "%s"' % item)
                kwargs[k] = v
            else:
                args.append(item)

        # trying to get command instance
        if ':' in cmd_name:
            digest_name, command = cmd_name.split(':')
        else:
            digest_name = cmd_name
            command = None
        try:
            digest = commands[digest_name]
        except KeyError:
            sys.stdout.write('Commands:\n')
            for k in commands.keys():
                sys.stdout.write(str(k))
                sys.stdout.write('\n')
            sys.exit('Command "%s" not found' % digest_name)
        try:
            digest(command, *args, **kwargs)
        except CommandNotFound:
            sys.stdout.write(commands[digest_name].description())
            sys.exit('Command "%s:%s" not found' % (digest_name, command))
    else:
        sys.exit('Please provide any command')


class CommandDigest(object):
    ''

    def default(self, *args, **kwargs):
        '''This method will be called if command_name in __call__ is None'''
        sys.stdout.write(self.description())

    def description(self):
        '''Description outputed to console'''
        _help = self.__class__.__doc__ if self.__class__.__doc__ else ''
        for k in dir(self):
            if k.startswith('command_'):
                _help += '\n'
                cmd_doc = getattr(self, k).__doc__
                if cmd_doc:
                    _help += cmd_doc
        return _help

    def __call__(self, command_name, *args, **kwargs):
        if command_name is None:
            self.default(*args, **kwargs)
        elif command_name == 'help':
            sys.stdout.write(self.__doc__)
            for k in self.__dict__.keys():
                if k.startswith('command_'):
                    sys.stdout.write(k.__doc__)
        elif hasattr(self, 'command_'+command_name):
            getattr(self, 'command_'+command_name)(*args, **kwargs)
        else:
            if self.__class__.__doc__:
                sys.stdout.write(self.__class__.__doc__)
            raise CommandNotFound()


#--------- TESTS ------------
import unittest


class CommandDigestTest(unittest.TestCase):

    def test_manage(self):
        assrt = self.assertEquals
        class TestCommand(CommandDigest):
            def command_test(self, arg, kwarg=None, kwarg2=False):
                assrt(arg, 'arg1')
                assrt(kwarg, 'kwarg3')
                assrt(kwarg2, False)
            def default(self, arg, kwarg=None, kwarg2=False):
                assrt(arg, 'arg')
                assrt(kwarg, 'kwarg')
                assrt(kwarg2, True)
        test_cmd = TestCommand()
        argv = 'mage.py test arg --kwarg=kwarg --kwarg2'
        manage(dict(test=test_cmd), argv.split())
        argv = 'mage.py test:test arg1 --kwarg=kwarg3'
        manage(dict(test=test_cmd), argv.split())



if __name__ == '__main__':
    unittest.main()
