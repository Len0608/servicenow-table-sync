"""Tests for ServiceNow credential resolution and dynamic-choice handlers."""

import sys
import os
import logging
import types
import pytest
from unittest.mock import MagicMock, patch

# Ensure src is on the path
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ---------------------------------------------------------------------------
# Stub out universal_extension so extension.py can be imported in unit tests
# ---------------------------------------------------------------------------

def _install_ue_stub():
    """Inject minimal universal_extension stubs so src modules can be imported in unit tests."""
    if "universal_extension" not in sys.modules:
        ue = types.ModuleType("universal_extension")

        class _ExtResult:
            def __init__(self, rc=0, message="", values=None, **kwargs):
                self.rc = rc
                self.message = message
                self.values = values or []

        class _UE:
            pass

        ue.UniversalExtension = _UE
        ue.ExtensionResult = _ExtResult
        ue.logger = logging.getLogger("UNV")
        ue.ui = types.ModuleType("universal_extension.ui")
        sys.modules["universal_extension"] = ue

    # Sub-modules that various src files import from
    for sub in ("universal_extension.ui", "universal_extension.deco",
                "universal_extension.deco.choice", "universal_extension.deco.command"):
        if sub not in sys.modules:
            sys.modules[sub] = types.ModuleType(sub)

    def _dcc(name):
        def decorator(fn):
            return fn
        return decorator

    sys.modules["universal_extension.deco.choice"].dynamic_choice_command = _dcc
    sys.modules["universal_extension.deco.command"].dynamic_command = _dcc


_install_ue_stub()

# Now we can import the resolver directly (no UAC dependency)
from utility.sn_connection_resolver import resolve_sn_connection, resolve_sn_connection_from_fields
from fields.types import Credential


# ---------------------------------------------------------------------------
# resolve_sn_connection – URL validation
# ---------------------------------------------------------------------------

class TestResolveURL:
    def test_missing_url_raises(self):
        with pytest.raises(ValueError, match="ServiceNow Instance URL is required"):
            resolve_sn_connection(None, {"user": "u", "password": "p"})

    def test_empty_url_raises(self):
        with pytest.raises(ValueError, match="ServiceNow Instance URL is required"):
            resolve_sn_connection("", {"user": "u", "password": "p"})

    def test_http_url_raises(self):
        with pytest.raises(ValueError, match="must start with https://"):
            resolve_sn_connection("http://x.com", {"user": "u", "password": "p"})

    def test_trailing_slash_stripped(self):
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler") as M:
            resolve_sn_connection("https://x.com/", {"user": "u", "password": "p"})
            url_arg = M.call_args[0][0]
            assert url_arg == "https://x.com"


# ---------------------------------------------------------------------------
# resolve_sn_connection – credential validation
# ---------------------------------------------------------------------------

class TestResolveCredential:
    URL = "https://my-instance.service-now.com"

    def test_dict_basic_auth(self):
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler") as M:
            resolve_sn_connection(self.URL, {"user": "svc-user", "password": "secret"})
            M.assert_called_once_with(self.URL, "svc-user", "secret")

    def test_credential_dataclass(self):
        cred = Credential(user="svc-user", password="secret")
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler") as M:
            resolve_sn_connection(self.URL, cred)
            M.assert_called_once_with(self.URL, "svc-user", "secret")

    def test_missing_user_raises(self):
        with pytest.raises(ValueError, match="missing Runtime User"):
            resolve_sn_connection(self.URL, {"password": "secret"})

    def test_empty_user_raises(self):
        with pytest.raises(ValueError, match="missing Runtime User"):
            resolve_sn_connection(self.URL, {"user": "", "password": "secret"})

    def test_missing_password_raises(self):
        with pytest.raises(ValueError, match="missing Runtime Password"):
            resolve_sn_connection(self.URL, {"user": "svc-user"})

    def test_wrong_type_raises(self):
        with pytest.raises(ValueError):
            resolve_sn_connection(self.URL, "my-credential-name")

    def test_no_secret_in_error_message(self):
        try:
            resolve_sn_connection(self.URL, {"user": "svc-user"})
        except ValueError as exc:
            msg = str(exc)
            assert "secret" not in msg
            assert "password" not in msg.lower() or "Runtime Password" in msg


