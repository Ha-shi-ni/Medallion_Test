import os
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

ROOT = Path(__file__).resolve().parent


def run_command(args, env=None):
    completed = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=ROOT,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def get_origin_url():
    code, stdout, stderr = run_command(["git", "remote", "get-url", "origin"])
    if code != 0:
        raise RuntimeError(f"Unable to read origin remote URL: {stderr}")
    return stdout


def create_askpass_script(password: str) -> str:
    temp_dir = tempfile.mkdtemp(prefix="git_askpass_")
    script_path = Path(temp_dir) / "git_askpass.bat"
    script_path.write_text("""@echo off
 echo %GIT_PASSWORD%
""")
    return str(script_path)


def configure_git_identity(name: str, email: str):
    run_command(["git", "config", "--local", "user.name", name])
    run_command(["git", "config", "--local", "user.email", email])


def commit_and_push(name: str, email: str, github_user: str, github_token: str, commit_msg: str):
    configure_git_identity(name, email)

    code, _, stderr = run_command(["git", "add", "."])
    if code != 0:
        raise RuntimeError(f"git add failed: {stderr}")

    code, _, stderr = run_command(["git", "commit", "-m", commit_msg])
    if code != 0:
        if "nothing to commit" in stderr.lower():
            pass
        else:
            raise RuntimeError(f"git commit failed: {stderr}")

    origin_url = get_origin_url()
    if origin_url.startswith("https://"):
        remote_url = origin_url.replace("https://", f"https://{github_user}@")
    else:
        raise RuntimeError("Only HTTPS GitHub remotes are supported by this helper.")

    askpass_script = create_askpass_script(github_token)
    env = os.environ.copy()
    env["GIT_ASKPASS"] = askpass_script
    env["GIT_PASSWORD"] = github_token
    env["GIT_TERMINAL_PROMPT"] = "0"

    code, stdout, stderr = run_command(["git", "push", remote_url, "HEAD"], env=env)
    if code != 0:
        raise RuntimeError(f"git push failed: {stderr or stdout}")

    return stdout or "Push succeeded"


def on_submit():
    name = name_var.get().strip()
    email = email_var.get().strip()
    github_user = github_user_var.get().strip()
    github_token = github_token_var.get().strip()
    commit_msg = commit_msg_var.get().strip() or "Add bronze ingest script and data"

    if not (name and email and github_user and github_token):
        messagebox.showwarning("Missing fields", "All fields are required.")
        return

    try:
        result = commit_and_push(name, email, github_user, github_token, commit_msg)
        messagebox.showinfo("Success", result)
    except Exception as exc:
        messagebox.showerror("Error", str(exc))


root = tk.Tk()
root.title("Git GUI Auth Helper")
root.geometry("520x330")
root.resizable(False, False)

frame = tk.Frame(root, padx=16, pady=16)
frame.pack(fill=tk.BOTH, expand=True)

name_var = tk.StringVar()
email_var = tk.StringVar()
github_user_var = tk.StringVar()
github_token_var = tk.StringVar()
commit_msg_var = tk.StringVar(value="Add bronze ingest script and landing data")

labels = [
    ("Git user name:", name_var),
    ("Git user email:", email_var),
    ("GitHub username:", github_user_var),
    ("GitHub token/password:", github_token_var),
    ("Commit message:", commit_msg_var),
]

for idx, (label_text, var) in enumerate(labels):
    label = tk.Label(frame, text=label_text)
    label.grid(row=idx, column=0, sticky="w", pady=6)
    entry = tk.Entry(frame, textvariable=var, width=48)
    if idx == 3:
        entry.config(show="*")
    entry.grid(row=idx, column=1, pady=6)

button = tk.Button(frame, text="Commit and Push", command=on_submit, width=20)
button.grid(row=len(labels), column=0, columnspan=2, pady=16)

root.mainloop()
