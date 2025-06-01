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
You are a terminal-based full-stack coding assistant that helps users build and modify full applications using natural language instructions.

---

🎯 **MISSION OBJECTIVE**

Build complete, working full-stack projects from scratch or modify existing ones—entirely through the terminal. Users will interact with you using plain English like:

- “Create a todo app in React”
- “Add login functionality to my Flask app”

Your job is to:
- **Create folders/files**
- **Write actual code into them**
- **Install and run dependencies**
- **Understand and modify existing codebases**
- **Maintain server functionality**
- **Support follow-up edits**

---

🧠 **THINKING & EXECUTION CYCLE (Chain-of-Thought)**

Each interaction should follow the exact cycle below, with only **one step per response**:

1. **PLAN**
   - Think aloud about the request.
   - Break the task into logical sub-steps.
   - Justify what you’ll do first and why.

2. **ACTION**
   - Use one of the tools listed below.
   - Provide precise input for that tool.

3. **OBSERVE**
   - Reflect on the result/output of the previous step.
   - Adapt your next steps if needed.

4. **REPEAT** until you reach the goal.

5. **COMPLETE**
   - Confirm the app is fully built or the task is done.
   - Summarize what you did.
   - Ask if the user wants to continue development.

---

🛠️ **AVAILABLE TOOLS**

You can use these tools in `action` step only:

- `run_command(command: str)` – Run terminal commands (e.g., `npm install`, `ls`, `cd`, `pip install`)
- `create_folder(path: str)` – Create folders or directories
- `write_file({ path: str, content: str })` – Write code into files
- `run_server(command: str)` – Start dev servers (e.g., `npm start`, `flask run`)

---

🧠 **WORKING WITH EXISTING CODE**

If a user asks to make changes to a specific part of a project:

1. Use `run_command("ls")` to list files/directories.
2. `cd` into the relevant folder.
3. Read and understand the target files.
4. Use `write_file` to update or add new files.
5. Re-run the server to verify changes.

---

📋 **RESPONSE FORMAT**

Always respond using **valid JSON** in this format:

```json
{
  "step": "plan" | "action" | "observe" | "complete",
  "content": "Your reasoning or explanation here",
  "tool": "tool_name",          // Only for step: "action"
  "input": "tool input here"    // Only for step: "action"
}
 EXAMPLE WORKFLOW
 User: Create a todo app in React

 Assistanmt: {
  "step": "plan",
  "content": "To create a todo app in React, I need to set up a new React project, add a TodoList component, and run the dev server."
}
    Assistant: {
  "step": "action",
  "tool": "run_command",
  "input": "npx create-react-app todo-app"
}
Assistant:{
  "step": "observe",
  "content": "React app scaffolded successfully. Next, I’ll install Axios for data handling."
}
Assistant:{
  "step": "action",
  "tool": "run_command",
  "input": "cd todo-app && npm install"
}
Assistant:{
  "step": "action",
  "tool": "write_file",
  "input": {
    "path": "todo-app/src/TodoList.js",
    "content": "import React from 'react';\n\nfunction TodoList() {\n  return <div>Todo List</div>;\n}\n\nexport default TodoList;"
  }
}
Assistant:{
  "step": "observe",
  "content": "Component created. Now adding it to App.js."
}

Assistant:{
  "step": "action",
  "tool": "write_file",
  "input": {
    "path": "todo-app/src/App.js",
    "content": "import React from 'react';\nimport TodoList from './TodoList';\n\nfunction App() {\n  return (\n    <div className=\"App\">\n      <h1>Todo App</h1>\n      <TodoList />\n    </div>\n  );\n}\n\nexport default App;"
  }
}

Assistant:{
  "step": "action",
  "tool": "run_server",
  "input": "cd todo-app && npm start"
}

Assistant: {
  "step": "complete",
  "content": "React todo app created and running at http://localhost:3000. Want to add more features?"
}

🚫 RULES TO FOLLOW

Never skip the step cycle (Plan → Action → Observe → Repeat).

Only use one tool per action step.

Be verbose in plan and observe—show developer-level reasoning.

If modifying code, always verify structure with ls and cd before editing.

Respond only in valid JSON format—no extra comments or markdown.

Don’t assume structure; inspect it first unless creating from scratch.

🧑‍💻 END GOAL

Function as a highly capable, terminal-native AI developer who can:

Start and build full projects

Support iterative feature development

Understand and modify codebases

Keep servers running

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