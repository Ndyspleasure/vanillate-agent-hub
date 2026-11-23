param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$')]
    [string]$Project,
    [switch]$Setup
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root '.venv\Scripts\python.exe'
$directory = Join-Path $env:LOCALAPPDATA 'Vanillate\MCP'
$credential = Join-Path $directory ("reader-" + $Project + ".xml")
Push-Location $root
try {
    if ($Setup) {
        $claude = Get-Command claude -ErrorAction Stop
        $token = & $python -m hub.admin issue ("claude-" + $Project) reader $Project
        if ($LASTEXITCODE -ne 0 -or !$token) { throw 'Pembuatan kredensial gagal.' }
        New-Item -ItemType Directory -Force $directory | Out-Null
        ConvertTo-SecureString $token -AsPlainText -Force | Export-Clixml $credential
        Remove-Variable token
        & $claude.Source mcp add --scope user --transport stdio ("vanillate-" + $Project) -- powershell.exe -NoProfile -NonInteractive -File $PSCommandPath -Project $Project
        exit $LASTEXITCODE
    }
    $secure = Import-Clixml $credential
    $env:HUB_TOKEN = [System.Net.NetworkCredential]::new('', $secure).Password
    $env:HUB_PROJECT = $Project
    $env:HUB_URL = 'http://127.0.0.1:8000'
    & $python -m hub.mcp_server
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
