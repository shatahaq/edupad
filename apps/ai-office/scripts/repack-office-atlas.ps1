param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$sourcePath = (Resolve-Path -LiteralPath $InputPath).Path
$outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
$source = [System.Drawing.Bitmap]::FromFile($sourcePath)

try {
    if ($source.Width -ne 1254 -or $source.Height -ne 1254) {
        throw "Atlas sumber harus berukuran 1254x1254, ditemukan $($source.Width)x$($source.Height)."
    }

    # Split points sit in the transparent valleys between generated objects, not at the
    # original 313.5 px mathematical boundaries that caused neighboring sprites to leak.
    $xBounds = @(0, 348, 665, 948, 1254)
    $yBounds = @(0, 330, 660, 945, 1254)
    $cellSize = 384
    $canvasSize = $cellSize * 4
    $safeInset = 26
    $alphaThreshold = 8

    $output = [System.Drawing.Bitmap]::new(
        $canvasSize,
        $canvasSize,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    )

    try {
        $graphics = [System.Drawing.Graphics]::FromImage($output)
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half

            for ($row = 0; $row -lt 4; $row += 1) {
                for ($column = 0; $column -lt 4; $column += 1) {
                    $left = $source.Width
                    $top = $source.Height
                    $right = -1
                    $bottom = -1

                    for ($y = $yBounds[$row]; $y -lt $yBounds[$row + 1]; $y += 1) {
                        for ($x = $xBounds[$column]; $x -lt $xBounds[$column + 1]; $x += 1) {
                            if ($source.GetPixel($x, $y).A -gt $alphaThreshold) {
                                if ($x -lt $left) { $left = $x }
                                if ($x -gt $right) { $right = $x }
                                if ($y -lt $top) { $top = $y }
                                if ($y -gt $bottom) { $bottom = $y }
                            }
                        }
                    }

                    if ($right -lt $left -or $bottom -lt $top) {
                        throw "Tidak ada objek pada sel row=$row column=$column."
                    }

                    $sourceWidth = $right - $left + 1
                    $sourceHeight = $bottom - $top + 1
                    $maximumSize = $cellSize - (2 * $safeInset)
                    $scale = [Math]::Min(1.0, [Math]::Min($maximumSize / $sourceWidth, $maximumSize / $sourceHeight))
                    $targetWidth = [Math]::Max(1, [int][Math]::Round($sourceWidth * $scale))
                    $targetHeight = [Math]::Max(1, [int][Math]::Round($sourceHeight * $scale))
                    $targetX = ($column * $cellSize) + [int][Math]::Floor(($cellSize - $targetWidth) / 2)
                    $targetY = ($row * $cellSize) + [int][Math]::Floor(($cellSize - $targetHeight) / 2)

                    $sourceRectangle = [System.Drawing.Rectangle]::new($left, $top, $sourceWidth, $sourceHeight)
                    $targetRectangle = [System.Drawing.Rectangle]::new($targetX, $targetY, $targetWidth, $targetHeight)
                    $graphics.DrawImage($source, $targetRectangle, $sourceRectangle, [System.Drawing.GraphicsUnit]::Pixel)

                    [PSCustomObject]@{
                        Frame = ($row * 4) + $column
                        Source = "$sourceWidth x $sourceHeight"
                        Output = "$targetWidth x $targetHeight"
                        MarginX = [int][Math]::Floor(($cellSize - $targetWidth) / 2)
                        MarginY = [int][Math]::Floor(($cellSize - $targetHeight) / 2)
                    }
                }
            }
        }
        finally {
            $graphics.Dispose()
        }

        $output.Save($outputFullPath, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $output.Dispose()
    }
}
finally {
    $source.Dispose()
}
