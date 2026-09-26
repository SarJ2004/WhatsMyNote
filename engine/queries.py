"""Typed reads. The model never sees these and never writes SQL."""


def spending_by_category(conn, start, end):
    with conn.cursor() as cur:
        cur.execute(
            "select category, sum(converted_minor) from expense_records e "
            "join records r on r.id = e.record_id "
            "where e.expense_date between %s and %s "
            "group by category order by category",
            (start, end),
        )
        return [(row[0], int(row[1])) for row in cur.fetchall()]
