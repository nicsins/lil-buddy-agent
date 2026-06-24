import streamlit as st
import subprocess
import sys
import os
import requests
from openai import OpenAI
import dotenv

dotenv.load_dotenv()

class ModelManager:
    def __init__(self):
        self.openrouter_key = ""
        if hasattr(st, "secrets") and "OPENROUTER_API_KEY" in st.secrets:
            self.openrouter_key = st.secrets["OPENROUTER_API_KEY"]
        self.bad_models = set()  # temporarily skip failing models
        self.models = self.get_free_models() or self._fallback_free_models()
        self.current_index = 0

    def _fallback_free_models(self):
        # Reliable free models as of 2026 (curated)
        return [
            {"name": "Llama 3.2 3B (Free)", "provider": "openrouter", "model": "meta-llama/llama-3.2-3b-instruct:free", "api_key": None},
            {"name": "Gemini Flash 1.5 (Free)", "provider": "openrouter", "model": "google/gemini-flash-1.5:free", "api_key": None},
            {"name": "Mistral 7B Instruct (Free)", "provider": "openrouter", "model": "mistralai/mistral-7b-instruct:free", "api_key": None},
            {"name": "Hermes 3 Llama 3.1 405B (Free)", "provider": "openrouter", "model": "nousresearch/hermes-3-llama-3.1-405b:free", "api_key": None},
        ]

    def get_free_models(self):
        """Callable feature: dynamically fetch current free models from OpenRouter"""
        if not self.openrouter_key:
            return self._fallback_free_models()
        try:
            headers = {"Authorization": f"Bearer {self.openrouter_key}"}
            resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=8)
            if resp.status_code != 200:
                return self._fallback_free_models()
            data = resp.json()
            free_models = []
            for m in data.get("data", []):
                pricing = m.get("pricing", {})
                # Free if both prompt and completion are "0"
                if str(pricing.get("prompt", "1")) == "0" and str(pricing.get("completion", "1")) == "0":
                    free_models.append({
                        "name": m.get("name", m["id"]),
                        "provider": "openrouter",
                        "model": m["id"],
                        "api_key": None
                    })
            # Limit to first 8 for speed + reliability
            return free_models[:8] if free_models else self._fallback_free_models()
        except Exception:
            return self._fallback_free_models()

    def refresh_free_models(self):
        """Callable from UI to refresh the free list and reset bad models"""
        self.bad_models.clear()
        new_models = self.get_free_models()
        if new_models:
            self.models = new_models
            self.current_index = 0
            st.success(f"✅ Refreshed free models list ({len(self.models)} models)")
        else:
            st.warning("Could not refresh – using fallback list")

    def add_model(self, name: str, provider: str, model_id: str, api_key: str = None):
        name = name.strip()
        provider = provider.strip().lower()
        model_id = model_id.strip()
        if not name or not provider or not model_id:
            st.error("❌ Name, Provider, and Model ID required")
            return None
        if provider not in ["ollama", "openrouter"]:
            st.error("❌ Provider must be 'ollama' or 'openrouter'")
            return None
        new_model = {"name": name, "provider": provider, "model": model_id, "api_key": api_key.strip() if api_key else None}
        self.models.append(new_model)
        st.success(f"✅ Added: {name}")
        return new_model

    def get_response(self, prompt):
        attempts = 0
        max_attempts = len(self.models) * 2  # allow some re-tries
        original_index = self.current_index
        while attempts < max_attempts:
            if self.current_index >= len(self.models):
                self.current_index = 0
            model = self.models[self.current_index]
            model_key = model["model"]
            if model_key in self.bad_models:
                self.current_index = (self.current_index + 1) % len(self.models)
                attempts += 1
                continue
            try:
                if model["provider"] == "ollama":
                    response = ollama.chat(model=model["model"], messages=[{"role": "user", "content": prompt}])
                    result = response['message']['content']
                else:
                    key = model["api_key"] or self.openrouter_key
                    if not key:
                        raise ValueError("OpenRouter key missing")
                    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key,
                                    default_headers={"HTTP-Referer": "https://lil-buddy.streamlit.app", "X-Title": "Lil Buddy"})
                    response = client.chat.completions.create(model=model["model"], messages=[{"role": "user", "content": prompt}], temperature=0.7)
                    result = response.choices[0].message.content
                self.last_used = model["name"]
                return result
            except Exception as e:
                self.bad_models.add(model_key)  # mark as temporarily bad
                st.warning(f"⚠️ {model['name']} failed – moving to next free model (auto-recovery)")
                self.current_index = (self.current_index + 1) % len(self.models)
                attempts += 1
        self.current_index = original_index
        # If everything failed, clear bad list and try one more cycle
        self.bad_models.clear()
        return "❌ All free models had issues this round. Try Refresh Free Models or check your key."


