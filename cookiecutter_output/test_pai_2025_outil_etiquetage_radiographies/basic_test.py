import numpy as np

from pai_2025_outil_etiquetage_radiographies.my_module import typed_function


def test_typed_function():
    assert not typed_function(np.zeros(10), "")
