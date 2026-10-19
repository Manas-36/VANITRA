"""Record labelled gesture takes from the glove over USB serial.

    pip install -r ml/requirements.txt
    python ml/collect_data.py --port COM5 --user manas            (Windows)
    python ml/collect_data.py --port /dev/ttyACM0 --user pragati   (Linux / macOS)

Calibrate the glove first (hold BOOT 2 s). For each sign you are asked to perform it repeatedly
for --seconds; every take is saved to ml/data/<LABEL>/<user>_<time>.csv.
Aim for >= 5 takes per sign per person, from at least 3 people, plus extra REST takes
(hand relaxed, typing, scratching, walking) so the glove learns when NOT to speak.
Two gloves: flash both, set the left one to role LEFT (serial 'r'), plug the RIGHT glove into USB.
It streams both hands (31 columns: right 15, left 15, left_ok); check left_ok is 1 before recording.
"""
import argparse
import csv
import os
import sys
import time

from vanitra_features import COLUMNS, COLUMNS_2

HERE = os.path.dirname(os.path.abspath(__file__))


def load_labels():
    with open(os.path.join(HERE, "vocabulary.csv"), newline="", encoding="utf-8") as f:
        return [(r["label"], r["say"], r["sign_hint"]) for r in csv.DictReader(f)]


def record(ser, seconds):
    """Returns rows of either COLUMNS (one glove) or COLUMNS_2 (two gloves)."""
    rows, t_end = [], time.time() + seconds
    ser.reset_input_buffer()
    while time.time() < t_end:
        line = ser.readline().decode(errors="ignore").strip()
        if not line.startswith("D,"):
            continue
        parts = line.split(",")[1:]
        if len(parts) in (len(COLUMNS), len(COLUMNS_2)):
            rows.append(parts)
    return rows


def main():
    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("pip install pyserial")
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--user", required=True, help="who is wearing the glove (used in file names)")
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--labels", nargs="*", help="only these labels (default: all in vocabulary.csv)")
    args = ap.parse_args()

    labels = load_labels()
    if args.labels:
        labels = [l for l in labels if l[0] in args.labels]
    ser = serial.Serial(args.port, 115200, timeout=0.5)
    time.sleep(1.5)
    ser.write(b"s")
    print("Streaming. Enter = record, s = skip sign, q = quit.\n")
    try:
        for label, say, hint in labels:
            print(f"=== {label}  ({say or 'silent'})\n    how: {hint}")
            while True:
                cmd = input("    [Enter] record a take, [s] next sign, [q] quit > ").strip().lower()
                if cmd == "q":
                    return
                if cmd == "s":
                    break
                for c in (3, 2, 1):
                    print(f"    {c}...", end="", flush=True)
                    time.sleep(0.7)
                print(" GO (keep repeating the sign)")
                rows = record(ser, args.seconds)
                if len(rows) < args.seconds * 40:
                    print(f"    only {len(rows)} frames - is the glove streaming? (send 's')")
                    continue
                folder = os.path.join(HERE, "data", label)
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, f"{args.user}_{time.strftime('%Y%m%d_%H%M%S')}.csv")
                with open(path, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(COLUMNS_2 if len(rows[0]) == len(COLUMNS_2) else COLUMNS)
                    w.writerows(rows)
                print(f"    saved {len(rows)} frames -> {os.path.relpath(path, HERE)}")
    finally:
        ser.write(b"x")
        ser.close()


if __name__ == "__main__":
    main()
