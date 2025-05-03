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
st.title("🧾 auto summarizationr")
st.write("""
Upload a plain‑text file, let GPT build a Jira issue payload,  
then optionally POST it to **Webhook.site** (or any webhook endpoint).
""")

# ---------- INPUTS ----------
uploaded = st.file_uploader("📄  Upload a .txt file", type=["txt"])
webhook_url = st.secrets.get("WEBHOOK")

# ---------- GENERATE ----------
if st.button("Generate Jira JSON") and uploaded:
    text = uploaded.read().decode("utf‑8", errors="ignore")

    st.subheader("Input text")
    st.text_area("Contents", text, height=200, disabled=True)

    # --- Summarize ---
    summarize_prompt = f"""
Summarize the following meeting notes or text into clear, concise bullet points.

Input:
\"\"\"{text}\"\"\"

Bullet points:
"""
    with st.spinner("Summarizing meeting notes..."):
        try:
            summary_resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summarize_prompt}],
                temperature=0.3,
            )
            summary = summary_resp.choices[0].message.content
            st.subheader("Meeting Summary")
            st.markdown(summary)
        except Exception as e:
            st.error(f"❌ Summarization error: {e}")
            st.stop()

    # --- Generate Jira JSON ---
    prompt = f"""
You convert user requests into Jira tasks.  
Parse the following text and output *only* valid JSON suitable for the Jira issue-creation REST API.

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
    with st.spinner("Calling OpenAI..."):
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw = resp.choices[0].message.content
            start, end = raw.find("{"), raw.rfind("}") + 1
            jira_json = json.loads(raw[start:end])
        except Exception as e:
            st.error(f"❌ OpenAI error or invalid JSON: {e}")
            st.stop()

    st.session_state["jira_json"] = jira_json
    st.success("✅ Generated!")

    # --- Display Editable JSON ---
    json_str = json.dumps(st.session_state["jira_json"], indent=2)
    edited_json_str = st.text_area(
        "Edit the JSON below before sending:",
        value=json_str,
        height=300,
        key="edited_json"
    )
    try:
        edited_json = json.loads(edited_json_str)
        st.session_state["jira_json"] = edited_json
    except json.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON: {e}")
        st.stop()

    # --- Send to Webhook ---
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
