param(
  [string]$HostName = "connect.westb.seetacloud.com",
  [int]$Port = 19498,
  [string]$User = "root",
  [string]$Package = "DN-baselines-lite.tar.gz",
  [string]$RemoteTmp = "/root/autodl-tmp"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $Package)) {
  throw "Package not found: $Package. Create it from the repo root before uploading."
}

$target = "${User}@${HostName}"
ssh -p $Port -o StrictHostKeyChecking=no $target "mkdir -p $RemoteTmp/DN $RemoteTmp/hf_cache $RemoteTmp/outputs $RemoteTmp/logs"
scp -P $Port -o StrictHostKeyChecking=no $Package "${target}:${RemoteTmp}/DN-baselines-lite.tar.gz"
ssh -p $Port -o StrictHostKeyChecking=no $target "cd $RemoteTmp && rm -rf DN/baselines DN/scripts/baselines && tar -xzf DN-baselines-lite.tar.gz -C DN && chmod +x DN/scripts/baselines/*.sh && echo UPLOAD_OK"

Write-Host "Uploaded and unpacked to ${target}:${RemoteTmp}/DN"
Write-Host "Next remote command:"
Write-Host "cd ${RemoteTmp}/DN && bash scripts/baselines/remote_autodl_setup.sh"
