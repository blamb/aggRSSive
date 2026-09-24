import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/help.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import scheduler  # noqa: E402
from aggrssive.help import pages  # noqa: E402
from aggrssive.main import app  # noqa: E402


def test_every_doc_page_renders_and_links_resolve():
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    docs = pages()
    assert list(docs)[0] == "index"
    assert {"sources", "bundles", "publishing", "lti-admin", "lti-instructors", "genai", "roles", "hosting", "tags-and-classification"} <= set(docs)
    with TestClient(app) as c:
        for slug, p in docs.items():
            r = c.get(f"/help/{slug}")
            assert r.status_code == 200 and p.title in r.text
            # every internal /help/... link points at a page that exists
            import re

            for target in re.findall(r'href="/help/([a-z0-9-]+)"', p.html):
                assert target in docs, f"{slug} links to missing page {target}"
        assert c.get("/help").status_code == 200
        assert c.get("/help/nope").status_code == 404
        assert "<script" not in c.get("/help/publishing").text.split("<article")[1].split("</article>")[0]
