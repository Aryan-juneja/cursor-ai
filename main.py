from dotenv import load_dotenv
from openai import OpenAI
import subprocess
import os
import json
import time
import signal
import threading
from pathlib import Path

# Load environment
load_dotenv()
client = OpenAI()

# Global variables for process management
running_processes = []
context_summary = ""

# ---------- ENHANCED TOOL DEFINITIONS ----------
def run_command(cmd, timeout=60):
    """Run command with timeout to prevent hanging"""
    try:
        # Handle cd commands specially
        if cmd.strip().startswith('cd '):
            path = cmd.strip()[3:].strip()
            try:
                os.chdir(path)
                return f"Changed directory to: {os.getcwd()}"
            except Exception as e:
                return f"Failed to change directory: {e}"
        
        # Check for server commands that should use run_server instead
        server_commands = ['npm start', 'npm run dev', 'yarn start', 'yarn dev', 
                          'flask run', 'python -m flask run', 'python app.py',
                          'node server.js', 'nodemon', 'serve', 'http-server']
        
        if any(server_cmd in cmd.lower() for server_cmd in server_commands):
            return f"⚠️ This looks like a server command. Use 'run_server' tool instead of 'run_command' for: {cmd}"
        
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=os.getcwd()
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds: {cmd}"
    except Exception as e:
        return f"Command failed: {e}"

def create_folder(path):
    """Create folder with better error handling"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Folder created: {os.path.abspath(path)}"
    except Exception as e:
        return f"Error creating folder: {e}"

def write_file(data):
    """Write file with backup and validation"""
    try:
        if isinstance(data, dict):
            path = data.get("path")
            content = data.get("content")
            if not path or content is None:
                return "Invalid input: 'path' and 'content' are required."
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Backup existing file if it exists
            if os.path.exists(path):
                backup_path = f"{path}.backup"
                os.rename(path, backup_path)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File written: {os.path.abspath(path)}"
        else:
            return "Input must be a dictionary with 'path' and 'content'."
    except Exception as e:
        return f"Error writing file: {e}"

def read_file(path):
    """Read file contents"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"File content ({path}):\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"

def list_files(path="."):
    """List files and directories with details"""
    try:
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                items.append(f"📁 {item}/")
            else:
                size = os.path.getsize(item_path)
                items.append(f"📄 {item} ({size} bytes)")
        return f"Contents of {os.path.abspath(path)}:\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing files: {e}"

