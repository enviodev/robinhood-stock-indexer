import os, json, urllib.request, urllib.error, time

TOKEN = os.environ["ENVIO_API_TOKEN"]
NVDA  = "0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec"
TR    = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
FROM, TO = 45_400_000, 45_500_000
PACE = 2.1   # stay inside the 30k units/min budget (1k per query)

class Timer:
    """Accumulates only time spent inside HTTP calls, never pacing sleeps."""
    def __init__(self): self.t = 0.0; self.n = 0

def post(url, body, timer, tries=8):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                headers={'Content-Type':'application/json','Authorization':f'Bearer {TOKEN}'})
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
            timer.t += time.perf_counter() - t0
            timer.n += 1
            time.sleep(PACE)          # outside the timed region
            return out
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("x-ratelimit-reset", 20)) + 2); continue
            if e.code in (502,503,504):
                time.sleep(min(2**i, 20)); continue
            raise
        except Exception:
            time.sleep(3); continue
    raise SystemExit(f"gave up on {url}")

def hypersync():
    tm = Timer(); n = 0; blk = FROM
    while blk < TO:
        d = post("https://robinhood.hypersync.xyz/query", {
            "from_block": blk, "to_block": TO,
            "logs": [{"address": [NVDA], "topics": [[TR]]}],
            "field_selection": {"log": ["block_number","transaction_hash","data","topic1","topic2"]},
        }, tm)
        for b in d.get('data', []): n += len(b.get('logs', []))
        nb = d.get('next_block')
        if not nb or nb <= blk: break
        blk = nb
    return tm, n

def hyperrpc(chunk):
    tm = Timer(); n = 0
    for start in range(FROM, TO, chunk):
        end = min(start + chunk - 1, TO)
        d = post("https://robinhood.rpc.hypersync.xyz", {
            "jsonrpc":"2.0","id":1,"method":"eth_getLogs",
            "params":[{"fromBlock":hex(start),"toBlock":hex(end),
                       "address":NVDA,"topics":[TR]}]}, tm)
        if "error" in d: return tm, None, d["error"]
        n += len(d.get("result", []))
    return tm, n, None

print(f"Task: every NVDA Transfer log, blocks {FROM:,} to {TO:,} ({TO-FROM:,} blocks)")
print("Timing counts HTTP request time only. Pacing sleeps for the shared")
print("rate limit are excluded so neither side is penalised for request count.\n")

tm, hs_n = hypersync()
print(f"HyperSync native query        {tm.t:7.2f}s   {hs_n:,} logs   {tm.n:>3} requests")
base = tm.t

for chunk in (10_000, 2_000):
    tm, n, err = hyperrpc(chunk)
    if err:
        print(f"HyperRPC eth_getLogs {chunk:>6,}   ERROR {err}")
        continue
    ok = "match" if n == hs_n else f"MISMATCH (expected {hs_n:,})"
    print(f"HyperRPC eth_getLogs {chunk:>6,}/req {tm.t:7.2f}s   {n:,} logs   "
          f"{tm.n:>3} requests   [{ok}]   {tm.t/base:.1f}x")
