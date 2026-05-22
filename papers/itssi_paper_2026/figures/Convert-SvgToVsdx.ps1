<#
.SYNOPSIS
    Converts SVG files to Microsoft Visio (.vsdx) using local Microsoft Visio's
    built-in SVG importer, driven over COM Interop.

.DESCRIPTION
    For each input SVG file, opens it invisibly in Visio via COM Interop, saves
    as .vsdx next to the source, then closes. This is the same approach used by
    deonvz/ConvertSVGtoVisio on GitHub, but written in PowerShell so no C#
    build, .msi installer, or third-party tool is required.

    Visio is invoked headless (Visible = False) and quitted at the end. Each
    file is opened with the visOpenHidden + visOpenRO flags (= 64 + 2 = 66) so
    Visio does not flash any windows during the batch.

    REQUIREMENTS
    - Windows (the Visio.Application COM server is Windows-only).
    - Microsoft Visio installed locally; any edition since Visio 2016 has a
      working SVG importer (Standard, Professional, or Office 365 Plan 1 / 2).
    - PowerShell 5.1+ (built into Windows 10/11) or PowerShell 7+.

    NOT SUPPORTED ON macOS / LINUX
    No COM Visio server exists outside Windows, so this script cannot run on
    macOS even with .NET / PowerShell Core installed. Run it on a Windows
    machine with Visio, then copy the resulting *.vsdx files back.

.PARAMETER Files
    Explicit list of SVG paths to convert. Relative paths resolve against the
    current working directory.

.PARAMETER All
    Convert every *.svg in the current directory.

.EXAMPLE
    # Default: convert the three ITSSI 2026 paper figures sitting in this folder
    .\Convert-SvgToVsdx.ps1

.EXAMPLE
    # Convert a single named file
    .\Convert-SvgToVsdx.ps1 -Files fig_1_pipeline.svg

.EXAMPLE
    # Batch-convert every SVG present in the current directory
    .\Convert-SvgToVsdx.ps1 -All

.NOTES
    Round-trip expectation
    - Times New Roman, Courier New: stock Windows fonts, survive cleanly.
    - Plain shapes (ellipse, rectangle, line) and arrows: survive cleanly.
    - Fig 2 contains one embedded raster (the 100x100 MNIST digit "7" PNG);
      Visio imports embedded raster sub-images as raster shapes, expected.
    - After conversion, eyeball-check the .vsdx in Visio: font, label
      positions, line strokes. Re-export from draw.io if anything drifts.

    Reference
    - VisOpenSaveAs enum used here:
      visOpenRO = 2, visOpenHidden = 64. Combined value 66 opens the doc
      hidden + read-only so Visio neither flashes a window nor marks the SVG
      as modified during the SaveAs.
#>

[CmdletBinding(DefaultParameterSetName = 'Default')]
param(
    [Parameter(ParameterSetName = 'Files', Position = 0)]
    [string[]]$Files,

    [Parameter(ParameterSetName = 'All')]
    [switch]$All
)

# Resolve the list of SVG paths to convert based on which parameter set the user picked
switch ($PSCmdlet.ParameterSetName) {
    'All' {
        $targets = Get-ChildItem -Path . -Filter '*.svg' | ForEach-Object { $_.FullName }
    }
    'Files' {
        $targets = $Files | ForEach-Object {
            $resolved = Resolve-Path -Path $_ -ErrorAction SilentlyContinue
            if ($resolved) { $resolved.Path }
            else           { Write-Warning "Not found: $_"; $null }
        }
    }
    default {
        # No args -> the three ITSSI 2026 figure SVGs in the current folder
        $defaults = @('fig_1_pipeline.svg', 'fig_2_digit7_graph.svg', 'fig_3_concept_7_1.svg')
        $targets = $defaults | ForEach-Object {
            $resolved = Resolve-Path -Path $_ -ErrorAction SilentlyContinue
            if ($resolved) { $resolved.Path }
            else           { Write-Warning "Not found (skipping): $_"; $null }
        }
    }
}

$targets = $targets | Where-Object { $_ }
if (-not $targets) {
    Write-Error 'No SVG files to convert. Run from the figures/ folder, or pass -Files / -All explicitly.'
    exit 1
}

# Start Visio over COM. This is the line that proves whether Visio is available.
try {
    $visio = New-Object -ComObject Visio.Application
}
catch {
    Write-Error @"
Cannot start the Visio COM server.
Make sure Microsoft Visio is installed on this Windows machine (any edition since Visio 2016).
Underlying error: $($_.Exception.Message)
"@
    exit 1
}

$visio.Visible = $false

# Visio open flags: hidden + read-only
$openFlags = 64 + 2

$results = @()
foreach ($svg in $targets) {
    $vsdx = [System.IO.Path]::ChangeExtension($svg, '.vsdx')
    Write-Host ("  {0,-32} -> {1}" -f (Split-Path -Leaf $svg), (Split-Path -Leaf $vsdx))
    try {
        $doc = $visio.Documents.OpenEx($svg, $openFlags)
        $doc.SaveAs($vsdx)
        $doc.Close()
        $results += [pscustomobject]@{
            File   = (Split-Path -Leaf $svg)
            Status = 'ok'
            Out    = (Split-Path -Leaf $vsdx)
        }
    }
    catch {
        Write-Warning ("Conversion failed for {0}: {1}" -f $svg, $_.Exception.Message)
        $results += [pscustomobject]@{
            File   = (Split-Path -Leaf $svg)
            Status = 'error'
            Out    = ''
        }
    }
}

# Cleanup: quit Visio, release COM references so the process actually exits
$visio.Quit()
[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($visio)
[GC]::Collect()
[GC]::WaitForPendingFinalizers()

Write-Host ''
Write-Host 'Summary:' -ForegroundColor Cyan
$results | Format-Table -AutoSize

# Exit with non-zero status if any file failed (useful in CI)
if ($results | Where-Object { $_.Status -ne 'ok' }) {
    exit 2
}