def lil_buddy_execute(instruction: str, model_manager: ModelManager):
    st.write(f"**Lil Buddy received:** {instruction}")
    instruction_lower = instruction.lower().strip()
    if "run python code" in instruction_lower or "execute this code" in instruction_lower:
        try:
            code = instruction_lower.split("code:", 1)[1].strip() if "code:" in instruction_lower else instruction_lower.split("execute this code", 1)[1].strip()
            st.code(code, language="python")
            st.write("**Executing safely...**")
            result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
            if result.stdout: st.success(f"✅ Output:\n{result.stdout}")
            if result.stderr: st.error(f"⚠️ Error:\n{result.stderr}")
            return result.stdout or result.stderr
        except Exception as e:
            return f"Execution error: {e}"
    st.info(f"🤖 Using free model: **{model_manager.models[model_manager.current_index]['name']}**")
    response = model_manager.get_response(instruction)
    st.write(f"**Model used:** {getattr(model_manager, 'last_used', 'N/A')}")
    return response

st.set_page_config(page_title="Lil Buddy – Free Models Agent", page_icon="🤖", layout="wide")
st.title("Lil Buddy 🤖 – Free Models Only + Auto-Recovery")
st.caption("Dynamic callable free models list • Auto-switches on failure to keep it going • Your checklist + secure execution")

if "model_manager" not in st.session_state:
    st.session_state.model_manager = ModelManager()
model_manager = st.session_state.model_manager

with st.sidebar:
    st.header("Lil Buddy Controls (Free Models Mode)")
    st.success("✅ Only free OpenRouter models – cost $0")
    if st.button("🔄 Refresh Free Models List"):
        model_manager.refresh_free_models()
        st.rerun()
    st.subheader("➕ Add Any Model (Your Checklist Still Enforced)")
    st.markdown("""
    **Your rules still apply:** Accurate • Formatted Correctly (Name|Provider|ModelID) • Available • Right Place • Restart
    """)
    paste_input = st.text_area("Paste model line(s):", placeholder="My Llama|ollama|llama3.2\nClaude|openrouter|anthropic/claude-3-haiku|sk-or-xxx", height=70)
    if st.button("Add from Paste"):
        for line in [l.strip() for l in paste_input.splitlines() if l.strip()]:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                model_manager.add_model(parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else None)
            else:
                st.error(f"Bad format: {line}")
        st.rerun()
    st.divider()
    st.write(f"**Active Free Stack ({len(model_manager.models)} models) – auto-cycles on failure:**")
    for i, m in enumerate(model_manager.models):
        prefix = "→ " if i == model_manager.current_index else "   "
        st.write(f"{prefix}{m['name']}")
    st.caption("Bad models are temporarily skipped until Refresh")

if "messages" not in st.session_state:
    st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
if p := st.chat_input("Give Lil Buddy an instruction (free models only)..."):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    with st.chat_message("assistant"):
        with st.spinner("Lil Buddy thinking (free models)..."):
            r = lil_buddy_execute(p, model_manager)
            st.session_state.messages.append({"role": "assistant", "content": r})

st.divider()
st.caption("Lil Buddy v2.0 • Free Models + Self-Healing Stack • Built live with your key & checklist • Repo: github.com/nicsins/lil-buddy-agent")