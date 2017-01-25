#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64

from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes
from charmhelpers.core import hookenv


class RabbitMQRequires(RelationBase):
    scope = scopes.GLOBAL

    # These remote data fields will be automatically mapped to accessors
    # with a basic documentation string provided.
    auto_accessors = ['password', 'private-address', 'ssl_port',
                      'ssl_ca', 'ha_queues', 'ha-vip-only', 'clustered', 'vip']

    def vhost(self):
        return self.get_local('vhost')

    def username(self):
        return self.get_local('username')

    @hook('{requires:rabbitmq}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.connected')

    def update_state(self):
        if self.base_data_complete():
            self.set_state('{relation_name}.available')
            if self.ssl_data_complete():
                self.set_state('{relation_name}.available.ssl')
            else:
                self.remove_state('{relation_name}.available.ssl')
        else:
            self.remove_state('{relation_name}.available')
            self.remove_state('{relation_name}.available.ssl')
        if not self.rabbitmq_hosts():
            self.remove_state('{relation_name}.connected')

    @hook('{requires:rabbitmq}-relation-changed')
    def changed(self):
        self.update_state()

    @hook('{requires:rabbitmq}-relation-{broken,departed}')
    def departed(self):
        self.update_state()

    def base_data_complete(self):
        """
        Get the connection string, if available, or None.
        """
        data = {
            'hostname': self.private_address(),
            'vhost': self.vhost(),
            'username': self.username(),
            'password': self.password(),
        }
        if all(data.values()):
            return True
        return False

    def ssl_data_complete(self):
        """
        Get the connection string, if available, or None.
        """
        data = {
            'ssl_port': self.ssl_port(),
            'ssl_ca': self.ssl_ca(),
        }
        if all(data.values()):
            return True
        return False

    def request_access(self, username, vhost, hostname=None):
        """
        Request access to vhost for the supplied username.
        """
        if not hostname:
            try:
                hostname = hookenv.network_get_primary_address(
                    self.conversation().relation_name
                )
            except NotImplementedError:
                hostname = hookenv.unit_private_ip()

        relation_info = {
            'username': username,
            'vhost': vhost,
            'private-address': hostname,
        }
        self.set_local(**relation_info)
        self.set_remote(**relation_info)

    def configure(self, username, vhost):
        """
        DEPRECATED: use request_access instead
        Request access to vhost for the supplied username.
        """
        self.request_access(username, vhost)

    def get_remote_all(self, key, default=None):
        """Return a list of all values presented by remote units for key"""
        values = []
        for conversation in self.conversations():
            for relation_id in conversation.relation_ids:
                for unit in hookenv.related_units(relation_id):
                    value = hookenv.relation_get(key,
                                                 unit,
                                                 relation_id) or default
                    if value:
                        values.append(value)
        return list(set(values))

    def rabbitmq_hosts(self):
        return self.get_remote_all('private-address')

    def get_ssl_cert(self):
        """Return decoded CA cert from rabbit or None if no CA present"""
        if self.ssl_ca():
            return base64.b64decode(self.ssl_ca()).decode('utf-8')
        return None
