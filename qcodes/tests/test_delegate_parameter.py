"""
Test suite for DelegateParameter
"""
import pytest

from qcodes.instrument.parameter import (
    Parameter, DelegateParameter, ParamRawDataType)


@pytest.fixture()
def numeric_val():
    yield 1


@pytest.fixture()
def simple_param(numeric_val):
    yield Parameter('testparam', set_cmd=None, get_cmd=None,
                    scale = 2, offset = 17,
                    label='Test Parameter', unit='V',
                    initial_value=numeric_val)


@pytest.fixture(params=[True, False])
def make_observable_parameter(request):
    def make_parameter(
            *args,
            base_type: type = Parameter,
            override_getset: bool = True,
            **kwargs):
        class ObservableParam(base_type):
            def __init__(
                    self, *args,
                    **kwargs
            ):
                self.instr_val = None
                super().__init__(*args, **kwargs)

            def set_raw(self, value: ParamRawDataType) -> None:
                self.instr_val = value

            def get_raw(self) -> ParamRawDataType:
                return self.instr_val

            def get_instr_val(self):
                return self.instr_val

        if request.param:
            if override_getset == False:
                pytest.skip()
            param = ObservableParam(*args, **kwargs)
        else:
            val = None
            def set_cmd(value):
                nonlocal val
                val = value

            def get_cmd():
                nonlocal val
                return val

            param = base_type(*args, **kwargs, set_cmd=set_cmd, get_cmd=get_cmd)
            param.get_instr_val = get_cmd
        return param
    yield make_parameter


def test_observable_parameter(make_observable_parameter, numeric_val):
    p = make_observable_parameter('testparam')
    p(numeric_val)
    assert p.get_instr_val() == numeric_val

def test_observable_parameter_initial_value(make_observable_parameter, numeric_val):
    t = make_observable_parameter(
        'observable_parameter', initial_value = numeric_val)
    assert t.get_instr_val() == numeric_val

def test_same_value(simple_param):
    d = DelegateParameter('test_delegate_parameter', simple_param)
    assert d() == simple_param()

def test_same_lable_and_unit_on_init(simple_param):
    """
    Test that the lable and unit get used from source parameter if not
    specified otherwise.
    """
    d = DelegateParameter('test_delegate_parameter', simple_param)
    assert d.label == simple_param.label
    assert d.unit == simple_param.unit


def test_overwritten_label_on_init(simple_param):
    d = DelegateParameter('test_delegate_parameter', simple_param, unit='Ohm')
    assert d.label == simple_param.label
    assert not d.unit == simple_param.unit
    assert d.unit == 'Ohm'


def test_get_set_raises(simple_param):
    """
    Test that providing a get/set_cmd kwarg raises an error.
    """
    p = Parameter('testparam', set_cmd=None, get_cmd=None)
    for kwargs in ({'set_cmd': None}, {'get_cmd': None}):
        with pytest.raises(KeyError) as e:
            DelegateParameter('test_delegate_parameter', simple_param, **kwargs)
        assert str(e.value).startswith('\'It is not allowed to set')


def test_scaling(simple_param, numeric_val):
    scale = 5
    offset = 3
    d = DelegateParameter(
        'test_delegate_parameter', simple_param, offset=offset, scale=scale)

    simple_param(numeric_val)
    assert d() == (numeric_val - offset) / scale

    d(numeric_val)
    assert simple_param() == numeric_val * scale + offset


def test_scaling_delegate_initial_value(simple_param, numeric_val):
    scale = 5
    offset = 3
    DelegateParameter(
        'test_delegate_parameter', simple_param, offset=offset, scale=scale,
        initial_value=numeric_val)

    assert simple_param() == numeric_val * scale + offset


def test_scaling_initial_value(simple_param, numeric_val):
    scale = 5
    offset = 3
    d = DelegateParameter(
        'test_delegate_parameter', simple_param, offset=offset, scale=scale)
    assert d() == (simple_param() - offset) / scale


def test_snapshot():
    p = Parameter('testparam', set_cmd=None, get_cmd=None,
                  offset=1, scale=2, initial_value=1)
    d = DelegateParameter('test_delegate_parameter', p, offset=3, scale=5,
                          initial_value=2)

    snapshot = d.snapshot()
    source_snapshot = snapshot.pop('source_parameter')
    assert source_snapshot == p.snapshot()
    assert snapshot['value'] == 2
    assert source_snapshot['value'] == 13


def test_set_source_cache_changes_delegate_cache(simple_param):
    """ Setting the cached value of the source parameter changes the
    delegate parameter cache accordingly.

    """
    offset = 4
    scale = 5
    d = DelegateParameter('d', simple_param, offset=offset, scale=scale)
    new_source_value = 3
    simple_param.cache.set(new_source_value)

    assert d.cache.get() == (new_source_value - offset) / scale


def test_set_source_cache_changes_delegate_get(simple_param):
    """ When the delegate parameter's ``get`` is called, the new
    value of the source propagates.

    """
    offset = 4
    scale = 5
    d = DelegateParameter('d', simple_param, offset=offset, scale=scale)
    new_source_value = 3

    simple_param.cache.set(new_source_value)

    assert d.get() == (new_source_value - offset) / scale


def test_set_delegate_cache_changes_source_cache(simple_param):
    offset = 4
    scale = 5
    d = DelegateParameter('d', simple_param, offset=offset, scale=scale)

    new_delegate_value = 2
    d.cache.set(new_delegate_value)

    assert simple_param.cache.get() == (new_delegate_value * 5 + 4)

def test_instrument_val_invariant_under_delegate_cache_set(make_observable_parameter, numeric_val):
    """ Setting the cached value of the source parameter changes the
    delegate parameter. But it has no impact on the instrument value.

    """
    initial_value = numeric_val
    t = make_observable_parameter(
        'observable_parameter', initial_value = initial_value)
    new_source_value = 3
    t.cache.set(new_source_value)
    assert t.get_instr_val() == initial_value

def test_delegate_cache_pristine_if_not_set():
    p = Parameter('test')
    d = DelegateParameter('delegate', p)
    assert d.cache.get(get_if_invalid=False) == None


def test_delegate_get_updates_cache(make_observable_parameter, numeric_val):
    initial_value = numeric_val
    t = make_observable_parameter(
        'observable_parameter', initial_value=initial_value)
    d = DelegateParameter('delegate', t)

    assert d() == initial_value
    assert d.cache.get() == initial_value
    assert t.get_instr_val() == initial_value



class RawValueTests():
    """The :attr:`raw_value` will be deprecated soon, so tests should not use
     it.

     """

    def test_raw_value_scaling(self, make_observable_parameter):
        p = Parameter('testparam', offset=1, set_cmd=None, get_cmd=None, scale=2)
        d = DelegateParameter('test_delegate_parameter', p, offset=3, scale=5)

        val = 1
        p(val)
        assert d() == (val - 3) / 5

        d(val)
        assert d.raw_value == val * 5 + 3
        assert d.raw_value == p()
