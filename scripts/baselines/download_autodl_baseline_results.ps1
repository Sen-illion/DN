param(
  [string]$HostName = "connect.westb.seetacloud.com",
  [int]$Port = 19498,
  [string]$User = "root",
  [string]$RemoteOutputs = "/root/autodl-tmp/outputs",
  [string]$LocalDir = "remote_baseline_results"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$target = "${User}@${HostName}"
$remotePackage = "/root/autodl-tmp/DN-baseline-results-lite.tar.gz"

ssh -p $Port -o StrictHostKeyChecking=no $target @"
set -e
cd /root/autodl-tmp
rm -f DN-baseline-results-lite.tar.gz
tar -czf DN-baseline-results-lite.tar.gz \
  --ignore-failed-read \
  --exclude='*.ckpt' \
  --exclude='*.safetensors' \
  --exclude='*.bin' \
  --exclude='*.pt' \
  outputs
"@

scp -P $Port -o StrictHostKeyChecking=no "${target}:${remotePackage}" "$LocalDir/DN-baseline-results-lite.tar.gz"
tar -xzf "$LocalDir/DN-baseline-results-lite.tar.gz" -C $LocalDir

Write-Host "Downloaded baseline results to $LocalDir"
