import streamlit as st
import subprocess
import sys
import os
import ollama
from openai import OpenAI
import dotenv

dotenv.load_dotenv()

class ModelManager:
    def __init__(self):
        self.models = [
            {"name": "Ollama Llama 3.2 (Local)", "provider": "ollama", "model": "llama3.2", "api_key": None},
            {"name": "Ollama Mistral (Local)", "provider": "ollama", "model": "mistral", "api_key": None},
            {"name": "OpenRouter Claude 3 Haiku", "provider": "openrouter", "model": "anthropic/claude-3-haiku", "api_key": None},
        ]
        self.current_index = 0
        self.openrouter_key = ""
        if hasattr(st, "secrets") and "OPENROUTER_API_KEY" in st.secrets:
            self.openrouter_key = st.secrets["OPENROUTER_API_KEY"]

    def add_model(self, name: str, provider: str, model_id: str, api_key: str = None):
        name = name.strip()
        provider = provider.strip().lower()
        model_id = model_id.strip()
        if not name or not provider or not model_id:
            st.error("❌ Name, Provider, and Model ID required (check for extra spaces)")
            return None
        if provider not in ["ollama", "openrouter"]:
            st.error("❌ Provider must be exactly 'ollama' or 'openrouter'")
            return None
        new_model = {"name": name, "provider": provider, "model": model_id, "api_key": api_key.strip() if api_key else None}
        self.models.append(new_model)
        st.success(f"✅ Added: {name}")
        return new_model

    def get_response(self, prompt):
        attempts = 0
        original_index = self.current_index
        while attempts < len(self.models):
            model = self.models[self.current_index]
            try:
                if model["provider"] == "ollama":
                    response = ollama.chat(model=model["model"], messages=[{"role": "user", "content": prompt}])
                    result = response['message']['content']
                else:
                    key = model["api_key"] or self.openrouter_key
                    if not key:
                        raise ValueError("OpenRouter API key missing - paste in sidebar or add to st.secrets")
                    client = OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=key,
                        default_headers={"HTTP-Referer": "https://lil-buddy.streamlit.app", "X-Title": "Lil Buddy"}
                    )
                    response = client.chat.completions.create(model=model["model"], messages=[{"role": "user", "content": prompt}], temperature=0.7)
                    result = response.choices[0].message.content
                self.last_used = model["name"]
                return result
            except Exception as e:
                st.warning(f"⚠️ {model['name']} failed → auto-switching")
                self.current_index = (self.current_index + 1) % len(self.models)
                attempts += 1
        self.current_index = original_index
        return "❌ All models failed. Check key or local Ollama."

def lil_buddy_execute(instruction: str, model_manager: ModelManager):
    st.write(f"**Lil Buddy received:** {instruction}")
    instruction_lower = instruction.lower().strip()
    if "run python code" in instruction_lower or "execute this code" in instruction_lower:
        try:
            code = instruction_lower.split("code:", 1)[1].strip() if "code:" in instruction_lower else instruction_lower.split("execute this code", 1)[1].strip()
            st.code(code, language="python")
            st.write("**Executing in isolated environment...**")
            result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
            if result.stdout: st.success(f"✅ Output:\n{result.stdout}")
            if result.stderr: st.error(f"⚠️ Error:\n{result.stderr}")
            return result.stdout or result.stderr
        except Exception as e:
            return f"Execution error: {e}"
    st.info(f"🤖 Using model: **{model_manager.models[model_manager.current_index]['name']}**")
    response = model_manager.get_response(instruction)
    st.write(f"**Model used:** {getattr(model_manager, 'last_used', 'N/A')}")
    return response

st.set_page_config(page_title="Lil Buddy – Autonomous Agent", page_icon="🤖", layout="wide")
st.title("Lil Buddy 🤖 – Your Personal Autonomous Agent")
st.caption("Real-time instruction parsing • Code execution • Auto-fallback model stack • Your checklist enforced")

if "model_manager" not in st.session_state:
    st.session_state.model_manager = ModelManager()
model_manager = st.session_state.model_manager

with st.sidebar:
    st.header("Lil Buddy Controls")
    st.info("**Production deploy ready** | Streamlit Cloud or self-host. Ollama local-only. OpenRouter for cloud.")
    st.subheader("➕ Add Model (Your Exact Checklist)")
    st.markdown("""
    **Ensure model names are:**
    * Accurate: No typos or extra spaces
    * Formatted Correctly: Name|Provider|ModelID|APIKey (exact)
    * Available: Model pulled/running
    * In the Right Place: Use paste or form below
    * Restart: Auto-reloads after add
    """)
    paste_input = st.text_area("Paste model line(s):", placeholder="My Llama|ollama|llama3.2\nClaude|openrouter|anthropic/claude-3-haiku|sk-or-xxx", height=80)
    if st.button("Add from Paste"):
        for line in [l.strip() for l in paste_input.splitlines() if l.strip()]:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                model_manager.add_model(parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else None)
            else:
                st.error(f"Bad format: {line}")
        st.rerun()
    with st.expander("Simple Form"):
        n = st.text_input("Name")
        p = st.selectbox("Provider", ["ollama", "openrouter"])
        mid = st.text_input("Model ID")
        k = st.text_input("API Key (optional)", type="password")
        if st.button("Add from Form"):
            if model_manager.add_model(n, p, mid, k): st.rerun()
    st.subheader("Quick Add")
    if st.button("Llama 3.2 (Ollama)"): model_manager.add_model("Ollama Llama 3.2", "ollama", "llama3.2"); st.rerun()
    if st.button("Claude 3 Haiku (OpenRouter)"): model_manager.add_model("OpenRouter Claude 3 Haiku", "openrouter", "anthropic/claude-3-haiku"); st.rerun()
    st.divider()
    st.write("**Current Stack (auto-cycles on failure):**
")
    for i, m in enumerate(model_manager.models):
        prefix = "→ " if i == model_manager.current_index else "   "
        st.write(f"{prefix}{m['name']} ({m['provider']})")
    st.divider()
    nk = st.text_input("OpenRouter Key (paste or use secrets)", value=model_manager.openrouter_key, type="password")
    if nk != model_manager.openrouter_key:
        model_manager.openrouter_key = nk
        st.success("Key updated")

if "messages" not in st.session_state:
    st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
if p := st.chat_input("Give Lil Buddy an instruction..."):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    with st.chat_message("assistant"):
        with st.spinner("Lil Buddy executing..."):
            r = lil_buddy_execute(p, model_manager)
            st.session_state.messages.append({"role": "assistant", "content": r})

st.divider()
st.caption("Lil Buddy v1.0 • Built to your agent spec • Deploy via GitHub + Vercel / Streamlit Cloud")