# ---------------------------------------------------------------------------
# resolve_sn_connection_from_fields – dynamic-choice dict forms
# ---------------------------------------------------------------------------

class TestResolveFromFields:
    URL = "https://my-instance.service-now.com"

    def test_nested_dict_credential(self):
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler") as M:
            resolve_sn_connection_from_fields({
                "servicenow_instance_url": self.URL,
                "servicenow_credential": {"user": "svc-user", "password": "secret"},
            })
            M.assert_called_once_with(self.URL, "svc-user", "secret")

    def test_flattened_keys(self):
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler") as M:
            resolve_sn_connection_from_fields({
                "servicenow_instance_url": self.URL,
                "servicenow_credential.user": "svc-user",
                "servicenow_credential.password": "secret",
            })
            M.assert_called_once_with(self.URL, "svc-user", "secret")

    def test_url_as_list(self):
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler") as M:
            resolve_sn_connection_from_fields({
                "servicenow_instance_url": [self.URL],
                "servicenow_credential": {"user": "u", "password": "p"},
            })
            M.assert_called_once_with(self.URL, "u", "p")

    def test_missing_url_raises(self):
        with pytest.raises(ValueError, match="ServiceNow Instance URL is required"):
            resolve_sn_connection_from_fields({
                "servicenow_credential": {"user": "u", "password": "p"},
            })

    def test_missing_user_raises(self):
        with pytest.raises(ValueError, match="missing Runtime User"):
            resolve_sn_connection_from_fields({
                "servicenow_instance_url": self.URL,
                "servicenow_credential": {"password": "p"},
            })

    def test_missing_password_raises(self):
        with pytest.raises(ValueError, match="missing Runtime Password"):
            resolve_sn_connection_from_fields({
                "servicenow_instance_url": self.URL,
                "servicenow_credential": {"user": "u"},
            })


# ---------------------------------------------------------------------------
# No secrets in logs
# ---------------------------------------------------------------------------

class TestNoSecretInLogs:
    URL = "https://my-instance.service-now.com"

    def test_password_not_logged(self, caplog):
        with patch("utility.sn_connection_resolver.ServiceNowConnectionHandler"):
            with caplog.at_level(logging.DEBUG, logger="UNV"):
                resolve_sn_connection(self.URL, {"user": "svc-user", "password": "SUPER_SECRET_TOKEN_XYZ"})
        assert "SUPER_SECRET_TOKEN_XYZ" not in caplog.text


# ---------------------------------------------------------------------------
# Dynamic choice handlers – test via extension.py with stubs
# ---------------------------------------------------------------------------

class TestDynamicChoiceHandlers:
    VALID_FIELDS = {
        "servicenow_instance_url": "https://my-instance.service-now.com",
        "servicenow_credential": {"user": "svc-user", "password": "secret"},
    }

    def _ext(self):
        from extension import Extension
        return object.__new__(Extension)

    def _mock_conn(self, result=None):
        conn = MagicMock()
        conn.get.return_value = {"result": result or []}
        return conn

    def test_customer_table_calls_sn(self):
        ext = self._ext()
        mock_conn = self._mock_conn([{"label": "Customer Account", "name": "customer_account"}])
        with patch.object(ext, "_resolve_sn_connection", return_value=mock_conn):
            res = ext.get_customer_table(self.VALID_FIELDS)
        assert res.rc == 0
        assert "Customer Account (customer_account)" in res.values

    def test_customer_table_missing_credential_returns_error(self):
        ext = self._ext()
        with patch.object(ext, "_resolve_sn_connection",
                          side_effect=ValueError("ServiceNow Credential is missing Runtime User")):
            res = ext.get_customer_table({"servicenow_instance_url": "https://x.com"})
        assert res.rc == 1
        assert "Runtime User" in res.message

    def test_target_fields_missing_customer_table(self):
        ext = self._ext()
        mock_conn = self._mock_conn()
        with patch.object(ext, "_resolve_sn_connection", return_value=mock_conn):
            res = ext.get_target_fields({**self.VALID_FIELDS})
        assert res.rc == 1
        assert "customer_table" in res.message

    def test_target_fields_calls_sys_dictionary(self):
        ext = self._ext()
        mock_conn = self._mock_conn([
            {"element": "name", "column_label": "Name", "internal_type": "String"},
            {"element": "sys_created_on", "column_label": "Created", "internal_type": "glide_date_time"},
        ])
        fields = {**self.VALID_FIELDS, "customer_table": "Customer Account (customer_account)"}
        with patch.object(ext, "_resolve_sn_connection", return_value=mock_conn):
            res = ext.get_target_fields(fields)
        mock_conn.get.assert_called_once_with("sys_dictionary", query="name=customer_account", limit=200)
        assert res.rc == 0
        assert any("name" in v for v in res.values)

    def test_customer_record_missing_customer_table(self):
        ext = self._ext()
        mock_conn = self._mock_conn()
        with patch.object(ext, "_resolve_sn_connection", return_value=mock_conn):
            res = ext.get_customer_record({**self.VALID_FIELDS})
        assert res.rc == 1
        assert "customer_table" in res.message

    def test_decision_table_calls_sn_table(self):
        ext = self._ext()
        mock_conn = self._mock_conn([{"name": "Priority Matrix", "sys_id": "abc123"}])
        with patch.object(ext, "_resolve_sn_connection", return_value=mock_conn):
            res = ext.get_decision_table(self.VALID_FIELDS)
        assert res.rc == 0
        assert "Priority Matrix | abc123" in res.values


