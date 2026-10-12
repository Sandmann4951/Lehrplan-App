"""F05 / A05: Kalenderregeln."""
from datetime import date

from app.services.calendar import Closure, SchoolCalendar, merge_intervals, week_start

MON_FRI = [0, 1, 2, 3, 4]


def test_week_start_is_monday():
    assert week_start(date(2026, 9, 16)) == date(2026, 9, 14)
    assert week_start(date(2026, 9, 14)) == date(2026, 9, 14)
    assert week_start(date(2026, 9, 20)) == date(2026, 9, 14)  # Sonntag gehört zur Woche ab Montag


def test_a05_school_year_starting_wednesday():
    # Schuljahr beginnt Mittwoch, 16.09.2026; Woche 21.–25.09. sind Ferien.
    cal = SchoolCalendar(
        date(2026, 9, 16),
        date(2027, 7, 30),
        MON_FRI,
        [Closure(date(2026, 9, 21), date(2026, 9, 25), "Testferien")],
    )
    first = cal.week_info(date(2026, 9, 16))
    assert first.teaching_week == 1
    assert first.shortened is True
    assert first.active_days == 3
    assert first.capacity(5) == 3  # 5 × 3 / 5

    holiday = cal.week_info(date(2026, 9, 22))
    assert holiday.teaching_week is None
    assert holiday.fully_free is True

    second = cal.week_info(date(2026, 9, 28))
    assert second.teaching_week == 2
    assert second.shortened is False


def test_a05_year_change_iso_week():
    cal = SchoolCalendar(date(2026, 9, 14), date(2027, 7, 30), MON_FRI)
    # 2026 hat 53 ISO-Wochen; 28.12.2026 ist KW 53, 04.01.2027 ist KW 1/2027
    w = cal.week_info(date(2026, 12, 30))
    assert (w.iso_year, w.iso_week) == (2026, 53)
    w2 = cal.week_info(date(2027, 1, 4))
    assert (w2.iso_year, w2.iso_week) == (2027, 1)
    assert w2.teaching_week == w.teaching_week + 1


def test_week_spanning_year_end_iso_belongs_to_monday():
    cal = SchoolCalendar(date(2027, 9, 14), date(2028, 7, 28), MON_FRI)
    # Montag 27.12.2027 bis Sonntag 02.01.2028 → ISO 2027-W52
    w = cal.week_info(date(2028, 1, 1))
    assert w.week_start == date(2027, 12, 27)
    assert (w.iso_year, w.iso_week) == (2027, 52)


def test_outside_school_year_has_no_number():
    cal = SchoolCalendar(date(2026, 9, 15), date(2027, 7, 30), MON_FRI)
    w = cal.week_info(date(2026, 8, 3))
    assert w.in_school_year is False
    assert w.teaching_week is None
    w = cal.week_info(date(2027, 8, 9))
    assert w.teaching_week is None


def test_boundaries_inclusive_and_overlaps_merged():
    closures = [
        Closure(date(2026, 10, 5), date(2026, 10, 7)),
        Closure(date(2026, 10, 7), date(2026, 10, 9)),  # überlappend
    ]
    cal = SchoolCalendar(date(2026, 9, 14), date(2027, 7, 30), MON_FRI, closures)
    assert not cal.is_teaching_day(date(2026, 10, 5))
    assert not cal.is_teaching_day(date(2026, 10, 9))
    assert cal.is_teaching_day(date(2026, 10, 12))
    assert cal.week_info(date(2026, 10, 5)).fully_free
    assert merge_intervals([(date(2026, 1, 5), date(2026, 1, 7)), (date(2026, 1, 6), date(2026, 1, 10))]) == [(date(2026, 1, 5), date(2026, 1, 10))]


def test_partial_week_capacity_rounds_down():
    # Mittwoch frei → 4 von 5 Tagen; 7 Std. × 4 / 5 = 5,6 → 5
    cal = SchoolCalendar(date(2026, 9, 14), date(2027, 7, 30), MON_FRI, [Closure(date(2026, 11, 18), date(2026, 11, 18))])
    w = cal.week_info(date(2026, 11, 18))
    assert w.shortened and w.active_days == 4
    assert w.capacity(7) == 5


def test_class_weekdays_respected():
    cal = SchoolCalendar(date(2026, 9, 14), date(2027, 7, 30), [0, 2])  # Mo + Mi
    w = cal.week_info(date(2026, 9, 14))
    assert w.regular_days == 2
    assert [d.weekday() for d in w.teaching_days] == [0, 2]
