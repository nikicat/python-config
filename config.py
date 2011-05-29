'''
Created on Oct 26, 2010

@author: nbryskin
'''

import os
import os.path
import sys
import argparse
import logging
import logging.handlers

class config_parser(argparse.ArgumentParser):
    '''
    universal parser for config files, program options, kwargs options
    '''

    def __init__(self, name):
        argparse.ArgumentParser.__init__(self)
        self.options = argparse.Namespace()
        self.name = name

    def parse(self, **kwargs):
        # 1. set defaults
        self.add_argument('--config', default='/etc/{0}.conf'.format(self.name), help='config file path')
        self.add_argument('--log-file', default=None, help='log file path')
        self.add_argument('--log-level', default='INFO', help='log level; supported values: {0} or number'.format(', '.join(map(logging.getLevelName, range(0, 51, 10)))))
        self.add_argument('--log-format', default='%(module)s[%(process)d]: %(name)s: %(message)s', help='log format')
        self.add_argument('--syslog-facility', default=None, help='syslog facility')
        self.add_argument('--gen-config', type=int, default=0, help='generate config and exit')

        # 2. parse kwargs
        def parse_dict(d):
            for key, value in d:
                yield '--' + key.replace('_', '-')
                yield value
        self.parse_args(list(parse_dict(kwargs.items())), namespace=self.options)

        # 3. parse config file
        self.parse_known_args(namespace=self.options)
        if os.access(self.options.config, os.R_OK):
            COMMENT_CHAR = '#'
            OPTION_CHAR =  '='
            ALT_OPTION_CHAR =  ' '
            with open(self.options.config) as f:
                line_number = 0
                for line in f:
                    line_number += 1
                    # First, remove comments:
                    if COMMENT_CHAR in line:
                        # split on comment char, keep only the part before
                        line = line.split(COMMENT_CHAR, 1)[0]
                    line = line.strip()
                    # Second, find lines with an key=value:
                    if OPTION_CHAR in line:
                        key, value = line.split(OPTION_CHAR, 1)
                    elif ALT_OPTION_CHAR in line:
                        key, value = line.split(ALT_OPTION_CHAR, 1)
                    else:
                        continue
                    # strip spaces:
                    key = key.strip()
                    value = value.strip()
                    # store in dictionary:
                    actions = [action for action in self._actions if action.dest == key]
                    if len(actions) == 0:
                        self.error('unknown key in config file {0}:{1}: {2}'.format(self.options.config, line_number, key))
                    if actions[0].type is not None:
                        value = actions[0].type(value)
                    setattr(self.options, key, value)

        # 4. parse command line
        self.parse_args(namespace=self.options)

        if self.options.gen_config:
            self.genconfig()
            self.exit(message='config file generated at {0}\n'.format(self.options.config))

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)
        raise SystemExit(status)

    def genconfig(self):
        with open(self.options.config, 'a') as config_file:
            config_file.write('# {0} config file\n\n'.format(os.path.basename(sys.argv[0])))
            for key, value in sorted(self.options.__dict__.items(), key=lambda (k, v): k):
                if key in ['config', 'gen_config']:
                    continue
                help = [action.help for action in self._actions if action.dest == key][0]
                config_file.write('{0} = {1} # {2}\n'.format(key, value, help))

    def init_logging(self):
        handlers = []
        if self.options.syslog_facility is not None:
            handlers.append(logging.handlers.SysLogHandler('/dev/log', self.options.syslog_facility))
        if self.options.log_file is not None:
            handlers.append(logging.FileHandler(self.options.log_file))
        if self.options.log_file is None and self.options.syslog_facility is None:
            handlers.append(logging.StreamHandler())
        formatter = logging.Formatter(self.options.log_format)
        level = self.options.log_level.isdigit() and int(self.options.log_level) or logging.getLevelName(self.options.log_level)
        logging.root.setLevel(level)
        if logging.root.handlers:
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
        for handler in handlers:
            handler.setLevel(level)
            handler.setFormatter(formatter)
            logging.root.addHandler(handler)
