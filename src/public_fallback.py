import os


FALLBACK_INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Northwoods Events – Status</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font: 16px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }
    .ok { color: #0a7a0a; }
    .err { color: #a30008; }
    .warn { color: #a66f00; }
    code { background: #f3f3f3; padding: 0.15rem 0.35rem; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Northwoods Events – Status</h1>
  <p>If you intended to ship a custom dashboard, add <code>public/index.html</code> to the repo.</p>
  <ul>
    <li><a href="combined.ics">combined.ics</a></li>
    <li><a href="report.json">report.json</a></li>
    <li>Per-source feeds in <code>/by-source/</code>.</li>
  </ul>
</body>
</html>
"""


def ensure_index(public_dir: str) -> None:
    os.makedirs(public_dir, exist_ok=True)
    index_path = os.path.join(public_dir, "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(FALLBACK_INDEX)
