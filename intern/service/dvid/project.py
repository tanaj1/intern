# Copyright 2020 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from intern.service.dvid import DVIDService
from intern.service.dvid.metadata import MetadataService
from intern.resource.dvid.resource import *
import requests
import json
import ast


class ProjectService(DVIDService):
    """ProjectService for DVID service.
    """

    def __init__(self, base_url):
        """Constructor.

        Args:
            base_url (str): Base url to project service.

        """
        DVIDService.__init__(self)
        self.base_url = base_url
        self._metadata = MetadataService(base_url)

    def create(self, resource):
        """Creates a repository for the data to be placed in.

        Args:
            resource (intern.resource.dvid.DVIDResource): Data model object with attributes matching those of the resource.

        Returns:
            UUID (str): Randomly generated 32 character long UUID

        Raises:
            (HTTPError): On invalid request
        """

        if isinstance(resource, RepositoryResource):
            if resource.UUID:
                raise ValueError(
                    "resource UUID must be None during resource creation. It will be autogenerated."
                )
            r = requests.post(
                "{}/api/repos".format(self.base_url),
                data=json.dumps(
                    {"Alias": resource.alias, "Description": resource.description}
                ),
            )
            r = str(r.content)
            UUID = ast.literal_eval(r.split("'")[0])["root"]
            # We can set the resource UUID now.
            resource.UUID = UUID
            return UUID

        if isinstance(resource, DataInstanceResource):
            # If the UUID doesn't exist is None then we can create a new repo with this
            # instance in it.
            if not resource.UUID:
                exp_create_resp = requests.post(
                    "{}/api/repos".format(self.base_url),
                    data=json.dumps(
                        {"Alias": resource.alias, "Description": resource.description}
                    ),
                )
                exp_create_resp_cont = str(exp_create_resp.content)
                if exp_create_resp.status_code != 200:
                    raise requests.HTTPError(exp_create_resp.content)
                UUID = ast.literal_eval(exp_create_resp_cont.split("'")[1])["root"]
                # Define resource's UUID if it was created
                resource.UUID = UUID
            # Otherwise we use the given UUID.
            else:
                UUID = resource.UUID

            # Create the data instance
            data_instance_create_resp = requests.post(
                "{}/api/repo/{}/instance".format(self.base_url, UUID),
                data=json.dumps(
                    {
                        "typename": resource._type,
                        "dataname": resource.name,
                        "versioned": resource.version,
                        "sync": resource.sync,
                    }
                ),
            )

            # Imagetile type Data instances MUST have metadata otherwise create_cutouts will fail
            # This metadata can be overwritten by the user if desired.
            if resource._type == "imagetile":
                self._metadata.create_default_metadata(resource)

            if data_instance_create_resp.status_code != 200:
                raise requests.HTTPError(data_instance_create_resp.content)
            return UUID

    def get(self, resource):
        """Get attributes of the given resource.

        Args:
            resource (intern.resource.dvid.DVIDResource): Data model object with attributes matching those of the resource.

        Returns:
            (str): UUID corresponding to resource
            (str): Resource name

        Raises:
            (HTTPError): On invalid request
        """
        return resource.UUID, resource.name

    def delete(self, resource):
        """ Method to delete a project

        Args:
            resource (intern.resource.dvid.DVIDResource): Data model object with attributes matching those of the resource.

        Returns:
            (str) : HTTP Response

        Raises:
            (HTTPError): On invalid request
        """
        if isinstance(resource, RepositoryResource):
            del_resp = requests.delete(
                "{}/api/repo/{}?imsure=true".format(self.base_url, resource.UUID)
            )
            if del_resp.status_code != 200:
                raise requests.HTTPError(del_resp.content)
        elif isinstance(resource, DataInstanceResource):
            print(resource.UUID)
            del_resp = requests.delete(
                "{}/api/repo/{}/{}?imsure=true".format(
                    self.base_url, resource.UUID, resource.name
                )
            )
            if del_resp.status_code != 200:
                raise requests.HTTPError(del_resp.content)
        else:
            raise ValueError(
                "resource type must be RepositoryResource or DataInstanceResource, was {}".format(
                    resource
                )
            )
        return del_resp
