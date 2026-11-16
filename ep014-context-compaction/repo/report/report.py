"""Print a sales report. Usage: python3 report.py [--top N]"""
import argparse

SALES = [("mug", 120), ("tshirt", 340), ("sticker", 75), ("hoodie", 210)]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=len(SALES))
    a = p.parse_args(argv)
    rows = sorted(SALES, key=lambda r: -r[1])[:a.top]
    for name, total in rows:
        print(f"{name:10} {total:>6}")


if __name__ == "__main__":
    main()
