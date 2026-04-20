Set-Location "C:\Users\zhang\Desktop\DN"
$log = "C:\Users\zhang\Desktop\DN\experiments\benchmark\standard_runs\server_off_5002.console.log"
"[$(Get-Date -Format o)] launch off 5002" | Out-File -FilePath $log -Encoding utf8
$env:PYTHONPATH = (Resolve-Path '.venv\Lib\site-packages').Path
$env:PREGENERATION_ENABLED = 'false'
$env:FLASK_ENV = 'production'
python -c "from game_server import app; app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False, threaded=True)" *>> $log
