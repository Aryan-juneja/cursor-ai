from dotenv import load_dotenv
from openai import OpenAI
import subprocess
import os
import json
import time

# Load environment
load_dotenv()
client = OpenAI()

# ---------- TOOL DEFINITIONS ----------
def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Command failed: {e}"

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {e}"

def write_file(data):
    try:
        if isinstance(data, dict):
            path = data.get("path")
            content = data.get("content")
            if not path or not content:
                return "Invalid input: 'path' and 'content' are required."
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File written: {path}"
        else:
            return "Input must be a dictionary with 'path' and 'content'."
    except Exception as e:
        return f"Error writing file: {e}"

def run_server(cmd):
    try:
        subprocess.Popen(cmd, shell=True)
        return f"Server started with: {cmd}"
    except Exception as e:
        return f"Error starting server: {e}"

# ---------- TOOL MAPPING ----------
available_tools = {
    "run_command": run_command,
    "create_folder": create_folder,
    "write_file": write_file,
    "run_server": run_server,
}

# ---------- SYSTEM PROMPT ----------
SYSTEM_PROMPT = """
You are a terminal-based full-stack coding assistant that helps users build and modify full applications from natural language.

🌟 YOUR CORE MISSION:
Turn user commands like "create a todo app in React" or "add login functionality to my Flask app" into fully working codebases with actual file structures, real code, and live dev servers.

🛠️ AVAILABLE TOOLS:
You can use the following tools to act:
- run_command(command: str)
- create_folder(path: str)
- write_file({ path: str, content: str })
- run_server(command: str)

🔄 THINKING AND EXECUTION FLOW:
Follow a strict Chain-of-Thought (CoT) reasoning loop to break down tasks step-by-step:

1. **PLAN**:
   - Think aloud about the goal.
   - Break it into sub-steps logically.
   - Explain why each step is necessary.
   - Decide the first next action.

2. **ACTION**:
   - Pick exactly ONE tool from the list.
   - Use it with clear and minimal input to make progress.

3. **OBSERVE**:
   - Reflect on the result of the last action.
   - Adjust plan if needed.
   - Justify the next action.

4. **REPEAT** until the project is complete and the server is running.

📆 ALWAYS RESPOND IN VALID JSON:
```json
{
  "step": "plan" | "action" | "observe" | "complete",
  "content": "Your reasoning or explanation",
  "tool": "tool_name",           // only in action
  "input": tool_input_data       // only in action
}
```

📆 COMPLETION:
Once the server runs or project is fully built, set "step": "complete" and summarize what you created. Then ask if the user wants to make any more changes.

🧠 NOTES:
- Only one action per cycle.
- Explain every decision with developer-style reasoning.
- Parse existing files logically to guide follow-up actions.
- If no clear action is possible, continue thinking.

🌟 Your goal is to act like a real full-stack developer working step-by-step via terminal tools.
"""

# ---------- MAIN LOOP ----------
def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("\n🚀 Terminal Assistant Ready!")
    print("Ask me to build an app (e.g. 'todo app in React' or 'dashboard in Streamlit')")

    while True:
        try:
            user_input = input("\n📬 User > ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break

            messages.append({"role": "user", "content": user_input})

            while True:
                for attempt in range(2):
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            response_format={"type": "json_object"},
                            messages=messages,
                            temperature=0.3
                        )
                        reply = response.choices[0].message.content
                        parsed = json.loads(reply)
                        break
                    except Exception as e:
                        if attempt == 1:
                            print(f"❌ Failed to get valid JSON after retry: {e}")
                            return
                        time.sleep(1)

                print(f"\n🤖 Assistant: {reply}")
                messages.append({"role": "assistant", "content": reply})

                step = parsed.get("step")

                if step == "plan":
                    print(f"🔠 PLAN: {parsed['content']}")
                    continue

                elif step == "action":
                    tool_name = parsed.get("tool")
                    tool_input = parsed.get("input")
                    print(f"⚙️ ACTION: {tool_name} → {tool_input}")
                    if tool_name not in available_tools:
                        print(f"❌ Unknown tool: {tool_name}")
                        break

                    result = available_tools[tool_name](tool_input)
                    messages.append({
                        "role": "user",
                        "content": json.dumps({
                            "step": "tool_output",
                            "tool": tool_name,
                            "input": tool_input,
                            "output": result
                        })
                    })
                    continue

                elif step == "observe":
                    print(f"👁️ OBSERVE: {parsed['content']}")
                    continue

                elif step == "complete":
                    print(f"✅ COMPLETE: {parsed['content']}")
                    print("=" * 60)

                    while True:
                        follow_up = input("🛠️ Do you want to make any more changes? (yes/no): ").strip().lower()
                        if follow_up in ["no", "n", "i'm okay", "i am okay", "done", "finished", "exit"]:
                            print("🎉 Project finalized. Exiting.")
                            return
                        elif follow_up in ["yes", "y", "sure", "okay", "ok"]:
                            print("🔁 Okay, what else would you like to modify or add?")
                            next_change = input("📬 User > ").strip()
                            messages.append({"role": "user", "content": next_change})
                            break
                        else:
                            print("❓ Please answer 'yes' or 'no'.")

                else:
                    print(f"❓ Unknown step: {step}")
                    break

        except KeyboardInterrupt:
            print("\n👋 Interrupted. Exiting.")
            break
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            continue

# ---------- RUN ----------
if __name__ == "__main__":
    main()