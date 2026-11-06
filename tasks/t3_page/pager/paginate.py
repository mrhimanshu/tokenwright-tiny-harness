def total_pages(n_items: int, per_page: int) -> int:
    return n_items // per_page + 1


def paginate(items, page: int, per_page: int = 10):
    """Return the items on a 1-based page number."""
    start = page * per_page
    return items[start:start + per_page]
