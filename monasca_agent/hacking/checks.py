# Copyright 2017 FUJITSU LIMITED
#
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
import re

assert_no_xrange_re = re.compile(r"\s*xrange\s*\(")
assert_True = re.compile(r".*assertEqual\(True, .*\)")
assert_None = re.compile(r".*assertEqual\(None, .*\)")
assert_Not_Equal = re.compile(r".*assertNotEqual\(None, .*\)")
assert_Is_Not = re.compile(r".*assertIsNot\(None, .*\)")
assert_raises_regexp = re.compile(r"assertRaisesRegexp\(")
no_log_warn = re.compile(r".*LOG.warn\(.*\)")
mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")


def no_mutable_default_args(logical_line):
    msg = "M001: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


def no_xrange(logical_line):
    if assert_no_xrange_re.match(logical_line):
        yield (0, "M002: Do not use xrange().")


def validate_assertTrue(logical_line):
    if re.match(assert_True, logical_line):
        msg = ("M003: Unit tests should use assertTrue(value) instead"
               " of using assertEqual(True, value).")
        yield (0, msg)


def validate_assertIsNone(logical_line):
    if re.match(assert_None, logical_line):
        msg = ("M004: Unit tests should use assertIsNone(value) instead"
               " of using assertEqual(None, value).")
        yield (0, msg)


def no_log_warn_check(logical_line):
    if re.match(no_log_warn, logical_line):
        msg = ("M005: LOG.warn is deprecated, please use LOG.warning!")
        yield (0, msg)


def validate_assertIsNotNone(logical_line):
    if re.match(assert_Not_Equal, logical_line) or \
            re.match(assert_Is_Not, logical_line):
        msg = ("M006: Unit tests should use assertIsNotNone(value) instead"
               " of using assertNotEqual(None, value) or"
               " assertIsNot(None, value).")
        yield (0, msg)


def assert_raisesRegexp(logical_line):
    res = assert_raises_regexp.search(logical_line)
    if res:
        yield (0, "M007: assertRaisesRegex must be used instead "
                  "of assertRaisesRegexp")


def factory(register):
    register(no_mutable_default_args)
    register(no_xrange)
    register(validate_assertTrue)
    register(validate_assertIsNone)
    register(no_log_warn_check)
    register(validate_assertIsNotNone)
    register(assert_raisesRegexp)
