# EMERGENCY RECOVERY SCRIPT
# This removes the [Book] corruption from all files

param(
    [string]$Path = ".",
    [switch]$DryRun
)

$corruptedFiles = @()
$fixedFiles = @()

Get-ChildItem -Path $Path -Include "*.py","*.md" -Recurse | ForEach-Object {
    $file = $_
    $content = Get-Content $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    
    if ($content -match '\[Book\]') {
        $corruptedFiles += $file.FullName
        
        if (-not $DryRun) {
            # Remove all [Book] markers
            $fixed = $content -replace '\[Book\]', ''
            Set-Content -Path $file.FullName -Value $fixed -Encoding UTF8 -NoNewline
            $fixedFiles += $file.FullName
            Write-Host "[FIXED] $($file.FullName)" -ForegroundColor Green
        } else {
            Write-Host "[FOUND] $($file.FullName)" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n========== SUMMARY ==========" -ForegroundColor Cyan
Write-Host "Corrupted files found: $($corruptedFiles.Count)" -ForegroundColor Yellow
if (-not $DryRun) {
    Write-Host "Files fixed: $($fixedFiles.Count)" -ForegroundColor Green
}
