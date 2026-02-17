# Ralph Loop Runner - Portable Edition (PowerShell)
# Usage: .\ralph.ps1
# Interactive menu to select feature, mode, and model

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FeaturesDir = Join-Path $ProjectRoot ".claude\features"
$TemplatesDir = Join-Path $ScriptDir "templates"

function Get-OpenCodeModels {
    # Save old preference and set to Continue to avoid crashing on stderr output (INFO logs)
    $OldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    
    try {
        # Get all available models from all providers
        # We use 2>&1 to capture everything, then filter out the logs
        $modelOutput = opencode models 2>&1
        
        $models = @()
        
        $modelOutput | ForEach-Object {
            $line = $_.ToString().Trim()
            
            # Filter out log messages and headers
            if ($line -and 
                $line -notmatch '^(INFO|DEBUG|WARN|ERROR|FATAL|CRITICAL|Available|Models:|---|\s*$)' -and
                $line -match '^[\w\-]+/[\w\-\.]+') {
                $models += $line
            }
        }
        
        # Restore preference
        $ErrorActionPreference = $OldErrorActionPreference
        
        if ($models.Count -eq 0) {
            Write-Host "Warning: No models found from OpenCode" -ForegroundColor Yellow
            Write-Host "Make sure providers are configured with: opencode auth list" -ForegroundColor Yellow
            Write-Host "Falling back to default models" -ForegroundColor Yellow
            return @("anthropic/claude-sonnet-4", "anthropic/claude-opus-4", "anthropic/claude-haiku-4")
        }
        
        Write-Host "Found $($models.Count) models from all providers" -ForegroundColor Green
        return $models
    } catch {
        # Restore preference in case of error
        $ErrorActionPreference = $OldErrorActionPreference
        
        Write-Host "Error retrieving models: $_" -ForegroundColor Red
        Write-Host "Falling back to default models" -ForegroundColor Yellow
        return @("anthropic/claude-sonnet-4", "anthropic/claude-opus-4", "anthropic/claude-haiku-4")
    }
}

function Write-Header {
    Write-Host ""
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "           RALPH LOOP RUNNER - PORTABLE" -ForegroundColor Cyan
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
    Write-Host "    2. Run .\ralph.ps1 and select '$featureName'"
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
    
    if (Test-Path $localPath) {
        return @{
            Content = Get-Content $localPath -Raw
            Source = "Local"
            Path = $localPath
        }
    } elseif (Test-Path $templatePath) {
        $content = Get-Content $templatePath -Raw
        
        # Replacements
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
            Source = "Template"
            Path = $templatePath
        }
    }
    
    return $null
}

function Invoke-OpenCode {
    param(
        [string]$PromptText,
        [string]$Model
    )

    # Write prompt to a temp file for complex/multi-line prompts
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tempFile -Value $PromptText -Encoding UTF8 -NoNewline

        $OldErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"

        # Run from project root so opencode can see the full codebase
        Push-Location $ProjectRoot

        # Use 'opencode run' for non-interactive execution, reading prompt from file
        $promptContent = Get-Content $tempFile -Raw
        opencode run --model $Model $promptContent
        $exitCode = $LASTEXITCODE

        Pop-Location

        $ErrorActionPreference = $OldErrorActionPreference
        return $exitCode
    } finally {
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        }
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
        Write-Host "  Prompt:  " -NoNewline; Write-Host "$(Split-Path -Leaf $promptInfo.Path) (Template Fallback)" -ForegroundColor Yellow
    } else {
        Write-Host "  Prompt:  " -NoNewline; Write-Host (Split-Path -Leaf $promptInfo.Path) -ForegroundColor Green
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

        # Run OpenCode with the prompt content (non-interactive, one-shot)
        $exitCode = Invoke-OpenCode -PromptText $promptInfo.Content -Model $Model
        if ($exitCode -ne 0) {
            Write-Host "opencode exited with code $exitCode" -ForegroundColor Yellow
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
        Write-Host "  Prompt:  " -NoNewline; Write-Host "$(Split-Path -Leaf $promptInfo.Path) (Template Fallback)" -ForegroundColor Yellow
    } else {
        Write-Host "  Prompt:  " -NoNewline; Write-Host (Split-Path -Leaf $promptInfo.Path) -ForegroundColor Green
    }

    Write-Host "  Branch:  " -NoNewline; Write-Host $currentBranch -ForegroundColor Green
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host ""

    $exitCode = Invoke-OpenCode -PromptText $promptInfo.Content -Model $Model
    if ($exitCode -ne 0) {
        Write-Host "opencode exited with code $exitCode" -ForegroundColor Yellow
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
    Write-Host "Retrieving available models from OpenCode CLI..." -ForegroundColor Cyan
    $availableModels = Get-OpenCodeModels
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
