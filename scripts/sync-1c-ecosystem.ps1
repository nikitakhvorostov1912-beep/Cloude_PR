# Sync 1С-экосистемы между working copy (~/.claude) и SoT (claude-1c-toolkit)
#
# Usage:
#   .\sync-1c-ecosystem.ps1 -Mode Diff          # показать различия (default, read-only)
#   .\sync-1c-ecosystem.ps1 -Mode Push -Force   # global → toolkit (зафиксировать локальные правки)
#   .\sync-1c-ecosystem.ps1 -Mode Pull -Force   # toolkit → global (раскатить SoT)
#   .\sync-1c-ecosystem.ps1 -DryRun             # симуляция (только Push/Pull)
#
# Файлы для синхронизации (только 1С-экосистема):
#   agents/1c-*.md
#   rules/1c/*.md, rules/knowledge-router.md
#   skills/1c-*, skills/cf*/, skills/cfe-*, skills/form-*, skills/skd-*, skills/db-*,
#     skills/meta-*, skills/role-*, skills/mxl-*, skills/epf-*, skills/erf-*,
#     skills/subsystem-*, skills/bsl-lint, skills/bsp-patterns, skills/bpmn-diagram
#   hooks-handlers-1c/*.sh

param(
    [ValidateSet('Diff', 'Push', 'Pull')]
    [string]$Mode = 'Diff',
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Global = "$env:USERPROFILE\.claude"
$Toolkit = "C:\CLOUDE_PR\claude-1c-toolkit"

if (-not (Test-Path $Toolkit)) {
    Write-Error "Toolkit не найден: $Toolkit"
    exit 1
}

# 1С-специфичные пути для синхронизации
$Targets = @(
    @{ Src = "agents"; Pattern = "1c-*.md" },
    @{ Src = "rules\1c"; Pattern = "*.md" },
    @{ Src = "rules"; Pattern = "knowledge-router.md" },
    @{ Src = "hooks-handlers-1c"; Pattern = "*.sh" }
)

# Скиллы — папки целиком
$SkillPrefixes = @('1c-', 'cf-', 'cfe-', 'form-', 'skd-', 'db-', 'meta-', 'role-', 'mxl-', 'epf-', 'erf-', 'subsystem-')
$SkillExtra = @('bsl-lint', 'bsp-patterns', 'bpmn-diagram', 'help-add', 'img-grid', 'inspect', 'interface-edit', 'interface-validate', 'template-add', 'web-info', 'web-publish', 'web-stop', 'web-test', 'web-unpublish', 'erp-configuration-advisor', 'gap-analysis', 'kafka-1c-adapter', 'process-extraction', 'requirements-list', 'to-be-optimization', 'validate', 'write-1c-skill')

function Get-MatchingSkills {
    param([string]$Root)
    $result = @()
    foreach ($prefix in $SkillPrefixes) {
        $result += Get-ChildItem -Path "$Root\skills" -Directory -Filter "$prefix*" -ErrorAction SilentlyContinue
    }
    foreach ($name in $SkillExtra) {
        $path = Join-Path "$Root\skills" $name
        if (Test-Path $path) { $result += Get-Item $path }
    }
    $result | Sort-Object Name -Unique
}

function Show-Diff {
    Write-Host "=== Diff: $Global vs $Toolkit ===" -ForegroundColor Cyan
    foreach ($t in $Targets) {
        $srcDir = Join-Path $Global $t.Src
        $dstDir = Join-Path $Toolkit $t.Src
        if (-not (Test-Path $srcDir)) { continue }
        Get-ChildItem -Path $srcDir -Filter $t.Pattern -ErrorAction SilentlyContinue | ForEach-Object {
            $dst = Join-Path $dstDir $_.Name
            if (-not (Test-Path $dst)) {
                Write-Host "  [NEW in working]  $($t.Src)\$($_.Name)" -ForegroundColor Yellow
            } elseif ((Get-FileHash $_.FullName).Hash -ne (Get-FileHash $dst).Hash) {
                Write-Host "  [DIFFERS]         $($t.Src)\$($_.Name)" -ForegroundColor Magenta
            }
        }
    }
    Write-Host "--- skills ---"
    foreach ($skill in Get-MatchingSkills $Global) {
        $dst = Join-Path "$Toolkit\skills" $skill.Name
        if (-not (Test-Path $dst)) {
            Write-Host "  [NEW skill]       $($skill.Name)" -ForegroundColor Yellow
        }
    }
}

function Sync-Files {
    param([string]$From, [string]$To)
    foreach ($t in $Targets) {
        $srcDir = Join-Path $From $t.Src
        $dstDir = Join-Path $To $t.Src
        if (-not (Test-Path $srcDir)) { continue }
        if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
        Get-ChildItem -Path $srcDir -Filter $t.Pattern -ErrorAction SilentlyContinue | ForEach-Object {
            $dst = Join-Path $dstDir $_.Name
            if ($DryRun) {
                Write-Host "  [DRY] copy $($_.Name) → $($t.Src)" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $_.FullName -Destination $dst -Force
                Write-Host "  $($t.Src)\$($_.Name)" -ForegroundColor Green
            }
        }
    }
    foreach ($skill in Get-MatchingSkills $From) {
        $dst = Join-Path "$To\skills" $skill.Name
        if ($DryRun) {
            Write-Host "  [DRY] copy skill $($skill.Name)" -ForegroundColor DarkGray
        } else {
            if (Test-Path $dst) { Remove-Item -Path $dst -Recurse -Force }
            Copy-Item -Path $skill.FullName -Destination $dst -Recurse -Force
            Write-Host "  skills\$($skill.Name)" -ForegroundColor Green
        }
    }
}

switch ($Mode) {
    'Diff' { Show-Diff }
    'Push' {
        if (-not $Force) { Write-Error "Push требует -Force"; exit 1 }
        Write-Host "=== Push: working → toolkit ===" -ForegroundColor Cyan
        Sync-Files -From $Global -To $Toolkit
    }
    'Pull' {
        if (-not $Force) { Write-Error "Pull требует -Force"; exit 1 }
        Write-Host "=== Pull: toolkit → working ===" -ForegroundColor Cyan
        Sync-Files -From $Toolkit -To $Global
    }
}

Write-Host "`nDone." -ForegroundColor Cyan
