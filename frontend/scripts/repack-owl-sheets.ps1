param(
    [string]$AssetDirectory = (Join-Path $PSScriptRoot "..\public\assets\agents\owls"),
    [int]$FrameSize = 320
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$agentNames = @("nova", "pixel", "sora", "tempo", "metric", "nexus", "koin")

foreach ($agentName in $agentNames) {
    $sourcePath = Join-Path $AssetDirectory "$agentName-owl-v1.png"
    $targetPath = Join-Path $AssetDirectory "$agentName-owl-sheet-v1.png"
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Aset sumber tidak ditemukan: $sourcePath"
    }

    $source = [System.Drawing.Bitmap]::FromFile($sourcePath)
    try {
        $target = New-Object System.Drawing.Bitmap ($FrameSize * 4), ($FrameSize * 4), ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($target)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
                $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighSpeed
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::None

                for ($row = 0; $row -lt 4; $row++) {
                    for ($column = 0; $column -lt 4; $column++) {
                        $sourceLeft = [int][Math]::Round($column * $source.Width / 4.0)
                        $sourceTop = [int][Math]::Round($row * $source.Height / 4.0)
                        $sourceRight = [int][Math]::Round(($column + 1) * $source.Width / 4.0)
                        $sourceBottom = [int][Math]::Round(($row + 1) * $source.Height / 4.0)
                        $sourceWidth = $sourceRight - $sourceLeft
                        $sourceHeight = $sourceBottom - $sourceTop
                        $offsetX = [int][Math]::Floor(($FrameSize - $sourceWidth) / 2.0)
                        $offsetY = [int][Math]::Floor(($FrameSize - $sourceHeight) / 2.0)
                        $destination = New-Object System.Drawing.Rectangle (($column * $FrameSize) + $offsetX), (($row * $FrameSize) + $offsetY), $sourceWidth, $sourceHeight
                        $sourceRectangle = New-Object System.Drawing.Rectangle $sourceLeft, $sourceTop, $sourceWidth, $sourceHeight
                        $graphics.DrawImage($source, $destination, $sourceRectangle, [System.Drawing.GraphicsUnit]::Pixel)
                    }
                }
            }
            finally {
                $graphics.Dispose()
            }
            $target.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $target.Dispose()
        }
    }
    finally {
        $source.Dispose()
    }

    Write-Host "[ok] $agentName -> $targetPath"
}
