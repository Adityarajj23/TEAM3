def _pending_auto_test(qa):
    return qa.get("/tests?status=pending_review&automation=pytest&page_size=1").json()["items"]


def test_edit_creates_new_version_and_requires_rereview(qa, reviewer):
    t = qa.get("/tests?status=approved&automation=pytest&page_size=1").json()["items"][0]
    full = qa.get(f"/tests/{t['id']}").json()
    r = qa.patch(f"/tests/{t['id']}", json={"title": full["title"] + " (revised)", "note": "Clarified title"})
    assert r.status_code == 200
    after = r.json()
    assert after["version"] == full["version"] + 1 and after["status"] == "pending_review"
    hist = qa.get(f"/tests/{t['id']}").json()["versions"]
    assert hist[-1]["snapshot"]["title"] == full["title"] if len(hist) > 1 else True
    assert any(v["snapshot"]["title"] == full["title"] for v in hist), "original version preserved"
    assert reviewer.post(f"/tests/{t['id']}/review", json={"decision": "approve"}).status_code == 200


def test_invalid_script_cannot_be_approved(qa, reviewer):
    t = qa.get("/tests?status=approved&automation=pytest&page_size=1&page=3").json()["items"][0]
    r = qa.patch(f"/tests/{t['id']}", json={"script": "import os\n\ndef test_x():\n    os.system('id')\n"}).json()
    assert r["validation_status"] == "invalid" and any("os" in e for e in r["validation_errors"])
    resp = reviewer.post(f"/tests/{t['id']}/review", json={"decision": "approve"})
    assert resp.status_code == 409 and resp.json()["error"]["details"]["validation_errors"]


def test_request_changes_needs_comment_and_bulk_review(qa, reviewer):
    items = qa.get("/tests?status=pending_review&page_size=3").json()["items"]
    assert reviewer.post(f"/tests/{items[0]['id']}/review", json={"decision": "request_changes"}).status_code == 400
    out = reviewer.post("/tests/bulk-review", json={"test_ids": [i["id"] for i in items] + [999999],
                                                     "decision": "approve"}).json()
    assert out["skipped"] and any(s["id"] == 999999 for s in out["skipped"])


def test_manual_defect_from_failure_with_comments_links_and_reopen(qa, reviewer):
    ex = qa.get("/executions?status=failed&source=historical_import&page_size=1").json()["items"][0]
    detail = qa.get(f"/executions/{ex['id']}?result_status=failed").json()
    res = detail["results"][0]
    d = qa.post("/defects", json={"project_id": ex["project_id"], "title": "Manually logged failure for triage",
                                  "severity": "medium", "priority": "p3", "execution_result_id": res["id"]})
    assert d.status_code == 201, d.text
    d = d.json()
    assert d["execution_result_id"] == res["id"] and d["approval_status"] == "approved"
    other = next(x for x in qa.get(f"/defects?project_id={ex['project_id']}&page_size=5").json()["items"]
                 if x["id"] != d["id"])
    assert qa.post(f"/defects/{d['id']}/links", json={"related_key": other["key"], "link_type": "related"}).status_code == 201
    assert qa.post(f"/defects/{d['id']}/comments", json={"body": "Investigating"}).json()["comments"]
    assert qa.post(f"/defects/{d['id']}/transition", json={"status": "assigned"}).status_code == 409
    passed = qa.get(f"/executions/{ex['id']}?result_status=passed").json()["results"]
    bad = qa.post("/defects", json={"project_id": ex["project_id"], "title": "Linked to a passing result",
                                    "severity": "low", "priority": "p4", "execution_result_id": passed[0]["id"]})
    assert bad.status_code == 400
    closed = reviewer.get("/defects?status=closed&page_size=1").json()["items"]
    if closed:
        r = reviewer.post(f"/defects/{closed[0]['id']}/transition", json={"status": "reopened", "comment": "Regressed"})
        assert r.status_code == 200 and r.json()["resolved_at"] is None


def test_seeded_recommendation_can_be_dismissed(reviewer, admin):
    recs = admin.get("/defects?approval_status=recommended").json()["items"]
    assert recs
    r = admin.post(f"/defects/{recs[0]['id']}/dismiss", json={"comment": "Known environment issue"})
    assert r.status_code == 200 and r.json()["approval_status"] == "dismissed"
