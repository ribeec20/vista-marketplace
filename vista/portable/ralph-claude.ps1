# Ralph Loop Runner - Portable Edition (PowerShell) - Claude Code Version
# Usage: .\ralph-claude.ps1
# Interactive menu to select feature, mode, and model
# Uses the "claude" CLI (Claude Code) instead of OpenCode
#
# CLI Reference: https://code.claude.com/docs/en/cli-reference
# Key flags used:
#   -p, --print          Print response without interactive mode (non-interactive)
#   --model              Model alias: sonnet, opus, haiku
#   --allowedTools       Pre-authorize tools without permission prompts
#   --output-format      Output format: text, json, stream-json
#   --verbose            Enable verbose logging for debugging
#   --dangerously-skip-permissions  Skip all permission prompts (use with caution)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FeaturesDir = Join-Path $ProjectRoot ".claude\features"
$TemplatesDir = Join-Path $ScriptDir "templates"

function Get-ClaudeModels {
    # Claude Code supports full model identifiers via --model flag
    # Using explicit model IDs for Claude 4.5 family
    $models = @(
        "claude-sonnet-4-5",      # Claude Sonnet 4.5 - balanced performance
        "claude-opus-4-5",         # Claude Opus 4.5 - most capable
        "claude-4-5-haiku"         # Claude Haiku 3.5 - fast & efficient
    )

    Write-Host "Available Claude Code models:" -ForegroundColor Green
    return $models
}

function Write-Header {
    Write-Host ""
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "      RALPH LOOP RUNNER - PORTABLE (CLAUDE CODE)" -ForegroundColor Cyan
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-MenuHeader {
    param([string]$Title)
    Write-Host $Title -ForegroundColor Yellow
    Write-Host "----------------------------------------------------"
}

function Get-Features {
    $features = @()
    if (-not (Test-Path $FeaturesDir)) {
        return $features
    }
    Get-ChildItem -Path $FeaturesDir -Directory | ForEach-Object {
        $dirName = $_.Name

        $specsPath = Join-Path $_.FullName "specs"
        $planPath = Join-Path $_.FullName "IMPLEMENTATION_PLAN.md"
        $promptPath = Join-Path $_.FullName "PROMPT_build.md"

        if ((Test-Path $specsPath) -or (Test-Path $planPath) -or (Test-Path $promptPath)) {
            $features += $dirName
        }
    }
    return $features
}

function Select-Option {
    param(
        [string]$Prompt,
        [string[]]$Options
    )

    if ($Options.Count -eq 0) {
        Write-Host "No options available!" -ForegroundColor Red
        return $null
    }

    Write-MenuHeader $Prompt
    for ($i = 0; $i -lt $Options.Count; $i++) {
        Write-Host "  " -NoNewline
        Write-Host "$($i + 1)" -ForegroundColor Green -NoNewline
        Write-Host ") $($Options[$i])"
    }
    Write-Host ""

    while ($true) {
        $choice = Read-Host "Enter choice [1-$($Options.Count)]"
        if ($choice -match '^\d+$') {
            $num = [int]$choice
            if ($num -ge 1 -and $num -le $Options.Count) {
                return $Options[$num - 1]
            }
        }
        Write-Host "Invalid choice. Please enter a number between 1 and $($Options.Count)" -ForegroundColor Red
    }
}

function New-Feature {
    Write-Host ""
    $featureName = Read-Host "Enter feature name (e.g., my_feature)"

    if ([string]::IsNullOrWhiteSpace($featureName)) {
        Write-Host "Feature name cannot be empty" -ForegroundColor Red
        return $null
    }

    # Sanitize feature name
    $featureName = $featureName.ToLower() -replace '\s+', '_'

    # Ensure .claude/features directory exists
    if (-not (Test-Path $FeaturesDir)) {
        New-Item -ItemType Directory -Path $FeaturesDir -Force | Out-Null
    }

    $featureDir = Join-Path $FeaturesDir $featureName

    if (Test-Path $featureDir) {
        Write-Host "Feature '$featureName' already exists!" -ForegroundColor Red
        return $null
    }

    Write-Host "Creating feature: $featureName" -ForegroundColor Blue

    # Create directory structure
    New-Item -ItemType Directory -Path $featureDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $featureDir "specs") -Force | Out-Null

    # Get current date
    $currentDate = Get-Date -Format "yyyy-MM-dd"

    # Get project name
    try {
        $gitRoot = git rev-parse --show-toplevel 2>$null
        $projectName = Split-Path -Leaf $gitRoot
    } catch {
        $projectName = Split-Path -Leaf (Get-Location)
    }

    # Copy and process templates
    Get-ChildItem -Path $TemplatesDir -File | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        $content = $content -replace '\{\{FEATURE_NAME\}\}', $featureName
        $content = $content -replace '\{\{FEATURE_DIR\}\}', $featureDir
        $content = $content -replace '\{\{PROJECT_NAME\}\}', $projectName
        $content = $content -replace '\{\{DATE\}\}', $currentDate

        $destName = $_.Name
        if ($destName -eq "progress_template.txt") {
            $destName = "progress.txt"
        }

        $destPath = Join-Path $featureDir $destName
        Set-Content -Path $destPath -Value $content -NoNewline
    }

    # Create specs README
    $specsReadme = "# Feature Specification: $featureName`n`nAdd your specification files here.`n"
    Set-Content -Path (Join-Path $featureDir "specs\README.md") -Value $specsReadme

    Write-Host "Feature '$featureName' created successfully!" -ForegroundColor Green
    Write-Host "  Directory: $featureDir"
    Write-Host "  Next steps:"
    Write-Host "    1. Add specification files to $featureDir\specs\"
    Write-Host "    2. Run .\ralph-claude.ps1 and select '$featureName'"
    Write-Host ""

    return $featureName
}

