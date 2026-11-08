from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_dashboard_and_empty_filter():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py'),default_timeout=60).run()
    assert not app.exception
    assert len(app.tabs)==6
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any('Select at least one' in item.value for item in app.info)

def test_optional_access_gate(monkeypatch):
    monkeypatch.setenv('COMMERCE_ACCESS_PASSWORD','test-workspace-secret')
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py'),default_timeout=60).run()
    assert not app.exception and not app.tabs
    app.text_input[0].set_value('wrong')
    app.button[0].click().run()
    assert any('Invalid credentials' in item.value for item in app.error)
    app.text_input[0].set_value('test-workspace-secret')
    app.button[0].click().run()
    assert not app.exception and len(app.tabs)==6
    signout=next(b for b in app.button if b.label=='Sign out')
    signout.click().run()
    assert not app.tabs

def test_additional_workbenches():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard/app.py'),default_timeout=60).run()
    for label in ['Load transaction audit','Run segment sensitivity','Run operational checks']:
        control=next(c for c in app.checkbox if c.label==label)
        control.set_value(True).run()
        assert not app.exception
