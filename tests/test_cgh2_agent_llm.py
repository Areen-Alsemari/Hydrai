from hydrai_twin.cgh2_agent.llm import check_numbers, numbers_in


def test_arabic_digits_and_decimals():
    assert numbers_in("المعدل ١٫٥ كغ/ساعة") == [1.5]


def test_checker_accepts_copied_numbers_and_rejects_invented_ones():
    out = [{"estimate": {"leak_rate": {"value": 1.57, "lo": 0.97, "hi": 2.17}}, "text_en": "about 1.7 kg released so far"}]
    assert check_numbers("The leak is 1.57 kg/h (0.97-2.17) and about 1.7 kg is out.", out)[0]
    ok, bad = check_numbers("The leak is 3.2 kg/h.", out)
    assert not ok and bad == [3.2]
    assert check_numbers("Roughly 1.6 kg/h", out)[0]                     # rounding for readability is fine
    ok, bad = check_numbers("Roughly 1.8 kg/h", out)                      # anything else is an invented number
    assert not ok and bad == [1.8]


def test_fallback_without_model():
    from hydrai_twin.cgh2_agent import llm
    class S:  # minimal stand-in: no client -> template text, no tool calls
        class ctx:
            @staticmethod
            def monitor(_):
                return {}
    r = llm.answer("how big is the leak?", S, 0, client=None, fallback_text="template text")
    assert r["answer"] == "template text" and r["tool_calls"] == 0


def test_leak_forecast_is_finite_when_the_inventory_estimate_is_not_positive():
    import math

    from hydrai_twin.cgh2_agent.tools.t10_forecast_consequence import leak_forecast
    for i0 in (-5.0, 0.0, 150.0):
        assert all(v is None or math.isfinite(v) for v in leak_forecast(80.0, i0, 100.0).values())