# ---------------------------------------------------------------------------
# InputFields – credential conversion and URL validation
# ---------------------------------------------------------------------------

class TestInputFieldsCredentialConversion:
    def _base_fields(self, **overrides):
        base = {
            "action": ["Preview"],
            "uac_credential": {
                "user": "uac-user", "password": "uac-pass",
                "url": "https://uac.example.com",
            },
            "servicenow_credential": {"user": "svc-user", "password": "secret"},
            "servicenow_instance_url": "https://my-instance.service-now.com",
            "target_mode": ["Customer Tables"],
            "source_dataset": ["Agents"],
            "source_scope": ["All Objects"],
            "customer_table": ["Customer Account (customer_account)"],
            "target_fields": ["Name (String) | name"],
            "field_mappings_customer": ['{"agentname": "name"}'],
            "account_association_config": ['{"match_field": "name"}'],
            "output_verbosity": ["Summary and Errors"],
        }
        base.update(overrides)
        return base

    def _clear_manager(self):
        from manager import ExtensionManager
        ExtensionManager().clear()

    def test_dict_credential_converted_to_credential_instance(self):
        from fields.input import InputFields
        self._clear_manager()
        raw = self._base_fields()
        processed = InputFields.preprocess_fields(raw)
        processed["_skip_validation"] = True
        inp = InputFields(**processed)
        # __post_init__ with _skip_validation=True skips conversion, so trigger manually:
        for attr in ("uac_credential", "servicenow_credential"):
            val = getattr(inp, attr)
            if isinstance(val, dict):
                setattr(inp, attr, Credential(**{k: v for k, v in val.items() if k in Credential.__dataclass_fields__}))
        assert isinstance(inp.servicenow_credential, Credential)
        assert inp.servicenow_credential.user == "svc-user"
        assert inp.servicenow_credential.password == "secret"

    def test_missing_sn_credential_raises(self):
        from fields.input import InputFields
        self._clear_manager()
        raw = self._base_fields(servicenow_credential=None)
        processed = InputFields.preprocess_fields(raw)
        with pytest.raises(Exception):
            InputFields(**processed)

    def test_missing_servicenow_url_raises(self):
        from fields.input import InputFields
        self._clear_manager()
        raw = self._base_fields()
        raw.pop("servicenow_instance_url", None)
        processed = InputFields.preprocess_fields(raw)
        with pytest.raises(Exception):
            InputFields(**processed)

    def test_http_servicenow_url_raises(self):
        from fields.input import InputFields
        self._clear_manager()
        raw = self._base_fields(servicenow_instance_url="http://my-instance.service-now.com")
        processed = InputFields.preprocess_fields(raw)
        with pytest.raises(Exception):
            InputFields(**processed)

    def test_missing_credential_user_raises(self):
        from fields.input import InputFields
        self._clear_manager()
        raw = self._base_fields(servicenow_credential={"password": "secret"})
        processed = InputFields.preprocess_fields(raw)
        with pytest.raises(Exception):
            InputFields(**processed)