function Get-SmartPromptContent {
    param(
        [string]$FeatureDir,
        [string]$Mode
    )

    $promptFileName = if ($Mode -eq "plan") { "PROMPT_plan.md" } else { "PROMPT_build.md" }
    $localPath = Join-Path $FeatureDir $promptFileName
    $templatePath = Join-Path $TemplatesDir $promptFileName

    # Determine which file to use
    $sourcePath = $null
    $source = $null
    if (Test-Path $localPath) {
        $sourcePath = $localPath
        $source = "Local"
    } elseif (Test-Path $templatePath) {
        $sourcePath = $templatePath
        $source = "Template"
    } else {
        return $null
    }

    # Read and substitute variables
    $content = Get-Content $sourcePath -Raw
    $featureName = Split-Path -Leaf $FeatureDir
    $currentDate = Get-Date -Format "yyyy-MM-dd"

    try {
        $gitRoot = git rev-parse --show-toplevel 2>$null
        $projectName = Split-Path -Leaf $gitRoot
    } catch {
        $projectName = "project"
    }

    $content = $content -replace '\{\{FEATURE_NAME\}\}', $featureName
    $content = $content -replace '\{\{FEATURE_DIR\}\}', $FeatureDir
    $content = $content -replace '\{\{PROJECT_NAME\}\}', $projectName
    $content = $content -replace '\{\{DATE\}\}', $currentDate

    return @{
        Content = $content
        Source = $source
        SourcePath = $sourcePath
    }
}

function Invoke-Claude {
    param(
        [string]$PromptContent,
        [string]$SourcePath
    )

    $OldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    try {
        # Run from ProjectRoot so claude has access to the full codebase
        Push-Location $ProjectRoot

        Write-Host ""
        Write-Host "Starting Claude..." -ForegroundColor Blue
        Write-Host "Prompt: $SourcePath" -ForegroundColor DarkGray
        Write-Host "----------------------------------------------------"
        Write-Host ""

        # Pipe prompt content directly to claude
        # Match exact pattern from loop.ps1
        $PromptContent | claude -p `
            --dangerously-skip-permissions `
            --output-format=stream-json `
            --model opus `
            --verbose
        $exitCode = $LASTEXITCODE

        Pop-Location

        Write-Host ""
        Write-Host "----------------------------------------------------"
        Write-Host "Claude finished (exit code: $exitCode)" -ForegroundColor Blue
        Write-Host ""

        $ErrorActionPreference = $OldErrorActionPreference
        return $exitCode
    } catch {
        $ErrorActionPreference = $OldErrorActionPreference
        Write-Host "Error invoking claude: $_" -ForegroundColor Red
        return 1
    } finally {
        Pop-Location -ErrorAction SilentlyContinue
    }
}

function Start-Loop {
    param(
        [string]$FeatureDir,
        [string]$Mode,
        [string]$Model,
        [int]$MaxIterations = 0
    )

    $promptInfo = Get-SmartPromptContent -FeatureDir $FeatureDir -Mode $Mode

    if (-not $promptInfo) {
        Write-Host "Error: Prompt file not found in feature directory or templates" -ForegroundColor Red
        return
    }

    try {
        $currentBranch = git branch --show-current 2>$null
        if (-not $currentBranch) { $currentBranch = "(not a git repo)" }
    } catch {
        $currentBranch = "(not a git repo)"
    }

    Write-Host ""
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "  Feature: " -NoNewline; Write-Host (Split-Path -Leaf $FeatureDir) -ForegroundColor Green
    Write-Host "  Mode:    " -NoNewline; Write-Host $Mode -ForegroundColor Green
    Write-Host "  Model:   " -NoNewline; Write-Host $Model -ForegroundColor Green

    if ($promptInfo.Source -eq "Template") {
        Write-Host "  Prompt:  " -NoNewline; Write-Host "$(Split-Path -Leaf $promptInfo.SourcePath) (Template Fallback)" -ForegroundColor Yellow
    } else {
        Write-Host "  Prompt:  " -NoNewline; Write-Host (Split-Path -Leaf $promptInfo.SourcePath) -ForegroundColor Green
    }

    Write-Host "  Branch:  " -NoNewline; Write-Host $currentBranch -ForegroundColor Green
    if ($MaxIterations -gt 0) {
        Write-Host "  Max:     " -NoNewline; Write-Host "$MaxIterations iterations" -ForegroundColor Green
    }
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host ""

    $iteration = 0

    while ($true) {
        if ($MaxIterations -gt 0 -and $iteration -ge $MaxIterations) {
            Write-Host "Reached max iterations: $MaxIterations" -ForegroundColor Yellow
            break
        }

        # Run Claude Code with the prompt content (non-interactive, one-shot)
        $exitCode = Invoke-Claude -PromptContent $promptInfo.Content -SourcePath $promptInfo.SourcePath
        if ($exitCode -ne 0) {
            Write-Host "claude exited with code $exitCode" -ForegroundColor Yellow
        }

        # Try to push if in a git repo
        try {
            git push origin $currentBranch 2>$null
        } catch {
            try {
                Write-Host "Creating remote branch..." -ForegroundColor Yellow
                git push -u origin $currentBranch 2>$null
            } catch { }
        }

        $iteration++
        Write-Host ""
        Write-Host "======================== LOOP $iteration ========================" -ForegroundColor Cyan
        Write-Host ""
    }
}

