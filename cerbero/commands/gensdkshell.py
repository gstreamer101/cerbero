# cerbero - a multi-platform build system for Open Source software
# Copyright (C) 2012 Andoni Morales Alastruey <ylatuya@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os

from cerbero.commands import Command, register_command
from cerbero.errors import FatalError
from cerbero.utils import _, N_, ArgparseArgument, shell


SCRIPT_TPL = """\
#!/bin/bash

%s

%s
"""


class GenSdkShell(Command):
    doc = N_('Create a script with the shell environment for the SDK')
    name = 'gensdkshell'

    DEFAULT_CMD = '$SHELL "$@"'

    def __init__(self):
        Command.__init__(
            self,
            [
                ArgparseArgument('name', nargs=1, default='sdk-shell', help=_('name of the scrips')),
                ArgparseArgument('-o', '--output-dir', default='.', help=_('output directory')),
                ArgparseArgument('-p', '--prefix', help=_('prefix of the SDK')),
                ArgparseArgument('--cmd', default=self.DEFAULT_CMD, help=_('command to run in the script')),
            ],
        )

    def run(self, config, args):
        name = args.name[0]
        prefix = args.prefix and args.prefix or config.prefix
        py_prefixes = config.py_prefixes
        output_dir = args.output_dir
        cmd = args.cmd
        self.runargs(config, name, output_dir, prefix, config.libdir, py_prefixes, cmd)

    def _putvar(self, var, value, append_separator=':'):
        if var in self._env:
            if append_separator is not None:
                self._env[var] = self._env[var] + append_separator + value
        else:
            self._env[var] = value

    def runargs(
        self,
        config,
        name,
        output_dir,
        prefix,
        libdir,
        py_prefixes,
        cmd=None,
        env=None,
        prefix_env_name='GSTREAMER_ROOT',
        root_from_name=False,
    ):
        if cmd is None:
            cmd = self.DEFAULT_CMD
        if env is None:
            env = {}
        else:
            env = env.copy()
        self._env = env
        prefix_env = '${%s}' % prefix_env_name
        libdir = libdir.replace(prefix, prefix_env)
        if isinstance(py_prefixes, str):
            python_path = os.path.join(prefix_env, py_prefixes)
        elif isinstance(py_prefixes, list):
            python_path = os.pathsep.join([os.path.join(prefix_env, x) for x in py_prefixes])
        else:
            python_path = ''
        self._putvar('PATH', '%s/bin${PATH:+:$PATH}' % prefix_env)
        self._putvar('LD_LIBRARY_PATH', '%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}' % libdir)
        self._putvar(
            'PKG_CONFIG_PATH',
            '%s/pkgconfig:%s/share/pkgconfig' '${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}' % (libdir, prefix_env),
        )
        self._putvar('XDG_DATA_DIRS', '%s/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}' % prefix_env)
        self._putvar('XDG_CONFIG_DIRS', '%s/etc/xdg${XDG_CONFIG_DIRS:+:$XDG_CONFIG_DIRS}' % prefix_env)
        self._putvar('GST_REGISTRY_1_0', '${HOME}/.cache/gstreamer-1.0/gstreamer-cerbero-registry', None)
        self._putvar('GST_PLUGIN_SCANNER_1_0', '%s/libexec/gstreamer-1.0/gst-plugin-scanner' % prefix_env)
        self._putvar('GST_PLUGIN_PATH_1_0', '%s/gstreamer-1.0' % libdir)
        self._putvar('GST_PLUGIN_SYSTEM_PATH_1_0', '%s/gstreamer-1.0' % libdir)
        self._putvar('PYTHONPATH', '%s${PYTHONPATH:+:$PYTHONPATH}' % python_path)
        self._putvar('CFLAGS', '-I%s/include ${CFLAGS}' % prefix_env, ' ')
        self._putvar('CXXFLAGS', '-I%s/include ${CXXFLAGS}' % prefix_env, ' ')
        self._putvar('CPPFLAGS', '-I%s/include ${CPPFLAGS}' % prefix_env, ' ')
        self._putvar('LDFLAGS', '-L%s ${LDFLAGS}' % libdir, ' ')
        self._putvar('GIO_EXTRA_MODULES', '%s/gio/modules' % libdir)
        self._putvar('GI_TYPELIB_PATH', '%s/girepository-1.0' % libdir)

        envstr = ''
        if root_from_name:
            envstr += 'scriptdir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-${(%):-%x}}" )" &> /dev/null && pwd)\n'
            envstr += 'export ' + prefix_env_name + '="${scriptdir%"/' + os.path.dirname(name) + '"}"\n'
            envstr += 'unset scriptdir\n'
        else:
            envstr += 'export %s="%s"\n' % (prefix_env_name, prefix)
        for e, v in env.items():
            envstr += 'export %s="%s"\n' % (e, v)
        try:
            filepath = os.path.join(output_dir, name)

            if not os.path.exists(os.path.dirname(filepath)):
                os.mkdir(os.path.dirname(filepath))

            with open(filepath, 'w+') as f:
                f.write(SCRIPT_TPL % (envstr, cmd))
            shell.new_call(['chmod', '+x', filepath])
        except IOError as ex:
            raise FatalError(_('Error creating script: %s' % ex))


register_command(GenSdkShell)
