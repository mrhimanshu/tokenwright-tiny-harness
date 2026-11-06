from pager.paginate import paginate, total_pages
ITEMS = list(range(1, 26))

def test_first_page(): assert paginate(ITEMS, 1, 10) == list(range(1, 11))
def test_last_page(): assert paginate(ITEMS, 3, 10) == [21, 22, 23, 24, 25]
def test_out_of_range(): assert paginate(ITEMS, 4, 10) == []
def test_total(): assert total_pages(25, 10) == 3
def test_total_exact(): assert total_pages(20, 10) == 2
def test_total_empty(): assert total_pages(0, 10) == 0
