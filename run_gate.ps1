Set-Location "C:\CLOUDE_PR\projects\survey-automation\backend"
python scripts/delivery_gate.py "data/projects/ecb4ac19b44f49bb9da0ab72d817251a/"
Write-Host "Exit code: $LASTEXITCODE"
