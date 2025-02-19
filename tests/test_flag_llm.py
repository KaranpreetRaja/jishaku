import os
import inspect
import pytest
from unittest.mock import patch
from jishaku.flags import Flag, FlagMeta

class TestFlag:
    @pytest.fixture
    def sample_flag(self):
        return Flag("TEST_FLAG", bool, default=False)

    def test_resolve_raw_no_env_no_override(self, sample_flag):
        assert sample_flag.resolve_raw(None) is False

    def test_resolve_raw_with_override(self, sample_flag):
        sample_flag.override = True
        assert sample_flag.resolve_raw(None) is True

    def test_resolve_raw_from_env(self, sample_flag):
        with patch.dict(os.environ, {"JISHAKU_TEST_FLAG": "true"}):
            assert sample_flag.resolve_raw(None) is True

    def test_resolve_raw_from_env_disabled(self, sample_flag):
        with patch.dict(os.environ, {"JISHAKU_TEST_FLAG": "false"}):
            assert sample_flag.resolve_raw(None) is False

    def test_resolve_with_handler(self):
        handler = lambda x: not x
        flag = Flag("TEST_FLAG", bool, default=False, handler=handler)
        assert flag.resolve(None) is True

    def test_resolve_raw_non_bool_type(self):
        flag = Flag("INT_FLAG", int, default=0)
        with patch.dict(os.environ, {"JISHAKU_INT_FLAG": "123"}):
            assert flag.resolve_raw(None) == 123

    def test_resolve_raw_bool_invalid_value(self):
        flag = Flag("BOOL_FLAG", bool, default=False)
        with patch.dict(os.environ, {"JISHAKU_BOOL_FLAG": "invalid"}):
            result = flag.resolve_raw(None)
            assert result is False

    def test_resolve_raw_callable_default(self):
        class CallableDefault:
            def __call__(self, flags):
                return "called"
        
        callable_default = CallableDefault()
        flag = Flag("CALLABLE_FLAG", str, default=callable_default)
        result = flag.resolve_raw(None)
        assert result == callable_default


class TestFlagMeta:
    def test_metaclass_flag_creation(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = False

        assert isinstance(TestFlags.flag_map["TEST_FLAG"], Flag)
        assert TestFlags.TEST_FLAG is False

    def test_metaclass_override(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = False

        TestFlags.TEST_FLAG = True
        assert TestFlags.TEST_FLAG is True

    def test_metaclass_override_wrong_type(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = False

        with pytest.raises(ValueError):
            TestFlags.TEST_FLAG = "not a bool"

    def test_metaclass_with_handler(self):
        def handler(value):
            return not value

        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = (False, handler)

        assert isinstance(TestFlags.flag_map["TEST_FLAG"], Flag)
        assert TestFlags.flag_map["TEST_FLAG"].handler == handler
        assert TestFlags.TEST_FLAG is True  # False inverted by handler

    def test_metaclass_attribute_error(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = False

        with pytest.raises(AttributeError):
            _ = TestFlags.NONEXISTENT_FLAG

    def test_metaclass_set_non_flag_attribute(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = False

        TestFlags.NEW_ATTRIBUTE = "value"
        assert TestFlags.NEW_ATTRIBUTE == "value"

    def test_metaclass_with_empty_default(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool
            
        assert isinstance(TestFlags.flag_map["TEST_FLAG"], Flag)
        assert TestFlags.TEST_FLAG is False

    def test_metaclass_with_tuple_default_no_handler(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = (True, None)

        assert isinstance(TestFlags.flag_map["TEST_FLAG"], Flag)
        assert TestFlags.TEST_FLAG is True

    def test_metaclass_non_flag_getattr(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG: bool = False
            normal_attr = "value"

        assert TestFlags.normal_attr == "value"

    def test_metaclass_flag_map_initialization(self):
        class TestFlags(metaclass=FlagMeta):
            TEST_FLAG_1: bool = True
            TEST_FLAG_2: str = "test"
            TEST_FLAG_3: int = 42

        assert len(TestFlags.flag_map) == 3
        assert all(isinstance(flag, Flag) for flag in TestFlags.flag_map.values())
        assert TestFlags.TEST_FLAG_1 is True
        assert TestFlags.TEST_FLAG_2 == "test"
        assert TestFlags.TEST_FLAG_3 == 42