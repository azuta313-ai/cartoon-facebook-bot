"""Read-only Pollen balance check. Never makes generation requests."""
import json,os,urllib.request,urllib.error
key=os.getenv("POLLINATIONS_API_KEY")
if not key:
    print("BLOCKED: POLLINATIONS_API_KEY not available to this workflow")
    raise SystemExit(0)
req=urllib.request.Request("https://gen.pollinations.ai/account/balance",headers={"Authorization":"Bearer "+key})
try:
    with urllib.request.urlopen(req,timeout=25) as response:
        obj=json.load(response)
    balance=obj.get("balance")
    if isinstance(balance,(int,float)):
        print("Balance endpoint succeeded; total Pollen balance:",balance)
        print("CAUTION: combined balance does NOT prove credits are free/Quest-only")
    else:
        print("Balance endpoint returned no numeric balance; generation prohibited")
except urllib.error.HTTPError as e:
    print("Balance check HTTP status:",e.code,"; generation prohibited")
except Exception as e:
    print("Balance check unavailable:",type(e).__name__,"; generation prohibited")
print("NO_GENERATION_NO_SPEND")
