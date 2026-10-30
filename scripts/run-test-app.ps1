$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/course-env.ps1"
& "$PSScriptRoot/../.test-env/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8081 --workers 1 --limit-concurrency 128
