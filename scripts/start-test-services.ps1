$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
$mysql = (Get-ChildItem "$root/.local/mysql" -Recurse -Filter mysqld.exe | Select-Object -First 1).FullName
$redis = (Get-ChildItem "$root/.local/redis" -Recurse -Filter redis-server.exe | Select-Object -First 1).FullName
if (!$mysql -or !$redis) { throw 'Extract MySQL and Redis under .local first.' }
$data = "$root/.local/mysql-data"
if (!(Test-Path "$data/mysql")) {
    & $mysql --initialize-insecure "--basedir=$(Split-Path (Split-Path $mysql))" "--datadir=$data" --console
    if ($LASTEXITCODE) { throw 'MySQL initialization failed' }
}
function Test-Port($port) {
    $client = [Net.Sockets.TcpClient]::new()
    try { $client.Connect('127.0.0.1', $port); return $true } catch { return $false } finally { $client.Dispose() }
}
if (!(Test-Port 3307)) {
    Start-Process $mysql -WindowStyle Hidden -ArgumentList @("--datadir=`"$data`"", '--port=3307', '--bind-address=127.0.0.1', '--mysqlx=0', '--console') -RedirectStandardOutput "$root/.local/mysql.stdout.log" -RedirectStandardError "$root/.local/mysql.stderr.log"
}
if (!(Test-Port 6380)) {
    Start-Process $redis -WorkingDirectory (Split-Path $redis) -WindowStyle Hidden -ArgumentList @('--bind', '127.0.0.1', '--port', '6380', '--appendonly', 'yes') -RedirectStandardOutput "$root/.local/redis.stdout.log" -RedirectStandardError "$root/.local/redis.stderr.log"
}
for ($i=0; $i -lt 60; $i++) {
    if ((Test-Port 3307) -and (Test-Port 6380)) { Write-Output 'MySQL 3307 / Redis 6380 ready'; exit 0 }
    Start-Sleep -Seconds 1
}
throw 'Services did not become ready; inspect .local/*.log'