def run_server(cmd):
    """Start server in background with process tracking"""
    try:
        process = subprocess.Popen(
            cmd, 
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        running_processes.append(process)
        return f"Server started (PID: {process.pid}): {cmd}"
    except Exception as e:
        return f"Error starting server: {e}"

def stop_servers():
    """Stop all running servers"""
    stopped = 0
    for process in running_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
            stopped += 1
        except:
            try:
                process.kill()
                stopped += 1
            except:
                pass
    running_processes.clear()
    return f"Stopped {stopped} running processes"

def get_current_directory():
    """Get current working directory"""
    return f"Current directory: {os.getcwd()}"

def find_files(pattern, path="."):
    """Find files matching pattern"""
    try:
        import glob
        matches = glob.glob(os.path.join(path, pattern), recursive=True)
        if matches:
            return f"Found files matching '{pattern}':\n" + "\n".join(matches)
        else:
            return f"No files found matching '{pattern}'"
    except Exception as e:
        return f"Error finding files: {e}"

def check_port(port):
    """Check if port is in use"""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', int(port)))
            if result == 0:
                return f"Port {port} is in use"
            else:
                return f"Port {port} is available"
    except Exception as e:
        return f"Error checking port: {e}"

# ---------- CONTEXT MANAGEMENT ----------
def should_summarize_context(messages):
    """Check if context should be summarized"""
    total_tokens = sum(len(msg["content"]) for msg in messages)
    return total_tokens > 15000  # Approximate token limit

def summarize_context(messages):
    """Summarize conversation context"""
    try:
        # Keep system prompt and recent messages
        system_msg = messages[0]
        recent_messages = messages[-10:]  # Keep last 10 messages
        
        # Summarize middle messages
        middle_messages = messages[1:-10] if len(messages) > 11 else []
        
        if middle_messages:
            summary_prompt = """Summarize the following conversation between a user and a coding assistant. 
            Focus on: 1) What project was built, 2) Key features implemented, 3) Current state of the project.
            Keep it concise but informative."""
            
            summary_content = "\n".join([msg["content"] for msg in middle_messages])
            
            summary_response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for summarization
                messages=[
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": summary_content}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            summary = summary_response.choices[0].message.content
            summary_msg = {"role": "system", "content": f"CONTEXT SUMMARY: {summary}"}
            
            return [system_msg, summary_msg] + recent_messages
        
        return messages
    except Exception as e:
        print(f"Error summarizing context: {e}")
        return messages

# ---------- ENHANCED TOOL MAPPING ----------
available_tools = {
    "run_command": run_command,
    "create_folder": create_folder,
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_server": run_server,
    "stop_servers": stop_servers,
    "get_current_directory": get_current_directory,
    "find_files": find_files,
    "check_port": check_port,
}

# ---------- ENHANCED SYSTEM PROMPT ----------
SYSTEM_PROMPT = """
You are an advanced terminal-based full-stack coding assistant that helps users build complete applications.

🎯 **ENHANCED CAPABILITIES**
- Build full-stack projects from scratch
- Modify existing codebases intelligently  
- Manage file systems and directories
- Handle server processes and ports
- Debug and troubleshoot issues
- Provide code reviews and improvements

🧠 **EXECUTION CYCLE**
1. **PLAN** - Analyze request and create strategy
2. **ACTION** - Execute one tool at a time  
3. **OBSERVE** - Review results and adapt
4. **REPEAT** - Continue until completion
5. **COMPLETE** - Summarize and offer next steps

🛠️ **AVAILABLE TOOLS**
- `run_command(cmd, timeout=60)` - Execute terminal commands with timeout (NOT for servers)
- `create_folder(path)` - Create directories with parents
- `write_file({path, content})` - Write/update files with backup
- `read_file(path)` - Read file contents
- `list_files(path=".")` - List directory contents with details
- `run_server(cmd)` - Start servers in background (USE THIS for npm start, flask run, etc.)
- `stop_servers()` - Stop all running processes
- `get_current_directory()` - Get current working directory
- `find_files(pattern, path=".")` - Find files by pattern
- `check_port(port)` - Check if port is available

🚨 **CRITICAL: Server Commands**
NEVER use `run_command` for these - they will hang:
- `npm start`, `npm run dev`, `yarn start`
- `flask run`, `python app.py`
- `node server.js`, `nodemon`
- Any command that starts a server

ALWAYS use `run_server` for server commands!

📋 **RESPONSE FORMAT**
Always respond in valid JSON:
```json
{
  "step": "plan|action|observe|complete",
  "content": "Your reasoning or explanation",
  "tool": "tool_name",     // Only for action step
  "input": "tool_input"    // Only for action step
}
```

🔄 **ENHANCED EXAMPLES**

**Creating a Full-Stack App:**
```json
{"step": "plan", "content": "I'll create a full-stack todo app with React frontend and Express backend. First, I'll set up the project structure."}
{"step": "action", "tool": "create_folder", "input": "todo-fullstack"}
{"step": "action", "tool": "get_current_directory", "input": ""}
{"step": "action", "tool": "run_command", "input": "cd todo-fullstack"}
{"step": "action", "tool": "create_folder", "input": "frontend"}
{"step": "action", "tool": "create_folder", "input": "backend"}
```

**Debugging Server Issues:**
```json
{"step": "plan", "content": "User reports server not starting. I'll check the port, review logs, and identify the issue."}
{"step": "action", "tool": "check_port", "input": "3000"}
{"step": "action", "tool": "list_files", "input": "."}
{"step": "action", "tool": "read_file", "input": "package.json"}
```

**Modifying Existing Code:**
```json
{"step": "plan", "content": "User wants to add authentication. I'll first explore the codebase structure."}
{"step": "action", "tool": "find_files", "input": "*.js"}
{"step": "action", "tool": "read_file", "input": "src/App.js"}
{"step": "observe", "content": "Found React app structure. I'll add auth context and login component."}
```

🚨 **ANTI-HANG MEASURES**
- Commands timeout after 60 seconds
- Long-running processes started in background
- Directory navigation handled specially
- Process management for servers

🧠 **SMART CONTEXT MANAGEMENT**
- Automatically summarize when context gets heavy
- Preserve recent interactions and project state
- Maintain performance with large conversations

Always be thorough in planning, precise in actions, and reflective in observations.
"""

# ---------- MAIN LOOP WITH ENHANCEMENTS ----------
def main():
    global context_summary
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    print("\n🚀 Enhanced Terminal Assistant Ready!")
    print("Available commands: build apps, modify code, manage servers, debug issues")
    print("Type 'help' for examples or 'quit' to exit")

    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down gracefully...")
        stop_servers()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            user_input = input("\n📬 User > ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                stop_servers()
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == "help":
                print("""
🔧 **EXAMPLE COMMANDS:**
• "Create a React todo app"
• "Add authentication to my Express server"  
• "Build a dashboard with charts"
• "Fix my server that won't start"
• "Add a new feature to my existing app"
• "Show me the current project structure"
                """)
                continue

            # Check if context should be summarized
            if should_summarize_context(messages):
                print("🔄 Summarizing context to improve performance...")
                messages = summarize_context(messages)

            messages.append({"role": "user", "content": user_input})

            # Main conversation loop
            while True:
                for attempt in range(3):  # Increased retry attempts
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            response_format={"type": "json_object"},
                            messages=messages,
                            temperature=0.3,
                            max_tokens=2000
                        )
                        reply = response.choices[0].message.content
                        parsed = json.loads(reply)
                        break
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON parsing error (attempt {attempt + 1}): {e}")
                        if attempt == 2:
                            print("❌ Failed to get valid JSON after 3 attempts")
                            break
                        time.sleep(1)
                    except Exception as e:
                        print(f"⚠️ API error (attempt {attempt + 1}): {e}")
                        if attempt == 2:
                            print("❌ Failed to get response after 3 attempts")
                            break
                        time.sleep(2)
                else:
                    break

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
                    print(f"📤 OUTPUT: {result}")
                    
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
                        follow_up = input("🛠️ Continue development? (yes/no/status): ").strip().lower()
                        if follow_up in ["no", "n", "done", "finished", "exit"]:
                            print("🎉 Project finalized.")
                            return
                        elif follow_up in ["yes", "y", "sure", "okay", "ok"]:
                            next_change = input("📬 What would you like to add/modify? > ").strip()
                            messages.append({"role": "user", "content": next_change})
                            break
                        elif follow_up == "status":
                            print(f"📁 Current directory: {os.getcwd()}")
                            print(f"🖥️ Running processes: {len(running_processes)}")
                            continue
                        else:
                            print("❓ Please answer 'yes', 'no', or 'status'.")
                    break

                else:
                    print(f"❓ Unknown step: {step}")
                    break

        except KeyboardInterrupt:
            print("\n🛑 Interrupted. Stopping servers...")
            stop_servers()
            break
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            continue

# ---------- RUN ----------
if __name__ == "__main__":
    main()