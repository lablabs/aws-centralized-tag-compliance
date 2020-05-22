# aws-centralized-tag-compliance

[<img src="ll-logo.png">](https://lablabs.io/)

We help companies build, run, deploy and scale software and infrastructure by embracing the right technologies and principles. Check out our website at https://lablabs.io/

---

## Description

A simple python script which helps with enforcing centralized tag compliance.

As of now, these are the alternative ways to achieve the same goal using AWS managed services:

* AWS Config + ["required-tags" managed rule](https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html) - This setup might get quite expensive in case there are a lot of changes happening in the AWS Setup which is common in clusters which auto-scale. With AWS Config, you are charged based on the number of configuration items recorded. A configuration item is a record of the configuration state of a resource in your AWS account.
* AWS Organization [Tag policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html) - The problem with this solution is that resources that have never had tags don't show as noncompliant in reports. Although it's possible to force creation of tagged resources using SCP (Service Control Policies), we want to avoid a situation when we can't scale out or setup a service quickly because we need to tag it properly first. Usually it's preferred to just get a notification when there is a running resource without proper tags.
* [AWS Service Catalog + DynamoDB + Lambda + Cloudwatch events](https://aws.amazon.com/blogs/apn/enforce-centralized-tag-compliance-using-aws-service-catalog-amazon-dynamodb-aws-lambda-and-amazon-cloudwatch-events/) - This setup might be overkill and too complicated.

## Features

- Slack notifications about noncompliant resources.

## Prerequisites

- A compute platform where the python script can run - kubernetes, lambda, ecs, ...

## Contributing and reporting issues

Feel free to create an issue in this repository if you have questions, suggestions or feature requests.

## License

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

See [LICENSE](LICENSE) for full details.

    Licensed to the Apache Software Foundation (ASF) under one
    or more contributor license agreements.  See the NOTICE file
    distributed with this work for additional information
    regarding copyright ownership.  The ASF licenses this file
    to you under the Apache License, Version 2.0 (the
    "License"); you may not use this file except in compliance
    with the License.  You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing,
    software distributed under the License is distributed on an
    "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
    KIND, either express or implied.  See the License for the
    specific language governing permissions and limitations
    under the License.
