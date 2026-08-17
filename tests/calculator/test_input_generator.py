import inspect

from monty.json import MSONable

from matsimpy.calculator.input_generator import InputGenerator


def test_input_generator_is_native_msonable_base():
    assert issubclass(InputGenerator, MSONable)
    assert inspect.isabstract(InputGenerator)
