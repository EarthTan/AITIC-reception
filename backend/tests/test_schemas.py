from datetime import date, datetime

from app.schemas.visit import VisitOut, mask_id_number

from app.models.visit import EntrySource, IdentityType, Visit, VisitStatus


def test_mask_id_number_keeps_first_three_and_last_four():
    # 14-char id_number: keeps "110" (first 3), "0101" (last 4), inserts 7 stars
    assert mask_id_number("11010119900101") == "110*******0101"


def test_mask_id_number_leaves_short_values_untouched():
    # < 7 chars: not enough room to keep first 3 + last 4 + 7 stars, so unchanged
    assert mask_id_number("123") == "123"
    assert mask_id_number(None) is None


def test_visit_out_from_visit_masks_id_number():
    visit = Visit(
        id=1,
        visit_date=date(2026, 7, 6),
        session_time=datetime(2026, 7, 6, 10, 0),
        name="张三",
        id_number="11010119900101",  # 14 chars, exercises the 3+7+4 split
        identity_type=IdentityType.ENTERPRISE_LEADER,
        entry_source=EntrySource.MANUAL,
        import_batch_id="batch-1",
        status=VisitStatus.PENDING,
        created_at=datetime(2026, 7, 6, 8, 0),
        updated_at=datetime(2026, 7, 6, 8, 0),
    )

    out = VisitOut.from_visit(visit)

    assert out.id_number == "110*******0101"
    assert out.name == "张三"
