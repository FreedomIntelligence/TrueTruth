import pytest
from hypertensiondb.schema.pico import EffectSize, Pico


@pytest.mark.unit
def test_effect_size_requires_numeric_value():
    with pytest.raises(Exception):
        EffectSize(metric="MD", value="not-a-number", ci_low=-10.0, ci_high=-6.0)


@pytest.mark.unit
def test_valid_effect_size():
    es = EffectSize(metric="MD", value=-8.4, ci_low=-10.1, ci_high=-6.7, p=0.001)
    assert es.value == -8.4


@pytest.mark.unit
def test_ci_low_must_be_less_than_ci_high():
    with pytest.raises(Exception):
        EffectSize(metric="RR", value=1.2, ci_low=2.0, ci_high=1.0)


@pytest.mark.unit
def test_valid_pico_minimal():
    pico = Pico(
        population={"condition": "原发性高血压", "sample_size": 612},
        intervention={"name": "缬沙坦 80mg + 氨氯地平 5mg", "drug_class": ["ARB", "CCB"]},
        comparison={"name": "缬沙坦单药"},
        outcomes={"primary": [], "secondary": []},
    )
    assert pico.population.condition == "原发性高血压"
