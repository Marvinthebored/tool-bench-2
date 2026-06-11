import os, time

def make_timestamp():
    epoch_ms = time.time_ns() // 1_000_000
    lt = time.localtime(epoch_ms / 1000)
    iso = time.strftime("%Y-%m-%dT%H:%M:%S", lt)
    frac = f".{epoch_ms % 1000:03d}"
    tz = time.strftime("%z")
    tz_fmt = tz[:3] + ":" + tz[3:] if tz else "+00:00"
    return {
        "epoch_ms": epoch_ms,
        "iso": iso + frac + tz_fmt,
        "pid": os.getpid(),
        "user": os.environ.get("USER", "unknown"),
    }
