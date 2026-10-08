import pytest

from ml.headline_metrics import WEEK_S, alarm_events, score_episode, summarize, summarize_by_fault

T = [i * 60.0 for i in range(0, 60 * 24 * 7)]          # one week at 60 s


def _flags(*spans):
    f = [False] * len(T)
    for a, b in spans:
        for i, t in enumerate(T):
            if a <= t <= b:
                f[i] = True
    return f


def _meta(fid, onset, obs=None, **kw):
    return {"episode_id": f"E{fid}-{onset}", "fault_id": fid, "onset_s": onset, "first_observable_s": obs,
            "duration_s": T[-1], "healthy_exposure_s": onset if onset is not None else T[-1], "scenario_class": "standard", **kw}


def test_alarm_events_merge_within_gap():
    t = [0, 60, 120, 5000, 5060, 20000]
    f = [True, True, False, True, True, True]
    assert alarm_events(t, f, merge_gap_s=3600) == [0.0, 5000.0, 20000.0]
    assert alarm_events(t, f, merge_gap_s=100) == [0.0, 5000.0, 20000.0]
    assert alarm_events(t, f, merge_gap_s=10000) == [0.0, 20000.0]
    assert alarm_events(t, [False] * 6) == []


def test_agent_first_lead_time_and_delays():
    m = _meta(4, onset=86400.0, obs=90000.0)
    s = score_episode(m, T, _flags((95000, 96000)), _flags((200000, 201000)))
    assert s.outcome == "agent_first"
    assert s.first_alarm_s == 95040.0 and s.static_first_alarm_s == 200040.0       # first 60 s sample inside each span
    assert s.lead_vs_static_s == 105000.0
    assert s.delay_vs_onset_s == pytest.approx(95040 - 86400) and s.delay_vs_observable_s == pytest.approx(5040)
    assert s.n_false_alarms == 0


def test_outcomes_static_first_agent_only_static_only_both_missed():
    m = _meta(2, onset=86400.0)
    assert score_episode(m, T, _flags((200000, 201000)), _flags((100000, 101000))).outcome == "static_first"
    assert score_episode(m, T, _flags((200000, 201000)), _flags()).outcome == "agent_only"
    assert score_episode(m, T, _flags(), _flags((100000, 101000))).outcome == "static_only"
    assert score_episode(m, T, _flags(), _flags()).outcome == "both_missed"


def test_alarm_before_onset_is_a_false_alarm_not_a_detection():
    m = _meta(5, onset=200000.0)
    s = score_episode(m, T, _flags((1000, 2000)), _flags())
    assert s.n_false_alarms == 1 and s.first_alarm_s is None and s.outcome == "both_missed"


def test_false_alarms_per_week_over_healthy_exposure():
    normal = score_episode(_meta(0, None), T, _flags((1000, 1500), (300000, 300500)), _flags())     # 2 events over ~1 week
    fault = score_episode(_meta(2, onset=T[-1] / 2), T, _flags(), _flags())                         # half a week healthy, 0 events
    d = summarize([normal, fault])
    fa = d["false_alarms"]
    assert fa["events"] == 2
    assert fa["healthy_exposure_weeks"] == pytest.approx((T[-1] + T[-1] / 2) / WEEK_S)
    assert fa["per_week"] == pytest.approx(2 / fa["healthy_exposure_weeks"])
    assert fa["per_week_ci95"][0] < fa["per_week"] < fa["per_week_ci95"][1]


def test_summary_counts_failures_and_per_fault_breakdown():
    ep = [score_episode(_meta(4, 86400.0), T, _flags((90000, 91000)), _flags((200000, 201000))),
          score_episode(_meta(4, 86400.0), T, _flags(), _flags()),
          score_episode(_meta(2, 86400.0), T, _flags((90000, 91000)), _flags())]
    d = summarize(ep)
    assert d["lead_vs_static"]["outcomes"] == {"agent_first": 1, "both_missed": 1, "agent_only": 1}
    assert d["detection"]["fraction"] == pytest.approx(2 / 3)
    assert d["lead_vs_static"]["n_both_fired"] == 1
    by = summarize_by_fault(ep)
    assert by[4]["n"] == 2 and by[2]["n"] == 1


def test_alarms_inside_injected_data_faults_are_counted_separately_not_as_false_alarms_or_detections():
    from ml.headline_metrics import score_episode as se
    df = [1000 <= t <= 3000 for t in T]
    normal = se(_meta(0, None), T, _flags((1500, 1600), (300000, 300500)), _flags(), data_fault_flags=df)
    assert normal.n_false_alarms == 1 and normal.n_data_fault_alarms == 1          # the first alarm started inside a data fault
    d = summarize([normal])
    assert d["false_alarms"]["events"] == 1 and d["false_alarms"]["data_fault_alarm_events"] == 1
    # in a fault episode: an alarm that starts inside a data fault is not credited as the detection (conservative); a later one is
    inside = se(_meta(2, onset=86400.0), T, _flags((86500, 90000)), _flags(), data_fault_flags=[86400 <= t <= 87000 for t in T])
    assert inside.first_alarm_s is None and inside.outcome == "both_missed"
    later = se(_meta(2, onset=86400.0), T, _flags((86500, 90000), (200000, 201000)), _flags(), data_fault_flags=[86400 <= t <= 87000 for t in T])
    assert later.first_alarm_s == 200040.0


def test_alarm_load_constants_and_verdicts():
    from ml.headline_metrics import (AGENT_TARGET_PER_H, EEMUA_BUSY_CEILING_PER_H, EEMUA_MANAGEABLE_PER_H, alarm_load_verdict, alerts_per_hour)
    assert (EEMUA_MANAGEABLE_PER_H, EEMUA_BUSY_CEILING_PER_H, AGENT_TARGET_PER_H) == (6.0, 12.0, 1.0)
    assert alerts_per_hour(12, 4 * 3600.0) == 3.0 and alerts_per_hour(1, 0.0) is None
    assert alarm_load_verdict(5.0, "operator") == "manageable" and "busy" in alarm_load_verdict(9.0, "operator")
    assert "ABOVE" in alarm_load_verdict(13.0, "operator")
    assert alarm_load_verdict(0.8, "agent") == "within target" and "ABOVE" in alarm_load_verdict(2.0, "agent")
    normal = score_episode(_meta(0, None), T, _flags((1000, 1500), (100000, 100500), (200000, 200500)), _flags())
    d = summarize([normal])
    assert d["alerts_per_hour_healthy"] == pytest.approx(3 / (T[-1] / 3600.0))
