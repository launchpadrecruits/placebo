# Copyright (c) 2015 Mitch Garnaat
#
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

import boto3
import datetime
import placebo
import StringIO
import sys
import unittest


kp_result_one = {
    "KeyPairs": [
        {
            "KeyName": "foo",
            "KeyFingerprint": "ad:08:8a:b3:13:ea:6c:20:fa"
        }
    ]
}

kp_result_two = {
    "KeyPairs": [
        {
            "KeyName": "bar",
            "KeyFingerprint": ":27:21:b9:ce:b5:5a:a2:a3:bc"
        }
    ]
}

addresses_result_one = {
    "Addresses": [
        {
            "InstanceId": "",
            "PublicIp": "192.168.0.1",
            "Domain": "standard"
        }
    ]
}

date_sample = {
    "LoginProfile": {
        "UserName": "baz",
        "CreateDate": datetime.datetime(2015, 1, 4, 9, 1, 2, 0),
    }
}

date_json = """{
    "foo.get_foo": {
        "index": 0,
        "responses": [
            [
                200,
                {
                    "LoginProfile": {
                        "UserName": "baz",
                        "CreateDate": {
                            "hour": 9,
                            "__class__": "datetime",
                            "month": 1,
                            "second": 2,
                            "microsecond": 0,
                            "year": 2015,
                            "day": 4,
                            "minute": 1
                        }
                    }
                }
            ]
        ]
    }
}"""

class TestPlacebo(unittest.TestCase):

    def test_ec2(self):
        session = boto3.Session()
        placebo.attach(session)
        ec2_client = session.client('ec2')
        ec2_client.meta.placebo.add_response(
            'ec2', 'DescribeAddresses', addresses_result_one)
        ec2_client.meta.placebo.start()
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')

    def test_ec2_multiple_responses(self):
        session = boto3.Session()
        placebo.attach(session)
        ec2_client = session.client('ec2')
        ec2_client.meta.placebo.add_response(
            'ec2', 'DescribeKeyPairs', kp_result_one)
        ec2_client.meta.placebo.add_response(
            'ec2', 'DescribeKeyPairs', kp_result_two)
        ec2_client.meta.placebo.start()
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'foo')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'bar')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'bar')

    def test_multiple_clients(self):
        session = boto3.Session()
        placebo.attach(session)
        ec2_client = session.client('ec2')
        iam_client = session.client('iam')
        ec2_client.meta.placebo.add_response(
            'ec2', 'DescribeAddresses', addresses_result_one)
        ec2_client.meta.placebo.start()
        result = ec2_client.describe_addresses()
        self.assertEqual(iam_client.meta.placebo.mock_responses, {})

    def test_datetime_to_json(self):
        obj = placebo.Placebo(client='foo')
        obj.add_response('foo', 'get_foo', date_sample)
        tempfile = StringIO.StringIO()
        obj.save(tempfile)
        tempfile.seek(0)
        result = tempfile.read()
        self.assertEqual("".join(result.split()), "".join(date_json.split()))

    def test_datetime_from_json(self):
        obj = placebo.Placebo(client='foo')
        source = StringIO.StringIO()
        source.write(date_json)
        source.seek(0)
        obj.load(source)
        service_data = obj.mock_responses['foo.get_foo']
        response = service_data['responses'][0][1]
        self.assertEqual(response, date_sample)
