# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the account functions."""
import json
import logging
import os
import uuid
from typing import Any
from unittest import skipIf

from qiskit_ibm_provider.accounts import (
    AccountManager,
    Account,
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAccountError,
)
from qiskit_ibm_provider.accounts.account import IBM_QUANTUM_API_URL
from qiskit_ibm_provider.proxies import ProxyConfiguration
from .mock.fake_provider import FakeProvider
from ..account import (
    temporary_account_config_file,
    custom_envs,
    no_envs,
)
from ..ibm_test_case import IBMTestCase

_DEFAULT_ACCOUNT_NAME_LEGACY = "default-legacy"

_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM = "default-ibm-quantum"

_TEST_IBM_QUANTUM_ACCOUNT = Account(
    channel="ibm_quantum",
    token="token-x",
    url="https://auth.quantum-computing.ibm.com/api",
    instance="ibm-q/open/main",
)

_TEST_LEGACY_ACCOUNT = {
    "auth": "legacy",
    "token": "token-x",
    "url": "https://auth.quantum-computing.ibm.com/api",
    "instance": "ibm-q/open/main",
}


class TestAccount(IBMTestCase):
    """Tests for Account class."""

    dummy_token = "123"
    dummy_ibm_quantum_url = "https://auth.quantum-computing.ibm.com/api"

    def test_invalid_channel(self):
        """Test invalid values for channel parameter."""

        with self.assertRaises(InvalidAccountError) as err:
            invalid_channel: Any = "phantom"
            Account(
                channel=invalid_channel,
                token=self.dummy_token,
                url=self.dummy_ibm_quantum_url,
            ).validate()
        self.assertIn("Invalid `channel` value.", str(err.exception))

    def test_invalid_token(self):
        """Test invalid values for token parameter."""

        invalid_tokens = [1, None, ""]
        for token in invalid_tokens:
            with self.subTest(token=token):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(
                        channel="ibm_quantum",
                        token=token,
                        url=self.dummy_ibm_quantum_url,
                    ).validate()
                self.assertIn("Invalid `token` value.", str(err.exception))

    def test_invalid_url(self):
        """Test invalid values for url parameter."""

        subtests = [
            {"channel": "ibm_quantum", "url": 123},
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(**params, token=self.dummy_token).validate()
                self.assertIn("Invalid `url` value.", str(err.exception))

    def test_invalid_instance(self):
        """Test invalid values for instance parameter."""

        subtests = [
            {"channel": "ibm_quantum", "instance": ""},
            {"channel": "ibm_quantum", "instance": "no-hgp-format"},
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(
                        **params, token=self.dummy_token, url=self.dummy_ibm_quantum_url
                    ).validate()
                self.assertIn("Invalid `instance` value.", str(err.exception))

    def test_invalid_proxy_config(self):
        """Test invalid values for proxy configuration."""

        subtests = [
            {
                "proxies": ProxyConfiguration(**{"username_ntlm": "user-only"}),
            },
            {
                "proxies": ProxyConfiguration(**{"password_ntlm": "password-only"}),
            },
            {
                "proxies": ProxyConfiguration(**{"urls": ""}),
            },
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(ValueError) as err:
                    Account(
                        **params,
                        channel="ibm_quantum",
                        token=self.dummy_token,
                        url=self.dummy_ibm_quantum_url,
                    ).validate()
                self.assertIn("Invalid proxy configuration", str(err.exception))


# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestAccountManager(IBMTestCase):
    """Tests for AccountManager class."""

    @temporary_account_config_file(
        contents={"conflict": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format()}
    )
    def test_save_without_override(self):
        """Test to override an existing account without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                name="conflict",
                token=_TEST_IBM_QUANTUM_ACCOUNT.token,
                url=_TEST_IBM_QUANTUM_ACCOUNT.url,
                instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
                channel="ibm_quantum",
                overwrite=False,
            )
        # TODO remove test when removing auth parameter

    @temporary_account_config_file(
        contents={_DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT}
    )
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_channel_ibm_quantum_over_auth_legacy_without_overwrite(self):
        """Test to overwrite an existing auth "legacy" account with channel "ibm_quantum"
        and without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                token=_TEST_IBM_QUANTUM_ACCOUNT.token,
                url=_TEST_IBM_QUANTUM_ACCOUNT.url,
                instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
                channel="ibm_quantum",
                name=None,
                overwrite=False,
            )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(
        contents={_DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT}
    )
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_channel_ibm_quantum_over_auth_legacy_with_overwrite(self):
        """Test to overwrite an existing auth "elegacy" account with channel "ibm_quantum"
        and with setting overwrite=True."""
        AccountManager.save(
            token=_TEST_IBM_QUANTUM_ACCOUNT.token,
            url=_TEST_IBM_QUANTUM_ACCOUNT.url,
            instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
            channel="ibm_quantum",
            name=None,
            overwrite=True,
        )
        self.assertEqual(
            _TEST_IBM_QUANTUM_ACCOUNT, AccountManager.get(channel="ibm_quantum")
        )

    @temporary_account_config_file(
        contents={"conflict": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format()}
    )
    def test_get_none(self):
        """Test to get an account with an invalid name."""
        with self.assertRaises(AccountNotFoundError):
            AccountManager.get(name="bla")

    @temporary_account_config_file(contents={})
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_get(self):
        """Test save and get."""

        # Each tuple contains the
        # - account to save
        # - the name passed to AccountManager.save
        # - the name passed to AccountManager.get
        sub_tests = [
            (_TEST_IBM_QUANTUM_ACCOUNT, "acct-1", "acct-1"),
            # verify default account name handling for ibm_quantum accounts
            (
                _TEST_IBM_QUANTUM_ACCOUNT,
                None,
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
            ),
            # verify account override
            (_TEST_IBM_QUANTUM_ACCOUNT, "acct", "acct"),
        ]
        for account, name_save, name_get in sub_tests:
            with self.subTest(
                f"for account type '{account.channel}' "
                f"using `save(name={name_save})` and `get(name={name_get})`"
            ):
                AccountManager.save(
                    token=account.token,
                    url=account.url,
                    instance=account.instance,
                    channel=account.channel,
                    proxies=account.proxies,
                    verify=account.verify,
                    name=name_save,
                    overwrite=True,
                )
                self.assertEqual(account, AccountManager.get(name=name_get))

    @temporary_account_config_file(
        contents=json.dumps(
            {
                "ibm_quantum": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
            }
        )
    )
    def test_list(self):
        """Test list."""

        with temporary_account_config_file(
            contents={
                "key2": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
            }
        ), self.subTest("non-empty list of accounts"):
            accounts = AccountManager.list()

            self.assertEqual(len(accounts), 1)
            self.assertTrue(accounts["key2"], _TEST_IBM_QUANTUM_ACCOUNT)

        with temporary_account_config_file(contents={}), self.subTest(
            "empty list of accounts"
        ):
            self.assertEqual(len(AccountManager.list()), 0)

        with temporary_account_config_file(
            contents={
                "key2": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM: Account(
                    "ibm_quantum", "token-ibm-quantum"
                ).to_saved_format(),
            }
        ), self.subTest("filtered list of accounts"):

            accounts = list(AccountManager.list(channel="ibm_quantum").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(accounts, ["key2", _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM])

    @temporary_account_config_file(
        contents={
            "key1": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
            _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM: _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
        }
    )
    def test_delete(self):
        """Test delete."""

        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default ibm_quantum account"):
            self.assertTrue(AccountManager.delete())

        self.assertTrue(len(AccountManager.list()) == 0)

    @temporary_account_config_file(
        contents={
            "key1": _TEST_LEGACY_ACCOUNT,
            _DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT,
        }
    )
    def test_delete_auth(self):
        """Test delete accounts already saved using auth."""

        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default auth='legacy' account using channel"):
            self.assertTrue(AccountManager.delete())

        self.assertTrue(len(AccountManager.list()) == 0)


MOCK_PROXY_CONFIG_DICT = {
    "urls": {"https": "127.0.0.1", "username_ntlm": "", "password_ntlm": ""}
}

# TODO: update and reenable test cases to work with qiskit-ibm-provider
# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestEnableAccount(IBMTestCase):
    """Tests for IBMRuntimeService enable account."""

    def test_enable_account_by_name(self):
        """Test initializing account by name."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            service = FakeProvider(name=name)

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)

    def test_enable_account_by_token_url(self):
        """Test initializing account by token or url."""
        token = uuid.uuid4().hex
        subtests = [
            {"token": token},
            {"token": token, "url": "some_url"},
        ]
        for param in subtests:
            with self.subTest(param=param):
                service = FakeProvider(**param)
                self.assertTrue(service._account)
                if "token" in param:
                    self.assertEqual(service._account.token, param["token"])
                if "url" in param:
                    self.assertEqual(service._account.url, param["url"])

    def test_enable_account_by_name_and_other(self):
        """Test initializing account by name and other."""
        subtests = [
            {"token": "some_token"},
            {"url": "some_url"},
            {"token": "some_token", "url": "some_url"},
        ]

        name = "foo"
        token = uuid.uuid4().hex
        for param in subtests:
            with self.subTest(param=param), temporary_account_config_file(
                name=name, token=token
            ):
                with self.assertLogs("qiskit_ibm_provider", logging.WARNING) as logged:
                    service = FakeProvider(name=name, **param)

                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                self.assertIn("are ignored", logged.output[0])

    def test_enable_account_by_token_url_2(self):
        """Test initializing ibm quantum account by  token, url."""

        token = uuid.uuid4().hex
        with temporary_account_config_file(token=token), no_envs(["QISKIT_IBM_TOKEN"]):
            with self.assertLogs("qiskit_ibm_provider", logging.WARNING) as logged:
                service = FakeProvider(url="some_url")

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        expected = IBM_QUANTUM_API_URL
        self.assertEqual(service._account.url, expected)
        self.assertIn("url", logged.output[0])

    def test_enable_account_by_only_channel(self):
        """Test initializing account with single saved account."""
        token = uuid.uuid4().hex
        with temporary_account_config_file(token=token), no_envs(["QISKIT_IBM_TOKEN"]):
            service = FakeProvider()
        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        expected = IBM_QUANTUM_API_URL
        self.assertEqual(service._account.url, expected)
        self.assertEqual(service._account.channel, "ibm_quantum")

    def test_enable_account_by_env_auth(self):
        """Test initializing account by environment variable and auth."""

        token = uuid.uuid4().hex
        url = uuid.uuid4().hex
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": "h/g/p",
        }
        with custom_envs(envs):
            service = FakeProvider()

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        self.assertEqual(service._account.url, url)
        self.assertEqual(service._account.channel, "ibm_quantum")

    def test_enable_account_bad_name(self):
        """Test initializing account by bad name."""
        name = "phantom"
        with temporary_account_config_file() as _, self.assertRaises(
            AccountNotFoundError
        ) as err:
            _ = FakeProvider(name=name)
        self.assertIn(name, str(err.exception))

    def test_enable_account_by_name_pref(self):
        """Test initializing account by name and preferences."""
        name = "foo"
        subtests = [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": "h/g/p"},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": "h/g/p"},
        ]
        for extra in subtests:
            with self.subTest(extra=extra):
                with temporary_account_config_file(name=name, verify=True, proxies={}):
                    service = FakeProvider(name=name, **extra)
                self.assertTrue(service._account)
                self._verify_prefs(extra, service._account)

    def test_enable_account_by_env_pref(self):
        """Test initializing account by environment variable and preferences."""
        subtests = [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": "h/g/p"},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": "h/g/p"},
        ]
        for extra in subtests:
            with self.subTest(extra=extra):
                token = uuid.uuid4().hex
                url = uuid.uuid4().hex
                envs = {
                    "QISKIT_IBM_TOKEN": token,
                    "QISKIT_IBM_URL": url,
                    "QISKIT_IBM_INSTANCE": "h/g/p",
                }
                with custom_envs(envs):
                    service = FakeProvider(**extra)
                self.assertTrue(service._account)
                self._verify_prefs(extra, service._account)

    def test_enable_account_by_name_input_instance(self):
        """Test initializing account by name and input instance."""
        name = "foo"
        instance = "h1/g1/p1"
        with temporary_account_config_file(name=name, instance="h/g/p"):
            service = FakeProvider(name=name, instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def test_enable_account_by_env_input_instance(self):
        """Test initializing account by env and input instance."""
        instance = "h1/g1/p1"
        envs = {
            "QISKIT_IBM_TOKEN": "some_token",
            "QISKIT_IBM_URL": "some_url",
            "QISKIT_IBM_INSTANCE": "h/g/p",
        }
        with custom_envs(envs):
            service = FakeProvider(instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def _verify_prefs(self, prefs, account):
        if "proxies" in prefs:
            self.assertEqual(account.proxies, ProxyConfiguration(**prefs["proxies"]))
        if "verify" in prefs:
            self.assertEqual(account.verify, prefs["verify"])
        if "instance" in prefs:
            self.assertEqual(account.instance, prefs["instance"])
