# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Scaleway Driver
"""

import copy
try:
    import simplejson as json
except:
    import json

from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.compute.base import NodeDriver, NodeImage, Node, NodeSize, NodeLocation
from libcloud.compute.base import StorageVolume, VolumeSnapshot
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState, VolumeSnapshotState
from libcloud.utils.iso8601 import parse_date
from libcloud.utils.py3 import httplib

__all__ = [
    'ScalewayResponse',
    'ScalewayConnection',
    'ScalewayNodeDriver'
]

SCALEWAY_API_HOST = 'api.scaleway.com'

# The API doesn't currently expose all of the required values for libcloud,
# so we simply list what's available right now, along with all of the various
# attributes that are needed by libcloud.
SCALEWAY_INSTANCE_TYPES = [
    {
        'id': 'ARM64-2GB',
        'name': 'ARM64-2GB',
        'ram': 2048,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.006,
        'extra': {
            'cores': 4,
            'monthly': 2.99,
            'range': 'Starter',
            'arch': 'arm',
        },
    },
    {
        'id': 'ARM64-4GB',
        'name': 'ARM64-4GB',
        'ram': 4096,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.012,
        'extra': {
            'cores': 6,
            'monthly': 5.99,
            'range': 'Starter',
            'arch': 'arm',
        },
    },
    {
        'id': 'ARM64-8GB',
        'name': 'ARM64-8GB',
        'ram': 8192,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.024,
        'extra': {
            'cores': 8,
            'monthly': 11.99,
            'range': 'Starter',
            'arch': 'arm',
        },
    },
    {
        'id': 'VC1S',
        'name': 'VC1S',
        'ram': 2048,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.006,
        'extra': {
            'cores': 2,
            'monthly': 2.99,
            'range': 'Starter',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'VC1M',
        'name': 'VC1M',
        'ram': 4096,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.012,
        'extra': {
            'cores': 4,
            'monthly': 5.99,
            'range': 'Starter',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'VC1L',
        'name': 'VC1L',
        'ram': 8192,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.02,
        'extra': {
            'cores': 6,
            'monthly': 9.99,
            'range': 'Starter',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'C1',
        'name': 'C1',
        'ram': 2048,
        'disk': 50,
        'bandwidth': 200,
        'price': 0.006,
        'extra': {
            'cores': 4,
            'monthly': 2.99,
            'range': 'Baremetal',
            'arch': 'arm',
        },
    },
    {
        'id': 'C2S',
        'name': 'C2S',
        'ram': 8192,
        'disk': 50,
        'bandwidth': 300,
        'price': 0.024,
        'extra': {
            'cores': 4,
            'monthly': 11.99,
            'range': 'Baremetal',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'C2M',
        'name': 'C2M',
        'ram': 16384,
        'disk': 50,
        'bandwidth': 500,
        'price': 0.036,
        'extra': {
            'cores': 8,
            'monthly': 17.99,
            'range': 'Baremetal',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'C2L',
        'name': 'C2L',
        'ram': 32768,
        'disk': 50,
        'bandwidth': 800,
        'price': 0.048,
        'extra': {
            'cores': 8,
            'monthly': 23.99,
            'range': 'Baremetal',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'ARM64-16GB',
        'name': 'ARM64-16GB',
        'ram': 16384,
        'disk': 50,
        'bandwidth': 500,
        'price': 0.07,
        'extra': {
            'cores': 16,
            'monthly': 34.99,
            'range': 'Intensive',
            'arch': 'arm',
        },
    },
    {
        'id': 'ARM64-32GB',
        'name': 'ARM64-32GB',
        'ram': 32768,
        'disk': 50,
        'bandwidth': 500,
        'price': 0.14,
        'extra': {
            'cores': 32,
            'monthly': 69.99,
            'range': 'Intensive',
            'arch': 'arm',
        },
    },
    {
        'id': 'ARM64-64GB',
        'name': 'ARM64-64GB',
        'ram': 65536,
        'disk': 50,
        'bandwidth': 1000,
        'price': 0.28,
        'extra': {
            'cores': 48,
            'monthly': 139.99,
            'range': 'Intensive',
            'arch': 'arm',
        },
    },
    {
        'id': 'ARM64-128GB',
        'name': 'ARM64-128GB',
        'ram': 131072,
        'disk': 50,
        'bandwidth': 1000,
        'price': 0.56,
        'extra': {
            'cores': 64,
            'monthly': 279.99,
            'range': 'Intensive',
            'arch': 'arm',
        },
    },
    {
        'id': 'X64-15GB',
        'name': 'X64-15GB',
        'ram': 15360,
        'disk': 50,
        'bandwidth': 250,
        'price': 0.05,
        'extra': {
            'cores': 6,
            'monthly': 24.99,
            'range': 'Intensive',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'X64-30GB',
        'name': 'X64-30GB',
        'ram': 30720,
        'disk': 50,
        'bandwidth': 500,
        'price': 0.1,
        'extra': {
            'cores': 8,
            'monthly': 49.99,
            'range': 'Intensive',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'X64-60GB',
        'name': 'X64-60GB',
        'ram': 61440,
        'disk': 50,
        'bandwidth': 1000,
        'price': 0.18,
        'extra': {
            'cores': 10,
            'monthly': 89.99,
            'range': 'Intensive',
            'arch': 'x86_64',
        },
    },
    {
        'id': 'X64-120GB',
        'name': 'X64-120GB',
        'ram': 122880,
        'disk': 50,
        'bandwidth': 1000,
        'price': 0.36,
        'extra': {
            'cores': 12,
            'monthly': 179.99,
            'range': 'Intensive',
            'arch': 'x86_64',
        },
    },
]

# The API also doesn't give location info, so we provide it ourselves, instead.
SCALEWAY_LOCATION_DATA = [
    {'id': 'par1', 'name': 'Paris 1', 'country': 'FR'},
    {'id': 'ams1', 'name': 'Amsterdam 1', 'country': 'NL'},
]

class ScalewayResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED,
                            httplib.CREATED, httplib.NO_CONTENT]

    def parse_error(self):
        return super(ScalewayResponse, self).parse_error()['message']

    def success(self):
        return self.status in self.valid_response_codes


class ScalewayConnection(ConnectionUserAndKey):
    """
    Connection class for the Scaleway driver.
    """

    host = SCALEWAY_API_HOST
    allow_insecure = False
    responseCls = ScalewayResponse

    def request(self, action, params=None, data=None, headers=None,
                method='GET', raw=False, stream=False, region=None):
        if region:
            old_host = self.host
            self.host = 'cp-%s.scaleway.com' % (region.id if isinstance(region,
                                                NodeLocation) else region)
            if not self.host == old_host:
                self.connect()

        return super(ScalewayConnection, self).request(action, params, data,
                                                       headers, method, raw,
                                                       stream)

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request
        """
        headers['X-Auth-Token'] = self.key
        headers['Content-Type'] = 'application/json'
        return headers


