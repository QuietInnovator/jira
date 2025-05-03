# app.py
import json
import os
import requests
import streamlit as st
import openai

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="🧾  Jira JSON Generator", page_icon="🧾")

# ---------- OPENAI KEY ----------
openai.api_key = (
    st.secrets.get("OPENAI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
)

if not openai.api_key:
    st.error(
        "⚠️  Please set your OpenAI key in Streamlit → Settings → Secrets "
        "or export OPENAI_API_KEY before running."
    )
    st.stop()

# ---------- TITLE ----------
st.title("🧾 Jira Task JSON Generator")
st.write("""
Upload a plain‑text file, let GPT build a Jira issue payload,  
then optionally POST it to **Webhook.site** (or any webhook endpoint).
""")

# ---------- INPUTS ----------
uploaded = st.file_uploader("📄  Upload a .txt file", type=["txt"])
webhook_url =st.secrets.get("WEBHOOK")
# ---------- GENERATE ----------
if st.button("Generate Jira JSON") and uploaded:
    text = uploaded.read().decode("utf‑8", errors="ignore")

    st.subheader("Input text")
    st.text_area("Contents", text, height=200, disabled=True)

    prompt = f"""
You convert user requests into Jira tasks.  
Parse the following text and output *only* valid JSON suitable for the Jira issue‑creation REST API.

Input:
\"\"\"{text}\"\"\"

Required shape:
{{
  "fields": {{
    "project": {{"key": "PROJ"}},
    "summary": "Short summary",
    "description": "Detailed description",
    "issuetype": {{"name": "Task"}},
    "labels": ["ai-generated"],
    "priority": {{"name": "Medium"}}
  }}
}}
"""

    with st.spinner("Calling OpenAI…"):
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",   # swap to "gpt-4o" / "gpt-4" if you like
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw = resp.choices[0].message.content
            # Extract the first JSON object in the reply
            start, end = raw.find("{"), raw.rfind("}") + 1
            jira_json = json.loads(raw[start:end])
        except Exception as e:
            st.error(f"❌ OpenAI error or invalid JSON: {e}")
            st.stop()

    # Persist it for later button clicks
    st.session_state["jira_json"] = jira_json

    st.success("✅ Generated!")
    st.json(jira_json)

# ---------- DISPLAY SAVED JSON ----------
if "jira_json" in st.session_state:
    st.subheader("Generated Jira JSON")
    st.json(st.session_state["jira_json"])

    # ---------- SEND ----------
    if st.button("Send JSON to Webhook") and webhook_url:
        try:
            r = requests.post(
                webhook_url.strip(),
                json=st.session_state["jira_json"],
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            r.raise_for_status()
            st.success(f"🎉 Posted successfully! HTTP {r.status_code}")
        except Exception as e:
            st.error(f"❌ POST failed: {e}")
else:
    st.info("⬆️ Upload a file and click **Generate Jira JSON** to begin.")
