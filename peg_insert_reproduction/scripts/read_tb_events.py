#!/usr/bin/env python3
"""Read scalars out of a TensorBoard event file using only the standard library.

The container has no numpy/tensorboard pair that imports cleanly, so this parses the
TFRecord + protobuf records by hand.  Only the two field shapes rl_games writes are
needed: Event.step (field 2, varint) and Event.summary (field 5) -> Summary.value
(field 1) -> Value.tag (field 1, string) / Value.simple_value (field 2, float32).

Usage:
    read_tb_events.py DIR [tag,tag,...]
"""

import glob
import os
import struct
import sys


def varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def skip(b, i, fn, wt):
    """Advance past one field whose payload we do not care about."""
    if wt == 0:
        _, i = varint(b, i)
    elif wt == 1:
        i += 8
    elif wt == 2:
        ln, i = varint(b, i)
        i += ln
    elif wt == 5:
        i += 4
    elif wt == 3:  # start group: walk to the matching end group
        while i < len(b):
            k, i = varint(b, i)
            f2, w2 = k >> 3, k & 7
            if w2 == 4:
                break
            i = skip(b, i, f2, w2)
    return i


def fields(b):
    i, n = 0, len(b)
    while i < n:
        k, i = varint(b, i)
        fn, wt = k >> 3, k & 7
        if wt == 0:
            v, i = varint(b, i)
            yield fn, wt, v
        elif wt == 1:
            yield fn, wt, b[i : i + 8]
            i += 8
        elif wt == 2:
            ln, i = varint(b, i)
            yield fn, wt, b[i : i + ln]
            i += ln
        elif wt == 5:
            yield fn, wt, b[i : i + 4]
            i += 4
        else:
            i = skip(b, i, fn, wt)


def records(path):
    with open(path, "rb") as f:
        while True:
            # record = uint64 length | crc32(length) | data | crc32(data)
            hdr = f.read(8)
            if len(hdr) < 8:
                return
            ln = struct.unpack("<Q", hdr)[0]
            f.read(4)  # masked crc32 of the length
            rec = f.read(ln)
            if len(rec) < ln:
                return
            f.read(4)  # masked crc32 of the data
            yield rec


def events(path):
    for rec in records(path):
        step, summary = None, None
        for fn, wt, v in fields(rec):
            if fn == 2 and wt == 0:
                step = v
            elif fn == 5 and wt == 2:
                summary = v
        if summary is None:
            continue
        for fn, wt, v in fields(summary):
            if fn != 1 or wt != 2:
                continue
            tag, val = None, None
            for f2, w2, v2 in fields(v):
                if f2 == 1 and w2 == 2:
                    tag = v2.decode("utf-8", "replace")
                elif f2 == 2 and w2 == 5 and len(v2) == 4:
                    val = struct.unpack("<f", v2)[0]
            if tag is not None:
                yield step, tag, val


def main():
    d = sys.argv[1]
    want = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    files = sorted(glob.glob(os.path.join(d, "summaries", "events.out.tfevents.*")), key=os.path.getmtime)
    if not files:
        print("no event files under", os.path.join(d, "summaries"))
        return
    series = {}
    for p in files:
        for step, tag, val in events(p):
            if want is None or tag in want:
                series.setdefault(tag, []).append((step, val))
    print("event files:", len(files), "distinct tags:", len(series))
    for t in sorted(series):
        s = series[t]
        print(
            "%-32s n=%-6d first_step=%-9s first=%-12s last_step=%-9s last=%s"
            % (t, len(s), s[0][0], s[0][1], s[-1][0], s[-1][1])
        )


if __name__ == "__main__":
    main()
