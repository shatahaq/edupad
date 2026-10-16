$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetDir = Join-Path $PSScriptRoot '../public/assets/office'
$outputDir = Join-Path $assetDir 'furniture-muted'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$source = [System.Drawing.Bitmap]::FromFile((Join-Path $assetDir 'furniture-muted-source-v1.png'))
# Isolate each complete object, including silhouettes wider than a nominal atlas cell.
# Coordinates are fractions of the inspected 1254px source; no distortion or recoloring.
$regions = @(
  @(0,80,365,245), @(367,90,269,235), @(640,90,292,235), @(942,90,310,235),
  @(0,360,365,260), @(370,370,315,250), @(720,340,160,285), @(945,370,309,255),
  @(75,635,180,285), @(390,660,160,255), @(630,660,300,255), @(1000,665,200,250),
  @(20,940,325,270), @(390,920,145,290), @(580,940,355,280), @(950,975,304,235)
)
try {
  for ($i=0; $i -lt $regions.Count; $i++) {
    $r=$regions[$i]; $ratio=$source.Width / 1254.0
    $x=[int]($r[0]*$ratio); $y=[int]($r[1]*$ratio)
    $right=[Math]::Min($source.Width,[int](($r[0]+$r[2])*$ratio))
    $bottom=[Math]::Min($source.Height,[int](($r[1]+$r[3])*$ratio))
    $minX=$right; $minY=$bottom; $maxX=$x; $maxY=$y
    for($py=$y;$py -lt $bottom;$py++){ for($px=$x;$px -lt $right;$px++){
      if($source.GetPixel($px,$py).A -gt 24){
        $minX=[Math]::Min($minX,$px); $minY=[Math]::Min($minY,$py)
        $maxX=[Math]::Max($maxX,$px); $maxY=[Math]::Max($maxY,$py)
      }
    }}
    $rect=New-Object System.Drawing.Rectangle $minX,$minY,($maxX-$minX+1),($maxY-$minY+1)
    $sprite=$source.Clone($rect,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try { $sprite.Save((Join-Path $outputDir "$i.png"),[System.Drawing.Imaging.ImageFormat]::Png) }
    finally { $sprite.Dispose() }
    Write-Host "$i $($rect.Width)x$($rect.Height)"
  }
} finally { $source.Dispose() }
