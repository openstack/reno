# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from reno import formatter
from reno import loader


def report_cmd(args, conf):
    "Generates a release notes report"
    encoding = conf.options['encoding']

    with loader.Loader(conf) as ldr:
        if args.version:
            versions = args.version
        else:
            versions = ldr.versions
        text = formatter.format_report(
            ldr,
            conf,
            versions,
            title=args.title,
            show_source=args.show_source,
            branch=args.branch,
        )

    if args.output:
        with open(args.output, 'w', encoding=encoding) as f:
            f.write(text)
    else:
        print(text)
    return
