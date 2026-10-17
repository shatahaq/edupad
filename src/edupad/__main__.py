import sys

from edupad.cli import main

# Penjaga wajib: proses anak multiprocessing "spawn" (konversi PDF) mengimpor modul ini lagi.
if __name__ == "__main__":
    sys.exit(main())
