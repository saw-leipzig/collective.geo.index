def _intersects(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "intersects"}}


def _equals(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "equals"}}


def _touches(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "touches"}}


def _crosses(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "crosses"}}


def _within(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "within"}}


def _contains(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "contains"}}


def _overlaps(context, row):
    return {row.index: {'query': row.values, 'geometry_operator': "overlaps"}}
