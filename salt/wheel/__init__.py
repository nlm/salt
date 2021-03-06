# -*- coding: utf-8 -*-
'''
Modules used to control the master itself
'''
from __future__ import absolute_import
#import python libs
import collections
import os
import time

# Import salt libs
from salt import syspaths
import salt.config
import salt.loader
import salt.payload
import salt.utils
from salt.client import mixins
from salt.utils.error import raise_error
from salt.utils.event import tagify


class WheelClient(mixins.SyncClientMixin, mixins.AsyncClientMixin, object):
    '''
    An interface to Salt's wheel modules

    :ref:`Wheel modules <all-salt.wheel>` interact with various parts of the
    Salt Master.

    Importing and using ``WheelClient`` must be done on the same machine as the
    Salt Master and it must be done using the same user that the Salt Master is
    running as. Unless :conf_master:`external_auth` is configured and the user
    is authorized to execute wheel functions: (``@wheel``).
    '''
    client = 'wheel'
    tag_prefix = 'wheel'

    def __init__(self, opts=None):
        if not opts:
            opts = salt.config.client_config(
                    os.environ.get(
                        'SALT_MASTER_CONFIG',
                        os.path.join(syspaths.CONFIG_DIR, 'master')
                        )
                    )

        self.opts = opts
        self.functions = salt.loader.wheels(opts)

    def cmd(self, fun, **kwargs):
        '''
        Execute a wheel function

        .. code-block:: python

            >>> opts = salt.config.master_config('/etc/salt/master')
            >>> wheel = salt.wheel.Wheel(opts)
            >>> wheel.call_func('key.list_all')
            {'local': ['master.pem', 'master.pub'],
            'minions': ['jerry'],
            'minions_pre': [],
            'minions_rejected': []}
        '''
        return self.low(fun, kwargs)

    call_func = cmd  # alias for backward-compat

    def master_call(self, **kwargs):
        '''
        Execute a wheel function through the master network interface (eauth).
        '''
        load = kwargs
        load['cmd'] = 'wheel'
        master_uri = 'tcp://' + salt.utils.ip_bracket(self.opts['interface']) + \
                     ':' + str(self.opts['ret_port'])
        channel = salt.transport.Channel.factory(self.opts,
                                                 crypt='clear',
                                                 master_uri=master_uri)
        ret = channel.send(load)
        if isinstance(ret, collections.Mapping):
            if 'error' in ret:
                raise_error(**ret['error'])
        return ret

    def cmd_sync(self, low, timeout=None):
        '''
        Execute a wheel function synchronously; eauth is respected

        This function requires that :conf_master:`external_auth` is configured
        and the user is authorized to execute runner functions: (``@wheel``).

        .. code-block:: python

            >>> wheel.cmd_sync({
                'fun': 'key.finger',
                'match': 'jerry',
                'eauth': 'auto',
                'username': 'saltdev',
                'password': 'saltdev',
            })
            {'minions': {'jerry': '5d:f6:79:43:5e:d4:42:3f:57:b8:45:a8:7e:a4:6e:ca'}}
        '''
        return self.master_call(**low)

    def cmd_async(self, low):
        '''
        Execute a wheel function asynchronously; eauth is respected

        This function requires that :conf_master:`external_auth` is configured
        and the user is authorized to execute runner functions: (``@wheel``).

        .. code-block:: python

            >>> wheel.cmd_async({
                'fun': 'key.finger',
                'match': 'jerry',
                'eauth': 'auto',
                'username': 'saltdev',
                'password': 'saltdev',
            })
            {'jid': '20131219224744416681', 'tag': 'salt/wheel/20131219224744416681'}
        '''
        fun = low.pop('fun')
        return self.async(fun, low)

Wheel = WheelClient  # for backward-compat
