import json
with open("output.json") as f:
    data = json.load(f)
print("Verdict:", data.get("verdict"))
print("Healing loops:", data.get("healing_loop"))
print("Total test results:", len(data.get("test_results", [])))
print("Total adversarial results:", len(data.get("adversarial_results", [])))
print("Tests passed:", sum(1 for r in data.get("test_results", []) if r.get("passed")))
print("Adv tests passed:", sum(1 for r in data.get("adversarial_results", []) if r.get("passed")))
print("Metric results:")
for m in data.get("metric_results", []):
    flag = "ok" if m["passed"] else "flag"
    print(f'  {m["name"]}: {m["score"]} -> {flag}')
print("Escalate reason:", data.get("escalate_reason", "")[:300])
print("Error messages from failures:")
for r in data.get("test_results", []) + data.get("adversarial_results", []):
    if not r.get("passed"):
        print(f'  {r.get("name","?")[:60]}: type={r.get("error_type","")} msg={r.get("error_message","")[:120]}')
