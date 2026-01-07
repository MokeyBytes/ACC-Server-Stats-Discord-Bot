$results = "C:\accserver\server\results"
$python  = "py"
$script  = "C:\accserver\stats\import_acc_results.py"

# Watch for both .json and .JSON (Windows file system is case-insensitive but we want to be explicit)
$fsw = New-Object System.IO.FileSystemWatcher $results, "*.*"
$fsw.IncludeSubdirectories = $false
$fsw.EnableRaisingEvents = $true

# ACC commonly writes temp then renames → catch both Created + Renamed
# Capture variables for use in scriptblock
$action = {
    $full = $Event.SourceEventArgs.FullPath
    $pythonCmd = $Event.MessageData.Python
    $scriptPath = $Event.MessageData.Script

    # Only process files that match your naming pattern (case-insensitive match)
    if ($full -notmatch "(?i)\\\d{6}_\d{6}_(FP|Q|R)\.json$") { return }

    Write-Host "[FILEWATCHER] Processing: $full"

    # Wait until the file is finished writing (no locks)
    for ($i=0; $i -lt 50; $i++) {
        try {
            $stream = [System.IO.File]::Open($full,'Open','Read','None')
            $stream.Close()
            break
        } catch {
            Start-Sleep -Milliseconds 200
        }
    }

    # Run importer (it's idempotent; will skip if already imported)
    Write-Host "[FILEWATCHER] Running import script..."
    & $pythonCmd $scriptPath
}

# Create message data object to pass variables to scriptblock
$messageData = @{
    Python = $python
    Script = $script
}

Register-ObjectEvent $fsw Created -Action $action -MessageData $messageData | Out-Null
Register-ObjectEvent $fsw Renamed -Action $action -MessageData $messageData | Out-Null

Write-Host "Watching $results for new ACC result files..."
while ($true) { Start-Sleep -Seconds 1 }