"""Deepfake awareness survey backend.
Run:  pip install -r requirements.txt && ADMIN_KEY=yourSecret python app.py
Participants open  http://<host>:5000/
You download data: /admin/export/wide.csv?key=yourSecret   (1 row / participant)
                   /admin/export/trials.csv?key=yourSecret (1 row / participant x stimulus)
"""
import csv, io, json, os, sqlite3
from datetime import datetime, timezone
from flask import Flask, Response, abort, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DB_PATH", os.path.join(BASE, "survey.db"))
ADMIN_KEY = os.environ.get("ADMIN_KEY", "change-me")
STIM = json.load(open(os.path.join(BASE, "stimuli.json"), encoding="utf-8"))
TRUTH = {s["id"]: s["truth"] for s in STIM}

app = Flask(__name__, static_folder="static", static_url_path="/static")


def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS responses(pid TEXT PRIMARY KEY, data TEXT, final INTEGER, updated TEXT)")
    return c


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/config")
def config():  # truth is NOT sent to the browser
    return jsonify([{k: s[k] for k in ("id", "file", "type")} for s in STIM])


@app.post("/api/save")
def save():
    b = request.get_json(force=True)
    pid, data, final = str(b.get("pid", ""))[:64], b.get("data", {}), bool(b.get("final"))
    if not pid:
        abort(400)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if final:
        data["finished"] = now
    with db() as c:
        old = c.execute("SELECT final FROM responses WHERE pid=?", (pid,)).fetchone()
        if old and old[0]:  # already completed: ignore late partial saves
            return jsonify(ok=True)
        c.execute("REPLACE INTO responses VALUES(?,?,?,?)", (pid, json.dumps(data, ensure_ascii=False), int(final), now))
    out = {"ok": True}
    if final:
        res = [{"id": t["sid"], "truth": TRUTH.get(t["sid"]), "answer": t.get("q1")} for t in data.get("trials", [])]
        out["results"] = res
        out["score"] = sum(r["truth"] == r["answer"] for r in res)
    return jsonify(out)


# ---------- CSV export ----------
def rows():
    with db() as c:
        return [(p, json.loads(d), f) for p, d, f in c.execute("SELECT pid,data,final FROM responses ORDER BY updated")]


def csv_response(header, body, name):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(body)
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}"})


def need_key():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)


TRIAL_FIELDS = ["order", "q1", "correct", "q1_rt_ms", "q2_confidence", "q3_authenticity", "q4_share", "q5_feature", "view_ms"]


def trial_vals(t):
    t = dict(t)
    t["correct"] = int(t.get("q1") == TRUTH.get(t.get("sid"))) if t.get("q1") else ""
    return [t.get(f, "") for f in TRIAL_FIELDS]


@app.get("/admin/export/wide.csv")
def wide():
    need_key()
    data = rows()
    demo_keys = sorted({k for _, d, _ in data for k in d.get("demo", {})}, key=lambda k: (int(k[1:].split("_")[0]), k))
    aw_keys = [f"{p}{i}" for p in ("SA", "SO", "SI") for i in range(1, 6)]
    head = ["pid", "completed", "started", "finished", "timezone", "language", "screen", "user_agent"] + demo_keys + aw_keys
    head += [f"{s['id']}_{f}" for s in STIM for f in ["truth"] + TRIAL_FIELDS]
    out = []
    for pid, d, fin in data:
        g, tr = d.get("geo", {}), {t["sid"]: t for t in d.get("trials", [])}
        r = [pid, int(fin), d.get("started", ""), d.get("finished", ""), g.get("tz", ""), g.get("lang", ""), g.get("screen", ""), g.get("ua", "")]
        r += [("; ".join(v) if isinstance(v, list) else v) for v in (d.get("demo", {}).get(k, "") for k in demo_keys)]
        r += [d.get("aware", {}).get(k, "") for k in aw_keys]
        for s in STIM:
            r += [s["truth"]] + (trial_vals(tr[s["id"]]) if s["id"] in tr else [""] * len(TRIAL_FIELDS))
        out.append(r)
    return csv_response(head, out, "survey_wide.csv")


@app.get("/admin/export/trials.csv")
def trials():
    need_key()
    out = [[pid, int(fin), t["sid"], TRUTH.get(t["sid"]), next((s["type"] for s in STIM if s["id"] == t["sid"]), "")] + trial_vals(t)
           for pid, d, fin in rows() for t in d.get("trials", [])]
    return csv_response(["pid", "completed", "stimulus", "truth", "media_type"] + TRIAL_FIELDS, out, "survey_trials_long.csv")


@app.get("/admin/count")
def count():
    need_key()
    r = rows()
    return jsonify(started=len(r), completed=sum(1 for _, _, f in r if f))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
