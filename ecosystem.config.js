const path = require("node:path");

module.exports = {
  apps: [{
    name: "vanillate-agent-hub",
    cwd: __dirname,
    script: path.join(__dirname, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
    interpreter: "none",
    args: ["-m", "uvicorn", "hub.api:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"],
    instances: 1,
    exec_mode: "fork",
    restart_delay: 3000,
    max_restarts: 8
  }]
};
