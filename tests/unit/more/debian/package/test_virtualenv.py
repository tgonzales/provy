from contextlib import contextmanager
import os
import sys
from unittest import TestCase

from mock import MagicMock, patch, call
from nose.tools import istest

from provy.more.debian import PipRole, VirtualenvRole


class VirtualenvRoleTest(TestCase):
    def setUp(self):
        self.role = VirtualenvRole(prov=None, context={'user': 'johndoe',})

    @istest
    def refers_to_specific_subdir_at_user_home(self):
        role = VirtualenvRole(prov=None, context={'user': 'johndoe',})

        self.assertEqual(role.base_directory, '/home/johndoe/.virtualenvs')

    @istest
    def refers_to_specific_subdir_at_root_home(self):
        role = VirtualenvRole(prov=None, context={'user': 'root',})

        self.assertEqual(role.base_directory, '/root/.virtualenvs')

    @istest
    def installs_virtualenv_harness_when_provisioned(self):
        mock_role = MagicMock(spec=PipRole)

        @contextmanager
        def fake_using(self, klass):
            yield mock_role

        with patch('provy.core.roles.Role.using', fake_using):
            self.role.provision()
            install_calls = mock_role.ensure_package_installed.mock_calls
            self.assertEqual(install_calls, [call('virtualenv'), call('virtualenvwrapper')])

    @istest
    def creates_a_virtual_environment(self):
        with patch('provy.core.roles.Role.execute') as execute:
            env_dir = self.role.create_env('foo_env')
            self.assertEqual(env_dir, '/home/johndoe/.virtualenvs/foo_env')
            execute.assert_called_with('virtualenv /home/johndoe/.virtualenvs/foo_env')

    @istest
    def wraps_the_env_usage_with_creation_activation_and_deactivation(self):
        execute = MagicMock()

        @contextmanager
        def prefix(command):
            execute('called before prefix')
            execute('prefix: "%s"' % command)
            yield
            execute('called after prefix')

        with patch('provy.core.roles.Role.execute', execute), patch('fabric.api.prefix', prefix):
            venv = VirtualenvRole(prov=None, context={'user': 'johndoe',})

            with venv('fancylib'):
                execute('some command')
                execute('some command 2')

            expected_executes = [
                call('virtualenv %s/fancylib' % venv.base_directory),
                call('called before prefix'),
                call('prefix: "source %s/fancylib/bin/activate"' % venv.base_directory),
                call('some command'),
                call('some command 2'),
                call('called after prefix'),
            ]
            execute.assert_has_calls(expected_executes)