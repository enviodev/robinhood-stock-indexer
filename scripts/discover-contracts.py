import os, json, urllib.request, urllib.error, collections, time

T = os.environ["ENVIO_API_TOKEN"]
URL = "https://robinhood.hypersync.xyz/query"

def q(body, tries=8):
    for i in range(tries):
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                headers={'Content-Type':'application/json','Authorization':f'Bearer {T}'})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429,502,503,504):
                w = min(2**i, 30); time.sleep(w); continue
            raise
        except Exception:
            time.sleep(3); continue
    raise SystemExit("gave up")

START = 45400000
END   = 45500000
addr, topic = collections.Counter(), collections.Counter()
pair = collections.Counter()
nlogs = 0; blk = START; t0 = time.time(); rounds = 0
while blk < END:
    d = q({"from_block": blk, "to_block": END, "logs":[{}],
           "field_selection":{"log":["address","topic0"]}})
    for b in d.get('data',[]):
        for l in b.get('logs',[]):
            a=l.get('address'); t=l.get('topic0')
            addr[a]+=1; topic[t]+=1; pair[(a,t)]+=1; nlogs+=1
    nb = d.get('next_block'); rounds+=1
    if not nb or nb<=blk: break
    blk = nb
    time.sleep(0.35)
    if rounds % 25 == 0: print(f"  ...{blk-START:,} blocks, {nlogs:,} logs, {time.time()-t0:.0f}s", flush=True)
print(f"\nscanned blocks {START}..{blk} ({blk-START:,} blocks) in {rounds} requests, {time.time()-t0:.1f}s wall")
print(f"total logs: {nlogs:,}   unique contracts: {len(addr):,}   unique topic0: {len(topic):,}")
print("\n--- TOP 20 CONTRACTS BY LOG COUNT ---")
for a,c in addr.most_common(20): print(f"{c:>9,}  {a}")
print("\n--- TOP 15 EVENT SIGNATURES ---")
for t,c in topic.most_common(15): print(f"{c:>9,}  {t}")
json.dump({"addr":addr.most_common(100),"topic":topic.most_common(50),
           "start":START,"end":blk,"nlogs":nlogs,"ncontracts":len(addr)}, open('agg.json','w'))