function Start-SingleIteration {
    param(
        [string]$FeatureDir,
        [string]$Mode,
        [string]$Model
    )

    $promptInfo = Get-SmartPromptContent -FeatureDir $FeatureDir -Mode $Mode

    if (-not $promptInfo) {
        Write-Host "Error: Prompt file not found in feature directory or templates" -ForegroundColor Red
        return
    }

    try {
        $currentBranch = git branch --show-current 2>$null
        if (-not $currentBranch) { $currentBranch = "(not a git repo)" }
    } catch {
        $currentBranch = "(not a git repo)"
    }

    Write-Host ""
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "  Feature: " -NoNewline; Write-Host (Split-Path -Leaf $FeatureDir) -ForegroundColor Green
    Write-Host "  Mode:    " -NoNewline; Write-Host "$Mode (single iteration)" -ForegroundColor Green
    Write-Host "  Model:   " -NoNewline; Write-Host $Model -ForegroundColor Green

    if ($promptInfo.Source -eq "Template") {
        Write-Host "  Prompt:  " -NoNewline; Write-Host "$(Split-Path -Leaf $promptInfo.SourcePath) (Template Fallback)" -ForegroundColor Yellow
    } else {
        Write-Host "  Prompt:  " -NoNewline; Write-Host (Split-Path -Leaf $promptInfo.SourcePath) -ForegroundColor Green
    }

    Write-Host "  Branch:  " -NoNewline; Write-Host $currentBranch -ForegroundColor Green
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host ""

    $exitCode = Invoke-Claude -PromptContent $promptInfo.Content -SourcePath $promptInfo.SourcePath
    if ($exitCode -ne 0) {
        Write-Host "claude exited with code $exitCode" -ForegroundColor Yellow
    }

    try {
        git push origin $currentBranch 2>$null
    } catch {
        try {
            git push -u origin $currentBranch 2>$null
        } catch { }
    }

    Write-Host ""
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "Single iteration complete" -ForegroundColor Green
    Write-Host "  Review output, make edits, then run again"
    Write-Host "====================================================" -ForegroundColor Cyan
}

# Main
function Main {
    Write-Header

    # Step 1: Select or create feature
    $features = @(Get-Features)
    $features += "[Create New Feature]"

    $selected = Select-Option "Step 1: Select Feature" $features

    if ($selected -eq "[Create New Feature]") {
        $newFeature = New-Feature
        if (-not $newFeature) {
            return
        }
        $features = @(Get-Features)
        if ($features.Count -eq 0) {
            Write-Host "No features found. Please create a feature first." -ForegroundColor Red
            return
        }
        $selected = Select-Option "Select the new feature" $features
    }

    $featureName = $selected
    $featureDir = Join-Path $FeaturesDir $featureName

    Write-Host "Selected: $featureName" -ForegroundColor Green
    Write-Host ""

    # Step 2: Select mode
    $modes = @("plan", "build")
    $mode = Select-Option "Step 2: Select Mode" $modes
    Write-Host "Selected: $mode" -ForegroundColor Green
    Write-Host ""

    # Step 3: Select model
    $availableModels = Get-ClaudeModels
    $model = Select-Option "Step 3: Select Model" $availableModels
    Write-Host "Selected: $model" -ForegroundColor Green
    Write-Host ""

    # Step 4: Select run type
    $runTypes = @("Single Iteration", "Continuous Loop", "Limited Loop (set max)")
    $runType = Select-Option "Step 4: Run Type" $runTypes

    switch ($runType) {
        "Single Iteration" {
            Start-SingleIteration -FeatureDir $featureDir -Mode $mode -Model $model
        }
        "Continuous Loop" {
            Start-Loop -FeatureDir $featureDir -Mode $mode -Model $model -MaxIterations 0
        }
        "Limited Loop (set max)" {
            $maxIter = Read-Host "Enter max iterations"
            if (-not ($maxIter -match '^\d+$')) {
                $maxIter = 5
            }
            Start-Loop -FeatureDir $featureDir -Mode $mode -Model $model -MaxIterations ([int]$maxIter)
        }
    }
}

Main

# Ensure the script exits cleanly (useful when launched from a new terminal window)
exit 0