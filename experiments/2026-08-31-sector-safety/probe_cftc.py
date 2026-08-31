import requests

r = requests.get(
    "https://publicreporting.cftc.gov/resource/gpe5-46if.json",
    params={"$limit": 1, "$where": "cftc_contract_market_code='13874A'"},
    timeout=90,
)
print(r.status_code)
d = r.json()
if not d:
    print("empty")
else:
    for k in sorted(d[0]):
        print(f"{k} = {d[0][k]}")
