# batch_outfits.ps1 — rig de TODAS as roupas Alice x anims, via apply_knobs (SHD).
# Cada combinacao roupa x anim = 1 GLB animado. Saida: work/out/<slug>_<anim>.glb
#
# Uso:
#   .\batch_outfits.ps1                     # todas roupas, anim idle+walk+attack
#   .\batch_outfits.ps1 -Anims idle         # so idle
#   .\batch_outfits.ps1 -Only dress         # so 1 roupa

[CmdletBinding()]
param(
  [string[]]$Anims = @("idle","walk","attack"),
  [string]$Only = ""
)
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$BLENDER = "D:\Blender Foundation\blender.exe"
$BODY    = "D:\Alice\tools\body-rebuild\out\alice_body_clean.fbx"
$APPLY   = "$PSScriptRoot\apply_knobs.py"
$OUT     = "$PSScriptRoot\work\out"
New-Item -ItemType Directory -Path $OUT -Force | Out-Null

# roupa slug -> FBX
$OUTFITS = [ordered]@{
  "alice-dress"      = "E:\References\3D\SK_AliceDress.fbx"
  "alice-cheshire"   = "E:\References\3D\SK_Alice_Cheshire.fbx"
  "alice-rainha"     = "E:\References\3D\SK_Alice_Rainha.fbx"
  "alice-chapeleiro" = "E:\References\3D\SK_Alice_Chapeleiro.fbx"
  "alice-coelho"     = "E:\References\3D\SK_Alice_Coelho.fbx"
  "alice-lagarta"    = "E:\References\3D\SK_Alice_Lagarta.fbx"
}
# anim key -> FBX
$ANIMMAP = @{
  "idle"   = "D:\model\anims\Standing Idle.fbx"
  "walk"   = "D:\model\anims\Walking.fbx"
  "attack" = "D:\model\anims\Standing Melee Attack Horizontal.fbx"
}

# knobs vencedores
$KNOBS = '{"arm_angle_x":35,"arm_scale":1.0,"skirt_to_hips":true,"dress_offset_z":0.0,"shd_res":110,"hide_body_under":true,"hide_dist":0.03}'
$kfile = "$PSScriptRoot\work\knobs.json"
Set-Content -Path $kfile -Value $KNOBS -Encoding UTF8

$results = @()
foreach ($slug in $OUTFITS.Keys) {
  if ($Only -and $slug -ne $Only) { continue }
  $outfit = $OUTFITS[$slug]
  if (-not (Test-Path $outfit)) { Write-Host "SKIP $slug (sem $outfit)"; continue }
  foreach ($ak in $Anims) {
    $anim = $ANIMMAP[$ak]
    $glb  = "$OUT\${slug}_${ak}.glb"
    Write-Host "=== $slug + $ak ==="
    $log = "$OUT\${slug}_${ak}.log"
    & $BLENDER -b --python $APPLY -- $kfile $glb "body=$BODY" "outfit=$outfit" "anim=$anim" *> $log
    if (Test-Path $glb) {
      $mb = [math]::Round((Get-Item $glb).Length/1MB,1)
      Write-Host "   OK ${mb}MB"
      $results += [pscustomobject]@{slug=$slug;anim=$ak;mb=$mb;ok=$true}
    } else {
      Write-Host "   FALHOU (ver $log)"
      $results += [pscustomobject]@{slug=$slug;anim=$ak;mb=0;ok=$false}
    }
  }
}
Write-Host "`n=== RESUMO ==="
$results | Format-Table -Auto | Out-String | Write-Host
"total GLB: $(($results | Where-Object ok).Count)/$($results.Count)"
"total MB:  $([math]::Round((Get-ChildItem $OUT -Filter *.glb | Measure-Object Length -Sum).Sum/1MB,1))"