def _kb_to_mb(size):
    return int(size / 1000 / 1000 / 1000)


def _mb_to_kb(size):
    return int(size * 1000 * 1000 * 1000)


class ScalewayNodeDriver(NodeDriver):
    """
    Scaleway NodeDriver
    """

    type = Provider.SCALEWAY
    connectionCls = ScalewayConnection
    name = 'Scaleway'
    website = 'https://www.scaleway.com/'

    SNAPSHOT_STATE_MAP = {  # TODO map all states
        'snapshotting': VolumeSnapshotState.CREATING
    }

    def list_locations(self):
        return [NodeLocation(driver=self, **copy.deepcopy(location))
                for location in SCALEWAY_LOCATION_DATA]

    def list_sizes(self):
        return [NodeSize(driver=self, **copy.deepcopy(size))
                for size in SCALEWAY_INSTANCE_TYPES]

    def list_images(self, region=None):
        response = self.connection.request('/images', region=region)
        images = response.object['images']
        return [self._to_image(image) for image in images]

    def create_image(self, node, name, description=None, region=None):
        data = {
            'organization': self.key,
            'name': name,
            'arch': node.extra['arch'],
            'root_volume': node.extra['volumes']['0']['id']  # TODO check this
        }
        response = self.connection.request('/images', data=json.dumps(data),
                                           region=region,
                                           method='POST')
        image = response.object['image']
        return self._to_image(image)

    def delete_image(self, node_image, region=None):
        return self.connection.request('/images/%s' % node_image.id,
                                       region=region,
                                       method='DELETE').success()

    def get_image(self, image_id, region=None):
        response = self.connection.request('/images/%s' % image_id,
                                           region=region)
        image = response.object['image']
        return self._to_image(image)

    def _to_image(self, image):
        return NodeImage(id=image['id'],
                         name=image['name'],
                         driver=self,
                         extra={
                            'arch': image['arch'],
                            'creation_date': parse_date(image['creation_date']),
                            'modification_date': parse_date(image['modification_date']),
                            'organization': image['organization'],
                         })

    def list_nodes(self, region=None):
        response = self.connection.request('/servers', region=region)
        servers = response.object['servers']
        return [self._to_node(server) for server in servers]

    def _to_node(self, server):
        public_ip = server['public_ip']
        private_ip = server['private_ip']
        location = server['location'] or {}
        return Node(id=server['id'],
                    name=server['name'],
                    state=NodeState.fromstring(server['state']),
                    public_ips=[public_ip['address']] if public_ip else [],
                    private_ips=[private_ip] if private_ip else [],
                    driver=self,
                    extra={'volumes': server['volumes'],
                           'tags': server['tags'],
                           'arch': server['arch'],
                           'organization': server['organization'],
                           'region': location.get('zone_id', 'par1')},
                    created_at=parse_date(server['creation_date']))

    def create_node(self, name, size, image, ex_volumes=None, ex_tags=None,
                    region=None):
        data = {
            'name': name,
            'organization': self.key,
            'image': image.id,
            'volumes': ex_volumes or {},
            'commercial_type': size.id,
            'tags': ex_tags or []
        }

        response = self.connection.request('/servers', data=json.dumps(data),
                                           region=region,
                                           method='POST')
        server = response.object['server']
        node = self._to_node(server)
        node.extra['region'] = (region.id if isinstance(region, NodeLocation)
                                else region) or 'par1'

        # Scaleway doesn't start servers by default, let's do it
        self._action(node.id, 'poweron')

        return node

    def _action(self, server_id, action, region=None):
        return self.connection.request('/servers/%s/action' % server_id,
                                       region=region,
                                       data=json.dumps({'action': action}),
                                       method='POST').success()

    def reboot_node(self, node):
        return self._action(node.id, 'reboot')

    def destroy_node(self, node):
        return self._action(node.id, 'terminate')

    def list_volumes(self, region=None):
        response = self.connection.request('/volumes', region=region)
        volumes = response.object['volumes']
        return [self._to_volume(volume) for volume in volumes]

    def _to_volume(self, volume):
        return StorageVolume(id=volume['id'],
                             name=volume['name'],
                             size=_kb_to_mb(volume['size']),
                             driver=self,
                             extra={
                                'organization': volume['organization'],
                                'volume_type': volume['volume_type'],
                                'creation_date': parse_date(volume['creation_date']),
                                'modification_date': parse_date(volume['modification_date']),
                             })

    def list_volume_snapshots(self, volume, region=None):
        response = self.connection.request('/snapshots', region=region)
        snapshots = filter(lambda s: s['base_volume']['id'] == volume.id,
                           response.object['snapshots'])
        return [self._to_snapshot(snapshot) for snapshot in snapshots]

    def _to_snapshot(self, snapshot):
        state = self.SNAPSHOT_STATE_MAP.get(snapshot['state'],
                                            VolumeSnapshotState.UNKNOWN)
        return VolumeSnapshot(id=snapshot['id'],
                              driver=self,
                              size=_kb_to_mb(snapshot['size']),
                              created=parse_date(snapshot['creation_date']),
                              state=state,
                              extra={
                                'organization': snapshot['organization'],
                                'volume_type': snapshot['volume_type'],
                              })

    def create_volume(self, size, name, region=None):
        data = {
            'name': name,
            'organization': self.key,
            'volume_type': 'l_ssd',
            'size': _mb_to_kb(size)
        }
        response = self.connection.request('/volumes',
                                           region=region,
                                           data=json.dumps(data),
                                           method='POST')
        volume = response.object['volume']
        return self._to_volume(volume)

    def create_volume_snapshot(self, volume, name, region=None):
        data = {
            'name': name,
            'organization': self.key,
            'volume_id': volume.id
        }
        response = self.connection.request('/snapshots',
                                           region=region,
                                           data=json.dumps(data),
                                           method='POST')
        snapshot = response.object['snapshot']
        return self._to_snapshot(snapshot)

    def destroy_volume(self, volume, region=None):
        return self.connection.request('/volumes/%s' % volume.id,
                                       region=region,
                                       method='DELETE').success()

    def destroy_volume_snapshot(self, snapshot, region=None):
        return self.connection.request('/snapshots/%s' % snapshot.id,
                                       region=region,
                                       method='DELETE').success()
