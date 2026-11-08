"""Optional shared-workspace gate; use host SSO/TLS for managed deployments."""
import hashlib
import hmac
import os
import time

def require_access(st):
    secret=os.getenv('COMMERCE_ACCESS_PASSWORD')
    if not secret:
        return
    fingerprint=hashlib.sha256(secret.encode()).hexdigest()
    previous=st.session_state.get('access_session',{})
    if previous.get('fingerprint')==fingerprint and time.time()-previous.get('time',0)<3600:
        if st.sidebar.button('Sign out'):
            st.session_state.pop('access_session',None)
            st.rerun()
        return
    st.title('Analytics workspace')
    with st.form('access'):
        supplied=st.text_input('Workspace password',type='password')
        submitted=st.form_submit_button('Sign in')
    if submitted:
        if hmac.compare_digest(supplied.encode(),secret.encode()):
            st.session_state['access_session']={'fingerprint':fingerprint,'time':time.time()}
            st.rerun()
        else:st.error('Invalid credentials')
    st.stop()
