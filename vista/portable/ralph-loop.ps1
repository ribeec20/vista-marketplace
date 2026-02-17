# Ralph Loop - Simple executor called by ralph.py
# Usage: Called by ralph.py with prompt piped via stdin
#
# Parameters passed via environment:
#   RALPH_MODE         - plan or build
#   RALPH_MAX_ITER     - max iterations (0 = unlimited)
#   RALPH_MODEL        - model to use (opus, sonnet, haiku)
#   RALPH_FEATURE_DIR  - feature directory path
#   RALPH_PROJECT_ROOT - project root path

param()

$Mode = $env:RALPH_MODE
$MaxIterations = [int]$env:RALPH_MAX_ITER
$Model = $env:RALPH_MODEL
$FeatureDir = $env:RALPH_FEATURE_DIR
$ProjectRoot = $env:RALPH_PROJECT_ROOT
$ProgressFile = Join-Path $FeatureDir "progress.txt"

# Read prompt from stdin
$PromptContent = [Console]::In.ReadToEnd()

if ([string]::IsNullOrWhiteSpace($PromptContent)) {
    Write-Host "Error: No prompt content received via stdin" -ForegroundColor Red
    exit 1
}

# Get current branch
Push-Location $ProjectRoot
$CurrentBranch = git branch --show-current
Pop-Location

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Mode:    $Mode"
Write-Host "Model:   $Model"
Write-Host "Branch:  $CurrentBranch"
Write-Host "Feature: $FeatureDir"
if ($MaxIterations -gt 0) {
    Write-Host "Max:     $MaxIterations iterations"
} else {
    Write-Host "Max:     unlimited"
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Push-Location $ProjectRoot

$Iteration = 0

while ($true) {
    if ($MaxIterations -gt 0 -and $Iteration -ge $MaxIterations) {
        Write-Host "`nReached max iterations: $MaxIterations" -ForegroundColor Yellow
        break
    }

    $Iteration++
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

    Write-Host ""
    Write-Host "======================== ITERATION $Iteration ========================" -ForegroundColor Green
    Write-Host "Started: $Timestamp"
    Write-Host ""

    # Run Claude with NO limits - let it run as long as needed
    # Pipe the prompt content directly to claude
    $PromptContent | claude -p `
        --dangerously-skip-permissions `
        --output-format=stream-json `
        --model $Model `
        --verbose

    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "claude exited with code $exitCode" -ForegroundColor Yellow
    }

    # Push changes after each iteration
    git push origin $CurrentBranch 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Creating remote branch..." -ForegroundColor Yellow
        git push -u origin $CurrentBranch 2>$null
    }

    Write-Host ""
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] ITERATION $Iteration complete" -ForegroundColor Green

    # Check if all phases complete (build mode only)
    if ($Mode -eq "build") {
        $ProgressContent = Get-Content $ProgressFile -Raw -ErrorAction SilentlyContinue
        if ($ProgressContent -match "ALL PHASES COMPLETE") {
            Write-Host "`nAll phases complete! Stopping loop." -ForegroundColor Green
            break
        }
    }
}

Pop-Location

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Loop finished after $Iteration iteration(s)"
Write-Host "Check: $ProgressFile"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
