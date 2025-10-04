"""
make_icon.py

Converts a provided PNG (`icon.png`) into `icon.ico` suitable for PyInstaller.

Usage:
    python make_icon.py path/to/icon.png

If no argument is provided, it will look for `icon.png` in the current directory.
"""
from PIL import Image
import sys
from pathlib import Path


def make_icon(src: Path, dst: Path):
    img = Image.open(src)
    # ICO should include multiple sizes; common sizes: 16,32,48,64,128,256
    sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
    imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save(dst, format='ICO', sizes=sizes)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('icon.png')
    if not src.exists():
        print(f"Icon source not found: {src}")
        return
    dst = Path('icon.ico')
    make_icon(src, dst)
    print(f"Wrote {dst}")


if __name__ == '__main__':
    main()
